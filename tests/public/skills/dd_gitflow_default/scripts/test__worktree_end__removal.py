"""A merged or cleaned worktree leaves
nothing behind — its parent folder once empty, and its branch on the remote when it was pushed — and
`list` shows a directory that holds no tree. Size: MEDIUM (real git and a bare remote, tmp workspace).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.platform import quote
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import (
    PERMISSIONS_ENFORCED,
    command,
    make_readonly,
    make_writable,
    write_text,
)
from tests.helpers.worktree_ws import (
    NEW_JOB,
    approve,
    commit,
    fixes,
    git,
    land,
    make_workspace,
    open_tree,
    run,
    run_fix,
)

RC = "0.5.0/rc-1/wt-rc"
JOB2 = "0.5.0/rc-1/job-2/wt-main"
BRANCH = f"wt/{NEW_JOB}"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    git(ws / "repos/r", "checkout", "-q", "feature/0.5.0")
    open_tree(ws, RC)
    assert open_tree(ws, NEW_JOB).is_dir()
    return ws


def _push_to_a_remote(root: Path) -> None:
    remote = root.parent / "remote.git"
    git(root.parent, "init", "-q", "--bare", str(remote))
    git(root / "repos/r", "remote", "add", "origin", str(remote))
    git(root / "repos/r", "push", "-q", "-u", "origin", BRANCH)


def _on_the_remote(root: Path) -> str:
    return git(root / "repos/r", "ls-remote", "--heads", "origin", BRANCH).strip()


def test_a_merge_removes_the_emptied_job_folder_and_the_pushed_branch(root: Path) -> None:
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    _push_to_a_remote(root)
    assert _on_the_remote(root)
    merged = run(root, "merge", f"worktrees/r/{NEW_JOB}")
    assert merged.returncode == 0, merged.stderr
    assert not (root / "worktrees/r/0.5.0/rc-1/job-1").exists()
    assert _on_the_remote(root) == ""


def test_clean_removes_the_emptied_job_folder_and_the_pushed_branch(root: Path) -> None:
    _push_to_a_remote(root)
    cleaned = run(root, "clean", f"worktrees/r/{NEW_JOB}")
    assert cleaned.returncode == 0, cleaned.stderr
    assert not (root / "worktrees/r/0.5.0/rc-1/job-1").exists()
    assert _on_the_remote(root) == ""


def test_a_merge_removes_a_level_folder_left_holding_only_its_file(root: Path) -> None:
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    assert (root / "worktrees/r/0.5.0/rc-1/job-1/AGENTS.md").is_file()
    assert run(root, "merge", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert not (root / "worktrees/r/0.5.0/rc-1/job-1").exists()
    assert (root / "worktrees/r" / RC).is_dir()  # the rc folder still holds its tree


def test_clean_removes_a_level_folder_left_holding_only_its_file(root: Path) -> None:
    rc_folder = root / "worktrees/r/0.5.0/rc-1"
    assert (rc_folder / "job-1/AGENTS.md").is_file() and (rc_folder / "AGENTS.md").is_file()
    assert run(root, "clean", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert run(root, "clean", f"worktrees/r/{RC}").returncode == 0
    assert not rc_folder.exists()


def test_a_level_folder_holding_a_sibling_tree_keeps_its_file(root: Path) -> None:
    assert open_tree(root, JOB2).is_dir()
    assert run(root, "clean", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert (root / "worktrees/r/0.5.0/rc-1/AGENTS.md").is_file()
    assert (root / "worktrees/r" / JOB2).is_dir()


def test_clean_of_the_last_tree_under_a_version_removes_the_version_folder(root: Path) -> None:
    version = root / "worktrees/r/0.5.0"
    assert (version / "AGENTS.md").is_file()
    assert run(root, "clean", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert run(root, "clean", f"worktrees/r/{RC}").returncode == 0
    assert not version.exists()


def test_a_version_folder_holding_an_open_lane_keeps_its_file(root: Path) -> None:
    lane = "0.5.0/wt-backlog-an-idea"
    assert open_tree(root, lane).is_dir()
    assert run(root, "clean", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert run(root, "clean", f"worktrees/r/{RC}").returncode == 0
    assert (root / "worktrees/r/0.5.0/AGENTS.md").is_file()
    assert (root / "worktrees/r" / lane).is_dir()


def test_a_merge_with_no_remote_still_lands_and_keeps_a_sibling_tree(root: Path) -> None:
    """No remote is assumed: nothing to delete there, and a parent folder still holding a tree stays."""
    assert open_tree(root, JOB2).is_dir()
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    assert run(root, "merge", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert (root / "worktrees/r" / JOB2).is_dir()


def test_list_reports_a_directory_that_holds_no_tree(root: Path) -> None:
    (root / "worktrees/r/0.5.0-rc9").mkdir(parents=True)
    (root / "worktrees/r/stray").mkdir()  # a one-level directory holding only a file
    write_text(root / "worktrees/r/stray/f.txt", "x")
    rows = json.loads(run(root, "list", "--json").stdout)
    assert [(r["state"], r["path"]) for r in rows if r["state"] != "empty"] == [
        ("unregistered", str(root / "worktrees/r/0.5.0-rc9")),
        ("unregistered", str(root / "worktrees/r/stray")),
    ]


def test_list_gives_one_row_per_path_the_orphan_winning(root: Path) -> None:
    assert (tree := open_tree(root, JOB2)).is_dir()
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
    tree.mkdir()  # the branch stays; the directory survives, files only
    write_text(tree / "f.txt", "x")
    rows = json.loads(run(root, "list", "--json").stdout)
    assert [(r["state"], r["path"]) for r in rows if r["state"] != "empty"] == [
        ("orphan", str(tree))
    ]


def test_an_orphan_whose_directory_survives_names_the_move_and_following_it_empties_list(
    root: Path,
) -> None:
    assert (tree := open_tree(root, JOB2)).is_dir()
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
    tree.mkdir()
    write_text(tree / "f.txt", "x")
    [row] = [r for r in json.loads(run(root, "list", "--json").stdout) if r["state"] != "empty"]
    assert row["fix"] == f"Agent action: stop what holds files open in {tree}, then move the folder {tree} out of the lane path (it may hold work)"  # fmt: skip
    assert row["exit"] == row["fix"]  # the closure refusal and `context dead` print `exit`
    tree.rename(root.parent / "aside")  # the act the fix names
    assert run(root, "merge", str(tree)).returncode == 0
    assert [
        r for r in json.loads(run(root, "list", "--json").stdout) if r["state"] != "empty"
    ] == []


@pytest.mark.parametrize(
    ("ref", "shape", "lacks"),
    [
        # refuses unmerged commits, never forces: branch -d, never -D
        ("wt/0.4.0-rc9/job-1", lambda line, _path: " branch -d " in line, " -D "),
        # lands its commits: the merge of its own path, never a branch -d
        (
            f"wt/{JOB2}",
            lambda line, path: line.endswith(f"worktree.py merge {quote(path)}"),
            " branch -d ",
        ),
    ],
    ids=["old-grammar", "named"],
)
def test_a_wt_branch_with_no_tree_is_removed_by_its_rows_fix_line(
    root: Path, ref: str, shape, lacks: str
) -> None:
    git(root / "repos/r", "branch", ref, "feature/0.5.0")
    [row] = [
        r
        for r in json.loads(run(root, "list", "--json").stdout)
        if r["state"] == "orphan"
        and r["path"] == str(root / "worktrees/r" / ref.removeprefix("wt/"))
    ]
    assert row["fix"] and row["exit"] == row["fix"]
    line = row["fix"].split("`")[-2] if "`" in row["fix"] else row["fix"]
    assert shape(line, row["path"]), line
    assert lacks not in line

    run_fix(root, subprocess.CompletedProcess([], 1, "", f"fix: {line}\n"))

    assert git(root / "repos/r", "branch", "--list", ref).strip() == ""
    assert [
        r for r in json.loads(run(root, "list", "--json").stdout) if r["state"] == "orphan"
    ] == []


def _push_upstream(root: Path, remote_name: str) -> Path:
    remote = root.parent / f"{remote_name}.git"
    git(root.parent, "init", "-q", "--bare", str(remote))
    git(root / "repos/r", "remote", "add", remote_name, str(remote))
    git(root / "repos/r", "push", "-q", "-u", remote_name, BRANCH)
    return remote


def test_a_merge_deletes_the_pushed_branch_on_a_non_origin_upstream(root: Path) -> None:
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    remote = _push_upstream(root, "mirror")
    merged = run(root, "merge", f"worktrees/r/{NEW_JOB}")
    assert merged.returncode == 0, merged.stderr
    assert git(root.parent, "-C", str(remote), "branch", "--list", BRANCH).strip() == ""


def test_a_refused_remote_delete_is_reported_with_its_fix_line(root: Path) -> None:
    remote = _push_upstream(root, "origin")
    git(root.parent, "-C", str(remote), "config", "receive.denyDeletes", "true")
    cleaned = run(root, "clean", f"worktrees/r/{NEW_JOB}")
    assert BRANCH in cleaned.stderr + cleaned.stdout
    assert "fix: " in cleaned.stderr + cleaned.stdout


def test_clean_leaves_a_folder_no_level_names_holding_only_an_agents_file(root: Path) -> None:
    (root / "worktrees/r/foo").mkdir()
    write_text(root / "worktrees/r/foo/AGENTS.md", "x")
    assert run(root, "clean", f"worktrees/r/{NEW_JOB}").returncode == 0
    assert (root / "worktrees/r/foo/AGENTS.md").is_file()


def _gone(root: Path) -> Path:
    """The job tree removed by hand, its folder and branch left; the tree's path."""
    tree = root / "worktrees/r" / NEW_JOB
    git(root / "repos/r", "worktree", "remove", "-f", "-f", str(tree))
    return tree


