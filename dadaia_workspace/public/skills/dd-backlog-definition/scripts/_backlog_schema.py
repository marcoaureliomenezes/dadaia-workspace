#!/usr/bin/env python3
"""The two backlog schemas, this ledger's vocabulary, and the JSON-Schema subset the
documents are read with — `backlog.py`'s one validation primitive.

The schemas are ``schemas/backlog-v1.schema.json`` and
``schemas/histo-record-v1.schema.json`` beside this file, copies `public stage` makes.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CODE = "LEDGER-BACKLOG-SCHEMA"
LEDGER = "backlog/BACKLOG.json"
HISTO = "backlog/_archive/backlog_histo.jsonl"
#: A backlog item is delivered, superseded or rejected — `resolved` is a bug's word and
#: a deferred item returns to active[] rather than exiting.
DISPOSITIONS = ("delivered", "superseded", "rejected")
#: The five terminal words, none of which may label a LIVE active[] entry.
TERMINAL = ("delivered", "resolved", "superseded", "deferred", "rejected")
#: The one status exempt from the typed-intents requirement (dd-backlog-definition §2).
IDEA = "idea"
_JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


_SCHEMAS = Path(__file__).resolve().parent / "schemas"
#: Source-tree fallback: before `public stage` copies a schema in beside the script.
_SHIPPED = Path(__file__).resolve().parents[3] / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    own = _SCHEMAS / f"{name}.schema.json"
    path = own if own.is_file() else next(_SHIPPED.rglob(own.name), own)
    schema: dict[str, Any] = json.loads(path.read_text("utf-8"))
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
    const = spec.get("const")
    if const is not None and value != const:
        yield f"{where} must be {const!r}, got {value!r}"
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


def validate(
    value: object, spec: dict[str, Any], root: dict[str, Any], where: str
) -> Iterator[str]:
    """The JSON-Schema subset these two documents use: ``$ref`` into ``$defs``, type,
    const, enum, pattern, minLength, required, ``additionalProperties: false``, items."""
    ref = spec.get("$ref")
    if ref is not None:
        spec = root["$defs"][ref.rsplit("/", 1)[-1]]
    declared = spec.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, _JSON_TYPES[name]) for name in allowed):
        yield f"{where} must be of type {declared}"
        return
    yield from _scalar_errors(where, value, spec)
    if isinstance(value, list) and "items" in spec:
        for index, item in enumerate(value):
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
