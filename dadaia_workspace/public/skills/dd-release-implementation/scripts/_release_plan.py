#!/usr/bin/env python3
"""The ONE PLAN judge — structure only (ADR 0041, 0141): the `phase IMPLEMENTATION`
transition and `check` both call :func:`plan_errors`, so they cannot disagree."""

from __future__ import annotations

import re
from pathlib import Path

AS_IS = re.compile(r"^##[ \t].*\bas[- ]is review", re.IGNORECASE | re.MULTILINE)
AUTHORITIES = re.compile(r"^###[ \t].*\bAuthorities\b", re.IGNORECASE | re.MULTILINE)
SCHEDULE = re.compile(r"^##[ \t].*\bParallel schedule", re.IGNORECASE | re.MULTILINE)
SKILL = Path(__file__).resolve().parents[2] / "dd-release-definition" / "SKILL.md"
PLAN_FIX = (
    f"copy the PLAN skeletons of {SKILL} — §1 As-is review, §5 Parallel schedule — into PLAN.md"
)
_ID = r"T-\d+(?:-\d+)*"


def _table(text: str, columns: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        cells = [c.strip(" \t`*") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if rows and "|" not in line:
            break
        if rows or [c.lower() for c in cells] == columns:
            rows.append(cells + [""] * len(columns))
    return rows[2:] if len(rows) >= 3 else []


def _section(plan: str, heading: re.Pattern[str]) -> str | None:
    return plan[m.end() :].split("\n## ")[0] if (m := heading.search(plan)) else None


def _as_is_errors(plan: str) -> list[str]:
    if (section := _section(plan, AS_IS)) is None:
        return ["PLAN.md has no '## … As-is review' heading"]
    if not (rows := _table(section, ["unit", "today", "bugs", "verdict", "why"])):
        return ["PLAN.md's As-is review heading is not followed by a table with header "
                "'unit | today | bugs | verdict | why' and >= 1 row"]  # fmt: skip
    errors = [f"PLAN.md As-is review row {row[0]!r} carries verdict {row[3]!r} — one of "
              "DELETE REBUILD UPDATE KEEP ADD" for row in rows
              if row[3].upper() not in {"DELETE", "REBUILD", "UPDATE", "KEEP", "ADD"}]  # fmt: skip
    columns = ["question", "authority", "consults", "deleted"]
    if not (rows := _table(_section(section, AUTHORITIES) or "", columns)):
        return [*errors, "PLAN.md §1 has no '### … Authorities' table with header "
                "'question | authority | consults | deleted' and >= 1 row"]  # fmt: skip
    seen: dict[str, str] = {}
    for question, authority, *_ in rows:
        if not authority:
            errors.append(f"PLAN.md Authorities row {question!r} has an empty authority")
        elif (first := seen.setdefault(question.lower(), authority)) != authority:
            errors.append(f"PLAN.md Authorities question {question.lower()!r} names two "
                          f"authorities: `{first}` and `{authority}` — keep one")  # fmt: skip
    return errors


def _schedule_errors(plan: str, unfinished: list[str]) -> list[str]:
    """Each width counts its tasks; unfinished tasks in one step write disjoint `W:` sets
    outside the merged `TASKS.md` and `*.jsonl` (ADR 0141) and each path suffix the section
    declares as "derived `<path>`" (ADR 0148); a merged task opens no worktree."""
    section = _section(plan, SCHEDULE) or ""
    if not (rows := _table(section, ["step", "tasks open together", "width", "how"])):
        return [
            "PLAN.md has no '## … Parallel schedule' table 'step | tasks open together | width | how'"
        ]
    derived = re.findall(r"\bderived `([^`]+)`", section, re.I)
    shared = ("/TASKS.md", ".jsonl", *(f"/{path}" for path in derived))
    writes = {m[1]: set(re.findall(r"`([^`]+)`", re.sub(r"\([^)]*\)", "", m[2])))
              for line in unfinished if (m := re.search(rf"({_ID})\b.*?`W:`([^·]*)", line))}  # fmt: skip
    errors = [] if "Critical path" in section else ["the Parallel schedule states no critical path"]
    for step, cell, width, *_ in rows:
        ids, seen = re.findall(_ID, cell), dict[str, str]()
        if width != str(len(ids)):
            errors.append(f"step {step} declares width {width} for {len(ids)} task(s)")
        for task in ids:
            for path in writes.get(task, set()):
                if not f"/{path}".endswith(shared) and seen.setdefault(path, task) != task:
                    errors.append(f"step {step}: {seen[path]} and {task} both write {path}")
    return errors


def plan_errors(plan: str, unfinished: list[str]) -> list[str]:
    """Every structural defect of *plan*, given TASKS.md's unfinished task lines."""
    return _as_is_errors(plan) + _schedule_errors(plan, unfinished)
