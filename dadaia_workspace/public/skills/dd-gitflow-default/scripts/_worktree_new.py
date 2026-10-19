#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name, on its parent's branch."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from _bugs_check import OPEN
from _grammar import STATE
from _platform import act, command, git_line, is_link
from _specs import check_release, parse
from _worktree_git import flow_for, git, not_a_name, work_version, work_versions
from _worktree_names import (
    LAUNCH,
    LEVEL_FILE,
    LOCK,
    NAME_RE,
    Refusal,
    base_of,
    branch,
    kind_of,
    level_folders,
    tree_path,
)

_LEVELS = Path(__file__).parent / "levels"


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (tree_path(root, ""), tree_path(root, repo_name)):
        if is_link(part):
            raise Refusal(f"{part} is a symlink", command("rm", str(part)))


def _refuse_unopened_bug(main: Path, work: str, bug: str) -> None:
    """A hotfix lane is the fix of one bug the main repo's ledger holds open on *work*."""
    try:
        found = parse(git(main, "show", f"{work}:specs/bugs/BUGS.jsonl", check=False))
    except ValueError:
        found = []
    if not any(r.get("id") == bug and r.get("status") == OPEN for r in found):
        known = any(r.get("id") == bug for r in found)
        what = "the regression as a new bug" if known else f"bug {bug}"
        raise Refusal(f"no open bug record {bug} on {work}",
                      act("operator", f"confirm {what} (dd-bug-registration §2)"))  # fmt: skip


def _refuse_unready(root: Path, main: Path, version: str, rc: str) -> None:
    """A main tree opens only while its release state, on the rc's tree, passes `release.py check` and is in IMPLEMENTATION; no state reads as not."""
    rc_name = f"{version}/{rc}/wt-rc"
    rc_tree = tree_path(root, main.name, rc_name)
    state = rc_tree / "specs/releases" / version / STATE
    if not rc_tree.exists():  # removed by hand while its branch lives
        raise Refusal(f"{rc_tree} does not exist", git_line(main, "worktree", "add", "-f", "-f", str(rc_tree), branch(rc_name)))  # fmt: skip
    phase = None
    if state.is_file():
        check_release(rc_tree / "specs")
        phase = json.loads(state.read_text("utf-8")).get("phase")
    if phase != "IMPLEMENTATION":
        raise Refusal(f"a job needs release {version} in phase IMPLEMENTATION on {branch(rc_name)}",
                      act("agent", f"reach phase IMPLEMENTATION in {STATE} on {branch(rc_name)} at {rc_tree} (release.py phase), then open its job again"))  # fmt: skip


def absent_levels(root: Path, repo_name: str, name: str) -> list[tuple[Path, str]]:
    """The level folders tree *name* needs that do not exist yet, each with its level."""
    return [(f, lv) for f, lv in level_folders(tree_path(root, repo_name), name) if not f.exists()]


def write_level_files(made: list[tuple[Path, str]]) -> None:
    """Writes each level's `AGENTS.md` into its folder, which a tree's `worktree add` created."""
    for folder, level in made:
        shutil.copyfile(_LEVELS / f"{level}.md", folder / LEVEL_FILE)


def new(root: Path, repo_name: str, name: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    match = NAME_RE.match(name)
    if match is None:
        live = work_versions(repo, flow)
        raise not_a_name(name, live[0] if len(live) == 1 else "")
    version = work_version(repo, flow)
    if match["v"] != version:
        raise not_a_name(name, version)
    start = base_of(name, flow["work"]) or ""
    if not git(repo, "branch", "--list", start).strip():  # a tree is cut from its parent's branch
        raise Refusal(f"no {start} branch", command(*LAUNCH, "new", repo.name, start.removeprefix("wt/")))  # fmt: skip
    if kind_of(name) == "main":
        _refuse_unready(root, root / "repos" / flow["main"], version, match["rc"])
    if match["bug"]:
        _refuse_unopened_bug(root / "repos" / flow["main"], start, match["bug"])
    tree = tree_path(root, repo_name, name)
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", command(*LAUNCH, "list"))
    made = absent_levels(root, repo_name, name)
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), start)  # fmt: skip
    write_level_files(made)
    return tree
