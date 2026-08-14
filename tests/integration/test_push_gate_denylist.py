"""Push-range denylist scan over a REAL throwaway git repo (SPEC v0.9.0 FR4/FR6).

Intent: CONTRACT — v0.9.0 A4.2, A6.1

Exercises the real ``GitSubprocessObjectReader`` adapter (real ``git`` subprocess) wired
into ``push_gate_decision`` — no CLI layer, so this stays a fast, direct integration
proof of the FROZEN<->scan invariant (FR4) and the fail-closed git-failure boundary
(FR6 row 2). Only synthetic terms ever appear here (TASKS standing rule).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import GitObjectReadError
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader

_SYNTHETIC_TERM = "zz-frozen-invariant-term"
_ZERO = "0" * 40


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init"], path)
    _git(["config", "user.email", "t@example.com"], path)
    _git(["config", "user.name", "T"], path)


def _commit(path: Path, message: str) -> str:
    _git(["add", "-A"], path)
    _git(["commit", "-m", message], path)
    return _git(["rev-parse", "HEAD"], path).stdout.strip()


def _tag_push_ref(local_sha: str, *, remote_sha: str = _ZERO) -> PushRef:
    return PushRef(
        local_ref="refs/tags/v1",
        local_sha=local_sha,
        remote_ref="refs/tags/v1",
        remote_sha=remote_sha,
    )


def test_git_mv_into_archive_produces_no_new_blob_and_a_clean_scan(tmp_path: Path) -> None:
    """FR4/A4.2: renaming a tainted file into ``specs/_archive/`` reuses the same blob
    object — the range carries no NEW blob, so the scan is clean by construction."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content\n")
    # Simulates a push already reachable at the remote — the FROZEN↔scan invariant only
    # holds relative to a real range boundary; `remote_sha` anchors it (FR1 row 1).
    already_published_sha = _commit(repo, "already-published")

    (repo / "specs" / "_archive").mkdir(parents=True)
    _git(["mv", "notes.md", "specs/_archive/notes.md"], repo)
    renamed_sha = _commit(repo, "archive: git mv the tainted file")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        tmp_path / "handoff-empty",
        [_tag_push_ref(renamed_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed, decision.message


def test_editing_the_same_content_produces_a_new_blob_and_a_refusal(tmp_path: Path) -> None:
    """FR4/A4.2 contrast case: an EDIT of the same tainted content (not a bare rename)
    creates a genuinely new blob object, which the scan correctly refuses."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content\n")
    already_published_sha = _commit(repo, "already-published")

    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content, plus more\n")
    edited_sha = _commit(repo, "edit the tainted file in place")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        tmp_path / "handoff-empty",
        [_tag_push_ref(edited_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message


def test_real_git_failure_refuses_naming_the_failure(tmp_path: Path) -> None:
    """FR6 row 2, integration-tier: a genuinely non-git directory wired through the
    REAL adapter refuses, never silently allows an unscannable push."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    reader = GitSubprocessObjectReader()

    decision = push_gate_decision(
        tmp_path / "handoff-empty",
        [_tag_push_ref("a" * 40)],
        object_source=reader,
        repo=not_a_repo,
    )

    assert not decision.allowed
    assert "--no-verify" in decision.message


def test_git_object_read_error_is_importable_from_core_protocols() -> None:
    """Sentinel-level sanity: the typed failure the adapter raises stays importable
    from `core.protocols` without pulling in infrastructure (purity boundary)."""
    assert issubclass(GitObjectReadError, Exception)
