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

import contextlib
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


def _rev_list_candidates(repo: Path, local_sha: str, base: str | None) -> list[tuple[str, str]]:
    """Return ``(sha, path)`` pairs for every object with a path in the FR1 range —
    blobs AND trees (type filtering happens separately, in :func:`_blob_info`).

    *base* is the ALREADY-RESOLVED base (SPEC v0.11.0 FR2 — ``None`` means the
    fallback shape): resolution happens ONCE, in :meth:`GitSubprocessObjectReader.new_objects`,
    and is reused here AND for the prior-side lookup, rather than being re-derived.

    v0.11.0 FR7/A7.4: the argv carries a trailing ``--`` end-of-options marker after
    the revision arguments on both range shapes, closing the git argv interpolation
    site (CWE-88/CWE-20).
    """
    if base is not None:
        args = ["git", "rev-list", "--objects", local_sha, "--not", base, "--"]
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


def _resolve_prior_texts(repo: Path, base: str, paths: list[str]) -> dict[str, str]:
    """Resolve the published prior text of every DISTINCT path in *paths*, at *base*
    (SPEC v0.11.0 FR2, rides the SAME chunk this is called from).

    Two batched calls, on the SAME shape the content read already uses:

    1. ``git cat-file --batch-check`` fed ``<base>:<path>`` lines — this both filters
       non-existent paths (git answers ``<spec> missing``) and supplies the size, so
       the cap is applied BEFORE any prior content is fetched. ``--batch-check``
       preserves stdin ORDER in its output (one line per input line), which is how
       each output line is correlated back to its requesting path — the returned
       ``%(objectname)`` is the PRIOR BLOB's sha, not the ``<base>:<path>`` spec, so
       content-based correlation is not available here (unlike :func:`_blob_info`,
       which correlates by the requested blob sha itself).
    2. ``git cat-file --batch`` for the under-cap survivors — full content, never
       truncated (already filtered to under-cap sizes).

    A path missing from the returned dict has NO prior content — never mapped to an
    empty string, which would silently amnesty nothing but would also hide the
    distinction (over-cap / undecodable / genuinely absent) from a future reader.
    """
    if not paths:
        return {}
    unique_paths = list(dict.fromkeys(paths))
    check_stdin = ("\n".join(f"{base}:{path}" for path in unique_paths) + "\n").encode("utf-8")
    check_result = _run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        repo,
        input_bytes=check_stdin,
    )
    if check_result.returncode != 0:
        raise GitObjectReadError(
            "git cat-file --batch-check failed resolving prior content: "
            f"{_decode(check_result.stderr).strip()}"
        )
    check_lines = _decode(check_result.stdout).splitlines()
    if len(check_lines) != len(unique_paths):
        raise GitObjectReadError(
            "git cat-file --batch-check desynchronised resolving prior content "
            f"(expected {len(unique_paths)} line(s), got {len(check_lines)})"
        )

    under_cap: dict[str, int] = {}
    for path, line in zip(unique_paths, check_lines, strict=True):
        parts = line.split()
        if len(parts) != 3:
            continue  # "<base>:<path> missing" (or any non-3-field line) -> absence
        _sha, obj_type, size_str = parts
        # code-reviewer LOW finding (v0.11.0 pre-PR review): a path that was a
        # DIRECTORY at the base resolves to its TREE object, not a blob — only
        # objecttype "blob" may ever supply prior text; anything else (tree, or any
        # future object kind) is treated exactly like a missing path, never fetched.
        if obj_type != "blob":
            continue
        try:
            size = int(size_str)
        except ValueError:
            continue
        if size <= _MAX_BLOB_BYTES:
            under_cap[path] = size

    if not under_cap:
        return {}

    fetch_paths = list(under_cap)
    fetch_stdin = ("\n".join(f"{base}:{path}" for path in fetch_paths) + "\n").encode("utf-8")
    batch_result = _run(["git", "cat-file", "--batch"], repo, input_bytes=fetch_stdin)
    if batch_result.returncode != 0:
        raise GitObjectReadError(
            "git cat-file --batch failed resolving prior content: "
            f"{_decode(batch_result.stderr).strip()}"
        )

    out = batch_result.stdout
    pos = 0
    prior_texts: dict[str, str] = {}
    for path in fetch_paths:
        try:
            newline_idx = out.index(b"\n", pos)
            header = out[pos:newline_idx].decode("utf-8", errors="replace")
            pos = newline_idx + 1
            parts = header.split()
            if len(parts) != 3:
                raise ValueError(f"unexpected header shape {header!r}")
            _obj_sha, _obj_type, size_str = parts
            content_size = int(size_str)
        except ValueError as exc:
            raise GitObjectReadError(
                "git cat-file --batch stream desynchronised resolving prior content "
                f"for path {path!r}: {exc}"
            ) from exc
        content = out[pos : pos + content_size]
        pos += content_size + 1  # skip the trailing newline after the content block
        # Undecodable prior blob -> absence, never a partial/garbled string.
        with contextlib.suppress(UnicodeDecodeError):
            prior_texts[path] = content.decode("utf-8")
    return prior_texts


