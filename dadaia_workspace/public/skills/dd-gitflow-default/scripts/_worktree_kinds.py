#!/usr/bin/env python3
"""Worktree kinds: the allowed-set table and the name grammar (ADRs 0106, 0107, 0124) —
module data the gate imports."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

SCRIPT = Path(__file__).parent / "worktree.py"
#: Any path outside `specs/` — code, tests, repo docs.
CODE = "<code>"
#: The TASKS files whose markers replay on a rebase conflict (ADR 0111).
REPLAY = "specs/releases/*/rc-*/TASKS.md"
#: Each kind's allowed set (ADRs 0106, 0124, 0148 (7), 0153), fnmatch globs from the repo root.
KINDS: dict[str, tuple[str, ...]] = {
    "impl": (CODE, REPLAY),
    "bug": (CODE, "specs/bugs/BUGS.jsonl", "specs/bugs/_archive/*"),
    "backlog": ("specs/backlog/*", "specs/ADRs/decisions.jsonl", "specs/bugs/BUGS.jsonl"),
    "release": (
        "specs/releases/*",
        "specs/ADRs/decisions.jsonl",
        "specs/memory/*",
        "specs/*/AGENTS.md",
        "specs/constitution.md",
    ),
}
CAPS = {"impl": 5, "release": 1}
LOCK = "dadaia:"
_NAME_RE = re.compile(r"^(?P<v>\d+\.\d+\.\d+)(?P<l>[a-z])-(?P<k>" + "|".join(KINDS) + r")$")


class Refusal(Exception):
    def __init__(self, message: str, fix: str) -> None:
        super().__init__(message)
        self.fix = fix


def kind_for(rel: str) -> str | None:
    """The kind a workspace-relative path under `worktrees/<repo>/<name>/` belongs to."""
    parts = Path(rel).parts
    match = _NAME_RE.match(parts[2]) if len(parts) > 2 and parts[0] == "worktrees" else None
    return match.group("k") if match else None


def allows(kind: str, path: str) -> bool:
    """Whether repo-relative *path* is inside *kind*'s allowed set."""
    return any(
        not path.startswith("specs/") if glob == CODE else fnmatch.fnmatch(path, glob)
        for glob in KINDS[kind]
    )


def kind_holding(path: str) -> str | None:
    """The first kind whose allowed set holds repo-relative *path*; ``None`` when no kind can merge it."""
    return next((k for k in KINDS if allows(k, path)), None)
