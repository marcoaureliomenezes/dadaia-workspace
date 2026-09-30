"""Intent: CONTRACT — AC1.8 (T-050-96, T-050-108): `worktree.py merge` fast-forwards, removes
and `branch -d`s a reviewed worktree, re-runnable; every refusal (dirty, outside the kind's
allowed set, conflicting rebase, no APPROVED verdict for HEAD, ignored files, wrong branch)
carries one `fix:` that clears it; `clean` removes only an empty `dadaia:` worktree.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import SCRIPT, approve, commit, fixes, git, make_workspace, run
from tests.helpers.worktree_ws import run_fix as _fix

pytestmark = pytest.mark.integration

TREE = "worktrees/r/0.5.0a-impl"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", "--kind", "impl").returncode == 0
    return tmp_path


def test_merge_fast_forwards_removes_and_reruns(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    sha = commit(tree, "src/a.py")
    approve(root, sha)
    result = run(root, "merge", TREE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == sha
    assert not tree.exists() and not git(repo, "branch", "--list", "wt/*").strip()
    assert run(root, "merge", TREE).returncode == 0  # a finished merge re-runs clean
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0a-impl", str(tree))
    commit(tree, "src/b.py")
    git(repo, "worktree", "remove", str(tree))  # interrupted: tree gone, its commit unmerged
    assert fixes(run(root, "merge", TREE)) == [
        f"fix: git -C {repo} worktree add {tree} wt/0.5.0a-impl"
    ]
    assert git(repo, "branch", "--list", "wt/0.5.0a-impl").strip()  # never -D


def test_dirty_outside_set_and_conflict_each_refuse_with_one_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    (tree / "wip.py").write_text("")
    _fix(root, dirty := run(root, "merge", TREE))
    assert "uncommitted" in dirty.stderr
    commit(tree, "specs/backlog/BACKLOG.json", "{}")  # new: the undo removes it
    commit(tree, "specs/releases/0.5.0/SPEC.md", "edited")  # on the work branch: restored
    for rel, owner in (("specs/backlog/BACKLOG.json", "backlog"), ("SPEC.md", "release")):
        outside = run(root, "merge", TREE)
        assert rel in outside.stderr and f"{owner} worktree" in outside.stderr
        _fix(root, outside)
    commit(repo, "src/a.py", "main side\n")
    commit(tree, "src/a.py", "tree side\n")
    conflict = run(root, "merge", TREE)
    assert not (Path(git(tree, "rev-parse", "--git-dir").strip()) / "rebase-merge").exists()
    assert fixes(conflict) == [f"fix: git -C {tree} rebase feature/0.5.0"]


@pytest.mark.parametrize(
    ("named", "verdict", "valid"),
    [(False, "APPROVED", True), (True, "REJECTED", True), (True, "APPROVED", False)],
    ids=["other-sha", "rejected", "invalid"],
)
def test_merge_needs_a_valid_approval_of_the_exact_head(
    root: Path, named: bool, verdict: str, valid: bool
) -> None:
    old = commit(root / TREE, "src/a.py")
    head = commit(root / TREE, "src/b.py")
    target = (
        approve(root, head, verdict=verdict, valid=valid)
        if named
        else (approve(root, old), "--all")[1]
    )
    result = run(root, "merge", TREE)
    assert result.returncode == 1 and head in result.stderr
    assert fixes(result) == [f"fix: {root / '.dadaia/.venv/bin/dadaia'} reports validate {target}"]
    assert git(root / "repos/r", "rev-parse", "feature/0.5.0").strip() != head


def test_merge_lists_ignored_files_and_keeps_them_by_its_fix(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    approve(root, commit(tree, "src/a.py"))
    (tree / "notes.scratch").write_text("keep me")
    (tree / "__pycache__").mkdir()
    (tree / "__pycache__/a.pyc").write_bytes(b"")
    git(repo, "checkout", "-q", "main")
    refused = run(root, "merge", TREE)
    assert "notes.scratch" in refused.stderr and "__pycache__" not in refused.stderr
    wrong_branch = run(root, "merge", TREE, "--keep", "notes.scratch")
    assert fixes(wrong_branch) == [f"fix: git -C {repo} switch feature/0.5.0"]
    _fix(root, wrong_branch)
    _fix(root, refused)
    assert (repo / "notes.scratch").read_text() == "keep me" and not tree.exists()


def test_clean_removes_only_an_empty_dadaia_worktree(root: Path) -> None:
    repo, tree = root / "repos/r", root / TREE
    commit(tree, "src/a.py")
    assert fixes(run(root, "clean", TREE)) == [f"fix: python3 {SCRIPT} merge {tree}"]
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    assert run(root, "clean", TREE).returncode == 0 and not tree.exists()
    git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0b-bug", str(root / "worktrees/r/0.5.0b-bug"))
    foreign = run(root, "clean", "worktrees/r/0.5.0b-bug")
    assert foreign.returncode == 1 and (root / "worktrees/r/0.5.0b-bug").exists()


def test_each_kind_allows_its_own_set_only() -> None:
    """ADRs 0106, 0124: the allowed sets `merge` enforces, one row per kind boundary."""
    spec = importlib.util.spec_from_file_location("kinds", SCRIPT.parent / "_worktree_kinds.py")
    assert spec and spec.loader
    kinds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kinds)
    rows = {
        ("impl", "src/a.py"): True,
        ("impl", "specs/releases/0.5.0/TASKS.md"): True,
        ("impl", "specs/backlog/BACKLOG.json"): False,
        ("bug", "specs/bugs/BUGS.jsonl"): True,
        ("bug", "specs/releases/0.5.0/SPEC.md"): False,
        ("backlog", "specs/backlog/_archive/backlog_histo.jsonl"): True,
        ("backlog", "src/a.py"): False,
        ("release", "specs/memory/ARCHITECTURE.md"): True,
        ("release", "specs/constitution.md"): False,
    }
    assert {row: kinds.allows(*row) for row in rows} == rows
