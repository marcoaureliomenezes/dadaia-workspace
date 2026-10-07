#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name."""

from __future__ import annotations

import sys
from pathlib import Path

for _skill in ("dd-release-implementation", "dd-bug-resolution"):
    sys.path.append(str(Path(__file__).resolve().parents[2] / _skill / "scripts"))

from _release_schema import extract_status  # noqa: E402
from _specs import parse  # noqa: E402
from _worktree_git import flow_for, git, ours, quote, rows, script, work_version  # noqa: E402
from _worktree_names import LOCK, NAME_RE, SCRIPT, TASK_CAP, Refusal, base, branch  # noqa: E402


def _refuse_symlink(root: Path, repo_name: str) -> None:
    for part in (root / "worktrees", root / "worktrees" / repo_name):
        if part.is_symlink():
            raise Refusal(f"{part} is a symlink", f"rm {part}")


def _exit(root: Path, path: str) -> str:
    """The worktree's one exit, `clean` or `merge`, as `rows()` rules it."""
    return next(str(row["exit"]) for row in rows(root) if row["path"] == path)


def _refuse_unopened_bug(main: Path, work: str, bug: str) -> None:
    """A hotfix job is the fix of one bug the main repo's ledger holds open on *work*."""
    try:
        found = parse(git(main, "show", f"{work}:specs/bugs/BUGS.jsonl", check=False))
    except ValueError:
        found = []
    if not any(r.get("id") == bug and r.get("status") == "open" for r in found):
        raise Refusal(f"no open bug record {bug} on {work}",
                      f"Operator action: register bug {bug} on {work} as open (dd-bug-registration), then open its hotfix job again")  # fmt: skip


def new(root: Path, repo_name: str, name: str) -> Path:
    repo = root / "repos" / repo_name
    _refuse_symlink(root, repo_name)
    flow = flow_for(root, repo)
    version = work_version(repo, flow)
    work = f"{flow['work']}{version}"
    match = NAME_RE.match(name)
    if match is None or match["v"] not in (None, version):
        shape = f"{version}-rc<N>/<job>[--<task-id>]"
        raise Refusal(
            f"{name!r} is not a worktree name: {shape}, {version}-rc<N>/define, backlog/<slug> or hotfix/<bug-id>",
            f"{script(SCRIPT)} list",
        )
    if match["rc"] and match["job"] != "define":  # a job runs only under an Approved SPEC
        main = root / "repos" / flow["main"]  # the context's trio lives in its main repo
        rc = match["rc"].rpartition("-rc")[2]
        spec = git(main, "show", f"{work}:specs/releases/{version}/rc-{rc}/SPEC.md", check=False)
        if extract_status(spec) != "Approved":
            raise Refusal(
                f"a job needs an Approved rc-{rc}/SPEC.md on {work}",
                f"{script(SCRIPT)} new {quote(flow['main'])} {match['rc']}/define",
            )
    if match["bug"]:  # a block-list hotfix: no rc SPEC, only its open bug
        _refuse_unopened_bug(root / "repos" / flow["main"], work, match["bug"])
    start = base(name, work)
    if match["task"]:  # cut from its job branch; at most TASK_CAP open per rc
        tasks = [r for r in ours(repo) if (m := NAME_RE.match(r["name"])) and m["task"]
                 and m["rc"] == match["rc"]]  # fmt: skip
        if len(tasks) >= TASK_CAP:
            raise Refusal(f"{TASK_CAP} task worktrees are open in {match['rc']}",
                          _exit(root, tasks[0]["path"]))  # fmt: skip
        if not git(repo, "branch", "--list", start).strip():
            job = f"{match['rc']}/{match['job']}"
            raise Refusal(
                f"no job branch {start}", f"{script(SCRIPT)} new {quote(repo_name)} {job}"
            )
    tree = root / "worktrees" / repo_name / name
    if git(repo, "branch", "--list", branch(name)).strip():
        raise Refusal(f"{branch(name)} exists", f"{script(SCRIPT)} list")
    git(repo, "worktree", "add", "-q", "--lock", "--reason", f"{LOCK}{name}", "-b", branch(name),
        str(tree), start)  # fmt: skip
    return tree
