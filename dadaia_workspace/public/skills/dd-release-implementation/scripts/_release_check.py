#!/usr/bin/env python3
"""The `_RELEASE.json` + releases_histo.jsonl validator — the read half of `release.py`.

Every write in `release.py` runs :func:`state_findings` over the bytes it is about to
commit, so a writer/validator disagreement about what a valid release state is cannot
be represented.

The tree walk (`_release_tree.check`) is the one release validator the doctor delegates
to; this file validates the documents a write touches.
"""

from __future__ import annotations

import functools
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))

from _ledger import finding as _finding  # noqa: E402
from _ledger import load_schema, validate  # noqa: E402
from _release_schema import (  # noqa: E402
    CODE,
    DELIVERED,
    HISTO,
)

#: One `check --json` record of this ledger: `_ledger.finding` bound to CODE.
finding = functools.partial(_finding, CODE)


def _log_errors(document: dict[str, Any]) -> list[str]:
    """``log`` is append-only and oldest first: a later entry never predates an earlier."""
    stamps = [entry.get("ts") for entry in document.get("log", []) if isinstance(entry, dict)]
    return [
        f"log[{index + 1}].ts {later!r} precedes log[{index}].ts {earlier!r}"
        for index, (earlier, later) in enumerate(zip(stamps, stamps[1:], strict=False))
        if isinstance(earlier, str) and isinstance(later, str) and later < earlier
    ]


def state_findings(text: str, rel: str) -> list[dict[str, Any]]:
    """Every finding one live release-state document's *text* carries, at *rel*."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        return [finding(rel, exc.lineno, f"document is not valid JSON: {exc.msg}")]
    schema = load_schema("release-state-v1")
    if messages := list(validate(document, schema, schema, "state")):
        return [finding(rel, 1, message) for message in messages]
    return [finding(rel, 1, m) for m in _log_errors(document)]


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