def test_a_gone_tree_merged_behind_its_upstream_is_removed_with_its_pushed_branch(
    root: Path,
) -> None:
    land(root, "src/a.py")
    _push_to_a_remote(root)
    land(root, "src/b.py")  # the branch moves past what the upstream holds
    git(root / "worktrees/r" / RC, "merge", "-q", "--ff-only", BRANCH)
    _gone(root)

    merged = run(root, "merge", f"worktrees/r/{NEW_JOB}")

    assert merged.returncode == 0, merged.stderr
    assert git(root / "repos/r", "branch", "--list", BRANCH).strip() == ""
    assert _on_the_remote(root) == ""


def test_a_gone_tree_whose_parent_is_off_its_branch_keeps_the_pushed_branch_until_switched(
    root: Path,
) -> None:
    rc = root / "worktrees/r" / RC
    land(root, "src/a.py")
    git(rc, "merge", "-q", "--ff-only", BRANCH)
    _push_to_a_remote(root)
    git(rc, "switch", "-q", "-c", "elsewhere")
    _gone(root)

    refused = run(root, "merge", f"worktrees/r/{NEW_JOB}")

    fix = [f for f in refused.stderr.splitlines() if f.startswith("fix: ")]
    assert refused.returncode == 1 and fix == [f"fix: {command('git', '-C', str(rc), 'switch', f'wt/{RC}')}"]  # fmt: skip
    assert _on_the_remote(root)
    run_fix(root, refused)
    merged = run(root, "merge", f"worktrees/r/{NEW_JOB}")
    assert merged.returncode == 0, merged.stderr
    assert git(root / "repos/r", "branch", "--list", BRANCH).strip() == ""
    assert _on_the_remote(root) == ""


