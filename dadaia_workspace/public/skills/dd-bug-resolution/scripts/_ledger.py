#!/usr/bin/env python3
"""What every ledger script shares; `public stage` copies this file beside each one:
the one atomic write (`replace`), schema read and validation, and `private_refusal`,
which runs the push gate's own matcher (`_privacy.py`, a staged `core/redaction.py`)."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_HERE = Path(__file__).resolve().parent
_OWN = _HERE / "_privacy.py"
_SOURCE = _OWN if _OWN.is_file() else _HERE.parents[3] / "core" / "redaction.py"
_SPEC = importlib.util.spec_from_file_location("_privacy", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
_privacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_privacy)


JSON_TYPES: dict[str, Any] = {
    "string": str, "object": dict, "array": list, "boolean": bool,
    "null": type(None), "integer": int, "number": (int, float),
}  # fmt: skip


def load_schema(name: str) -> dict[str, Any]:
    """``schemas/<name>.schema.json`` beside the script, else the shipped one."""
    own = _HERE / "schemas" / f"{name}.schema.json"
    shipped = _HERE.parents[2] / "schemas"
    path = own if own.is_file() else next(shipped.rglob(own.name), own)
    schema: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return schema


def validate(value: object, spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    """The JSON-Schema subset the ledgers use: ``$ref`` into ``$defs``, type, const, enum,
    pattern, min/maxLength, minItems, items, required, ``additionalProperties: false``."""
    if "$ref" in spec:
        spec = root["$defs"][spec["$ref"].rsplit("/", 1)[-1]]
    declared = spec.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, JSON_TYPES[name]) for name in allowed):
        yield f"{where} must be of type {declared}"
        return
    if "const" in spec and value != spec["const"]:
        yield f"{where} must be {spec['const']!r}, got {value!r}"
    if isinstance(value, str):
        if spec.get("enum") and value not in spec["enum"]:
            yield f"{where} must be one of {sorted(spec['enum'])}, got {value!r}"
        if "pattern" in spec and re.search(spec["pattern"], value) is None:
            yield f"{where} value {value!r} does not match {spec['pattern']}"
        if len(value) < spec.get("minLength", 0):
            yield f"{where} is shorter than its minLength of {spec['minLength']}"
        if len(value) > spec.get("maxLength", len(value)):
            yield f"{where} is longer than its maxLength of {spec['maxLength']}"
    if isinstance(value, list):
        if len(value) < spec.get("minItems", 0):
            yield f"{where} carries fewer than its minItems of {spec['minItems']}"
        for index, item in enumerate(value if "items" in spec else []):
            yield from validate(item, spec["items"], root, f"{where}[{index}]")
    if isinstance(value, dict):
        properties: dict[str, Any] = spec.get("properties", {})
        yield from (f"{where} is missing required field {k!r}"
                    for k in spec.get("required", ()) if k not in value)  # fmt: skip
        if spec.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                yield f"{where} carries field {key!r}, which the schema does not allow"
        for key, child in value.items():
            if key in properties:
                yield from validate(child, properties[key], root, f"{where}.{key}")


def find_specs(start: Path) -> Path:
    """The nearest ``specs/`` at or above *start* whose parent holds ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / "specs").is_dir() and (candidate / ".git").exists():
            return candidate / "specs"
    print(f"error: no git-rooted specs/ at or above {start}", file=sys.stderr)
    print("fix: run this script again with --specs <path-to-specs>", file=sys.stderr)
    raise SystemExit(1)


def stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime) — how a write detects a concurrent one; ``None`` when absent."""
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return (info.st_size, info.st_mtime_ns)


def replace(path: Path, text: str) -> None:
    """Write *text* to *path* atomically: LF bytes to a temp sibling, then ``os.replace``;
    the temp sibling never survives, whichever step fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _baseline() -> list[SimpleNamespace]:
    own = _HERE / "privacy_baseline.json"
    path = own if own.is_file() else _SOURCE.parents[1] / "infrastructure" / "data" / own.name
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        SimpleNamespace(
            id=p["id"], regex=re.compile(p["regex"]), reason=p.get("reason", ""),
            exclude=re.compile(p["exclude_regex"]) if p.get("exclude_regex") else None,
        )
        for p in raw["patterns"]
    ]  # fmt: skip


def _terms() -> list[tuple[str, str]]:
    """`$DADAIA_PRIVACY_DENYLIST`, else the nearest `.dadaia/states/privacy_denylist.json`."""
    env, cwd = os.environ.get("DADAIA_PRIVACY_DENYLIST"), Path.cwd().resolve()
    paths = [Path(env)] if env else []
    paths += [d / ".dadaia" / "states" / "privacy_denylist.json" for d in (cwd, *cwd.parents)]
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            raise SystemExit(f"error: privacy denylist {path} is not one JSON object")
        if raw:
            return [(str(term), str(reason)) for term, reason in raw.items()]
    return []


def private_refusal(record: dict[str, Any]) -> tuple[str, str] | None:
    """The refusal ``(message, fix)`` for the first field of *record* the push would
    refuse, or ``None`` — the caller raises it before anything is written."""
    hit = _privacy.first_private(record, _terms(), _baseline())
    if hit is None:
        return None
    return (
        f"field {hit[0]!r} carries {hit[1]!r}, which the push refuses — nothing was written",
        "re-run this command with that value rewritten without the private term",
    )
