#!/usr/bin/env python3
"""The worktree path grammar and its one reader: a tree's name is its path under `worktrees/<repo>/`,
its leaf (`wt-rc`, `wt-main`, `wt-task-NNN`, `wt-backlog-<slug>`, `wt-hotfix-<bug>`) fixes its kind."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from _ledger import load_schema
from _refusal import Refusal as Refusal

SCRIPT = Path(__file__).parent / "worktree.py"
LOCK = "dadaia:"
_WORD = load_schema("backlog-v1")["$defs"]["slug"]["pattern"].removeprefix("^").removesuffix("$")
#: One leaf grammar; a tree's branch is wt/ plus its path.
NAME_RE = re.compile(
    rf"^(?P<v>\d+\.\d+\.\d+)/(?:(?P<rc>rc-\d+)/(?:wt-rc|(?P<job>job-\d+)/wt-(?:main"
    rf"|task-(?P<task>\d{{3}})))|wt-(?:backlog-(?P<slug>{_WORD})|hotfix-(?P<bug>{_WORD})))$"
)


def locate(rel: str) -> tuple[str, str | None, tuple[str, ...]] | None:
    """`(repo, tree name, tail)` of a path under `worktrees/<repo>/`: the name runs to the first
    `wt-` segment, `(repo, None, ())` when there is none; `None` elsewhere."""
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    if len(parts) < 3 or parts[0] != "worktrees":
        return None
    leaf = next((i for i in range(2, len(parts)) if parts[i].startswith("wt-")), None)
    if leaf is None:
        return parts[1], None, ()
    return parts[1], "/".join(parts[2 : leaf + 1]), parts[leaf + 1 :]


def tree_path(root: Path, repo: str, name: str = "") -> Path:
    """The one `worktrees/<repo>/<name>` derivation (the repo's home when *name* is empty)."""
    return root / "worktrees" / repo / name


def branch(name: str) -> str:
    return f"wt/{name}"


def kind_of(name: str) -> str | None:
    """`task`, `main`, `rc`, `backlog` or `hotfix` by the leaf of tree *name*; `None` if no tree."""
    return name.rsplit("/", 1)[-1].split("-")[1] if NAME_RE.match(name) else None


def name_of(ref: str) -> str | None:
    """The tree name a `wt/` branch *ref* belongs to, `None` for any other branch."""
    return ref[3:] if ref.startswith("wt/") and NAME_RE.match(ref[3:]) else None


def base_of(name: str, work_prefix: str) -> str | None:
    """The branch tree *name* is cut from: a task's `wt-main`, a main's `wt-rc`, else the work
    branch `<work_prefix><v>`; `None` if *name* is no tree."""
    match = NAME_RE.match(name)
    if match is None:
        return None
    if match["task"]:
        return branch(f"{match['v']}/{match['rc']}/{match['job']}/wt-main")
    if match["job"]:
        return branch(f"{match['v']}/{match['rc']}/wt-rc")
    return f"{work_prefix}{match['v']}"


def base(name: str, work: str) -> str:
    """`base_of` with the prefix of *work*, the work branch of the name's version; *work* if no tree."""
    return base_of(name, work.removesuffix(name.split("/", 1)[0])) or work


def pushable(ref: str) -> bool:
    """Whether pre-push accepts the `wt/` branch *ref*: a release, main or backlog tree's only."""
    name = name_of(ref)
    return name is not None and kind_of(name) in ("rc", "main", "backlog")
