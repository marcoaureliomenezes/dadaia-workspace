#!/usr/bin/env python3
"""The worktree name grammar and its one path reader: one-segment plain changes plus release,
backlog and hotfix trees. A task tree is cut from its job branch and lands back on it."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from _grammar import TASK_ID_RE
from _ledger import load_schema
from _refusal import Refusal as Refusal

SCRIPT = Path(__file__).parent / "worktree.py"
LOCK = "dadaia:"


def _unanchored(pattern: str) -> str:
    return pattern.removeprefix("^").removesuffix("$")


#: The backlog slug (single hyphens: `--` separates a job from its task) and the release task id.
_WORD = _unanchored(load_schema("backlog-v1")["$defs"]["slug"]["pattern"])
_TASK = rf"(?:--(?P<task>{_unanchored(TASK_ID_RE.pattern)}))?"
NAME_RE = re.compile(
    rf"^(?:(?P<rc>(?P<v>\d+\.\d+\.\d+)-rc\d+)/(?P<job>{_WORD}){_TASK}|backlog/(?P<slug>{_WORD})"
    rf"|hotfix/(?P<bug>{_WORD})|(?P<plain>(?!(?:backlog|hotfix)$){_WORD}))$"
)


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
    if len(parts) >= 3 and parts[0] == "worktrees":
        return parts[1], parts[2], parts[3:]
    return None


def tree_path(root: Path, repo: str, name: str = "") -> Path:
    """The one `worktrees/<repo>/<name>` derivation (the repo's home when *name* is empty)."""
    return root / "worktrees" / repo / name


def branch(name: str) -> str:
    return f"wt/{name}"


def name_of(ref: str) -> str | None:
    """The tree name a `wt/` branch *ref* belongs to, `None` for any other branch."""
    return ref[3:] if ref.startswith("wt/") and NAME_RE.match(ref[3:]) else None


def base(name: str, work: str) -> str:
    """The branch tree *name* is cut from and lands on: its job branch for a task, else *work*."""
    match = NAME_RE.match(name)
    return branch(f"{match['rc']}/{match['job']}") if match and match["task"] else work


def plain(name: str) -> bool:
    """Whether *name* is the one-segment light-worktree shape."""
    match = NAME_RE.match(name)
    return bool(match and match["plain"])


def non_code(name: str) -> bool:
    """A `define` or `backlog` tree: its merge lands `specs/` only, reviewed, untested."""
    match = NAME_RE.match(name)
    return match is not None and (match["job"] == "define" or match["slug"] is not None)


def pushable(ref: str) -> bool:
    """A `wt/` branch pre-push accepts: a job's or a backlog tree's; never a task's, `define`'s
    or any other `wt/` branch."""
    match = NAME_RE.match(name_of(ref) or "")
    return bool(
        match
        and not match["task"]
        and (match["slug"] is not None or match["job"] not in (None, "define"))
    )
