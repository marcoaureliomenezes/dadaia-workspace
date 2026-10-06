#!/usr/bin/env python3
"""The worktree name grammar and its one path reader — module data the gate imports: a folder
per rc holding sibling trees, `worktrees/<repo>/<M.m.p>-rc<N>/{define,reconcile,<job>,
<job>--<task-id>}`, and `worktrees/<repo>/backlog/<slug>` outside one; tree name `<a>/<b>` is
on the branch `wt/<a>/<b>`. A task tree is cut from its job branch and lands back on it."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

SCRIPT = Path(__file__).parent / "worktree.py"
LOCK = "dadaia:"
#: Task worktrees open at once per rc.
TASK_CAP = 5
_WORD = r"[a-z0-9]+(?:-[a-z0-9]+)*"  # single hyphens: `--` separates a job from its task
_TASK = r"(?:--(?P<task>[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*))?"
NAME_RE = re.compile(
    rf"^(?:(?P<rc>(?P<v>\d+\.\d+\.\d+)-rc\d+)/(?P<job>{_WORD}){_TASK}|backlog/(?P<slug>{_WORD}))$"
)


class Refusal(Exception):
    def __init__(self, message: str, fix: str) -> None:
        super().__init__(message)
        self.fix = fix


def locate(rel: str) -> tuple[str, str | None, tuple[str, ...]] | None:
    """`(repo, tree name, repo-relative tail)` of a workspace-relative path under `repos/<r>/`
    (name `None`) or `worktrees/<r>/<a>/<b>/` at its fixed depth, whatever the name — whether
    it is canonical is `NAME_RE`'s question, not this one; `None` elsewhere. The gate, the
    doctor and reaper (through `list`) and every verb read a worktree path here alone."""
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    if len(parts) >= 2 and parts[0] == "repos":
        return parts[1], None, parts[2:]
    if len(parts) >= 4 and parts[0] == "worktrees":
        return parts[1], f"{parts[2]}/{parts[3]}", parts[4:]
    return None


def branch(name: str) -> str:
    return f"wt/{name}"


def name_of(ref: str) -> str | None:
    """The tree name a `wt/` branch *ref* belongs to, `None` for any other branch."""
    return ref[3:] if ref.startswith("wt/") and NAME_RE.match(ref[3:]) else None


def base(name: str, work: str) -> str:
    """The branch tree *name* is cut from and lands on: its job branch for a task, else *work*."""
    match = NAME_RE.match(name)
    return branch(f"{match['rc']}/{match['job']}") if match and match["task"] else work


def non_code(name: str) -> bool:
    """A `define` or `backlog` tree: its merge lands `specs/` only, reviewed, untested."""
    match = NAME_RE.match(name)
    return match is not None and (match["job"] == "define" or match["slug"] is not None)


def pushable(ref: str) -> bool:
    """A `wt/` branch pre-push accepts: a job's (its push runs the CI matrix) or a backlog
    tree's; never a task's, `define`'s or any other `wt/` branch."""
    match = NAME_RE.match(name_of(ref) or "")
    return match is not None and match["job"] != "define" and not match["task"]
