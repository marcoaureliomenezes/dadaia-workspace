#!/usr/bin/env python3
"""The worktree path grammar and its one reader: a tree's name is its path under `worktrees/<repo>/`,
its leaf (`wt-rc`, `wt-main`, `wt-task-NNN`, `wt-backlog-<slug>`, `wt-hotfix-<bug>`) fixes its kind."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

from _ledger import load_schema
from _refusal import Refusal as Refusal

SCRIPT = Path(__file__).parent / "worktree.py"
#: The words that run this script: `command(*LAUNCH, verb, …)` is a finished fix line.
LAUNCH = (sys.executable, str(SCRIPT.resolve()))
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


#: The folder at each depth under `worktrees/<repo>/`: its level and its name.
_LEVELS = (("version", r"\d+\.\d+\.\d+"), ("rc", r"rc-\d+"), ("job", r"job-\d+"))
LEVEL_FILE = "AGENTS.md"


def level_folders(home: Path, name: str) -> list[tuple[Path, str]]:
    """The level folders tree *name* sits in under *home*, outermost first, each with its level."""
    parts = name.split("/")[:-1]
    return [(home.joinpath(*parts[:i]), _LEVELS[i - 1][0]) for i in range(1, len(parts) + 1)]


def is_bare_level(home: Path, folder: Path) -> bool:
    """Whether *folder* is a level folder under *home*, named for its depth, holding only its file."""
    parts = folder.relative_to(home).parts
    named = 0 < len(parts) <= len(_LEVELS) and all(
        re.fullmatch(_LEVELS[i][1], p) for i, p in enumerate(parts)
    )
    return named and [p.name for p in folder.iterdir()] == [LEVEL_FILE]


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


def pushable(ref: str) -> bool:
    """Whether pre-push accepts the `wt/` branch *ref*: a release, main or backlog tree's only."""
    name = name_of(ref)
    return name is not None and kind_of(name) in ("rc", "main", "backlog")
