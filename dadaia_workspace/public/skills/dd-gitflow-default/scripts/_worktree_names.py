#!/usr/bin/env python3
"""The worktree name grammar (ADR 0191) and its one path reader — module data the gate
imports: `<M.m.p>-rc<N>/{define,reconcile,<job>}` inside an rc (a job's tasks share its tree),
`backlog/<slug>` outside one; each on the branch `wt/<name>`."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

SCRIPT = Path(__file__).parent / "worktree.py"
LOCK = "dadaia:"
_WORD = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NAME_RE = re.compile(
    rf"^(?:(?P<rc>(?P<v>\d+\.\d+\.\d+)-rc\d+)/(?P<job>{_WORD})|backlog/(?P<slug>{_WORD}))$"
)


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
    if len(parts) >= 4 and parts[0] == "worktrees" and NAME_RE.match(f"{parts[2]}/{parts[3]}"):
        return parts[1], f"{parts[2]}/{parts[3]}", parts[4:]
    return None


def non_code(name: str) -> bool:
    """A `define` or `backlog` tree: its merge lands `specs/` only, reviewed, untested."""
    match = NAME_RE.match(name)
    return match is not None and (match["job"] == "define" or match["slug"] is not None)
