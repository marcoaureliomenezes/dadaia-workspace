#!/usr/bin/env python3
"""What a valid audit tree is: every FINDINGS.jsonl record against `finding-record-v1`,
every archived line against `histo-record-v1` under this ledger's four-word subset.

This is what `audit.py check` reports and what every write validates its own result
against — one definition of valid, so the writer and the validator cannot disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audit_schema import (  # noqa: E402
    AUDITS,
    CODE,
    DISPOSITIONS,
    FINDINGS,
    HISTO,
    load_schema,
    validate,
)

Finding = dict[str, Any]


def _lines(text: str) -> list[tuple[int, str]]:
    return [(n, line) for n, line in enumerate(text.split("\n"), start=1) if line.strip()]


def _record_findings(
    text: str, rel: str, schema_name: str, terminal: tuple[str, ...]
) -> list[Finding]:
    schema = load_schema(schema_name)
    out: list[Finding] = []
    for number, line in _lines(text):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            out.append({"path": rel, "line": number, "message": f"not valid JSON ({exc.msg})"})
            continue
        for message in validate(record, schema, schema, schema_name):
            out.append({"path": rel, "line": number, "message": message})
        word = record.get("disposition") if isinstance(record, dict) else None
        if isinstance(word, str) and word not in terminal and schema_name.startswith("histo"):
            out.append({
                "path": rel, "line": number,
                "message": f"an audit exits as one of {list(terminal)}, not {word!r}",
            })  # fmt: skip
    return out


def findings_findings(text: str, rel: str) -> list[Finding]:
    """Findings against one audit's ``FINDINGS.jsonl`` text."""
    out = _record_findings(text, rel, "finding-record-v1", ("open", *DISPOSITIONS))
    seen: set[str] = set()
    for number, line in _lines(text):
        try:
            identity = json.loads(line).get("id")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(identity, str) and identity in seen:
            out.append(
                {"path": rel, "line": number, "message": f"duplicate finding id {identity!r}"}
            )
        elif isinstance(identity, str):
            seen.add(identity)
    return out


def histo_findings(text: str) -> list[Finding]:
    """Findings against the append-only ``audits_histo.jsonl`` text."""
    return _record_findings(text, HISTO, "histo-record-v1", DISPOSITIONS)


def check(specs: Path) -> list[Finding]:
    """Every live audit's findings plus the archive, in path order."""
    audits = specs / AUDITS
    out: list[Finding] = []
    for directory in sorted(child for child in audits.glob("*") if child.is_dir()):
        if directory.name == "_archive":
            continue
        path = directory / FINDINGS
        if not path.is_file():
            out.append({
                "path": f"{AUDITS}/{directory.name}", "line": 0,
                "message": f"an audit directory carries {FINDINGS}; this one does not",
            })  # fmt: skip
            continue
        out.extend(
            findings_findings(
                path.read_text(encoding="utf-8"), f"{AUDITS}/{directory.name}/{FINDINGS}"
            )
        )
    archive = specs / HISTO
    if archive.is_file():
        out.extend(histo_findings(archive.read_text(encoding="utf-8")))
    for finding in out:
        finding["code"] = CODE
    return out
