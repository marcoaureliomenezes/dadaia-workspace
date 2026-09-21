#!/usr/bin/env python3
"""The memory atom's frontmatter schema, its stdlib reader, and the JSON-Schema subset
the block is validated with — `memory.py`'s one validation primitive.

The schema is ``schemas/memory-frontmatter-v1.schema.json`` beside this file, a copy
`public stage` makes. The block is exactly five scalar/list keys (`slug title tldr
summary tags`), read without a YAML dependency — a key it cannot read is a finding.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CODE = "LEDGER-MEMORY-SCHEMA"
PRODUCT = "memory/product"
CATALOG = "memory/product/catalog.json"
INDEX = "memory/product/index.md"
_DELIMITER = "---"
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s?(.*)$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


_SCHEMAS = Path(__file__).resolve().parent / "schemas"
#: Source-tree fallback: before `public stage` copies a schema in beside the script.
_SHIPPED = Path(__file__).resolve().parents[3] / "schemas"


def _schema_file() -> Path:
    own = _SCHEMAS / "memory-frontmatter-v1.schema.json"
    return own if own.is_file() else next(_SHIPPED.rglob(own.name), own)


def load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(_schema_file().read_text("utf-8"))
    return schema


def find_specs(start: Path) -> Path:
    """The nearest ``specs/`` at or above *start* whose parent holds ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / "specs").is_dir() and (candidate / ".git").exists():
            return candidate / "specs"
    print(f"error: no git-rooted specs/ at or above {start}", file=sys.stderr)
    print("fix: run this script again with --specs <path-to-specs>", file=sys.stderr)
    raise SystemExit(1)


def _scalar(raw: str) -> str | list[str]:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_unquote(item.strip()) for item in inner.split(",") if item.strip()]
    return _unquote(value)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """``(frontmatter, body, error)`` for one atom's text.

    The block is the lines between the first two ``---`` delimiters: one ``key: value``
    per line, a value being a plain scalar or an inline ``[a, b]`` list, plus the
    ``- item`` block-list form. Anything else is an error, not a guess.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != _DELIMITER:
        return None, "", "no YAML frontmatter found"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _DELIMITER)
    except StopIteration:
        return None, "", "the frontmatter block is never closed by a '---' line"
    data: dict[str, Any] = {}
    key: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key is not None:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_unquote(line.lstrip()[2:].strip()))
            continue
        match = _KEY_RE.match(line)
        if match is None:
            return None, "", f"frontmatter line {line!r} is not 'key: value'"
        key = match.group(1)
        data[key] = _scalar(match.group(2)) if match.group(2).strip() else []
    return data, "\n".join(lines[end + 1 :]), None


def _scalar_errors(where: str, value: object, spec: dict[str, Any]) -> Iterator[str]:
    if not isinstance(value, str):
        return
    pattern = spec.get("pattern")
    if pattern is not None and re.search(pattern, value) is None:
        yield f"{where} value does not match {pattern}"
    minimum = spec.get("minLength")
    if minimum is not None and len(value) < minimum:
        yield f"{where} is shorter than its minLength of {minimum}"
    maximum = spec.get("maxLength")
    if maximum is not None and len(value) > maximum:
        yield f"{where} is {len(value)} characters, over its maxLength of {maximum}"


def validate(value: object, spec: dict[str, Any], where: str) -> Iterator[str]:
    """The JSON-Schema subset this frontmatter uses: type, pattern, minLength,
    maxLength, uniqueItems, required, ``additionalProperties: false``, items."""
    declared = spec.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, _JSON_TYPES[name]) for name in allowed):
        yield f"{where} must be of type {declared}"
        return
    yield from _scalar_errors(where, value, spec)
    if isinstance(value, list):
        if spec.get("uniqueItems") and len(set(map(str, value))) != len(value):
            yield f"{where} carries a duplicate item"
        for index, item in enumerate(value):
            if "items" in spec:
                yield from validate(item, spec["items"], f"{where}[{index}]")
    if not isinstance(value, dict):
        return
    properties: dict[str, Any] = spec.get("properties", {})
    for name in spec.get("required", ()):
        if name not in value:
            yield f"{where} is missing required field {name!r}"
    if spec.get("additionalProperties") is False:
        for name in sorted(set(value) - set(properties)):
            yield f"{where} carries field {name!r}, which the schema does not allow"
    for name, child in value.items():
        if name in properties:
            yield from validate(child, properties[name], f"{where}.{name}")
