#!/usr/bin/env python3
"""The worktree name grammar and its one path reader — module data the gate
imports: `worktrees/<repo>/<M.m.p>-rc<N>-{define,reconcile,<job>}` inside an rc (a job's tasks
share its tree), `backlog-<slug>` outside one — flat, so every tree sits at the one venv's
`../../../` depth; on the branch `wt/<M.m.p>-rc<N>/<job>` or `wt/backlog/<slug>`."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

SCRIPT = Path(__file__).parent / "worktree.py"
LOCK = "dadaia:"
_WORD = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NAME_RE = re.compile(
    rf"^(?:(?P<rc>(?P<v>\d+\.\d+\.\d+)-rc\d+)-(?P<job>{_WORD})|backlog-(?P<slug>{_WORD}))$"
)
_BRANCH_RE = re.compile(rf"^wt/(?:(\d+\.\d+\.\d+-rc\d+)/({_WORD})|(backlog)/({_WORD}))$")


class Refusal(Exception):
    def __init__(self, message: str, fix: str) -> None:
        super().__init__(message)
        self.fix = fix


def locate(rel: str) -> tuple[str, str | None, tuple[str, ...]] | None:
    """`(repo, tree name, repo-relative tail)` of a workspace-relative path under `repos/<r>/`
    (name `None`) or a canonical `worktrees/<r>/<name>/`; `None` elsewhere — the gate, the
    doctor and reaper (through `list`) and every verb read a worktree path here alone."""
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    if len(parts) >= 2 and parts[0] == "repos":
        return parts[1], None, parts[2:]
    if len(parts) >= 3 and parts[0] == "worktrees" and NAME_RE.match(parts[2]):
        return parts[1], parts[2], parts[3:]
    return None


def branch(name: str) -> str:
    """The branch of tree *name*: its first `-` after the rc (or `backlog`) becomes `/`."""
    match = NAME_RE.match(name)
    head = match["rc"] if match and match["rc"] else "backlog"
    return f"wt/{head}/{name[len(head) + 1 :]}"


def name_of(ref: str) -> str | None:
    """The tree name a `wt/` branch *ref* belongs to, `None` for any other branch."""
    match = _BRANCH_RE.match(ref)
    return "-".join(g for g in match.groups() if g) if match else None


def non_code(name: str) -> bool:
    """A `define` or `backlog` tree: its merge lands `specs/` only, reviewed, untested."""
    match = NAME_RE.match(name)
    return match is not None and (match["job"] == "define" or match["slug"] is not None)
