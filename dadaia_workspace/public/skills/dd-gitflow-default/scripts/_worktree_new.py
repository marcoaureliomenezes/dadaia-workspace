#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name, on its parent's branch."""

from __future__ import annotations

import shutil
from pathlib import Path

from _bugs_check import OPEN
from _grammar import STATE
from _jsonl import Unreadable, parse_object
from _platform import command, is_link
from _specs import parse
from _worktree_git import flow_for, git, not_a_name, work_version
from _worktree_names import (
    LAUNCH,
    LOCK,
    NAME_RE,
    Refusal,
    base_of,
    branch,
    kind_of,
    tree_path,
)

_LEVELS = Path(__file__).parent / "levels"
_LEVEL_FILES = ("version", "rc", "job")  # the folder at each depth under worktrees/<repo>/


def _level_folders(home: Path, name: str) -> list[tuple[Path, str]]:
    """The level folders *name* sits in under *home*, outermost first, each with its level file."""
    parts = name.split("/")[:-1]
    return [(home.joinpath(*parts[:i]), level) for i, level in enumerate(_LEVEL_FILES[: len(parts)], 1)]  # fmt: skip


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
        act = "the regression as a new bug" if known else f"bug {bug}"
        raise Refusal(f"no open bug record {bug} on {work}",
                      f"Operator action: confirm {act} (dd-bug-registration §2)")  # fmt: skip


def _refuse_unready(main: Path, version: str, rc: str) -> None:
    """A main tree opens only while its release is in IMPLEMENTATION on the rc's `wt-rc` branch."""
    rc_branch = branch(f"{version}/{rc}/wt-rc")
    fix = f"Agent action: repair {STATE} on {rc_branch} until release.py check passes"
    try:
        state = parse_object(git(main, "show", f"{rc_branch}:specs/releases/{version}/{STATE}", check=False), fix)  # fmt: skip
    except Unreadable as bad:
        raise Refusal(f"{STATE} on {rc_branch}: {bad}", bad.fix) from bad
    if state.get("phase") != "IMPLEMENTATION":
        raise Refusal(f"a job needs release {version} in phase IMPLEMENTATION on {rc_branch}",
                      f"Agent action: reach phase IMPLEMENTATION in {STATE} on {rc_branch} (release.py phase), then open its job again")  # fmt: skip


def new(root: Path, repo_name: str, name: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    match = NAME_RE.match(name)
    version = work_version(repo, flow) if match else ""
    if match is None or match["v"] != version:
        raise not_a_name(name, version)
    start = base_of(name, flow["work"]) or ""
    if not git(repo, "branch", "--list", start).strip():  # a tree is cut from its parent's branch
        raise Refusal(f"no {start} branch", command(*LAUNCH, "new", repo.name, start.removeprefix("wt/")))  # fmt: skip
    if kind_of(name) == "main":
        _refuse_unready(root / "repos" / flow["main"], version, match["rc"])
    if match["bug"]:
        _refuse_unopened_bug(root / "repos" / flow["main"], start, match["bug"])
    tree = tree_path(root, repo_name, name)
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", command(*LAUNCH, "list"))
    made = [(folder, level) for folder, level in _level_folders(tree_path(root, repo_name), name) if not folder.exists()]  # fmt: skip
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), start)  # fmt: skip
    for folder, level in made:
        shutil.copyfile(_LEVELS / f"{level}.md", folder / "AGENTS.md")
    return tree
