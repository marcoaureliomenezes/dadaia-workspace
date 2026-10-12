"""A job or hotfix tree whose HEAD tracks files under `tests/tmp/<job>/` is refused by
`worktree.py merge` and reported by `preflight`, one `[error]` line and one `fix:` line; only tracked
paths count, and every other tree kind is unaffected.
Size: MEDIUM (real git, a tmp workspace, a stub CLI).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.worktree_ws import JOB, approve, commit, git, land, make_workspace, run

BRANCH = "feature/0.5.0"
TEST = "def test_x():\n    pass\n"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", BRANCH)
    return tmp_path


def _tree(root: Path, name: str) -> Path:
    assert run(root, "new", "r", name).returncode == 0
    return root / "worktrees/r" / name


def _scaffold(tree: Path, job: str) -> None:
    commit(tree, f"tests/tmp/{job}/__init__.py", "")
    commit(tree, f"tests/tmp/{job}/test_x.py", TEST)


def _lines(root: Path, verb: str, tree: Path) -> tuple[int, list[str]]:
    done = run(root, verb, str(tree))
    kept = [
        ln
        for ln in (done.stdout + done.stderr).splitlines()
        if ln.startswith(("PREFLIGHT ", "[error] ", "fix: "))
    ]
    return done.returncode, kept


def _refused(root: Path, tree: Path, job: str) -> None:
    folder = tree / "tests" / "tmp" / job
    error = f"[error] {folder} exists: promote each test in it into its contract's home or delete it before the job lands"  # fmt: skip
    fix = f"fix: Operator action: promote each test in {folder} into its contract's home or delete it, then commit the removal"  # fmt: skip
    head = git(tree, "rev-parse", "HEAD").strip()
    assert _lines(root, "preflight", tree) == (1, [f"PREFLIGHT FAIL {tree} {head}", error, fix])
    assert _lines(root, "merge", tree) == (1, [error, fix])


def _clears(root: Path, tree: Path) -> None:
    head = git(tree, "rev-parse", "HEAD").strip()
    assert _lines(root, "preflight", tree) == (0, [f"PREFLIGHT PASS {tree} {head}"])
    approve(root, head)
    done = run(root, "merge", str(tree))
    assert done.returncode == 0, done.stderr


def test_a_job_tree_with_a_tracked_scaffold_is_refused_until_its_removal_is_committed(
    root: Path,
) -> None:
    job = _tree(root, JOB)
    _scaffold(job, "j1")
    _refused(root, job, "j1")
    git(job, "rm", "-rq", "tests/tmp/j1")
    git(job, "commit", "-qm", "drop the scaffold")
    _clears(root, job)


def test_a_hotfix_tree_names_the_folder_by_the_last_segment_of_its_name(root: Path) -> None:
    repo = root / "repos/r"
    commit(repo, "specs/bugs/BUGS.jsonl", '{"id": "bug1", "status": "open"}\n')
    tree = _tree(root, "hotfix/bug1")
    _scaffold(tree, "bug1")
    _refused(root, tree, "bug1")


def test_a_scaffold_collected_then_removed_leaves_untracked_bytecode_that_blocks_nothing(
    root: Path,
) -> None:
    commit(root / "repos/r", "tests/tmp/README.md", "scaffolding\n")
    job = _tree(root, JOB)
    _scaffold(job, "j1")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env["HYPOTHESIS_STORAGE_DIRECTORY"] = str(root / "hypothesis")
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/tmp/j1"],
        cwd=job, env=env, capture_output=True, text=True,
    )  # fmt: skip
    assert collected.returncode == 0, collected.stdout
    assert (job / "tests/tmp/j1/__pycache__").is_dir()
    _refused(root, job, "j1")
    git(job, "rm", "-rq", "tests/tmp/j1")
    git(job, "commit", "-qm", "drop the scaffold")
    assert (job / "tests/tmp/j1/__pycache__").is_dir()
    assert git(job, "ls-files", "--", "tests/tmp/j1") == ""
    _clears(root, job)


def test_a_task_tree_with_the_scaffold_merges(root: Path) -> None:
    _tree(root, JOB)
    land(root, "tests/tmp/j1/test_x.py", TEST, task_id="J1.T1")


def test_a_job_tree_without_a_tests_tmp_folder_passes(root: Path) -> None:
    job = _tree(root, JOB)
    commit(job, "src/a.py")
    _clears(root, job)


@pytest.mark.parametrize("name", ["0.5.0-rc1/define", "j1"])
def test_a_define_or_plain_tree_over_a_tracked_folder_of_its_name_passes(
    root: Path, name: str
) -> None:
    commit(root / "repos/r", f"tests/tmp/{name.rsplit('/')[-1]}/test_x.py", TEST)
    tree = _tree(root, name)
    head = git(tree, "rev-parse", "HEAD").strip()
    assert _lines(root, "preflight", tree) == (0, [f"PREFLIGHT PASS {tree} {head}"])
