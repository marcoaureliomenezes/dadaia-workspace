"""The state table of a lane path (`_worktree_git.state`): merge, clean, pause, new, resume and `list`
decide a name from it alone, each state prints the one act that ends it, and running that act ends
the state. Size: MEDIUM (real git and a bare remote, tmp workspace).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.cli_line import shell_line
from tests.helpers.oslib import write_text
from tests.helpers.worktree_ws import (
    SCRIPT,
    commit,
    fixes,
    git,
    make_workspace,
    open_tree,
    run,
    run_fix,
)

LANE = "0.5.0/wt-backlog-x"
VERBS = ["merge", "clean", "pause"]


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (ws := tmp_path / "ws").mkdir()
    make_workspace(ws)
    repo = ws / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "origin", "feature/0.5.0")
    return ws


def _line(*words: str) -> str:
    return f"fix: {shell_line(sys.executable, str(SCRIPT.resolve()), *words)}"


def _tree(root: Path) -> Path:
    return root / "worktrees/r" / LANE


def _branch(root: Path) -> str:
    return git(root / "repos/r", "branch", "--list", f"wt/{LANE}").strip()


def _lane(root: Path, commits: bool = True) -> Path:
    tree = open_tree(root, LANE)
    if commits:
        commit(tree, "specs/a.md")
    return tree


def _rows(root: Path) -> list[dict[str, Any]]:
    return json.loads(run(root, "list", "--json").stdout)  # type: ignore[no-any-return]


def _row(root: Path, path: Path) -> dict[str, Any]:
    [row] = [r for r in _rows(root) if r["path"] == str(path)]
    return row


def _refused(root: Path, verb: str, *more: str) -> str:
    """The one fix line the verb's refusal prints."""
    done = run(root, verb, *more)
    assert done.returncode == 1, done.stderr
    (fix,) = fixes(done)
    return fix


def _do(root: Path, fix: str) -> None:
    """Run the command an `Agent action:` line names, as printed."""
    cmd = (re.findall(r"`([^`]+)`", fix) or [fix.removeprefix("fix: ")])[-1]
    run_fix(root, subprocess.CompletedProcess([], 1, "", f"fix: {cmd}"))


def test_a_paused_name_is_taken_and_every_verb_names_resume(root: Path) -> None:
    tree, repo = _lane(root), root / "repos/r"
    tip = git(tree, "rev-parse", "HEAD").strip()
    assert run(root, "pause", str(tree)).returncode == 0
    bundle = next((root / ".dadaia/dist").rglob("*.bundle"))
    kept = bundle.read_bytes()
    resume = _line("resume", str(tree))

    for verb in ("pause", "merge", "clean", "sync"):
        assert _refused(root, verb, str(tree)) == resume
    assert _refused(root, "new", "r", LANE) == resume
    assert bundle.read_bytes() == kept and _branch(root) == ""
    assert _row(root, tree)["exit"] == resume.removeprefix("fix: ")
    run_fix(root, run(root, "new", "r", LANE))

    assert git(tree, "rev-parse", "HEAD").strip() == tip and not bundle.exists()
    assert git(repo, "rev-parse", f"wt/{LANE}").strip() == tip


def test_a_pause_never_replaces_a_bundle_holding_a_commit_the_branch_lacks(root: Path) -> None:
    tree, saved = _lane(root), root.parent / "saved.bundle"
    assert run(root, "pause", str(tree)).returncode == 0
    bundle = next((root / ".dadaia/dist").rglob("*.bundle"))
    shutil.copy(bundle, saved)
    assert run(root, "resume", str(tree)).returncode == 0
    git(tree, "reset", "-q", "--hard", "feature/0.5.0")
    other = commit(tree, "specs/other.md")
    bundle.parent.mkdir(parents=True)
    shutil.copy(saved, bundle)

    refused = run(root, "pause", str(tree))

    assert refused.returncode == 1 and bundle.read_bytes() == saved.read_bytes()
    assert git(tree, "rev-parse", "HEAD").strip() == other
    assert f"move the bundle {bundle} aside" in fixes(refused)[0]
    bundle.rename(root.parent / "aside.bundle")
    assert run(root, "pause", str(tree)).returncode == 0
    assert other in git(root / "repos/r", "bundle", "list-heads", str(bundle))


@pytest.mark.parametrize("verb", [*VERBS, "new", "resume"])
def test_a_moved_tree_is_named_by_every_verb_and_list_and_the_move_back_ends_it(
    root: Path, verb: str
) -> None:
    tree, moved = _lane(root, commits=False), root.parent / "elsewhere"
    git(root / "repos/r", "worktree", "move", "-f", "-f", str(tree), str(moved))
    args = ("r", LANE) if verb == "new" else (str(tree),)

    fix = _refused(root, verb, *args)

    assert fix == _refused(root, "merge", str(tree)) and "worktree move" in fix
    assert _row(root, moved)["state"] == "foreign" and _row(root, moved)["fix"] == fix[5:]
    run_fix(root, run(root, verb, *args))
    assert (tree / "specs").is_dir() and _row(root, tree)["state"] == "empty"


