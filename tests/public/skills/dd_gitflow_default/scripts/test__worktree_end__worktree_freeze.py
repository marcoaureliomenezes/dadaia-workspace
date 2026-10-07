"""ADR 0209, AC6.0-AC6.2: from the RED anchor on, a task or job `worktree.py merge` refuses any
diff that modifies or deletes a line of a path the work branch's `tests:` line declares; a pure
rename, a marker-only deletion (a line matching the work branch's `tests-red:`) and the lines a
new tests-only stage adds land. A repo with no `tests:` line refuses with one fix line.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.worktree_ws import (
    JOB,
    TASK,
    approve,
    attempt,
    commit,
    fixes,
    git,
    land,
    make_workspace,
    run,
)

TREE = f"worktrees/r/{JOB}"
RED = "def test_a():\n    assert 0\n"
GREEN = "def test_a():\n    assert 1\n"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert run(tmp_path, "new", "r", JOB).returncode == 0
    return tmp_path


def _frozen(path: str, anchor: str) -> list[str]:
    return [
        f"fix: Operator action: stop and report — {path} is frozen past the RED anchor {anchor} (ADR 0209)"
    ]


def _born(root: Path, text: str = RED) -> str:
    """Stage 1 lands `tests/test_a.py`, then stage 2 lands code: the anchor is stage 1's commit."""
    sha = land(root, "tests/test_a.py", text, "J1.S1.T1")
    land(root, "src/a.py", "x = 1\n", "J1.S2.T1")
    return sha


def test_a_modified_test_line_past_the_anchor_refuses(root: Path) -> None:
    anchor = _born(root)
    _, merged = attempt(root, {"tests/test_a.py": GREEN}, "J1.S2.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_deleted_test_file_past_the_anchor_refuses(root: Path) -> None:
    anchor = _born(root)
    assert run(root, "new", "r", TASK).returncode == 0
    tree = root / "worktrees/r" / TASK
    git(tree, "rm", "-q", "tests/test_a.py")
    git(tree, "commit", "-qm", "drop", "--trailer", "Owner-tests: tests/test_r.py")
    merged = run(root, "merge", f"worktrees/r/{TASK}")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_test_edit_inside_stage_one_alone_is_frozen_from_the_range_base(root: Path) -> None:
    land(root, "tests/test_a.py", RED, "J1.S1.T1")
    base = git(root / "repos/r", "rev-parse", "feature/0.5.0").strip()
    _, merged = attempt(root, {"tests/test_a.py": GREEN}, "J1.S1.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", base))


def test_a_file_born_after_the_anchor_and_then_edited_refuses(root: Path) -> None:
    anchor = _born(root)
    land(root, "tests/test_n.py", RED, "J1.S3.T1")
    _, merged = attempt(root, {"tests/test_n.py": GREEN}, "J1.S3.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_n.py", anchor))


def test_test_lines_added_in_a_stage_that_also_touches_code_refuse(root: Path) -> None:
    anchor = _born(root)
    _, merged = attempt(root, {"tests/test_b.py": RED}, "J1.S2.T3")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_b.py", anchor))


def test_test_lines_added_by_a_new_tests_only_stage_land(root: Path) -> None:
    _born(root)
    _, merged = attempt(root, {"tests/test_b.py": RED}, "J1.S3.T1")
    assert merged.returncode == 0, merged.stderr


def test_a_commit_with_no_stage_id_is_its_own_group(root: Path) -> None:
    _born(root)
    _, merged = attempt(root, {"tests/test_b.py": RED})
    assert merged.returncode == 0, merged.stderr


def test_a_pure_rename_lands(root: Path) -> None:
    _born(root)
    _, merged = attempt(root, {}, "J1.S2.T2", mv=("tests/test_a.py", "tests/test_z.py"))
    assert merged.returncode == 0, merged.stderr


def test_a_marker_only_deletion_lands_beside_the_fix(root: Path) -> None:
    _born(root, "@red\n" + RED)
    _, merged = attempt(root, {"tests/test_a.py": RED}, "J1.S2.T2")
    assert merged.returncode == 0, merged.stderr


