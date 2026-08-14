"""GitSubprocessObjectReader — the ``GitObjectReader`` adapter for the push-range scan.

Implements ``core.protocols.git_object_reader.GitObjectReader`` over ``git rev-list
--objects`` + ``git cat-file`` (SPEC v0.9.0 FR1). Kept in a sibling file to
``git_subprocess.py`` rather than grown inside it — the two modules serve different
concerns (workspace-management git operations vs. the push-range object reader) and
``git_subprocess.py`` is already close to the size that would warrant a split
(PLAN v0.9.0 §2).
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


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    """Run a git subcommand, capturing raw bytes (never ``text=True`` — decoding is the
    caller's job, and content bytes may not be valid UTF-8 at all)."""
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, timeout=_TIMEOUT_S)
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
    blobs AND trees (type filtering happens separately, in :func:`_blob_paths`)."""
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


def _blob_paths(repo: Path, candidates: list[tuple[str, str]]) -> dict[str, str]:
    """Return ``{sha: first-seen path}`` restricted to the candidates that are blobs.

    ``git rev-list --objects`` also emits trees with a path (directory names) — this
    filters those out via a single batched ``git cat-file --batch-check`` call rather
    than one subprocess per candidate.
    """
    if not candidates:
        return {}
    stdin_payload = "\n".join(sha for sha, _ in candidates).encode("utf-8")
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        cwd=repo,
        input=stdin_payload,
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise GitObjectReadError(
            f"git cat-file --batch-check failed: {_decode(result.stderr).strip()}"
        )
    blob_shas: set[str] = set()
    for line in _decode(result.stdout).splitlines():
        sha, _, rest = line.partition(" ")
        if rest.strip() == "blob":
            blob_shas.add(sha)
    first_path: dict[str, str] = {}
    for sha, path in candidates:
        if sha in blob_shas and sha not in first_path:
            first_path[sha] = path
    return first_path


def _read_blob(repo: Path, sha: str, path: str) -> ScannedObject:
    result = _run(["git", "cat-file", "-p", sha], repo)
    if result.returncode != 0:
        raise GitObjectReadError(f"git cat-file -p {sha} failed: {_decode(result.stderr).strip()}")
    try:
        text = result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return ScannedObject(path=path, sha=sha, text="", decodable=False)
    return ScannedObject(path=path, sha=sha, text=text, decodable=True)


class GitSubprocessObjectReader:
    """Subprocess-backed ``GitObjectReader`` (SPEC v0.9.0 FR1/FR7 injected port)."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterator[ScannedObject]:
        if not local_sha or local_sha == ZERO_SHA:
            return
        candidates = _rev_list_candidates(repo, local_sha, remote_sha)
        blob_paths = _blob_paths(repo, candidates)
        for sha, path in blob_paths.items():
            yield _read_blob(repo, sha, path)
