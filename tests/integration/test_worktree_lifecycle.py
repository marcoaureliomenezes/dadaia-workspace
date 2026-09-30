"""Intent: CONTRACT — AC1.8 (T-050-96): `worktree.py merge` fast-forwards, removes and
`branch -d`s a reviewed worktree, re-runnable; each refusal carries one executable `fix:`;
`clean` removes only an empty `dadaia:` worktree. Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import SCRIPT, approve, commit, fixes, git, make_workspace, run

pytestmark = pytest.mark.integration

TREE = "worktrees/r/0.5.0a-impl"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", "--kind", "impl").returncode == 0
    return tmp_path


def _shell(root: Path, fix: str) -> None:
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    command = fix.removeprefix("fix: ").replace("python3 ", f"{sys.executable} ", 1)
    subprocess.run(command, shell=True, cwd=root, env=env, check=True, capture_output=True)


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert not tree.exists() and not git(repo, "branch", "--list", "wt/*").strip()
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean


def test_merge_refusals_each_carry_one_fix_that_clears_them(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    (tree / "wip.py").write_text("")
    dirty = run(root, "merge", TREE)
    assert dirty.returncode == 1 and "uncommitted" in dirty.stderr
    _shell(root, fixes(dirty)[0])
    commit(repo, "src/a.py", "main side\n")
    commit(tree, "src/a.py", "tree side\n")
    conflict = run(root, "merge", TREE)
    assert conflict.returncode == 1 and "conflicts" in conflict.stderr
    assert not (Path(git(tree, "rev-parse", "--git-dir").strip()) / "rebase-merge").exists()
    (fix,) = fixes(conflict)
    assert fix == f"fix: git -C {tree} rebase feature/0.5.0"


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    approve(root, commit(tree, "src/a.py"))
    (tree / "notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(repo, "checkout", "-q", "main")
    refused = run(root, "merge", TREE)
    assert refused.returncode == 1 and "notes.scratch" in refused.stderr
    assert "__pycache__" not in refused.stderr
    (fix,) = fixes(refused)
    assert fix.endswith(f"merge {tree} --keep notes.scratch")
    wrong_branch = run(root, "merge", TREE, "--keep", "notes.scratch")
    assert fixes(wrong_branch) == [f"fix: git -C {repo} switch feature/0.5.0"]
    git(repo, "checkout", "-q", "feature/0.5.0")
    _shell(root, fix)
    assert (repo / "notes.scratch").read_text() == "keep me" and not tree.exists()


def test_clean_removes_only_an_empty_dadaia_worktree(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    busy = run(root, "clean", TREE)
    assert fixes(busy) == [f"fix: python3 {SCRIPT} merge {tree}"]
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0b-bug", str(root / "worktrees/r/0.5.0b-bug"))
    foreign = run(root, "clean", "worktrees/r/0.5.0b-bug")
    assert foreign.returncode == 1 and (root / "worktrees/r/0.5.0b-bug").exists()


def test_the_end_verbs_never_force() -> None:
    source = (SCRIPT.parent / "_worktree_end.py").read_text()
    assert '"--force"' not in source and '"-D"' not in source  # argv tokens, not prose
