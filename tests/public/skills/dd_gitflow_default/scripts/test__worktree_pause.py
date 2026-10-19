"""`worktree.py pause` bundles one clean lane or `wt-rc` tree (the commits origin lacks) at
`.dadaia/dist/<repo>/<name>.bundle`, removes the tree and its branch; `resume` recreates both from
the bundle and deletes it. Real git, a bare origin, a tmp workspace.
Size: MEDIUM.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.oslib import read_text
from tests.helpers.oslib import run as os_run
from tests.helpers.worktree_ws import commit, git, make_workspace, open_tree, run

RC, BACKLOG = "0.5.0/rc-1/wt-rc", "0.5.0/wt-backlog-x"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A workspace whose repo `r` has a bare `origin` holding the work branch."""
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "origin", "feature/0.5.0")
    return ws


def _bundle(root: Path, name: str) -> Path:
    """Where the bundle of tree *name* sits: `.dadaia/dist/<repo>/<name>.bundle`."""
    *folders, leaf = name.split("/")
    return root.joinpath(".dadaia", "dist", "r", *folders, f"{leaf}.bundle")


def _branch(name: str) -> str:
    return f"wt/{name}"


def _requires(repo: Path, bundle: Path) -> str:
    """What `git bundle verify` says the bundle needs from *repo*."""
    done = os_run(["git", "bundle", "verify", str(bundle)], cwd=repo)
    return done.stdout + done.stderr


@pytest.mark.parametrize("name", [BACKLOG, RC])
def test_pause_then_resume_restores_the_branch_tip_and_tree(root: Path, name: str) -> None:
    repo, tree = root / "repos/r", open_tree(root, name)
    tip = commit(tree, "specs/notes.md", "kept\n")
    snapshot = git(tree, "rev-parse", "HEAD^{tree}")

    paused = run(root, "pause", str(tree))

    assert paused.returncode == 0, paused.stderr
    assert _bundle(root, name).is_file()
    assert not tree.exists()
    assert git(repo, "branch", "--list", _branch(name)) == ""
    resumed = run(root, "resume", str(tree))
    assert resumed.returncode == 0, resumed.stderr
    assert git(tree, "rev-parse", "HEAD").strip() == tip
    assert git(repo, "rev-parse", _branch(name)).strip() == tip
    assert git(tree, "rev-parse", "HEAD^{tree}") == snapshot
    assert read_text(tree / "specs/notes.md") == "kept\n"
    assert git(tree, "status", "--porcelain") == ""
    assert not _bundle(root, name).exists()
    assert not (root / ".dadaia/dist/r").exists()


def test_the_bundle_holds_only_the_commits_origin_lacks(root: Path, tmp_path: Path) -> None:
    tree = open_tree(root, BACKLOG)
    pushed = commit(tree, "specs/a.md")
    git(tree, "push", "-q", "origin", _branch(BACKLOG))
    local = commit(tree, "specs/b.md")

    paused = run(root, "pause", str(tree))

    assert paused.returncode == 0, paused.stderr
    bundle = _bundle(root, BACKLOG)
    assert pushed in _requires(root / "repos/r", bundle)
    fresh = tmp_path / "fresh"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(fresh))
    git(fresh, "fetch", "-q", str(bundle), f"{_branch(BACKLOG)}:{_branch(BACKLOG)}")
    assert git(fresh, "rev-parse", _branch(BACKLOG)).strip() == local
    assert git(fresh, "rev-list", "--count", f"{pushed}..{local}").strip() == "1"
