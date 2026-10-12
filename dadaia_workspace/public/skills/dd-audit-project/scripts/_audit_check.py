#!/usr/bin/env python3
"""What a valid audit tree is: every FINDINGS.jsonl record against `finding-record-v1`,
every archived line against `histo-record-v1` under this ledger's four-word subset.

This is what `audit.py check` reports and what every write validates its own result
against — one definition of valid, so the writer and the validator cannot disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import _findings
import _ledger
from _ledger import SPECS, load_schema, validate

CODE = "LEDGER-FINDINGS-SCHEMA"
AUDITS = "audits"
HISTO = "audits/_archive/audits_histo.jsonl"
FINDINGS = "FINDINGS.jsonl"
_VOCAB = load_schema("finding-record-v1")["properties"]
#: The three pillars every audit reports counts for, in their fixed order.
PILLARS = tuple(_VOCAB["pillar"]["enum"])
#: A finding is born `open` and exits by exactly one of these three words.
DISPOSITIONS = tuple(word for word in _VOCAB["disposition"]["enum"] if word != "open")
#: The evidence each terminal word requires — the finding's governance triple is the
#: only surviving record of how it was closed.
REQUIRED_EVIDENCE = {
    "resolved": "release", "superseded": "release", "rejected": "reason",
}  # fmt: skip
#: The three fields `disposition` rewrites; every other field is the immutable core.
GOVERNANCE = ("disposition", "release", "reason")

Finding = dict[str, Any]


def _fix(rel: str, root: Path) -> Callable[[int], str]:
    """The act that repairs a line of *rel*: a FINDINGS line is appended by file tools and
    repaired in place; an archive line only `audit.py close` writes."""
    law = "specs/audits/AGENTS.md"
    if rel == HISTO:
        return lambda line: _ledger.unwritten(root / rel, line, "`audit.py close`", law)
    return lambda line: (
        f"Operator action: write line {line} of {root / rel} as one finding-record-v1 "
        f"record — a bound session writes audit findings directly; a disposition moves "
        f"only by `audit.py disposition` ({law})")  # fmt: skip


def live_findings(text: str, rel: str, root: Path = SPECS) -> list[Finding]:
    """Findings against one audit's ``FINDINGS.jsonl`` text: the schema, and one id per line."""
    schema = load_schema("finding-record-v1")
    seen: set[str] = set()

    def problems(record: Any) -> list[str]:
        messages = list(validate(record, schema, schema, "finding-record-v1"))
        identity = record.get("id") if isinstance(record, dict) else None
        if isinstance(identity, str) and identity in seen:
            messages.append(f"duplicate finding id {identity!r}")
        elif isinstance(identity, str):
            seen.add(identity)
        return messages

    return _findings.histo_findings(text, rel, CODE, problems, _fix(rel, root))


def archive_findings(text: str, root: Path = SPECS) -> list[Finding]:
    """Findings against the append-only ``audits_histo.jsonl`` text: ``histo-record-v1``
    under this ledger's subset of its dispositions."""
    schema = load_schema("histo-record-v1")

    def problems(record: Any) -> list[str]:
        messages = list(validate(record, schema, schema, "histo-record-v1"))
        word = record.get("disposition") if isinstance(record, dict) else None
        if isinstance(word, str) and word not in DISPOSITIONS:
            messages.append(f"an audit exits as one of {list(DISPOSITIONS)}, not {word!r}")
        return messages

    return _findings.histo_findings(text, HISTO, CODE, problems, _fix(HISTO, root))


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
            out.append(_findings.finding(CODE, f"{AUDITS}/{directory.name}", 0, message,
                       f"Operator action: write {path.resolve()} with one finding-record-v1 line per "
                       "finding of its AUDIT.md (specs/audits/AGENTS.md)"))  # fmt: skip
            continue
        out.extend(
            live_findings(
                path.read_text(encoding="utf-8"),
                f"{AUDITS}/{directory.name}/{FINDINGS}",
                specs.resolve(),
            )
        )
    archive = specs / HISTO
    if archive.is_file():
        out.extend(archive_findings(archive.read_text(encoding="utf-8"), specs.resolve()))
    return out