@pytest.mark.parametrize("verb", VERBS)
def test_a_moved_tree_whose_folder_is_gone_is_no_holder_and_the_verb_ends(
    root: Path, verb: str
) -> None:
    tree, moved = _lane(root, commits=verb == "pause"), root.parent / "elsewhere"
    git(root / "repos/r", "worktree", "move", "-f", "-f", str(tree), str(moved))
    shutil.rmtree(moved)
    row = _row(root, moved)
    assert row["state"] == "orphan" and row["exit"] == _line("merge", str(tree))[5:]

    done = run(root, verb, str(tree))

    assert done.returncode == 0, done.stderr
    assert _branch(root) == "" and "elsewhere" not in git(root / "repos/r", "worktree", "list")


@pytest.mark.parametrize("verb", [*VERBS, "new", "resume"])
def test_a_worktree_off_its_branch_at_the_path_is_named_alike_and_the_switch_ends_it(
    root: Path, verb: str
) -> None:
    tree = _lane(root, commits=False)
    git(tree, "switch", "-q", "--detach")
    args = ("r", LANE) if verb == "new" else (str(tree),)

    fix = _refused(root, verb, *args)

    assert fix == _refused(root, "merge", str(tree)) and f"switch wt/{LANE}" in fix
    assert _row(root, tree)["state"] == "foreign" and _row(root, tree)["fix"] == fix[5:]
    _do(root, fix)
    assert _row(root, tree)["state"] == "empty"


@pytest.mark.parametrize("has_branch", [False, True])
@pytest.mark.parametrize("verb", [*VERBS, "new", "sync"])
def test_a_folder_git_does_not_list_is_named_alike_and_the_move_ends_it(
    root: Path, verb: str, has_branch: bool
) -> None:
    tree = _tree(root)
    if has_branch:
        git(root / "repos/r", "branch", f"wt/{LANE}", "feature/0.5.0")
    tree.mkdir(parents=True)
    write_text(tree / "stray.txt", "x\n")
    args = ("r", LANE) if verb == "new" else (str(tree),)

    fix = _refused(root, verb, *args)

    assert fix == _refused(root, "merge", str(tree)) and f"move the folder {tree}" in fix
    assert [r["fix"] for r in _rows(root) if r["state"] == "orphan"] == ([fix[5:]] if has_branch else [])  # fmt: skip
    tree.rename(root.parent / "aside")
    ended = ("merge", str(tree)) if has_branch else ("new", "r", LANE)
    assert run(root, *ended).returncode == 0


@pytest.mark.parametrize("verb", ["merge", "clean"])
def test_a_branch_without_its_tree_is_ended_by_merge_and_clean_and_named_by_new(
    root: Path, verb: str
) -> None:
    repo = root / "repos/r"
    git(repo, "branch", f"wt/{LANE}", "feature/0.5.0")
    assert run(root, "new", "r", LANE).returncode == 1
    assert _refused(root, "new", "r", LANE) == _line("merge", str(_tree(root)))
    assert _rows(root)[-1]["exit"] == _line("merge", str(_tree(root)))[5:]

    assert run(root, verb, str(_tree(root))).returncode == 0
    assert _branch(root) == ""


@pytest.mark.parametrize("verb", [*VERBS, "sync"])
def test_an_absent_name_is_named_alike_and_new_ends_it(root: Path, verb: str) -> None:
    tree = _tree(root)

    fix = _refused(root, verb, str(tree))

    assert fix == _line("new", "r", LANE)
    run_fix(root, run(root, verb, str(tree)))
    assert (tree / "specs").is_dir()


def test_resume_of_a_name_no_bundle_holds_is_an_agent_rerun_never_new(root: Path) -> None:
    fix = _refused(root, "resume", str(_tree(root)))

    assert (
        fix == f"fix: Agent action: rerun with the tree of a bundle under {root / '.dadaia/dist/r'}"
    )


@pytest.mark.parametrize("verb", ["new", "resume"])
def test_an_open_tree_is_named_by_new_and_resume_with_clean(root: Path, verb: str) -> None:
    tree = _lane(root, commits=False)
    args = ("r", LANE) if verb == "new" else (str(tree),)

    assert _refused(root, verb, *args) == _line("clean", str(tree))
    run_fix(root, run(root, verb, *args))
    assert not tree.exists() and _branch(root) == ""


@pytest.mark.parametrize("occupant", ["folder", "worktree"])
@pytest.mark.parametrize("verb", [*VERBS, "new"])
def test_a_branch_held_elsewhere_names_the_act_for_an_occupied_path_before_the_move_back(
    root: Path, verb: str, occupant: str
) -> None:
    tree, moved = _lane(root, commits=False), root.parent / "elsewhere"
    repo = root / "repos/r"
    git(repo, "worktree", "move", "-f", "-f", str(tree), str(moved))
    if occupant == "folder":
        tree.mkdir(parents=True)
        write_text(tree / "stray.txt", "x\n")
    else:
        git(repo, "worktree", "add", "-q", "--detach", str(tree), "feature/0.5.0")
    args = ("r", LANE) if verb == "new" else (str(tree),)

    fix = _refused(root, verb, *args)

    assert fix == _refused(root, "merge", str(tree)) and "worktree move" in fix
    assert fix.index("worktree move") > fix.index("move the folder" if occupant == "folder" else "land the work")  # fmt: skip
    if occupant == "folder":
        tree.rename(root.parent / "aside")
    else:
        git(repo, "worktree", "remove", "--force", "--force", str(tree))
    _do(root, fix)  # the printed move-back, last
    assert (tree / "specs").is_dir() and _row(root, tree)["state"] == "empty"
