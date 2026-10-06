"""worktree-removal-leaves-empty-parent-and-remote-branch: a merged or cleaned worktree leaves
nothing behind — its rc folder once empty, and its branch on the remote when it was pushed — and
`list` shows a directory that holds no tree. Size: MEDIUM (real git and a bare remote, tmp workspace).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import JOB, approve, git, land, make_workspace, run

pytestmark = pytest.mark.integration

BRANCH = "wt/0.5.0-rc1/j1"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(ws, "new", "r", JOB).returncode == 0
    return ws


def _push_to_a_remote(root: Path) -> None:
    remote = root.parent / "remote.git"
    git(root.parent, "init", "-q", "--bare", str(remote))
    git(root / "repos/r", "remote", "add", "origin", str(remote))
    git(root / "repos/r", "push", "-q", "origin", BRANCH)


def _on_the_remote(root: Path) -> str:
    return git(root / "repos/r", "ls-remote", "--heads", "origin", BRANCH).strip()


@pytest.mark.xfail(
    strict=True, reason="JB.S3 RED: worktree-removal-leaves-empty-parent-and-remote-branch"
)
def test_a_merge_removes_the_emptied_rc_folder_and_the_pushed_branch(root: Path) -> None:
    approve(root, land(root, "src/a.py"))
    _push_to_a_remote(root)
    assert _on_the_remote(root)
    merged = run(root, "merge", f"worktrees/r/{JOB}")
    assert merged.returncode == 0, merged.stderr
    assert not (root / "worktrees/r/0.5.0-rc1").exists()
    assert _on_the_remote(root) == ""


@pytest.mark.xfail(
    strict=True, reason="JB.S3 RED: worktree-removal-leaves-empty-parent-and-remote-branch"
)
def test_clean_removes_the_emptied_rc_folder_and_the_pushed_branch(root: Path) -> None:
    _push_to_a_remote(root)
    cleaned = run(root, "clean", f"worktrees/r/{JOB}")
    assert cleaned.returncode == 0, cleaned.stderr
    assert not (root / "worktrees/r/0.5.0-rc1").exists()
    assert _on_the_remote(root) == ""


def test_a_merge_with_no_remote_still_lands_and_keeps_a_sibling_tree(root: Path) -> None:
    """No remote is assumed: nothing to delete there, and a rc folder still holding a tree stays."""
    assert run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0
    approve(root, land(root, "src/a.py"))
    assert run(root, "merge", f"worktrees/r/{JOB}").returncode == 0
    assert (root / "worktrees/r/0.5.0-rc1/j2").is_dir()


@pytest.mark.xfail(
    strict=True, reason="JB.S3 RED: worktree-removal-leaves-empty-parent-and-remote-branch"
)
def test_list_reports_a_directory_that_holds_no_tree(root: Path) -> None:
    (root / "worktrees/r/0.5.0-rc9").mkdir()
    rows = json.loads(run(root, "list", "--json").stdout)
    assert [(r["state"], r["path"]) for r in rows if r["state"] != "empty"] == [
        ("unregistered", str(root / "worktrees/r/0.5.0-rc9"))
    ]
