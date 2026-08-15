"""GitSubprocessObjectReader — the ``GitObjectReader`` adapter for the push-range scan.

Implements ``core.protocols.git_object_reader.GitObjectReader`` over ``git rev-list
--objects`` + ``git cat-file`` (SPEC v0.9.0 FR1). Kept in a sibling file to
``git_subprocess.py`` rather than grown inside it — the two modules serve different
concerns (workspace-management git operations vs. the push-range object reader) and
``git_subprocess.py`` is already close to the size that would warrant a split
(PLAN v0.9.0 §2).

Every subprocess invocation in this module — including the batch calls that need
``input=`` — is routed through :func:`_run` so a timeout or a missing ``git`` executable
always surfaces as :class:`GitObjectReadError` (SPEC v0.9.0 FR6 row 2 / the port's own
contract, ``core/protocols/git_object_reader.py``: "Any git failure raises
GitObjectReadError rather than returning a partial/empty result") — never a raw,
unhandled exception at the push boundary (code-reviewer MEDIUM finding).
"""

from __future__ import annotations

import queue
import re
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import (
    ZERO_SHA,
    GitObjectReadError,
    ScannedObject,
)

_TIMEOUT_S = 30

#: FR7/A7.4 (v0.11.0) — the same sha-shape check the service layer's
#: ``parse_push_stdin`` applies (40-char SHA-1 or 64-char SHA-256 hex). Re-checked here
#: as a second, independent layer: this adapter must never interpolate an
#: option-shaped string into a git argv, regardless of what already validated the
#: caller's input (CWE-88).
_SHA_SHAPE_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

#: SPEC v0.9.0 R3 — a per-blob size guard so one pathological blob cannot dominate the
#: scan's wall clock or memory: a blob at or under this cap is read and decoded; a blob
#: over it is never fetched at all and is reported ``decodable=False`` (counted the same
#: way an undecodable binary blob is, FR6 row 3).
_MAX_BLOB_BYTES = 5 * 1024 * 1024  # 5 MB

#: SPEC v0.11.0 FR9/ADR D8 — the ``git cat-file --batch`` conversation is chunked so the
#: peak resident set is bounded by a CONSTANT (``chunk_size x cap``) rather than growing
#: with the size of the pushed range. 500 is the code-reviewer's suggested size and the
#: PLAN's recorded default (PLAN §5) — a measured rationale, not a tunable a test may
#: depend on the exact value of. FR2's prior-side lookup (T-110-09) rides the SAME chunk
#: loop, doubling the bound to ``chunk_size x cap x 2`` rather than adding a second,
#: unbounded pass.
_BATCH_CHUNK_SIZE = 500


