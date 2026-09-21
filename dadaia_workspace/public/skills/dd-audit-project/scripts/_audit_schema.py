#!/usr/bin/env python3
"""The two audit schemas, this ledger's vocabulary, and the JSON-Schema subset the
records are read with — `audit.py`'s one validation primitive.

The schemas are ``schemas/finding-record-v1.schema.json`` and
``schemas/histo-record-v1.schema.json`` beside this file, copies `public stage` makes.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CODE = "LEDGER-FINDINGS-SCHEMA"
AUDITS = "audits"
HISTO = "audits/_archive/audits_histo.jsonl"
FINDINGS = "FINDINGS.jsonl"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
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
_JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


def load_schema(name: str) -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((_SCHEMAS / f"{name}.schema.json").read_text("utf-8"))
    return schema


def find_specs(start: Path) -> Path:
    """The nearest ``specs/`` at or above *start* whose parent holds ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / "specs").is_dir() and (candidate / ".git").exists():
            return candidate / "specs"
    print(f"error: no git-rooted specs/ at or above {start}", file=sys.stderr)
    print("fix: run this script again with --specs <path-to-specs>", file=sys.stderr)
    raise SystemExit(1)


def _scalar_errors(where: str, value: object, spec: dict[str, Any]) -> Iterator[str]:
    if not isinstance(value, str):
        return
    enum = spec.get("enum")
    if enum and value not in enum:
        yield f"{where} must be one of {sorted(enum)}, got {value!r}"
    pattern = spec.get("pattern")
    if pattern is not None and re.search(pattern, value) is None:
        yield f"{where} value {value!r} does not match {pattern}"
    minimum = spec.get("minLength")
    if minimum is not None and len(value) < minimum:
        yield f"{where} is shorter than its minLength of {minimum}"
    maximum = spec.get("maxLength")
    if maximum is not None and len(value) > maximum:
        yield f"{where} is longer than its maxLength of {maximum}"


def validate(
    value: object, spec: dict[str, Any], root: dict[str, Any], where: str
) -> Iterator[str]:
    """The JSON-Schema subset these records use: type, enum, pattern, minLength,
    maxLength, minItems, required, ``additionalProperties: false``, items."""
    declared = spec.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, _JSON_TYPES[name]) for name in allowed):
        yield f"{where} must be of type {declared}"
        return
    yield from _scalar_errors(where, value, spec)
    if isinstance(value, list):
        minimum = spec.get("minItems")
        if minimum is not None and len(value) < minimum:
            yield f"{where} carries fewer than its minItems of {minimum}"
        for index, item in enumerate(value):
            if "items" in spec:
                yield from validate(item, spec["items"], root, f"{where}[{index}]")
    if not isinstance(value, dict):
        return
    properties: dict[str, Any] = spec.get("properties", {})
    for key in spec.get("required", ()):
        if key not in value:
            yield f"{where} is missing required field {key!r}"
    if spec.get("additionalProperties") is False:
        for key in sorted(set(value) - set(properties)):
            yield f"{where} carries field {key!r}, which the schema does not allow"
    for key, child in value.items():
        if key in properties:
            yield from validate(child, properties[key], root, f"{where}.{key}")
