#!/usr/bin/env python3
"""The `_RELEASE.json` + releases_histo.jsonl validator — the read half of `release.py`.

Every write in `release.py` runs :func:`state_findings` over the bytes it is about to
commit, so a writer/validator disagreement about what a valid release state is cannot
be represented.

The tree walk (`_release_tree.check`) is the one release validator the doctor delegates
to; this file validates the documents a write touches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))

import _ledger  # noqa: E402
from _ledger import SPECS, load_schema, validate  # noqa: E402
from _release_schema import (  # noqa: E402
    CODE,
    DELIVERED,
    HISTO,
)

_LAW = "specs/releases/AGENTS.md: release.py is this ledger's ONE writer"


def finding(path: str, line: int, message: str, fix: str) -> dict[str, Any]:
    """One `check --json` record of this ledger."""
    return _ledger.finding(CODE, path, line, message, fix)


def _unwritten(
    path: str, line: int, message: str, root: Path, at: int | str | None = None
) -> dict[str, Any]:
    """Content of this ledger no `release.py` verb wrote: a histo line, or *at* a state key."""
    fix = _ledger.unwritten(root / path, line if at is None else at, "`release.py`", _LAW)
    return finding(path, line, message, fix)


def _log_errors(document: dict[str, Any]) -> list[str]:
    """``log`` is append-only and oldest first: a later entry never predates an earlier."""
    stamps = [entry.get("ts") for entry in document.get("log", []) if isinstance(entry, dict)]
    return [
        f"log[{index + 1}].ts {later!r} precedes log[{index}].ts {earlier!r}"
        for index, (earlier, later) in enumerate(zip(stamps, stamps[1:], strict=False))
        if isinstance(earlier, str) and isinstance(later, str) and later < earlier
    ]


def state_findings(text: str, rel: str, root: Path = SPECS) -> list[dict[str, Any]]:
    """Every finding one live release-state document's *text* carries, at *rel*."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        message, at = (
            f"document is not valid JSON: {exc.msg}",
            f"its JSON syntax (line {exc.lineno})",
        )
        return [_unwritten(rel, exc.lineno, message, root, at)]
    schema = load_schema("release-state-v1")
    messages = list(validate(document, schema, schema, "state")) or _log_errors(document)
    at = _ledger.keys(messages, "state") if messages else ""
    return [_unwritten(rel, 1, "; ".join(messages), root, at)] if messages else []


def histo_findings(text: str, root: Path = SPECS) -> list[dict[str, Any]]:
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
            findings.append(_unwritten(HISTO, number, f"line is not valid JSON: {exc.msg}", root))
            continue
        messages = list(validate(record, schema, schema, "record"))
        if not messages and record["disposition"] != DELIVERED:
            messages.append(
                f"disposition {record['disposition']!r} — a release ships {DELIVERED!r}"
            )
        if not messages and (first := seen.setdefault(str(record["id"]), number)) != number:
            messages.append(f"{record['id']!r} ships twice (first at line {first})")
        if messages:
            findings.append(_unwritten(HISTO, number, "; ".join(messages), root))
    return findings
