#!/usr/bin/env python3
"""`worktree.py new`: derive, lock and mark one canonical worktree, or roll it back."""

from __future__ import annotations

import string
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

from _release_schema import candidate_number, extract_status  # noqa: E402
from _worktree_git import flow_for, git, work_version  # noqa: E402
from _worktree_git import ours as our_trees  # noqa: E402
from _worktree_kinds import CAPS, LOCK, SCRIPT, UNION, Refusal  # noqa: E402


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (root / "worktrees", root / "worktrees" / repo_name):
        if part.is_symlink():
            raise Refusal(f"{part} is a symlink", f"rm {part}")


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
                    f"python3 {SCRIPT} new {repo_name} --kind release",
                )
    ours = [row for row in our_trees(repo) if row["v"] == version]
    same = [row for row in ours if row["kind"] == kind]
    if kind in CAPS and len(same) >= CAPS[kind]:
        raise Refusal(
            f"{kind} cap {CAPS[kind]} reached for {version}",
            f"python3 {SCRIPT} merge {same[0]['path']}",
        )
    taken = {
        b[len(f"wt/{version}")]
        for b in git(
            repo, "branch", "--list", f"wt/{version}?-*", "--format=%(refname:short)"
        ).split()
    }
    free = [letter for letter in string.ascii_lowercase if letter not in taken]
    if not free:
        target = ours[0]["path"] if ours else f"<a worktrees/{repo_name}/{version}?-* tree>"
        raise Refusal(f"letters a-z exhausted for {version}", f"python3 {SCRIPT} clean {target}")
    name = f"{version}{free[0]}-{kind}"
    tree, branch = root / "worktrees" / repo_name / name, f"wt/{name}"
    git(repo, "worktree", "add", "-q", "-b", branch, str(tree), work)
    try:
        git(repo, "worktree", "lock", "--reason", f"{LOCK}{kind}:{version}{free[0]}", str(tree))
        attributes = Path(
            git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        )
        attributes = attributes / "info" / "attributes"
        lines = attributes.read_text(encoding="utf-8").splitlines() if attributes.exists() else []
        if UNION not in lines:
            attributes.parent.mkdir(parents=True, exist_ok=True)
            attributes.write_text("\n".join([*lines, UNION]) + "\n", encoding="utf-8")
    except (OSError, RuntimeError) as error:
        # --force and -D only here: this call made the tree and branch, both hold nothing.
        git(repo, "worktree", "unlock", str(tree), check=False)
        git(repo, "worktree", "remove", "--force", str(tree), check=False)
        git(repo, "branch", "-D", branch, check=False)
        raise Refusal(
            f"rolled back {name}: {error}",
            f"python3 {SCRIPT} new {repo_name} --kind {kind}",
        ) from error
    return tree