def _read_blob_chunk(
    repo: Path,
    chunk_shas: list[str],
    blob_info: dict[str, tuple[str, int]],
    prior_texts: dict[str, str],
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

    v0.11.0 FR2: *prior_texts* (already resolved for this chunk's distinct paths, or
    empty in the fallback shape) supplies each yielded object's ``prior_text`` — a
    lookup miss maps to the explicit absence ``None``, never an empty string.
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
        prior_text = prior_texts.get(path)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            yield ScannedObject(
                path=path, sha=obj_sha, text="", decodable=False, prior_text=prior_text
            )
            continue
        yield ScannedObject(
            path=path, sha=obj_sha, text=text, decodable=True, prior_text=prior_text
        )


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


def _read_blobs(
    repo: Path, blob_info: dict[str, tuple[str, int]], base: str | None
) -> Iterator[ScannedObject]:
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

    v0.11.0 FR2/ADR D8: with *base* resolved, each CHUNK's prior-side lookup
    (:func:`_resolve_prior_texts`) rides the SAME loop as the content read — two extra
    batched calls per chunk, never per blob — so the peak resident set stays
    ``chunk_size x cap x 2`` rather than growing with the range. An oversized CURRENT
    object never carries prior text (the prior-side lookup rides the chunk loop only).
    """
    fetch_shas = [sha for sha, (_, size) in blob_info.items() if size <= _MAX_BLOB_BYTES]
    oversized_shas = [sha for sha, (_, size) in blob_info.items() if size > _MAX_BLOB_BYTES]

    for sha in oversized_shas:
        path, size = blob_info[sha]
        yield _read_oversized_blob(repo, sha, path, size)

    for start in range(0, len(fetch_shas), _BATCH_CHUNK_SIZE):
        chunk = fetch_shas[start : start + _BATCH_CHUNK_SIZE]
        prior_texts: dict[str, str] = {}
        if base is not None:
            chunk_paths = [blob_info[sha][0] for sha in chunk]
            prior_texts = _resolve_prior_texts(repo, base, chunk_paths)
        yield from _read_blob_chunk(repo, chunk, blob_info, prior_texts)


class GitSubprocessObjectReader:
    """Subprocess-backed ``GitObjectReader`` (SPEC v0.9.0 FR1/FR7 injected port)."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        # code-reviewer LOW finding (v0.11.0 pre-PR review): the module's stated
        # second-layer argv defence (module docstring above) must also cover
        # `local_sha` — the SAME shape check `_is_resolvable_commit` already applies to
        # `remote_sha`, here applied BEFORE `local_sha` ever reaches
        # `_rev_list_candidates`'s `git rev-list` argv (CWE-88). An option-shaped value
        # is rejected as a read failure rather than ever being interpolated.
        if not _SHA_SHAPE_RE.match(local_sha):
            raise GitObjectReadError(f"local_sha is not a valid sha shape: {local_sha!r}")
        # v0.11.0 FR2/ADR D7: base resolved ONCE per call — reused for the FR1 range
        # shape (_rev_list_candidates) AND the prior-side lookup (_read_blobs), rather
        # than re-derived. Unresolvable/zero remote_sha -> no base -> no object in this
        # call carries prior content (the fallback shape stays byte-identical to
        # v0.9.0).
        base = remote_sha if _is_resolvable_commit(repo, remote_sha) else None
        candidates = _rev_list_candidates(repo, local_sha, base)
        blob_info = _blob_info(repo, candidates)
        yield from _read_blobs(repo, blob_info, base)
