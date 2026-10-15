"""A merged or cleaned worktree leaves
nothing behind — its parent folder once empty, and its branch on the remote when it was pushed — and
`list` shows a directory that holds no tree. Size: MEDIUM (real git and a bare remote, tmp workspace).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import JOB, approve, git, land, make_workspace, run

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
    git(root / "repos/r", "push", "-q", "-u", "origin", BRANCH)


def _on_the_remote(root: Path) -> str:
    return git(root / "repos/r", "ls-remote", "--heads", "origin", BRANCH).strip()


def test_a_merge_removes_the_emptied_rc_folder_and_the_pushed_branch(root: Path) -> None:
    approve(root, land(root, "src/a.py"))
    _push_to_a_remote(root)
    assert _on_the_remote(root)
    merged = run(root, "merge", f"worktrees/r/{JOB}")
    assert merged.returncode == 0, merged.stderr
    assert not (root / "worktrees/r/0.5.0-rc1").exists()
    assert _on_the_remote(root) == ""


def test_clean_removes_the_emptied_rc_folder_and_the_pushed_branch(root: Path) -> None:
    _push_to_a_remote(root)
    cleaned = run(root, "clean", f"worktrees/r/{JOB}")
    assert cleaned.returncode == 0, cleaned.stderr
    assert not (root / "worktrees/r/0.5.0-rc1").exists()
    assert _on_the_remote(root) == ""


def test_a_merge_with_no_remote_still_lands_and_keeps_a_sibling_tree(root: Path) -> None:
    """No remote is assumed: nothing to delete there, and a parent folder still holding a tree stays."""
    assert run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0
    approve(root, land(root, "src/a.py"))
    assert run(root, "merge", f"worktrees/r/{JOB}").returncode == 0
    assert (root / "worktrees/r/0.5.0-rc1/j2").is_dir()


def test_list_reports_a_directory_that_holds_no_tree(root: Path) -> None:
    (root / "worktrees/r/0.5.0-rc9").mkdir()
    (root / "worktrees/r/stray").mkdir()  # a one-level directory holding only a file
    (root / "worktrees/r/stray/f.txt").write_text("x")
    rows = json.loads(run(root, "list", "--json").stdout)
    assert [(r["state"], r["path"]) for r in rows if r["state"] != "empty"] == [
        ("unregistered", str(root / "worktrees/r/0.5.0-rc9")),
        ("unregistered", str(root / "worktrees/r/stray")),
    ]


def test_list_gives_one_row_per_path_the_orphan_winning(root: Path) -> None:
    assert run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/j2"
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
    tree.mkdir()  # the branch stays; the directory survives, files only
    (tree / "f.txt").write_text("x")
    rows = json.loads(run(root, "list", "--json").stdout)
    assert [(r["state"], r["path"]) for r in rows if r["state"] != "empty"] == [
        ("orphan", str(tree))
    ]


def test_an_orphan_whose_directory_survives_names_the_removal_and_following_it_empties_list(
    root: Path,
) -> None:
    assert run(root, "new", "r", "0.5.0-rc1/j2").returncode == 0
    tree = root / "worktrees/r/0.5.0-rc1/j2"
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
    tree.mkdir()
    (tree / "f.txt").write_text("x")
    [row] = [r for r in json.loads(run(root, "list", "--json").stdout) if r["state"] != "empty"]
    assert row["fix"].startswith(f"Agent action: remove the directory {tree}, then run `")
    assert row["fix"].endswith(f"worktree.py merge {tree}`")
    assert row["exit"] == row["fix"]  # the closure refusal and `context dead` print `exit`
    shutil.rmtree(tree)  # the operator act the fix names
    assert run(root, "merge", str(tree)).returncode == 0
    assert [
        r for r in json.loads(run(root, "list", "--json").stdout) if r["state"] != "empty"
    ] == []


def _push_upstream(root: Path, remote_name: str) -> Path:
    remote = root.parent / f"{remote_name}.git"
    git(root.parent, "init", "-q", "--bare", str(remote))
    git(root / "repos/r", "remote", "add", remote_name, str(remote))
    git(root / "repos/r", "push", "-q", "-u", remote_name, BRANCH)
    return remote


def test_a_merge_deletes_the_pushed_branch_on_a_non_origin_upstream(root: Path) -> None:
    approve(root, land(root, "src/a.py"))
    remote = _push_upstream(root, "mirror")
    merged = run(root, "merge", f"worktrees/r/{JOB}")
    assert merged.returncode == 0, merged.stderr
    assert git(root.parent, "-C", str(remote), "branch", "--list", BRANCH).strip() == ""


def test_a_refused_remote_delete_is_reported_with_its_fix_line(root: Path) -> None:
    remote = _push_upstream(root, "origin")
    git(root.parent, "-C", str(remote), "config", "receive.denyDeletes", "true")
    cleaned = run(root, "clean", f"worktrees/r/{JOB}")
    assert BRANCH in cleaned.stderr + cleaned.stdout
    assert "fix: " in cleaned.stderr + cleaned.stdout
