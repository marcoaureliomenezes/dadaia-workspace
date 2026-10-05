#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

from _release_schema import extract_status  # noqa: E402
from _worktree_git import flow_for, git, quote, script, work_version  # noqa: E402
from _worktree_names import LOCK, NAME_RE, SCRIPT, Refusal, branch  # noqa: E402


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (root / "worktrees", root / "worktrees" / repo_name):
        if part.is_symlink():
            raise Refusal(f"{part} is a symlink", f"rm {part}")


def new(root: Path, repo_name: str, name: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    version = work_version(repo, flow)
    work = f"{flow['work']}{version}"
    match = NAME_RE.match(name)
    if match is None or match["v"] not in (None, version):
        shape = f"{version}-rc<N>-<job>"
        raise Refusal(
            f"{name!r} is not a worktree name: {shape}, {version}-rc<N>-define or backlog-<slug>",
            f"{script(SCRIPT)} list",
        )
    if match["rc"] and match["job"] != "define":  # a job runs only under an Approved SPEC
        main = root / "repos" / flow["main"]  # the context's trio lives in its main repo
        rc = match["rc"].rpartition("-rc")[2]
        spec = git(main, "show", f"{work}:specs/releases/{version}/rc-{rc}/SPEC.md", check=False)
        if extract_status(spec) != "Approved":
            raise Refusal(
                f"a job needs an Approved rc-{rc}/SPEC.md on {work}",
                f"{script(SCRIPT)} new {quote(flow['main'])} {match['rc']}-define",
            )
    tree = root / "worktrees" / repo_name / name
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", f"{script(SCRIPT)} list")
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), work)  # fmt: skip
    return tree
