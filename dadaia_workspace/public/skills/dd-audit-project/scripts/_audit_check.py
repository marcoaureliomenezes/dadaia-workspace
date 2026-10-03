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

import _ledger  # noqa: E402
from _ledger import SPECS, load_schema, validate  # noqa: E402

CODE = "LEDGER-FINDINGS-SCHEMA"
AUDITS = "audits"
HISTO = "audits/_archive/audits_histo.jsonl"
FINDINGS = "FINDINGS.jsonl"
#: The three pillars every audit reports counts for, in their fixed order.
PILLARS = ("bugs", "specs", "memory")
#: A finding is born `open` and exits by exactly one of these four words.
DISPOSITIONS = ("resolved", "superseded", "deferred", "rejected")
#: The evidence each terminal word requires — the finding's governance triple is the
#: only surviving record of how it was closed.
REQUIRED_EVIDENCE = {
    "resolved": "release", "superseded": "release",
    "deferred": "reason", "rejected": "reason",
}  # fmt: skip
#: The three fields `disposition` rewrites; every other field is the immutable core.
GOVERNANCE = ("disposition", "release", "reason")

Finding = dict[str, Any]


def _finding(rel: str, line: int, messages: list[str], root: Path) -> Finding:
    """One record per invalid line: a FINDINGS line is appended by file tools and repaired
    in place; an archive line only `audit.py close` writes."""
    law = "specs/audits/AGENTS.md"
    fix = (_ledger.unwritten(root / rel, line, "`audit.py close`", law) if rel == HISTO else
           f"Operator action: write line {line} of {root / rel} as one finding-record-v1 "
           f"record — a bound session writes audit findings directly; a disposition moves "
           f"only by `audit.py disposition` ({law})")  # fmt: skip
    return _ledger.finding(CODE, rel, line, "; ".join(messages), fix)


def _lines(text: str) -> list[tuple[int, str]]:
    return [(n, line) for n, line in enumerate(text.split("\n"), start=1) if line.strip()]


def _record_findings(
    text: str, rel: str, schema_name: str, terminal: tuple[str, ...], root: Path
) -> list[Finding]:
    schema = load_schema(schema_name)
    out: list[Finding] = []
    for number, line in _lines(text):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            out.append(_finding(rel, number, [f"not valid JSON ({exc.msg})"], root))
            continue
        messages = list(validate(record, schema, schema, schema_name))
        word = record.get("disposition") if isinstance(record, dict) else None
        if isinstance(word, str) and word not in terminal and schema_name.startswith("histo"):
            messages.append(f"an audit exits as one of {list(terminal)}, not {word!r}")
        if messages:
            out.append(_finding(rel, number, messages, root))
    return out


def findings_findings(text: str, rel: str, root: Path = SPECS) -> list[Finding]:
    """Findings against one audit's ``FINDINGS.jsonl`` text."""
    out = _record_findings(text, rel, "finding-record-v1", ("open", *DISPOSITIONS), root)
    seen: set[str] = set()
    for number, line in _lines(text):
        try:
            identity = json.loads(line).get("id")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(identity, str) and identity in seen:
            message = f"duplicate finding id {identity!r}"
            if prior := next((f for f in out if f["line"] == number), None):
                prior["message"] += f"; {message}"
            else:
                out.append(_finding(rel, number, [message], root))
        elif isinstance(identity, str):
            seen.add(identity)
    return out


def histo_findings(text: str, root: Path = SPECS) -> list[Finding]:
    """Findings against the append-only ``audits_histo.jsonl`` text."""
    return _record_findings(text, HISTO, "histo-record-v1", DISPOSITIONS, root)


def check(specs: Path) -> list[Finding]:
    """Every live audit's findings plus the archive, in path order."""
    audits = specs / AUDITS
    out: list[Finding] = []
    for directory in sorted(child for child in audits.glob("*") if child.is_dir()):
        if directory.name == "_archive":
            continue
        path = directory / FINDINGS
        if not path.is_file():
            message = f"an audit directory carries {FINDINGS}; this one does not"
            out.append(_ledger.finding(CODE, f"{AUDITS}/{directory.name}", 0, message,
                       f"Operator action: write {path.resolve()} with one finding-record-v1 line per "
                       "finding of its AUDIT.md (specs/audits/AGENTS.md)"))  # fmt: skip
            continue
        out.extend(
            findings_findings(
                path.read_text(encoding="utf-8"),
                f"{AUDITS}/{directory.name}/{FINDINGS}",
                specs.resolve(),
            )
        )
    archive = specs / HISTO
    if archive.is_file():
        out.extend(histo_findings(archive.read_text(encoding="utf-8"), specs.resolve()))
    return out
