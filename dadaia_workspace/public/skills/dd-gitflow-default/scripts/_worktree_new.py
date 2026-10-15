#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name."""

from __future__ import annotations

import re
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
    base,
    branch,
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


def _shape(repo: Path, flow: dict[str, str], name: str) -> tuple[re.Match[str], str]:
    """The grammar match of *name* and the live release version it must name."""
    match = NAME_RE.match(name)
    version = work_version(repo, flow) if match else ""
    if match is None or (match["v"] is not None and match["v"] != version):
        raise not_a_name(name, version)
    return match, version


def _refuse_unready(root: Path, flow: dict[str, str], work: str, version: str, rc: str) -> None:
    """A job opens only while its release is in IMPLEMENTATION on *work*."""
    fix = f"Agent action: repair {STATE} on {work} until release.py check passes"
    main = root / "repos" / flow["main"]  # the context's specs live in its main repo
    try:
        state = parse_object(git(main, "show", f"{work}:specs/releases/{version}/{STATE}", check=False), fix)  # fmt: skip
    except Unreadable as bad:
        raise Refusal(f"{STATE} on {work}: {bad}", bad.fix) from bad
    if state.get("phase") != "IMPLEMENTATION":
        raise Refusal(f"a job needs release {version} in phase IMPLEMENTATION on {work}",
                      f"{script(SCRIPT)} new {quote(flow['main'])} {rc}/define")  # fmt: skip


def _refuse_task(repo: Path, match: re.Match[str], start: str) -> None:
    """A task is cut from its job branch."""
    if not git(repo, "branch", "--list", start).strip():
        job = f"{match['rc']}/{match['job']}"
        raise Refusal(f"no job branch {start}", f"{script(SCRIPT)} new {quote(repo.name)} {job}")


def new(root: Path, repo_name: str, name: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    match, version = _shape(repo, flow, name)
    work = f"{flow['work']}{version}"
    if match["rc"] and match["job"] not in ("define", "reconcile"):
        _refuse_unready(root, flow, work, version, match["rc"])
    if match["bug"]:  # a block-list hotfix: no rc SPEC, only its open bug
        _refuse_unopened_bug(root / "repos" / flow["main"], work, match["bug"])
    start = base(name, work)
    if match["task"]:
        _refuse_task(repo, match, start)
    tree = tree_path(root, repo_name, name)
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", f"{script(SCRIPT)} list")
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), start)  # fmt: skip
    return tree
