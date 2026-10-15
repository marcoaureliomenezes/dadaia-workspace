#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name, on its parent's branch."""

from __future__ import annotations

from pathlib import Path

from _bugs_check import OPEN
from _grammar import STATE
from _jsonl import Unreadable, parse_object
from _specs import parse
from _worktree_git import (
    flow_for,
    git,
    not_a_name,
    quote,
    script,
    work_version,
)
from _worktree_names import (
    LOCK,
    NAME_RE,
    SCRIPT,
    Refusal,
    base_of,
    branch,
    kind_of,
    tree_path,
)


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (tree_path(root, ""), tree_path(root, repo_name)):
        if part.is_symlink():
            raise Refusal(f"{part} is a symlink", f"rm {part}")


def _refuse_unopened_bug(main: Path, work: str, bug: str) -> None:
    """A hotfix job is the fix of one bug the main repo's ledger holds open on *work*."""
    try:
        found = parse(git(main, "show", f"{work}:specs/bugs/BUGS.jsonl", check=False))
    except ValueError:
        found = []
    if not any(r.get("id") == bug and r.get("status") == OPEN for r in found):
        raise Refusal(f"no open bug record {bug} on {work}",
                      f"Operator action: confirm bug {bug} so it is registered on {work} as open (dd-bug-registration), then open its hotfix job again")  # fmt: skip


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
        raise Refusal(f"no {start} branch", f"{script(SCRIPT)} new {quote(repo.name)} {start.removeprefix('wt/')}")  # fmt: skip
    if kind_of(name) == "main":
        _refuse_unready(root / "repos" / flow["main"], version, match["rc"])
    if match["bug"]:
        _refuse_unopened_bug(root / "repos" / flow["main"], start, match["bug"])
    tree = tree_path(root, repo_name, name)
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", f"{script(SCRIPT)} list")
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), start)  # fmt: skip
    return tree
