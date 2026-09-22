#!/usr/bin/env python3
"""The `_RELEASE.json` + releases_histo.jsonl validator — the read half of `release.py`.

Every write in `release.py` runs :func:`state_findings` over the bytes it is about to
commit, so a writer/validator disagreement about what a valid release state is cannot
be represented.

The doctor's `RELEASE-TREE-*` reader answers a different question — is this repo's
whole release TREE conformant — and stays where it lives. This file validates the
documents a write touches, which is the only thing a writer may refuse on.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_schema import (  # noqa: E402
    CODE,
    DELIVERED,
    HISTO,
    PHASES,
    load_schema,
    validate,
)


def finding(path: str, line: int, message: str) -> dict[str, Any]:
    return {"code": CODE, "verdict": "error", "path": path, "line": line, "message": message}


def _phase_errors(document: dict[str, Any], *, archived: bool) -> list[str]:
    """The milestone invariants the schema alone cannot state: the phase vocabulary, the
    ARCHIVED-iff-under-_archive equivalence, and the publication an ARCHIVED release
    must name (the archive holds published versions only)."""
    phase = document.get("phase")
    if phase not in PHASES:
        return [f"phase {phase!r} is not one of {', '.join(PHASES)}"]
    errors: list[str] = []
    if archived != (phase == "ARCHIVED"):
        where = "under _archive/" if archived else "a live release directory"
        expected = "ARCHIVED" if archived else "a live phase"
        errors.append(f"{where} carries phase {phase!r}, expected {expected}")
    if phase == "ARCHIVED":
        shipped = document.get("shipped")
        if not (isinstance(shipped, dict) and shipped.get("sha") and shipped.get("pr")):
            errors.append("an ARCHIVED release carries no 'shipped' {sha, pr}")
    return errors


def _log_errors(document: dict[str, Any]) -> list[str]:
    """``log`` is append-only and oldest first: a later entry never predates an earlier."""
    stamps = [entry.get("ts") for entry in document.get("log", []) if isinstance(entry, dict)]
    return [
        f"log[{index + 1}].ts {later!r} precedes log[{index}].ts {earlier!r}"
        for index, (earlier, later) in enumerate(zip(stamps, stamps[1:], strict=False))
        if isinstance(earlier, str) and isinstance(later, str) and later < earlier
    ]


def state_findings(text: str, rel: str, *, archived: bool) -> list[dict[str, Any]]:
    """Every finding one release-state document's *text* carries, at *rel*.

    An ARCHIVED document is read, never ranked against the live schema: it was written
    by a schema version that no longer exists and history is never rewritten, so the
    shape rules apply to the live document alone. Its phase and log ordering still hold
    — those are facts about the release, not about the document's declared fields.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        return [finding(rel, exc.lineno, f"document is not valid JSON: {exc.msg}")]
    schema = load_schema("release-state-v1")
    messages = [] if archived else list(validate(document, schema, schema, "state"))
    if messages:
        return [finding(rel, 1, message) for message in messages]
    return [
        finding(rel, 1, message)
        for message in _phase_errors(document, archived=archived) + _log_errors(document)
    ]


def histo_findings(text: str) -> list[dict[str, Any]]:
    """The append-only ship ledger: the histo-record-v1 shape, `delivered`, one line per
    release, ever."""
    schema = load_schema("histo-record-v1")
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(finding(HISTO, number, f"line is not valid JSON: {exc.msg}"))
            continue
        messages = list(validate(record, schema, schema, "record"))
        findings.extend(finding(HISTO, number, message) for message in messages)
        if messages:
            continue
        if record["disposition"] != DELIVERED:
            findings.append(
                finding(
                    HISTO,
                    number,
                    f"disposition {record['disposition']!r} — a release ships {DELIVERED!r}",
                )
            )
        first = seen.setdefault(str(record["id"]), number)
        if first != number:
            findings.append(
                finding(HISTO, number, f"{record['id']!r} ships twice (first at line {first})")
            )
    return findings


def memory_refusals(
    phase: str, worklist: dict[str, Any], reviewed: list[str], changed: list[str]
) -> list[str]:
    """Why this `kind: memory` entry is not a reconciliation record: the worklist must be
    worked exactly — every entry reviewed or changed, nothing outside it named."""
    if phase != "CLOSURE":
        return [f"release is in phase {phase!r} — the memory reconciliation is CLOSURE work"]
    named = set(reviewed) | set(changed)
    listed = [str(atom["slug"]) for atom in worklist.get("atoms", [])]
    listed += [str(unit) for unit in worklist.get("uncovered", [])]
    errors = [f"worklist entry {e!r} is in neither --reviewed nor --changed"
              for e in listed if e not in named]  # fmt: skip
    return errors + [f"{e!r} is not in the window's worklist" for e in sorted(named - set(listed))]
