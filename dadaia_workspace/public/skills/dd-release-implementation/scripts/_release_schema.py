#!/usr/bin/env python3
"""The release ledger's vocabulary; schema reading and validation are `_ledger`'s."""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable
from pathlib import Path

CODE = "LEDGER-RELEASE-SCHEMA"
STATE = "_RELEASE.json"
HISTO = "releases/_archive/releases_histo.jsonl"
#: One candidate's trio, born in its own `rc-<N>/` and never rewritten after closure (ADR 0150).
TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")
#: A candidate folder; the live one is the highest N — `core.release_state.CANDIDATE_RE`.
CANDIDATE_RE = re.compile(r"^rc-([1-9][0-9]*)$")
#: The three lifecycle phases — pinned equal to the schema's enum; a shipped release
#: moves whole to `_archive/<v>/` (ADR 0152 (1)).
PHASES = ("DEFINITION", "IMPLEMENTATION", "CLOSURE")
#: The phases in which the live candidate's trio is REQUIRED; DEFINITION is authoring it.
TRIO_PHASES = frozenset({"IMPLEMENTATION", "CLOSURE"})
#: A release ships `delivered` — the one histo disposition this ledger writes.
DELIVERED = "delivered"
APPROVED = "Approved"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
#: A shipped commit sha as a human pastes it from a merge: short (7) to full (40).
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
#: Task markers that mean the candidate is NOT closed: open ``[ ]`` or reserved ``[-]``,
#: under any Markdown bullet (``-``, ``*``, ``+``) or none — the ONE task-marker rule.
UNFINISHED_RE = re.compile(r"^\s*(?:[-*+]\s+)?\[( |-)\]\s.*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
#: The Origin clause kinds, each at most once on the line (ADR 0161).
ORIGIN_KINDS = ("backlog", "bugs", "findings")
_ORIGIN_RE = re.compile(r"^\*\*Origin:\*\*[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_ORIGIN_GRAMMAR = "operator-demand | backlog:<ids>; bugs:<ids>; findings:<ids>, each kind once"


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_status(text: str) -> str | None:
    """The ``**Status:**`` token a trio document carries, or ``None``."""
    match = _STATUS_RE.search(text)
    return match.group(1) if match else None


def origin(text: str) -> dict[str, list[str]]:
    """The ids the first ``**Origin:**`` line carries, by kind; ``{}`` for operator-demand.
    The ONE Origin parser (ADR 0161): raises ``ValueError`` saying what is wrong."""
    match = _ORIGIN_RE.search(text)
    if match is None:
        raise ValueError(f"has no `**Origin:**` line ({_ORIGIN_GRAMMAR})")
    carried: dict[str, list[str]] = {}
    for clause in [] if match.group(1) == "operator-demand" else match.group(1).split(";"):
        kind, _, ids = clause.strip().partition(":")
        cited = [i.strip() for i in ids.split(",") if i.strip()]
        if kind not in ORIGIN_KINDS or kind in carried or not cited:
            raise ValueError(f"Origin {match.group(1)!r} is not canonical: {_ORIGIN_GRAMMAR}")
        carried[kind] = cited
    return carried


def origin_line(text: str) -> int:
    """The 1-based line :func:`origin` reads, 1 when there is none."""
    match = _ORIGIN_RE.search(text)
    return text.count("\n", 0, match.start()) + 1 if match else 1


def candidate_number(names: Iterable[str]) -> int:
    """The highest ``rc-<N>`` among *names*, 0 when none — the live candidate's number."""
    return max((int(m.group(1)) for n in names if (m := CANDIDATE_RE.match(n))), default=0)


def candidate_dir(release_dir: Path) -> Path | None:
    """The highest-numbered ``rc-<N>/`` under *release_dir* (ADR 0150) —
    `core.gitflow.candidate_dir`'s twin; ``None`` when there is none."""
    n = candidate_number(d.name for d in release_dir.iterdir() if d.is_dir())
    return release_dir / f"rc-{n}" if n else None


def next_candidate(release_dir: Path) -> Path:
    """The ``rc-<N+1>/`` a new candidate is born in — past every ``rc-<N>`` entry, a stray
    file included, so the birth never lands on an existing path."""
    names = [p.name for p in release_dir.iterdir()] if release_dir.is_dir() else []
    return release_dir / f"rc-{candidate_number(names) + 1}"


def unfinished_tasks(candidate: Path) -> list[str]:
    """The ``[ ]``/``[-]`` lines TASKS.md still carries — the LINES, so a refusal names
    the task that blocks it. A missing TASKS.md carries none: its absence is the trio
    rule's business, not this one's."""
    tasks = candidate / "TASKS.md"
    if not tasks.is_file():
        return []
    text = tasks.read_text(encoding="utf-8")
    return [match.group(0).strip() for match in UNFINISHED_RE.finditer(text)]
