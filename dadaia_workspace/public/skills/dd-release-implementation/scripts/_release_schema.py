#!/usr/bin/env python3
"""The release ledger's vocabulary; schema reading and validation are `_ledger`'s."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

CODE = "LEDGER-RELEASE-SCHEMA"
STATE = "_RELEASE.json"
HISTO = "releases/_archive/releases_histo.jsonl"
#: The closed-scope candidate trio that lives at the release root; the next candidate's
#: `new`-seeded SPEC overwrites it, and git holds the closed one at its CLOSURE commit.
TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")
#: Every artifact `new` refuses to mint over (CWE-73): a release directory is one unit.
ARTIFACTS = (*TRIO, STATE)
#: The four canonical lifecycle phases — pinned equal to the schema's enum by `check`.
PHASES = ("DEFINITION", "IMPLEMENTATION", "CLOSURE", "ARCHIVED")
#: The phases in which the trio is REQUIRED at the release root; DEFINITION sits
#: between candidates, when the next trio is still being authored.
TRIO_PHASES = frozenset({"IMPLEMENTATION", "CLOSURE"})
#: A release ships `delivered` — the one histo disposition this ledger writes.
DELIVERED = "delivered"
APPROVED = "Approved"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
#: A shipped commit sha as a human pastes it from a merge: short (7) to full (40).
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
#: Task markers that mean the candidate is NOT closed: open ``[ ]`` or reserved ``[-]``.
UNFINISHED_RE = re.compile(r"^\s*-\s\[( |-)\]\s.*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_status(text: str) -> str | None:
    """The ``**Status:**`` token a trio document carries, or ``None``."""
    match = _STATUS_RE.search(text)
    return match.group(1) if match else None


def unfinished_tasks(release_dir: Path) -> list[str]:
    """The ``[ ]``/``[-]`` lines TASKS.md still carries — the LINES, so a refusal names
    the task that blocks it. A missing TASKS.md carries none: its absence is the trio
    rule's business, not this one's."""
    tasks = release_dir / "TASKS.md"
    if not tasks.is_file():
        return []
    text = tasks.read_text(encoding="utf-8")
    return [match.group(0).strip() for match in UNFINISHED_RE.finditer(text)]
