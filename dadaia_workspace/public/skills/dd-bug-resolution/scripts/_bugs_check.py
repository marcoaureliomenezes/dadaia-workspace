#!/usr/bin/env python3
"""The BUGS.jsonl validator — the read half of the one bugs writer (`bugs.py`).

Every write in `bugs.py` runs :func:`findings_for` over the bytes it is about to
commit, so a writer/validator disagreement is unrepresentable. The schema is
``schemas/bug-record-v1.schema.json`` beside this file, a copy `public stage` makes.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _ledger  # noqa: E402
from _ledger import JSON_TYPES  # noqa: E402

CODE = "LEDGER-BUGS-SCHEMA"
LEDGER = "bugs/BUGS.jsonl"
HISTO = "bugs/_archive/bugs_histo.jsonl"
TERMINAL = ("resolved", "superseded", "deferred", "rejected")


def load_schema() -> dict[str, Any]:
    return _ledger.load_schema("bug-record-v1")


def _field_errors(key: str, value: object, spec: dict[str, Any]) -> Iterator[str]:
    declared = spec.get("type")
    allowed: list[str] = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, JSON_TYPES[name]) for name in allowed):
        yield f"field {key!r} must be of type {declared}"
        return
    if not isinstance(value, str):
        return
    enum = spec.get("enum")
    if enum and value not in enum:
        yield f"field {key!r} must be one of {sorted(enum)}, got {value!r}"
    pattern = spec.get("pattern")
    if pattern is not None and re.search(pattern, value) is None:
        yield f"field {key!r} value {value!r} does not match {pattern}"
    minimum = spec.get("minLength")
    if minimum is not None and len(value) < minimum:
        yield f"field {key!r} is shorter than its minLength of {minimum}"


def schema_errors(record: object, schema: dict[str, Any]) -> Iterator[str]:
    """The subset bug-record-v1 uses: required, type, enum, pattern, minLength and
    ``additionalProperties: false`` — the one that reports a retired key."""
    if not isinstance(record, dict):
        yield "record is not a JSON object"
        return
    properties: dict[str, Any] = schema["properties"]
    for key in schema["required"]:
        if key not in record:
            yield f"missing required field {key!r}"
    if schema.get("additionalProperties") is False:
        for key in sorted(set(record) - set(properties)):
            yield f"field {key!r} is not allowed by bug-record-v1 (unknown or retired key)"
    for key, value in record.items():
        spec = properties.get(key)
        if spec is not None:
            yield from _field_errors(key, value, spec)


def invariant_errors(record: dict[str, Any]) -> Iterator[str]:
    """The record's own cross-field law: ``closed_at`` is non-null if and only if
    ``status`` is terminal, and never earlier than ``ts``."""
    status, closed_at, ts = record["status"], record["closed_at"], record["ts"]
    terminal = status in TERMINAL
    if terminal and closed_at is None:
        yield f"record {record['id']!r} is terminal ({status!r}) but carries no 'closed_at'"
    if not terminal and closed_at is not None:
        yield (
            f"record {record['id']!r} is open but carries closed_at={closed_at!r} — "
            "closed_at is stamped only by a terminal transition"
        )
    if isinstance(closed_at, str) and closed_at < ts:
        yield f"record {record['id']!r} closed_at={closed_at!r} precedes its filing date ts={ts!r}"


def findings_for(text: str, rel: str = LEDGER) -> list[dict[str, Any]]:
    """Every finding the ledger *text* carries — the ONE validation path, run both by
    ``check`` over the committed file and by every write over its own candidate bytes."""
    schema = load_schema()
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}

    def add(line: int, message: str) -> None:
        findings.append(
            {"code": CODE, "verdict": "error", "path": rel, "line": line, "message": message}
        )

    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            add(number, f"line is not valid JSON: {exc.msg}")
            continue
        messages = list(schema_errors(record, schema))
        for message in messages:
            add(number, message)
        if messages:
            continue
        for message in invariant_errors(record):
            add(number, message)
        first = seen.setdefault(record["id"], number)
        if first != number:
            add(number, f"duplicate record id {record['id']!r} (first appended at line {first})")
    return findings


def histo_findings(text: str) -> list[dict[str, Any]]:
    """The archive's lines: each a bug-record-v1 record, or a pre-v6 ``event`` line that
    predates the record shape and is history, never rewritten."""
    schema = load_schema()
    out: list[dict[str, Any]] = []
    for number, raw in enumerate(text.split("\n"), start=1):
        try:
            record = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError as exc:
            record, messages = None, [f"line is not valid JSON: {exc.msg}"]
        else:
            legacy = isinstance(record, dict) and "event" in record
            messages = [] if record is None or legacy else list(schema_errors(record, schema))
        out += [{"code": CODE, "verdict": "error", "path": HISTO, "line": number,
                 "message": m} for m in messages]  # fmt: skip
    return out


def check(specs: Path) -> list[dict[str, Any]]:
    """Validate the committed ledger and its archive; a young specs tree with neither is
    not a finding."""
    ledger, histo = specs / LEDGER, specs / HISTO
    out = findings_for(ledger.read_text(encoding="utf-8")) if ledger.is_file() else []
    return out + (histo_findings(histo.read_text(encoding="utf-8")) if histo.is_file() else [])
