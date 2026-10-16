"""`_worktree_git` rows, read through `worktree.py list --json`: `ahead` counts against the
parent branch of the hierarchy, every leftover git does not list is one row per path with its
removal as the fix, and a git failure ends as one refusal. Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import quote
from tests.helpers.worktree_ws import commit, fixes, git, make_workspace, run

RC = "0.5.0/rc-1/wt-rc"
MAIN = "0.5.0/rc-1/job-1/wt-main"
TASK = "0.5.0/rc-1/job-1/wt-task-001"
LANE = "0.5.0/wt-hotfix-some-bug"
_COLUMNS = {
    "repo",
    "path",
    "state",
    "age_hours",
    "registered",
    "name",
    "ahead",
    "dirty",
    "warn",
    "fix",
    "exit",
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    return tmp_path


def _open(root: Path, name: str, base: str = "feature/0.5.0") -> Path:
    tree = root / "worktrees/r" / name
    git(root / "repos/r", "worktree", "add", "-q", "-b", f"wt/{name}", str(tree), base)
    return tree


def _rows(root: Path) -> list[dict[str, Any]]:
    listed = run(root, "list", "--json")
    assert listed.returncode == 0, listed.stderr
    return json.loads(listed.stdout)  # type: ignore[no-any-return]


def test_ahead_counts_against_the_parent_branch(root: Path) -> None:
    _open(root, RC)
    main = _open(root, MAIN, f"wt/{RC}")
    commit(main, "src/a.py")
    task = _open(root, TASK, f"wt/{MAIN}")
    commit(task, "src/b.py")
    commit(task, "src/c.py")
    lane = _open(root, LANE)
    commit(lane, "src/d.py")

    found = {r["name"]: (r["state"], r["ahead"]) for r in _rows(root) if "name" in r}

    assert found == {
        RC: ("empty", 0),
        MAIN: ("ready", 1),
        TASK: ("ready", 2),
        LANE: ("ready", 1),
    }


def test_the_row_schema_and_the_unregistered_rows_stay(root: Path) -> None:
    commit(_open(root, LANE), "src/a.py")
    gone = root / "repos/gone"
    gone.mkdir()
    git(gone, "init", "-q")
    git(gone, "commit", "-q", "--allow-empty", "-m", "init")
    git(gone, "worktree", "add", "-q", "-b", f"wt/{LANE}", str(root / "worktrees/gone" / LANE))

    theirs, ours = sorted(_rows(root), key=lambda r: r["registered"])

    assert (set(ours), ours["registered"], ours["state"]) == (_COLUMNS, True, "ready")
    assert (theirs["registered"], theirs["state"]) == (False, "unregistered")
    assert theirs["fix"].startswith("Agent action: land the work of ")


def test_an_orphan_wt_branch_at_any_depth_is_one_row_with_the_merge_as_its_fix(root: Path) -> None:
    git(root / "repos/r", "branch", f"wt/{TASK}", "feature/0.5.0")

    [orphan] = [r for r in _rows(root) if r["state"] == "orphan"]

    assert orphan["path"] == str(root / "worktrees/r" / TASK)
    assert orphan["fix"].endswith(f"worktree.py merge {quote(orphan['path'])}")


@pytest.mark.parametrize("filled", [True, False], ids=["non-empty", "empty"])
@pytest.mark.parametrize(
    "stray", ["0.5.0/junk", "0.5.0/rc-1/junk", "0.5.0/rc-1/job-1/junk"], ids=["lane", "rc", "job"]
)
def test_a_stray_folder_at_any_depth_is_one_row_whose_fix_removes_it(
    root: Path, stray: str, filled: bool
) -> None:
    _open(root, RC)
    folder = root / "worktrees/r" / stray
    folder.mkdir(parents=True)
    if filled:
        (folder / "f.txt").write_text("x")

    unregistered = [(r["path"], r["fix"]) for r in _rows(root) if r["state"] == "unregistered"]

    assert unregistered == [(str(folder), f"Agent action: remove the directory {folder}")]


def test_an_orphans_surviving_directory_is_the_orphans_row_alone(root: Path) -> None:
    git(root / "repos/r", "branch", f"wt/{LANE}", "feature/0.5.0")
    folder = root / "worktrees/r" / LANE
    folder.mkdir(parents=True)
    (folder / "f.txt").write_text("x")

    [row] = _rows(root)

    assert (row["state"], row["path"]) == ("orphan", str(folder))
    assert row["fix"].startswith(f"Agent action: remove the directory {folder}, then run `")


def test_a_git_failure_in_a_row_read_ends_as_one_refusal_with_an_agent_action_fix(
    root: Path,
) -> None:
    tree = _open(root, LANE)
    (tree / ".git").unlink()  # a tree git no longer recognizes

    refused = run(root, "list", "--json")

    assert refused.returncode == 1 and "Traceback" not in refused.stderr
    [fix] = fixes(refused)
    assert fix.startswith("fix: Agent action: ")


def test_a_symlink_under_worktrees_is_never_walked_into(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (outside / "a/b/c").mkdir(parents=True)
    (outside / "d").mkdir()
    (home := root / "worktrees/r/0.5.0").mkdir(parents=True)
    (home / "link").symlink_to(outside, target_is_directory=True)

    reached = [
        r for r in _rows(root) if Path(r["path"]).resolve().is_relative_to(outside.resolve())
    ]

    assert reached == []
