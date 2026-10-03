#!/usr/bin/env python3
"""`worktree.py new`: derive and lock one canonical worktree."""

from __future__ import annotations

import string
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

from _release_schema import candidate_number, extract_status  # noqa: E402
from _worktree_git import flow_for, git, quote, rows, script, work_version  # noqa: E402
from _worktree_git import ours as our_trees  # noqa: E402
from _worktree_kinds import CAPS, LOCK, SCRIPT, Refusal  # noqa: E402


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (root / "worktrees", root / "worktrees" / repo_name):
        if part.is_symlink():
            raise Refusal(f"{part} is a symlink", f"rm {part}")


def _exit(root: Path, path: str) -> str:
    """The worktree's one exit, `clean` or `merge`, as `rows()` rules it (ADR 0128)."""
    return next(str(row["exit"]) for row in rows(root) if row["path"] == path)


def new(root: Path, repo_name: str, kind: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    version = work_version(repo, flow)
    work = f"{flow['work']}{version}"
    if kind == "impl":
        release = f"{work}:specs/releases/{version}"
        rc = candidate_number(git(repo, "ls-tree", "--name-only", release, check=False).split())
        for doc in ("SPEC", "PLAN", "TASKS"):
            text = git(repo, "show", f"{release}/rc-{rc}/{doc}.md", check=False)
            if extract_status(text) != "Approved":
                raise Refusal(
                    f"impl needs an Approved trio; {doc}.md on {work} is not",
                    f"{script(SCRIPT)} new {quote(repo_name)} --kind release",
                )
    ours = [row for row in our_trees(repo) if row["v"] == version]
    same = [row for row in ours if row["kind"] == kind]
    if kind in CAPS and len(same) >= CAPS[kind]:
        raise Refusal(
            f"{kind} cap {CAPS[kind]} reached for {version}", _exit(root, same[0]["path"])
        )
    taken = {
        b[len(f"wt/{version}")]
        for b in git(
            repo, "branch", "--list", f"wt/{version}?-*", "--format=%(refname:short)"
        ).split()
    }
    free = [letter for letter in string.ascii_lowercase if letter not in taken]
    if not free:
        target = (f"Operator action: choose one of the worktrees/{repo_name}/{version}?-* trees "
                  f"and run `{script(SCRIPT)} clean` with it")  # fmt: skip
        raise Refusal(
            f"letters a-z exhausted for {version}", _exit(root, ours[0]["path"]) if ours else target
        )
    name = f"{version}{free[0]}-{kind}"
    tree, branch = root / "worktrees" / repo_name / name, f"wt/{name}"
    reason = f"{LOCK}{kind}:{version}{free[0]}"
    git(repo, "worktree", "add", "-q", "--lock", "--reason", reason, "-b", branch, str(tree), work)
    return tree
