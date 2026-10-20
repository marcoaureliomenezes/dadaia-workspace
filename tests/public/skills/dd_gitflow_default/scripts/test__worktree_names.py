"""`_worktree_names`: the hierarchy's one path reader. A tree name is the path under
`worktrees/<repo>/`; its leaf (`wt-rc`, `wt-main`, `wt-task-NNN`, `wt-backlog-<slug>`,
`wt-hotfix-<bug>`) fixes its kind, its base branch and whether its branch is pushable. Pure
functions, no git. Size: SMALL.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner

_names = load_owner("dd-gitflow-default", "_worktree_names")

TASK = "0.5.0/rc-1/job-1/wt-task-001"
MAIN = "0.5.0/rc-1/job-1/wt-main"
RC = "0.5.0/rc-1/wt-rc"
BACKLOG = "0.5.0/wt-backlog-some-slug"
HOTFIX = "0.5.0/wt-hotfix-some-bug"


def _fn(name: str) -> Callable[..., Any]:
    """Resolved at call time so a missing function fails its own row, not the collection."""
    return getattr(_names, name)  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        pytest.param(
            f"worktrees/r/{TASK}/secrets/k", ("r", TASK, ("secrets", "k")), id="task-with-tail"
        ),
        pytest.param(f"worktrees/r/{MAIN}/src/a.py", ("r", MAIN, ("src", "a.py")), id="main"),
        pytest.param(f"worktrees/r/{RC}/specs", ("r", RC, ("specs",)), id="rc"),
        pytest.param(f"worktrees/r/{BACKLOG}", ("r", BACKLOG, ()), id="backlog-no-tail"),
        pytest.param(f"worktrees/r/{HOTFIX}/x", ("r", HOTFIX, ("x",)), id="hotfix"),
        pytest.param(
            f"worktrees/r\\{TASK}\\src\\a.py", ("r", TASK, ("src", "a.py")), id="backslashes"
        ),
        pytest.param("worktrees/r/a/b/secrets/k", ("r", None, ()), id="no-wt-leaf"),
        pytest.param("worktrees/r/0.5.0/rc-1/job-1", ("r", None, ()), id="job-folder-is-no-tree"),
    ],
)
def test_locate_keys_on_the_first_wt_segment(
    rel: str, expected: tuple[str, str | None, tuple[str, ...]]
) -> None:
    assert _fn("locate")(rel) == expected


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        (TASK, "task"),
        (MAIN, "main"),
        (RC, "rc"),
        (BACKLOG, "backlog"),
        (HOTFIX, "hotfix"),
        ("0.5.0/rc-1/job-1/wt-task-1", None),
        ("0.5.0-rc1/j1", None),
        ("0.5.0-rc1/j1--J1.T1", None),
        ("0.5.0-rc1/define", None),
        ("0.5.0-rc1/reconcile", None),
        ("scratch", None),
    ],
)
def test_kind_of_reads_the_leaf(name: str, kind: str | None) -> None:
    assert _fn("kind_of")(name) == kind


@pytest.mark.parametrize(
    ("name", "base"),
    [
        (TASK, "wt/0.5.0/rc-1/job-1/wt-main"),
        (MAIN, "wt/0.5.0/rc-1/wt-rc"),
        ("0.6.1/rc-12/job-3/wt-task-014", "wt/0.6.1/rc-12/job-3/wt-main"),
        (RC, "feature/0.5.0"),
        (BACKLOG, "feature/0.5.0"),
        (HOTFIX, "feature/0.5.0"),
    ],
)
def test_base_of_walks_task_to_main_to_rc_to_the_work_branch(name: str, base: str) -> None:
    assert _fn("base_of")(name, "feature/") == base


def test_base_of_takes_its_work_prefix_from_the_gitflow() -> None:
    assert _fn("base_of")(RC, "release/") == "release/0.5.0"


@pytest.mark.parametrize(
    ("ref", "pushable"),
    [
        (f"wt/{RC}", True),
        (f"wt/{MAIN}", True),
        (f"wt/{BACKLOG}", True),
        (f"wt/{TASK}", False),
        (f"wt/{HOTFIX}", False),
        ("wt/0.5.0-rc1/j1", False),
        ("wt/0.5.0-rc1/define", False),
        ("wt/scratch", False),
        ("feature/0.5.0", False),
    ],
)
def test_pushable_holds_for_rc_main_and_backlog_only(ref: str, pushable: bool) -> None:
    assert _fn("pushable")(ref) is pushable


@pytest.mark.parametrize("name", [TASK, MAIN, RC, BACKLOG, HOTFIX])
def test_a_branch_is_wt_plus_the_path_and_name_of_inverts_it(name: str) -> None:
    assert _fn("branch")(name) == f"wt/{name}"
    assert _fn("name_of")(f"wt/{name}") == name


@pytest.mark.parametrize("ref", ["feature/0.5.0", "wt/0.5.0-rc1/j1", "wt/scratch", "wt/0.5.0/rc-1"])
def test_name_of_refuses_a_ref_that_is_no_tree_branch(ref: str) -> None:
    assert _fn("name_of")(ref) is None


@pytest.mark.parametrize(
    ("name", "levels"),
    [
        (TASK, [("0.5.0", "version"), ("0.5.0/rc-1", "rc"), ("0.5.0/rc-1/job-1", "job")]),
        (MAIN, [("0.5.0", "version"), ("0.5.0/rc-1", "rc"), ("0.5.0/rc-1/job-1", "job")]),
        (RC, [("0.5.0", "version"), ("0.5.0/rc-1", "rc")]),
        (BACKLOG, [("0.5.0", "version")]),
    ],
)
def test_level_folders_are_the_folders_a_name_sits_in_each_with_its_level_file(
    tmp_path: Path, name: str, levels: list[tuple[str, str]]
) -> None:
    assert _fn("level_folders")(tmp_path, name) == [(tmp_path / rel, kind) for rel, kind in levels]


@pytest.mark.parametrize(
    ("rel", "files", "bare"),
    [
        ("0.5.0", ["AGENTS.md"], True),
        ("0.5.0/rc-1", ["AGENTS.md"], True),
        ("0.5.0/rc-1/job-1", ["AGENTS.md"], True),
        ("0.5.0/rc-1/job-1", ["AGENTS.md", "note.txt"], False),
        ("0.5.0/rc-1/job-1", [], False),
        ("foo", ["AGENTS.md"], False),
        ("0.5.0/foo", ["AGENTS.md"], False),
        ("rc-1", ["AGENTS.md"], False),
        ("0.5.0/rc-1/job-1/job-2", ["AGENTS.md"], False),
    ],
)
def test_a_bare_level_folder_holds_only_its_file_and_is_named_for_its_depth(
    tmp_path: Path, rel: str, files: list[str], bare: bool
) -> None:
    folder = tmp_path / rel
    folder.mkdir(parents=True)
    for file in files:
        (folder / file).write_text("x")
    assert _fn("is_bare_level")(tmp_path, folder) is bare


@pytest.mark.parametrize("level", ["version", "rc", "job"])
def test_a_level_file_runs_five_to_ten_lines(level: str) -> None:
    text = (Path(_names.__file__).parent / "levels" / f"{level}.md").read_text(encoding="utf-8")
    assert 5 <= len(text.splitlines()) <= 10