def test_a_gone_tree_with_an_unmerged_branch_refuses_with_the_fix_that_restores_it_locked(
    root: Path,
) -> None:
    land(root, "src/a.py")
    tree = _gone(root)

    refused = run(root, "merge", f"worktrees/r/{NEW_JOB}")

    [fix] = [f for f in refused.stderr.splitlines() if f.startswith("fix: ")]
    assert refused.returncode == 1 and " worktree add -f -f --lock " in fix, refused.stderr
    run_fix(root, refused)
    assert (tree / ".git").exists()
    assert BRANCH in git(root / "repos/r", "branch", "--list", BRANCH)


def test_a_merged_orphan_wt_branch_is_dropped_by_its_rows_fix_when_head_is_elsewhere(
    root: Path,
) -> None:
    repo, ref = root / "repos/r", "wt/0.4.0-rc9/job-1"
    commit(repo, "ahead.txt")  # the work branch moves past `main`
    git(repo, "branch", ref)
    git(repo, "checkout", "-q", "main")
    [row] = [
        r
        for r in json.loads(run(root, "list", "--json").stdout)
        if r["state"] == "orphan"
        and r["path"] == str(root / "worktrees/r" / ref.removeprefix("wt/"))
    ]
    assert " branch -d " in row["fix"], row["fix"]

    for step in row["fix"].split("`")[1::2] or [row["fix"]]:
        run_fix(root, subprocess.CompletedProcess([], 1, "", f"fix: {step}\n"))

    assert git(repo, "branch", "--list", ref).strip() == ""