def _run(
    args: list[str], cwd: Path, *, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a git subcommand, capturing raw bytes (never ``text=True`` — decoding is the
    caller's job, and content bytes may not be valid UTF-8 at all).

    ``input_bytes``, when given, is piped to stdin — the shape the batch commands need
    (``git cat-file --batch[-check]`` reads one object id per line from stdin). Every
    call site in this module goes through here so a timeout or missing-``git`` failure
    is always converted to the typed :class:`GitObjectReadError`, never left to escape
    as a raw ``subprocess`` exception.
    """
    try:
        return subprocess.run(
            args, cwd=cwd, input=input_bytes, capture_output=True, timeout=_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise GitObjectReadError(f"git is not available on PATH: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitObjectReadError(f"git command timed out: {' '.join(args)}") from exc


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _is_resolvable_commit(repo: Path, sha: str) -> bool:
    """True when *sha* resolves to a commit object reachable locally (FR1 row 1/2).

    v0.11.0 FR7/A7.4: *sha* is shape-checked against :data:`_SHA_SHAPE_RE` BEFORE it is
    ever interpolated into the ``git cat-file -e <sha>^{commit}`` argv — an
    option-shaped value (e.g. ``--upload-pack=...``) is rejected here, never
    interpolated, and the caller treats it as unresolvable (falls back to the
    ``--not --remotes`` range shape) rather than spawning git with that string
    embedded (CWE-88).
    """
    if not sha or sha == ZERO_SHA or not _SHA_SHAPE_RE.match(sha):
        return False
    result = _run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo)
    return result.returncode == 0


def _rev_list_candidates(repo: Path, local_sha: str, remote_sha: str) -> list[tuple[str, str]]:
    """Return ``(sha, path)`` pairs for every object with a path in the FR1 range —
    blobs AND trees (type filtering happens separately, in :func:`_blob_info`).

    v0.11.0 FR7/A7.4: the argv carries a trailing ``--`` end-of-options marker after
    the revision arguments on both range shapes, closing the git argv interpolation
    site (CWE-88/CWE-20).
    """
    if _is_resolvable_commit(repo, remote_sha):
        args = ["git", "rev-list", "--objects", local_sha, "--not", remote_sha, "--"]
    else:
        args = ["git", "rev-list", "--objects", local_sha, "--not", "--remotes", "--"]
    result = _run(args, repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git rev-list --objects failed: {_decode(result.stderr).strip()}")
    entries: list[tuple[str, str]] = []
    for raw_line in _decode(result.stdout).splitlines():
        if not raw_line:
            continue
        sha, _, path = raw_line.partition(" ")
        if path:
            entries.append((sha, path))
    return entries


def _blob_info(repo: Path, candidates: list[tuple[str, str]]) -> dict[str, tuple[str, int]]:
    """Return ``{sha: (first-seen path, size)}`` restricted to the candidates that are
    blobs.

    ``git rev-list --objects`` also emits trees with a path (directory names) — this
    filters those out, and reads each blob's size in the same pass, via a single
    batched ``git cat-file --batch-check`` call rather than one subprocess per
    candidate. The size is what lets :func:`_read_blobs` apply the oversized-blob guard
    (R3) BEFORE ever fetching an oversized blob's content.
    """
    if not candidates:
        return {}
    stdin_payload = ("\n".join(sha for sha, _ in candidates) + "\n").encode("utf-8")
    result = _run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        repo,
        input_bytes=stdin_payload,
    )
    if result.returncode != 0:
        raise GitObjectReadError(
            f"git cat-file --batch-check failed: {_decode(result.stderr).strip()}"
        )
    blob_sizes: dict[str, int] = {}
    for line in _decode(result.stdout).splitlines():
        parts = line.split()
        if len(parts) != 3 or parts[1] != "blob":
            continue
        sha, size_str = parts[0], parts[2]
        try:
            blob_sizes[sha] = int(size_str)
        except ValueError:
            continue
    info: dict[str, tuple[str, int]] = {}
    for sha, path in candidates:
        if sha in blob_sizes and sha not in info:
            info[sha] = (path, blob_sizes[sha])
    return info


def _read_blob_chunk(
    repo: Path, chunk_shas: list[str], blob_info: dict[str, tuple[str, int]]
) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *chunk_shas*, via a SINGLE batched
    ``git cat-file --batch`` conversation scoped to just this chunk.

    v0.11.0 FR8/A8.1-A8.2: the header-parse pair (the newline lookup and the size-field
    conversion) is wrapped so a truncated stream or a non-numeric size field surfaces as
    the module's typed :class:`GitObjectReadError` instead of a raw ``ValueError``
    escaping past the module's contract. A desynchronised header shape (``len(parts) !=
    3``) raises the SAME typed error rather than yielding a fabricated
    ``decodable=False`` object and continuing: after a desync, ``pos`` points into
    content bytes and every later header parse is garbage — a stream of fabricated
    objects silently counted as binary skips. A gate that has lost sync with git's
    stream aborts; it does not invent.
    """
    stdin_payload = ("\n".join(chunk_shas) + "\n").encode("utf-8")
    result = _run(["git", "cat-file", "--batch"], repo, input_bytes=stdin_payload)
    if result.returncode != 0:
        raise GitObjectReadError(f"git cat-file --batch failed: {_decode(result.stderr).strip()}")

    out = result.stdout
    pos = 0
    for sha in chunk_shas:
        path, size = blob_info[sha]
        try:
            newline_idx = out.index(b"\n", pos)
            header = out[pos:newline_idx].decode("utf-8", errors="replace")
            pos = newline_idx + 1
            parts = header.split()
            if len(parts) != 3:
                raise ValueError(f"unexpected header shape {header!r}")
            obj_sha, _obj_type, size_str = parts
            content_size = int(size_str)
        except ValueError as exc:
            raise GitObjectReadError(
                f"git cat-file --batch stream desynchronised at object {sha}: {exc}"
            ) from exc
        content = out[pos : pos + content_size]
        pos += content_size + 1  # skip the trailing newline after the content block
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            yield ScannedObject(path=path, sha=obj_sha, text="", decodable=False)
            continue
        yield ScannedObject(path=path, sha=obj_sha, text=text, decodable=True)


def _read_oversized_blob_prefix(repo: Path, sha: str) -> bytes:
    """Read at most :data:`_MAX_BLOB_BYTES` of *sha*'s content through a SEPARATE,
    bounded per-object stream, then close it early (SPEC v0.11.0 FR4/ADR D2-a).

    This call deliberately does NOT go through :func:`_run`: closing the pipe before
    git has finished writing makes a non-zero exit / broken-pipe outcome EXPECTED on
    THIS call only, and ``_run``'s contract is to convert every subprocess failure into
    :class:`GitObjectReadError` — which would misreport this intentional early close as
    a git failure. git genuinely never produces the remainder once the pipe is closed,
    so v0.9.0's R3 "never fetched" property holds for the truncated tail exactly as
    before; only the DECISION of what to do with the (now non-empty) prefix changed.

    A missing ``git`` executable, or the read exceeding :data:`_TIMEOUT_S` with no
    prefix delivered, still raises :class:`GitObjectReadError` — the bound is on the
    NORMAL, expected-success path only, not on genuine git/environment failure.
    """
    try:
        proc = subprocess.Popen(  # noqa: S603 — fixed argv, no shell
            ["git", "cat-file", "blob", sha],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise GitObjectReadError(f"git is not available on PATH: {exc}") from exc

    result_q: queue.Queue[bytes | Exception] = queue.Queue(maxsize=1)

    def _reader() -> None:
        try:
            assert proc.stdout is not None
            result_q.put(proc.stdout.read(_MAX_BLOB_BYTES))
        except Exception as exc:  # noqa: BLE001 — surfaced via the queue, never re-raised bare
            result_q.put(exc)

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()
    try:
        outcome: bytes | Exception | None
        try:
            outcome = result_q.get(timeout=_TIMEOUT_S)
        except queue.Empty:
            outcome = None
    finally:
        # Close the read end and terminate now — this is the deliberate EARLY CLOSE:
        # git will see EPIPE/SIGPIPE on its next write and exit non-zero, which is
        # EXPECTED here and is never inspected or converted into an error.
        if proc.stdout is not None:
            proc.stdout.close()
        proc.terminate()
        try:
            proc.wait(timeout=_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if outcome is None:
        raise GitObjectReadError(f"git cat-file blob timed out reading oversized object {sha}")
    if isinstance(outcome, Exception):
        raise GitObjectReadError(
            f"git cat-file blob failed reading oversized object {sha}: {outcome}"
        ) from outcome
    return outcome


def _read_oversized_blob(repo: Path, sha: str, path: str, size: int) -> ScannedObject:
    """Build the :class:`ScannedObject` for one oversized blob (SPEC v0.11.0 FR4).

    The scanned prefix is decoded ``errors="strict"`` (PLAN §5): a truncation that
    happens to land mid-multi-byte-character is honestly reported as undecodable
    (A4.6) rather than silently repaired — the matcher then falls back to the SAME
    binary skip class as any other undecodable blob (denylist_scan.scan_objects).
    """
    prefix = _read_oversized_blob_prefix(repo, sha)
    try:
        text = prefix.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ScannedObject(
            path=path,
            sha=sha,
            text="",
            decodable=False,
            oversized=True,
            size_bytes=size,
            scanned_bytes=len(prefix),
        )
    return ScannedObject(
        path=path,
        sha=sha,
        text=text,
        decodable=True,
        oversized=True,
        size_bytes=size,
        scanned_bytes=len(prefix),
    )


def _read_blobs(repo: Path, blob_info: dict[str, tuple[str, int]]) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *blob_info*.

    Content is read via batched ``git cat-file --batch`` conversations, chunked to
    :data:`_BATCH_CHUNK_SIZE` blobs per call (SPEC v0.11.0 FR9/ADR D8) — one subprocess
    per CHUNK, not one per blob (code-reviewer MEDIUM finding; mirrors the batching
    pattern :func:`_blob_info` already uses) and NOT one whole-range subprocess whose
    output buffer grows unbounded with the range size. A blob over
    :data:`_MAX_BLOB_BYTES` is EXCLUDED from every batch conversation entirely — the
    single-conversation win is preserved for the under-cap population — and is instead
    read through :func:`_read_oversized_blob`'s separate, bounded per-object stream
    (SPEC v0.11.0 FR4, supersedes the v0.9.0 total-blind-spot skip): its first cap
    bytes are scanned and it is reported ``decodable=True``/``oversized=True`` when
    that prefix is valid UTF-8, or ``decodable=False``/``oversized=True`` otherwise
    (A4.6) — the remainder past the cap is genuinely never fetched either way.
    """
    fetch_shas = [sha for sha, (_, size) in blob_info.items() if size <= _MAX_BLOB_BYTES]
    oversized_shas = [sha for sha, (_, size) in blob_info.items() if size > _MAX_BLOB_BYTES]

    for sha in oversized_shas:
        path, size = blob_info[sha]
        yield _read_oversized_blob(repo, sha, path, size)

    for start in range(0, len(fetch_shas), _BATCH_CHUNK_SIZE):
        chunk = fetch_shas[start : start + _BATCH_CHUNK_SIZE]
        yield from _read_blob_chunk(repo, chunk, blob_info)


class GitSubprocessObjectReader:
    """Subprocess-backed ``GitObjectReader`` (SPEC v0.9.0 FR1/FR7 injected port)."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        candidates = _rev_list_candidates(repo, local_sha, remote_sha)
        blob_info = _blob_info(repo, candidates)
        yield from _read_blobs(repo, blob_info)
