"""`worktree.py merge` decides from git and the instance alone: a path nothing ever opened refuses
and a tree whose branch is unmerged is never success; an rc merge runs the instance's ledger scripts,
never one the tree tracks; a crashed check relays a fix line that is not about findings; the
test-path fallback is one rule. Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.helpers.oslib import write_text
from tests.helpers.worktree_ws import (
    NEW_JOB,
    NEW_TASK,
    approve,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    patch_cli,
    run,
)

RC, LANE = "0.5.0/rc-1/wt-rc", "0.5.0/wt-backlog-c"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    return tmp_path


def test_a_never_opened_path_refuses_with_one_fix_line(root: Path) -> None:
    refused = run(root, "merge", str(root / f"worktrees/r/{NEW_TASK}"))

    assert refused.returncode == 1
    assert "merged" not in refused.stdout
    assert len(fixes(refused)) == 1


def test_a_gone_tree_whose_branch_is_unmerged_is_never_success(root: Path) -> None:
    open_tree(root, RC)
    open_tree(root, NEW_JOB)
    task = open_tree(root, NEW_TASK)
    commit(task, "src/a.py")
    shutil.rmtree(task)
    git(root / "repos/r", "worktree", "prune")

    refused = run(root, "merge", str(task))

    assert refused.returncode == 1
    assert len(fixes(refused)) == 1


def test_an_rc_merge_never_runs_a_ledger_script_the_tree_tracks(root: Path) -> None:
    tree = open_tree(root, RC)
    marker = root / "ran"
    for skill, script in (
        ("dd-bug-resolution", "bugs.py"),
        ("dd-backlog-definition", "backlog.py"),
        ("dd-release-implementation", "release.py"),
    ):
        sha = commit(
            tree,
            f"dadaia_workspace/public/skills/{skill}/scripts/{script}",
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        )
    approve(root, sha, name=RC)

    run(root, "merge", str(tree))

    assert not marker.exists()


def test_a_crashed_check_relays_a_fix_line_that_is_not_about_findings(root: Path) -> None:
    patch_cli(root, 'sys.exit(os.path.exists(os.path.join(specs, "RED-doctor")))', 'raise RuntimeError("boom")')  # fmt: skip
    tree = open_tree(root, LANE)
    approve(root, commit(tree, "specs/notes", ""), name=LANE)

    refused = run(root, "merge", str(tree))

    assert refused.returncode == 1
    (fix,) = fixes(refused)
    assert "findings above" not in fix
    assert "doctor" in fix


@pytest.mark.parametrize(("subject", "lands"), [("test(J1.T1): red", True), ("feat(J1.T1): code", False)])  # fmt: skip
def test_the_fallback_test_path_rule_reaches_a_tests_folder_at_any_depth(
    root: Path, subject: str, lands: bool
) -> None:
    open_tree(root, RC)
    open_tree(root, NEW_JOB)
    task = open_tree(root, NEW_TASK)
    (task / "pkg/tests").mkdir(parents=True)
    write_text(task / "pkg/tests/helpers.py", "value = 1\n")
    git(task, "add", "pkg/tests/helpers.py")
    git(task, "commit", "-qm", subject)

    done = run(root, "merge", str(task))

    assert (done.returncode == 0) is lands, done.stderr
