#!/usr/bin/env python3
"""BUGS.jsonl validator — stdlib only, one ledger, one verb.

``check`` reads ``<specs>/bugs/BUGS.jsonl`` and validates every record against
``scripts/schemas/bug-record-v1.schema.json`` beside this file (a copy `public stage`
makes, so the script has no import path into the library), plus the record invariants a
JSON Schema cannot state. One ``<CODE> error <message>`` line per finding, exit 1 on any.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CODE = "LEDGER-BUGS-SCHEMA"
LEDGER = "bugs/BUGS.jsonl"
SCHEMA = Path(__file__).resolve().parent / "schemas" / "bug-record-v1.schema.json"
TERMINAL = frozenset({"resolved", "superseded", "deferred", "rejected"})
_JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


def find_specs(start: Path) -> Path:
    """The nearest ``specs/`` at or above *start* whose parent holds ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / "specs").is_dir() and (candidate / ".git").exists():
            return candidate / "specs"
    print(f"error: no git-rooted specs/ at or above {start}", file=sys.stderr)
    print("fix: run this script again with --specs <path-to-specs>", file=sys.stderr)
    raise SystemExit(1)


def _field_errors(key: str, value: object, spec: dict[str, Any]) -> Iterator[str]:
    declared = spec.get("type")
    allowed: list[str] = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, _JSON_TYPES[name]) for name in allowed):
        yield f"field {key!r} must be of type {declared}"
        return
    if not isinstance(value, str):
        return
    enum = spec.get("enum")
    # `x-enum-append` marks an enum whose arm is derived from the library's packages on
    # disk (`surface`): the closed list here is not the whole truth, so it is not closed.
    if enum and "x-enum-append" not in spec and value not in enum:
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


def check(specs: Path) -> list[dict[str, Any]]:
    path = specs / LEDGER
    if not path.is_file():  # a young specs tree has no bugs yet — not a finding
        return []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}

    def add(line: int, message: str) -> None:
        findings.append(
            {"code": CODE, "verdict": "error", "path": LEDGER, "line": line, "message": message}
        )

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    checker = sub.add_parser("check", help="validate every BUGS.jsonl record")
    checker.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
    checker.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    specs = args.specs if args.specs is not None else find_specs(Path.cwd())
    findings = check(specs)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for finding in findings:
            print(f"{CODE} error {LEDGER}:{finding['line']} {finding['message']}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
