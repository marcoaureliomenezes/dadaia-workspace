"""`_worktree_git` rows, read through `worktree.py list --json`: `ahead` counts against the
parent branch of the hierarchy, every leftover git does not list is one row per path with its
removal as the fix, and a git failure ends as one refusal. Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import git_inline, quote
from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.harness_env import run_bash
from tests.helpers.oslib import link, write_text
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
    "kind",
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


def test_each_named_row_carries_the_kind_of_its_leaf(root: Path) -> None:
    _open(root, RC)
    _open(root, MAIN, f"wt/{RC}")
    _open(root, TASK, f"wt/{MAIN}")
    _open(root, LANE)
    git(root / "repos/r", "branch", "wt/0.5.0/wt-backlog-an-idea", "feature/0.5.0")

    found = {r["name"] if "name" in r else Path(r["path"]).name: r["kind"] for r in _rows(root)}

    assert found == {
        RC: "rc",
        MAIN: "main",
        TASK: "task",
        LANE: "hotfix",
        "wt-backlog-an-idea": "backlog",
    }


def test_every_row_state_the_owner_emits_carries_an_exit_or_a_fix(
    root: Path, tmp_path: Path
) -> None:
    repo = root / "repos/r"
    _open(root, TASK)
    commit(_open(root, LANE), "src/a.py")
    dirty_tree = _open(root, "0.5.0/wt-backlog-idea")
    commit(dirty_tree, "src/b.py")
    write_text(dirty_tree / "loose.txt", "x")
    git(repo, "branch", "wt/0.5.0/rc-1/job-2/wt-main", "feature/0.5.0")
    git(repo, "branch", "wt/0.5.0/wt-hotfix-dead", "feature/0.5.0")
    (root / "worktrees/r/0.5.0/wt-hotfix-dead").mkdir(parents=True)
    gone = _open(root, MAIN)
    commit(gone, "src/c.py")
    shutil.rmtree(gone)
    git(repo, "branch", "wt/old-merged", "feature/0.5.0")
    old = tmp_path / "old-unmerged"
    git(repo, "worktree", "add", "-q", "-b", "wt/old-unmerged", str(old), "feature/0.5.0")
    commit(old, "src/d.py")
    git(repo, "worktree", "remove", str(old))
    git(
        repo, "worktree", "add", "-q", "-b", "elsewhere", str(tmp_path / "foreign"), "feature/0.5.0"
    )
    (root / "worktrees/r/stray").mkdir()

    found = [r for r in _rows(root) if r["path"] != str(repo)]

    assert sorted(r["state"] for r in found) == [
        "empty", "foreign", "open", "orphan", "orphan", "orphan", "orphan", "orphan",
        "ready", "unregistered",
    ]  # fmt: skip
    assert [r["kind"] for r in found if r.get("name") == MAIN] == ["main"]
    assert [r["path"] for r in found if not (r["exit"] or r["fix"])] == []
    by_name = {Path(r["path"]).name: r for r in found}
    assert by_name["old-unmerged"]["exit"] == ""
    assert "wt/old-unmerged" in by_name["old-unmerged"]["fix"]
    assert by_name["old-merged"]["exit"] == by_name["old-merged"]["fix"] != ""
    assert by_name["foreign"]["exit"] == ""
    assert by_name["foreign"]["fix"].startswith("Agent action: land")


def test_a_name_refusal_with_no_live_version_names_no_fixed_one() -> None:
    refusal = load_owner("dd-gitflow-default", "_worktree_git").not_a_name("bogus")

    assert "0.5.0" not in str(refusal)
    assert "<M.m.p>/rc-<N>/wt-rc" in str(refusal)


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


@pytest.mark.parametrize("ahead", [False, True], ids=["merged", "unmerged"])
def test_an_off_grammar_orphan_branch_has_an_exit_only_when_git_branch_d_runs(
    root: Path, ahead: bool
) -> None:
    repo = root / "repos/r"
    tip = "feature/0.5.0"
    if ahead:
        tip = git(repo, "commit-tree", "-p", tip, "-m", "x", f"{tip}^{{tree}}").strip()
    git(repo, "branch", "wt/stray", tip)

    [orphan] = [r for r in _rows(root) if r["state"] == "orphan"]

    assert (orphan["fix"], orphan["exit"]) == (
        (
            "Agent action: land or archive the wt/* branch wt/stray, then close again",
            "",
        )
        if ahead
        else (
            f"Agent action: run `{git_inline(repo, 'switch', tip)}`, "
            f"then run `{git_inline(repo, 'branch', '-d', 'wt/stray')}`",
        )
        * 2
    )


def test_an_off_grammar_orphan_branch_with_a_diverged_upstream_is_deleted_by_its_line(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    repo = root / "repos/r"
    origin = tmp_path_factory.mktemp("origin")
    git(origin, "init", "-q", "--bare")
    git(repo, "remote", "add", "origin", str(origin))
    other = git(repo, "commit-tree", "-m", "x", "feature/0.5.0^{tree}").strip()
    git(repo, "push", "-q", "origin", f"{other}:refs/heads/wt/stray")
    git(repo, "fetch", "-q", "origin")
    git(repo, "branch", "--track", "wt/stray", "feature/0.5.0")
    git(repo, "branch", "--set-upstream-to", "origin/wt/stray", "wt/stray")

    [orphan] = [r for r in _rows(root) if r["state"] == "orphan"]
    env = {**os.environ, "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"}
    for step in re.findall(r"`([^`]+)`", orphan["fix"]) or [orphan["fix"]]:
        run_bash(step, cwd=root, env=env, check=True)

    assert git(repo, "branch", "--list", "wt/stray") == ""
    assert orphan["exit"] == orphan["fix"]


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
        write_text(folder / "f.txt", "x")

    unregistered = [(r["path"], r["fix"]) for r in _rows(root) if r["state"] == "unregistered"]

    assert unregistered == [(str(folder), f"Agent action: remove the directory {folder}")]


def test_an_orphans_surviving_directory_is_the_orphans_row_alone(root: Path) -> None:
    git(root / "repos/r", "branch", f"wt/{LANE}", "feature/0.5.0")
    folder = root / "worktrees/r" / LANE
    folder.mkdir(parents=True)
    write_text(folder / "f.txt", "x")

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
    assert link(str(outside), home / "link", is_dir=True)

    reached = [
        r for r in _rows(root) if Path(r["path"]).resolve().is_relative_to(outside.resolve())
    ]

    assert reached == []


@pytest.mark.parametrize(
    ("rel", "stray"),
    [
        ("foo", "foo"),
        ("0.5.0/foo", "0.5.0/foo"),
        ("0.5.0/rc-1/job-1/job-2", "0.5.0/rc-1/job-1/job-2"),
        ("0.5.0", None),
    ],
)
def test_a_folder_holding_only_an_agents_file_is_layout_only_at_the_depth_its_name_fits(
    root: Path, rel: str, stray: str | None
) -> None:
    (root / "worktrees/r" / rel).mkdir(parents=True)
    write_text(root / "worktrees/r" / rel / "AGENTS.md", "x")
    found = [r["path"] for r in _rows(root) if r["state"] == "unregistered"]
    assert found == ([] if stray is None else [str(root / "worktrees/r" / stray)])


@pytest.mark.parametrize("merged", [True, False], ids=["merged", "unmerged"])
def test_the_several_work_fix_deletes_a_pushed_low_branch_that_has_later_commits(
    tmp_path: Path, merged: bool
) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    git(tmp_path, "init", "-q", "--bare", "o.git")
    repo = tmp_path / "r"
    git(tmp_path, "init", "-q", "r")
    commit(repo, "a.txt")
    git(repo, "remote", "add", "origin", str(tmp_path / "o.git"))
    git(repo, "switch", "-q", "-c", "feature/0.1.0")
    git(repo, "push", "-q", "-u", "origin", "feature/0.1.0")
    commit(repo, "later.txt")
    git(repo, "switch", "-q", "-c", "feature/0.2.0", "main")
    if merged:
        git(repo, "merge", "-q", "--no-edit", "feature/0.1.0")
    passes = 0
    while True:
        try:
            assert owner.work_version(repo, {"work": "feature/"}) == "0.2.0"
            break
        except owner.SeveralWork as refused:
            passes += 1
            steps = refused.text.split(", then ")
            assert len(steps) <= 3
            for step in steps:
                if step.startswith("merge "):
                    git(repo, "merge", "-q", "--no-edit", "feature/0.1.0")
                else:
                    subprocess.run(step.removeprefix("run ").strip("`"), shell=True, check=True)
    assert passes == (1 if merged else 2)
    assert "feature/0.1.0" not in git(repo, "branch", "--list", "feature/*")


ORIGIN = "refs/remotes/origin"


def _repo_with_origin(tmp_path: Path, local: list[str], origin: list[str]) -> Path:
    """A repo whose local work branches are *local* and whose origin holds *origin*."""
    git(tmp_path, "init", "-q", "--bare", "o.git")
    repo = tmp_path / "r"
    git(tmp_path, "init", "-q", "r")
    commit(repo, "a.txt")
    git(repo, "remote", "add", "origin", str(tmp_path / "o.git"))
    for version in origin:
        git(repo, "push", "-q", "origin", f"HEAD:refs/heads/feature/{version}")
    git(repo, "fetch", "-q", "origin")
    for version in local:
        git(repo, "branch", f"feature/{version}")
    return repo


def test_a_default_read_judges_local_branches_only_whatever_origin_holds(tmp_path: Path) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    repo = _repo_with_origin(tmp_path, ["0.8.0"], ["0.6.0", "0.8.0"])
    flow = {"work": "feature/", "integration": "develop", "main": "r"}

    assert owner.work_versions(repo, flow) == ["0.8.0"]
    assert owner.work_version(repo, flow) == "0.8.0"


def test_the_origin_read_lists_the_work_branches_origin_holds_and_keeps_the_highest(
    tmp_path: Path,
) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    repo = _repo_with_origin(tmp_path, ["0.8.0"], ["0.6.0", "0.8.0"])
    flow = {"work": "feature/", "integration": "develop", "main": "r"}

    assert sorted(owner.work_versions(repo, flow, ORIGIN)) == ["0.6.0", "0.8.0"]
    with pytest.raises(owner.SeveralWork) as several:
        owner.work_version(repo, flow, ORIGIN)
    assert several.value.keep == "0.8.0"


@pytest.mark.parametrize("merged", [True, False], ids=["drop-merged-low", "merge-unmerged-low"])
def test_the_several_work_decision_yields_the_kept_version_and_the_local_act(
    tmp_path: Path, merged: bool
) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    repo = _repo_with_origin(tmp_path, ["0.6.0", "0.8.0"], [])
    if not merged:
        git(repo, "switch", "-q", "feature/0.6.0")
        commit(repo, "low.txt")
    flow = {"work": "feature/"}

    keep, text = owner.several_work(repo, flow, ["0.6.0", "0.8.0"])

    assert keep == "0.8.0"
    switch = f"run `{owner.git_inline(repo, 'switch', 'feature/0.8.0')}`"
    if merged:
        assert (
            text
            == f"{switch}, then run `{owner.git_inline(repo, 'branch', '-d', 'feature/0.6.0')}`"
        )
    else:
        assert text == f"{switch}, then merge feature/0.6.0 into feature/0.8.0"


def test_an_origin_only_lower_work_branch_yields_no_local_step(tmp_path: Path) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    repo = _repo_with_origin(tmp_path, ["0.8.0"], ["0.6.0", "0.8.0"])

    assert owner.several_work(repo, {"work": "feature/"}, ["0.6.0", "0.8.0"], ORIGIN) == ("0.8.0", "")  # fmt: skip


def test_the_several_work_act_reads_the_merged_state_and_upstream_in_one_git_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    repo = _repo_with_origin(tmp_path, ["0.6.0", "0.8.0"], ["0.6.0"])
    git(repo, "branch", "--set-upstream-to=origin/feature/0.6.0", "feature/0.6.0")
    reads: list[tuple[str, ...]] = []
    real = owner.git
    monkeypatch.setattr(owner, "git", lambda tree, *args, **kw: (reads.append(args), real(tree, *args, **kw))[1])  # fmt: skip

    owner.several_work(repo, {"work": "feature/"}, ["0.6.0", "0.8.0"])

    assert len(reads) == 1, reads


def test_the_child_cli_is_handed_the_denylist_file_the_loader_reads(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = load_owner("dd-gitflow-default", "_worktree_git")
    workspace = root / ".dadaia/states/privacy_denylist.json"
    write_text(workspace, '{"zorblax": "private"}')
    write_text(root / "empty.json", "{}")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(root / "empty.json"))  # exists, holds no term
    seen: list[dict[str, str]] = []

    def spawn(_root: Path, *_args: str, env: dict[str, str], **_kw: Any) -> subprocess.CompletedProcess[str]:  # fmt: skip
        seen.append(env)
        return subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(owner, "run_cli", spawn)

    owner.cli(root, "doctor", tree=root / "worktrees/r/tree")

    assert [e["DADAIA_PRIVACY_DENYLIST"] for e in seen] == [str(workspace)]
