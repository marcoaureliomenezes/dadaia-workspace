#!/usr/bin/env python3
"""The release ledger's vocabulary and the JSON-Schema subset its documents are read
with — `release.py`'s one validation primitive.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CODE = "LEDGER-RELEASE-SCHEMA"
RELEASES = "releases"
STATE = "_RELEASE.json"
HISTO = "releases/_archive/releases_histo.jsonl"
#: The closed-scope candidate trio that lives at the release root; the next candidate's
#: `new`-seeded SPEC overwrites it, and git holds the closed one at its CLOSURE commit.
TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")
#: Every artifact `new` refuses to mint over (CWE-73): a release directory is one unit.
ARTIFACTS = (*TRIO, STATE)
#: The four canonical lifecycle phases — pinned equal to the schema's enum by `check`.
PHASES = ("DEFINITION", "IMPLEMENTATION", "CLOSURE", "ARCHIVED")
#: The phases in which the trio is REQUIRED at the release root; DEFINITION sits
#: between candidates, when the next trio is still being authored.
TRIO_PHASES = frozenset({"IMPLEMENTATION", "CLOSURE"})
#: A release ships `delivered` — the one histo disposition this ledger writes.
DELIVERED = "delivered"
APPROVED = "Approved"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
#: A shipped commit sha as a human pastes it from a merge: short (7) to full (40).
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
#: Task markers that mean the candidate is NOT closed: open ``[ ]`` or reserved ``[-]``.
UNFINISHED_RE = re.compile(r"^\s*-\s\[( |-)\]\s.*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
_JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


_SCHEMAS = Path(__file__).resolve().parent / "schemas"
#: Source-tree fallback, before `public stage` copies the schema in.
_SHIPPED = Path(__file__).resolve().parents[3] / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    own = _SCHEMAS / f"{name}.schema.json"
    path = own if own.is_file() else next(_SHIPPED.rglob(own.name), own)
    schema: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return schema


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def semver_key(release_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in release_id.split("."))


def extract_status(text: str) -> str | None:
    """The ``**Status:**`` token a trio document carries, or ``None``."""
    match = _STATUS_RE.search(text)
    return match.group(1) if match else None


def unfinished_tasks(release_dir: Path) -> list[str]:
    """The ``[ ]``/``[-]`` lines TASKS.md still carries — the LINES, so a refusal names
    the task that blocks it. A missing TASKS.md carries none: its absence is the trio
    rule's business, not this one's."""
    tasks = release_dir / "TASKS.md"
    if not tasks.is_file():
        return []
    text = tasks.read_text(encoding="utf-8")
    return [match.group(0).strip() for match in UNFINISHED_RE.finditer(text)]


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
    if isinstance(value, int) and not isinstance(value, bool):
        minimum = spec.get("minimum")
        if minimum is not None and value < minimum:
            yield f"{where} is below its minimum of {minimum}"
    if not isinstance(value, str):
        return
    enum = spec.get("enum")
    if enum and value not in enum:
        yield f"{where} must be one of {sorted(enum)}, got {value!r}"
    pattern = spec.get("pattern")
    if pattern is not None and re.search(pattern, value) is None:
        yield f"{where} value {value!r} does not match {pattern}"
    minimum_length = spec.get("minLength")
    if minimum_length is not None and len(value) < minimum_length:
        yield f"{where} is shorter than its minLength of {minimum_length}"


def validate(
    value: object, spec: dict[str, Any], root: dict[str, Any], where: str
) -> Iterator[str]:
    """The JSON-Schema subset these documents use: ``$ref`` into ``$defs``, type, const,
    enum, pattern, minLength, minimum, required, ``additionalProperties: false``, items."""
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