def test_a_marker_deleted_together_with_another_line_refuses(root: Path) -> None:
    anchor = _born(root, "@red\n" + RED)
    _, merged = attempt(root, {"tests/test_a.py": GREEN}, "J1.S2.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_deleted_line_the_repo_does_not_declare_as_a_marker_refuses(root: Path) -> None:
    anchor = _born(root, "@blue\n" + RED)
    _, merged = attempt(root, {"tests/test_a.py": RED}, "J1.S2.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_worktree_editing_its_own_tests_line_is_still_judged_by_the_work_branch(
    root: Path,
) -> None:
    anchor = _born(root)
    agents = (
        "verify: python scripts/ci.py job\nverify-task: python scripts/ci.py task\ntests: docs/**\n"
    )
    _, merged = attempt(root, {"AGENTS.md": agents, "tests/test_a.py": GREEN}, "J1.S2.T2")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_job_merge_refuses_a_test_edit_that_reached_the_branch_directly(root: Path) -> None:
    anchor = _born(root)
    approve(root, commit(root / TREE, "tests/test_a.py", GREEN))
    merged = run(root, "merge", TREE)
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


def test_a_repo_with_no_tests_line_refuses_until_the_work_branch_declares_it(root: Path) -> None:
    repo = root / "repos/r"
    commit(
        repo,
        "AGENTS.md",
        "verify: python scripts/ci.py job\nverify-task: python scripts/ci.py task\n",
    )
    sha, merged = attempt(root, {"src/a.py": "x = 1\n"}, "J1.S1.T1")
    assert (merged.returncode, fixes(merged)) == (
        1,
        ["fix: Operator action: commit the tests: line on feature/0.5.0's AGENTS.md"],
    )
    commit(repo, "AGENTS.md", "verify-task: python scripts/ci.py task\ntests: tests/**\n")
    landed = run(root, "merge", "worktrees/r/0.5.0-rc1/j1--J1.S1.T1")
    assert landed.returncode == 0, (sha, landed.stderr)


@pytest.mark.xfail(strict=True, reason="a merge commit's own diff is never read")
def test_a_merge_commit_that_edits_a_test_line_refuses(root: Path) -> None:
    anchor = _born(root)
    task = "0.5.0-rc1/j1--J1.S2.T2"
    assert run(root, "new", "r", task).returncode == 0
    tree = root / "worktrees/r" / task
    git(tree, "switch", "-qc", "side")
    commit(tree, "src/b.py")
    git(tree, "switch", "-q", "-")
    git(tree, "merge", "-q", "--no-ff", "--no-commit", "side")
    (tree / "tests/test_a.py").write_text(GREEN)
    git(tree, "add", "tests/test_a.py")
    git(
        tree,
        "commit",
        "-qm",
        "test(J1.S2.T2): merge side",
        "--trailer",
        "Owner-tests: tests/test_r.py",
    )
    merged = run(root, "merge", f"worktrees/r/{task}")
    assert (merged.returncode, fixes(merged)) == (1, _frozen("tests/test_a.py", anchor))


@pytest.mark.xfail(strict=True, reason="the range is work...HEAD, not <merge-base>..HEAD")
def test_a_work_branch_commit_the_job_lacks_is_not_judged_as_the_jobs(root: Path) -> None:
    _born(root)
    repo = root / "repos/r"
    commit(repo, "tests/test_o.py", RED)
    commit(repo, "tests/test_o.py", GREEN)
    _, merged = attempt(root, {"src/b.py": "y = 1\n"}, "J1.S2.T2")
    assert merged.returncode == 0, merged.stderr


@pytest.mark.xfail(strict=True, reason="no RED stage falls back to the range base")
def test_a_job_with_no_commit_naming_its_red_stage_refuses(root: Path) -> None:
    _, merged = attempt(root, {"src/a.py": "x = 1\n"}, "J1.S2.T1")
    assert (merged.returncode, fixes(merged)) == (
        1,
        [
            "fix: Operator action: stop and report — no commit since feature/0.5.0 names its RED stage, so the RED anchor cannot be derived (ADR 0209)"
        ],
    )


def test_a_hotfix_commit_with_no_task_id_holding_code_and_a_marker_deletion_lands(
    root: Path,
) -> None:
    land(root, "tests/test_a.py", "@red\n" + RED, "J1.S1.T1")
    task = "0.5.0-rc1/j1--J1.S2.T1"
    assert run(root, "new", "r", task).returncode == 0
    tree = root / "worktrees/r" / task
    (tree / "src").mkdir()
    (tree / "src/a.py").write_text("x = 1\n")
    (tree / "tests/test_a.py").write_text(RED)
    git(tree, "add", "src/a.py", "tests/test_a.py")
    git(
        tree,
        "commit",
        "-qm",
        "fix(bugs): b1 — the cause",
        "--trailer",
        "Owner-tests: tests/test_r.py",
    )
    merged = run(root, "merge", f"worktrees/r/{task}")
    assert merged.returncode == 0, merged.stderr
