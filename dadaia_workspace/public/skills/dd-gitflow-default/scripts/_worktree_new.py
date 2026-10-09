#!/usr/bin/env python3
"""`worktree.py new`: open and lock one canonical worktree by its name."""

from __future__ import annotations

import json
import sys
from pathlib import Path

for _skill in ("dd-release-implementation", "dd-bug-resolution"):
    sys.path.append(str(Path(__file__).resolve().parents[2] / _skill / "scripts"))

from _release_schema import STATE, live_ids  # noqa: E402
from _specs import parse  # noqa: E402
from _worktree_git import (  # noqa: E402
    flow_for,
    git,
    ours,
    quote,
    record_base,
    rows,
    script,
    work_version,
)
from _worktree_names import (  # noqa: E402
    LOCK,
    NAME_RE,
    SCRIPT,
    TASK_CAP,
    Refusal,
    base,
    branch,
    plain,
)


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
    match = NAME_RE.match(name)
    version = work_version(repo, flow) if not (match and plain(name)) else ""
    if match is None or (match["v"] is not None and match["v"] != version):
        version = version or work_version(repo, flow)
        shape = f"{version}-rc<N>/<job>[--<task-id>]"
        raise Refusal(
            f"{name!r} is not a worktree name: {shape}, {version}-rc<N>/define, backlog/<slug> or hotfix/<bug-id>",
            f"{script(SCRIPT)} list",
        )
    if plain(name):
        releases = live_ids(root / "repos" / flow["main"] / "specs")
        if len(releases) > 1:
            raise Refusal("multiple live releases make the plain worktree base ambiguous",
                          f"Operator action: make exactly one release live in repos/{flow['main']}/specs")  # fmt: skip
        start = (
            f"{flow['work']}{releases[0]}"
            if releases
            else git(repo, "branch", "--show-current").strip()
        )
        if not start:
            raise Refusal("a plain worktree needs a checked-out base branch when no release is live",
                          f"Operator action: switch {repo} to the branch this change should return to")  # fmt: skip
        work = start
    else:
        work = f"{flow['work']}{version}"
    if match["rc"] and match["job"] not in ("define", "reconcile"):
        main = root / "repos" / flow["main"]  # the context's trio lives in its main repo
        state = git(main, "show", f"{work}:specs/releases/{version}/{STATE}", check=False)
        if json.loads(state).get("phase") != "IMPLEMENTATION":
            raise Refusal(
                f"a job needs release {version} in phase IMPLEMENTATION on {work}",
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
    if plain(name):
        record_base(repo, name, start)
    return tree
