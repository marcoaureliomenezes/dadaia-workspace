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

import subprocess
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import (
    ZERO_SHA,
    GitObjectReadError,
    ScannedObject,
)

_TIMEOUT_S = 30

#: SPEC v0.9.0 R3 — a per-blob size guard so one pathological blob cannot dominate the
#: scan's wall clock or memory: a blob at or under this cap is read and decoded; a blob
#: over it is never fetched at all and is reported ``decodable=False`` (counted the same
#: way an undecodable binary blob is, FR6 row 3).
_MAX_BLOB_BYTES = 5 * 1024 * 1024  # 5 MB


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
    """True when *sha* resolves to a commit object reachable locally (FR1 row 1/2)."""
    if not sha or sha == ZERO_SHA:
        return False
    result = _run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo)
    return result.returncode == 0


def _rev_list_candidates(repo: Path, local_sha: str, remote_sha: str) -> list[tuple[str, str]]:
    """Return ``(sha, path)`` pairs for every object with a path in the FR1 range —
    blobs AND trees (type filtering happens separately, in :func:`_blob_info`)."""
    if _is_resolvable_commit(repo, remote_sha):
        args = ["git", "rev-list", "--objects", local_sha, "--not", remote_sha]
    else:
        args = ["git", "rev-list", "--objects", local_sha, "--not", "--remotes"]
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


def _read_blobs(repo: Path, blob_info: dict[str, tuple[str, int]]) -> Iterator[ScannedObject]:
    """Yield one :class:`ScannedObject` per blob in *blob_info*.

    Content is read via a SINGLE batched ``git cat-file --batch`` conversation — one
    subprocess for every blob in the range, not one per blob (code-reviewer MEDIUM
    finding; mirrors the batching pattern :func:`_blob_info` already uses). A blob over
    :data:`_MAX_BLOB_BYTES` is excluded from that conversation entirely — its content is
    never fetched — and is yielded directly as ``decodable=False`` (R3 size guard).
    """
    fetch_shas = [sha for sha, (_, size) in blob_info.items() if size <= _MAX_BLOB_BYTES]
    oversized_shas = [sha for sha, (_, size) in blob_info.items() if size > _MAX_BLOB_BYTES]

    for sha in oversized_shas:
        path, _size = blob_info[sha]
        yield ScannedObject(path=path, sha=sha, text="", decodable=False)

    if not fetch_shas:
        return

    stdin_payload = ("\n".join(fetch_shas) + "\n").encode("utf-8")
    result = _run(["git", "cat-file", "--batch"], repo, input_bytes=stdin_payload)
    if result.returncode != 0:
        raise GitObjectReadError(f"git cat-file --batch failed: {_decode(result.stderr).strip()}")

    out = result.stdout
    pos = 0
    for sha in fetch_shas:
        path, size = blob_info[sha]
        newline_idx = out.index(b"\n", pos)
        header = out[pos:newline_idx].decode("utf-8", errors="replace")
        pos = newline_idx + 1
        parts = header.split()
        if len(parts) != 3:
            # Defensive: the batch stream lost sync with the requested id (should not
            # happen — the batch-check pass just confirmed each id is a readable blob).
            # A gate never crashes on a git-protocol surprise; count it undecodable.
            yield ScannedObject(path=path, sha=sha, text="", decodable=False)
            continue
        obj_sha, _obj_type, size_str = parts
        content_size = int(size_str)
        content = out[pos : pos + content_size]
        pos += content_size + 1  # skip the trailing newline after the content block
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            yield ScannedObject(path=path, sha=obj_sha, text="", decodable=False)
            continue
        yield ScannedObject(path=path, sha=obj_sha, text=text, decodable=True)


class GitSubprocessObjectReader:
    """Subprocess-backed ``GitObjectReader`` (SPEC v0.9.0 FR1/FR7 injected port)."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        candidates = _rev_list_candidates(repo, local_sha, remote_sha)
        blob_info = _blob_info(repo, candidates)
        yield from _read_blobs(repo, blob_info)