def _branch_argv_of_a_clean(root: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    end: Any = load_owner("dd-gitflow-default", "_worktree_end")
    real, seen = end.git, []

    def record(repo: Path, *args: str, **kw: Any) -> str:
        if args[0] == "branch" and args[1] != "--show-current":
            seen.append(list(args))
        return real(repo, *args, **kw)

    monkeypatch.setattr(end, "git", record)
    end.clean(root, str(root / "worktrees/r" / NEW_JOB), [], False)
    return seen


def test_a_branch_with_an_upstream_is_unset_then_deleted(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _push_to_a_remote(root)
    assert _branch_argv_of_a_clean(root, monkeypatch) == [
        ["branch", "--unset-upstream", BRANCH],
        ["branch", "-d", BRANCH],
    ]


def test_a_branch_with_no_upstream_is_deleted_alone(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _branch_argv_of_a_clean(root, monkeypatch) == [["branch", "-d", BRANCH]]


def _stuck(root: Path, verb: str) -> Path:
    """The job tree to *verb* with a root folder git cannot empty: git forgets the tree, the folder stays."""
    if verb == "merge":
        approve(root, land(root, "fe/a.py"), name=NEW_JOB)
    make_readonly(tree := root / "worktrees/r" / NEW_JOB)
    return tree


@pytest.mark.skipif(not PERMISSIONS_ENFORCED, reason="needs a folder this process cannot empty")
@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_folder_git_cannot_delete_is_named_and_the_rerun_ends_the_tree(
    root: Path, verb: str
) -> None:
    tree = _stuck(root, verb)
    aside = root.parent / "aside"
    # the folder is still there, no longer a worktree: the same act, not a dead end
    for _ in range(2):
        refused = run(root, verb, str(tree))
        assert refused.returncode == 1
        (fix,) = fixes(refused)
        assert fix == f"fix: Agent action: stop what holds files open in {tree}, then move the folder {tree} out of the lane path (it may hold work)"  # fmt: skip
    make_writable(tree)
    tree.rename(aside)
    done = run(root, verb, str(tree))
    assert done.returncode == 0, done.stderr
    assert git(root / "repos/r", "branch", "--list", BRANCH).strip() == ""


@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_tree_git_lists_off_its_branch_keeps_its_files(root: Path, verb: str) -> None:
    tree = root / "worktrees/r" / NEW_JOB
    git(tree, "switch", "-q", "--detach")
    commit(tree, ".gitignore", "secret.env\n")
    write_text(tree / "secret.env", "key\n")
    refused = run(root, verb, str(tree))
    assert refused.returncode == 1
    assert (tree / "secret.env").read_text() == "key\n"
    assert str(tree) in git(root / "repos/r", "worktree", "list")


def test_a_remove_git_refuses_on_a_listed_tree_keeps_gits_message(root: Path) -> None:
    end: Any = load_owner("dd-gitflow-default", "_worktree_end")
    repo, tree, name, onto = end.target(root, str(root / "worktrees/r" / NEW_JOB))
    write_text(tree / "work.txt", "x")
    with pytest.raises(RuntimeError) as raised:
        end._remove(repo, tree, onto, name, [])
    assert "untracked" in str(raised.value) and "move the folder" not in str(raised.value)
    assert str(tree) in git(repo, "worktree", "list")


@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_folder_in_the_way_of_an_unmerged_branch_is_moved_before_the_tree_comes_back(
    root: Path, verb: str
) -> None:
    land(root, "src/a.py")
    tree = _gone(root)
    tree.mkdir()
    write_text(tree / "notes.txt", "mine\n")

    refused = run(root, verb, str(tree))

    assert refused.returncode == 1
    (fix,) = fixes(refused)
    assert f"move the folder {tree} out of the lane path" in fix
    assert (tree / "notes.txt").read_text() == "mine\n"
    tree.rename(root.parent / "aside")
    (again,) = fixes(run(root, verb, str(tree)))
    assert " worktree add -f -f --lock " in again


@pytest.mark.parametrize("verb", ["merge", "clean", "pause"])
def test_a_tree_git_lists_at_another_path_is_named_and_never_ended(root: Path, verb: str) -> None:
    repo, tree, moved = root / "repos/r", root / "worktrees/r" / RC, root.parent / "elsewhere"
    git(repo, "worktree", "move", "-f", "-f", str(tree), str(moved))
    write_text(moved / "notes.txt", "mine\n")

    refused = run(root, verb, str(tree))

    assert refused.returncode == 1
    assert str(moved) in refused.stderr
    assert (moved / "notes.txt").read_text() == "mine\n"
    assert git(repo, "branch", "--list", f"wt/{RC}").strip() != ""
    assert f"{moved} " in git(repo, "worktree", "list")
    assert not (root / ".dadaia/dist").exists()
    run_fix(root, refused)
    assert f"{tree} " in git(repo, "worktree", "list")
    assert str(moved) not in run(root, verb, str(tree)).stderr
