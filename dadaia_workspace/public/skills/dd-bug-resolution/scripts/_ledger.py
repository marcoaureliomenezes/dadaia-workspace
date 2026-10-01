#!/usr/bin/env python3
"""What every ledger script shares, staged beside each one: the atomic write, schema read,
validation, the `check` record, and `private_refusal` (the push gate's own matcher)."""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

_HERE = Path(__file__).resolve().parent
_STATES = Path(".dadaia") / "states"
_OWN = _HERE / "_privacy.py"
_SOURCE = _OWN if _OWN.is_file() else _HERE.parents[3] / "core" / "redaction.py"
_privacy = ModuleType("_privacy")  # executed from source: no loader, no bytecode beside it
exec(compile(_SOURCE.read_text(encoding="utf-8"), _SOURCE, "exec"), _privacy.__dict__)


JSON_TYPES: dict[str, Any] = {"string": str, "object": dict, "array": list, "boolean": bool,
                              "null": type(None), "integer": int, "number": (int, float)}  # fmt: skip


def load_schema(name: str) -> dict[str, Any]:
    """``schemas/<name>.schema.json`` beside the script, else the shipped one."""
    own = _HERE / "schemas" / f"{name}.schema.json"
    shipped = _HERE.parents[2] / "schemas"
    path = own if own.is_file() else next(shipped.rglob(own.name), own)
    return dict(json.loads(path.read_text("utf-8")))


def validate(value: object, spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    """The JSON-Schema subset the ledgers use: ``$ref`` into ``$defs``, type, const, enum,
    pattern, min/maxLength, minItems, items, required, ``additionalProperties: false``,
    if/then, allOf, not."""
    spec = root["$defs"][spec["$ref"].rsplit("/", 1)[-1]] if "$ref" in spec else spec
    for member in [spec, *spec.get("allOf", ())]:
        if "if" in member and not any(validate(value, member["if"], root, where)):
            yield from validate(value, member["then"], root, where)
    if "not" in spec and not any(validate(value, spec["not"], root, where)):
        yield f"{where} must not match {spec['not']}"
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


class LineError(ValueError):
    """Line *number* of a JSONL ledger is not a JSON object."""

    def __init__(self, number: int, message: str) -> None:
        super().__init__(message)
        self.number = number


def records(path: Path) -> list[dict[str, Any]]:
    """Every JSON object of the JSONL ledger *path*, in file order; absent reads empty."""
    return parse(path.read_text(encoding="utf-8")) if path.is_file() else []


def parse(text: str) -> list[dict[str, Any]]:
    """Every JSON object of JSONL *text*, split on ``\\n`` alone — ``splitlines()``
    breaks a record holding U+2028."""
    out: list[dict[str, Any]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LineError(number, f"is not valid JSON ({exc.msg})") from exc
        if not isinstance(record, dict):
            raise LineError(number, "is not a JSON object")
        out.append(record)
    return out


def finding(code: str, path: str, line: int, message: str) -> dict[str, Any]:
    return {"code": code, "verdict": "error", "path": path, "line": line, "message": message}


def stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime) — how a write detects a concurrent one; ``None`` when absent."""
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return (info.st_size, info.st_mtime_ns)


def replace(path: Path, text: str) -> None:
    """Write *text* to *path* atomically, in LF, via a temp sibling that never survives."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="")
        for _ in range(49):  # Windows refuses the swap while a reader holds *path* open
            with contextlib.suppress(PermissionError):
                return os.replace(tmp, path)
            time.sleep(0.01)
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


def workspace_of(path: Path) -> Path | None:
    """The nearest ancestor of *path* holding ``.dadaia/states/spec_contexts.json``."""
    path = path.resolve()
    return next(
        (d for d in (path, *path.parents) if (d / _STATES / "spec_contexts.json").is_file()), None
    )


def terms(root: Path | None) -> list[tuple[str, str]]:
    """The operator denylist, ONE loader (ADR 0157): `$DADAIA_PRIVACY_DENYLIST`, else
    ``<root>/.dadaia/states/privacy_denylist.json``. Absent is empty; a present file that is
    not one ``{"<term>": "<reason>"}`` object refuses — never read as no terms."""
    env = os.environ.get("DADAIA_PRIVACY_DENYLIST")
    for path in [
        *([Path(env)] if env else []),
        *([root / _STATES / "privacy_denylist.json"] if root else []),
    ]:
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = None
        if not isinstance(raw, dict):
            raise SystemExit(
                f"error: privacy denylist {path} is not one JSON object\n"
                f'fix: Operator action: rewrite {path} as one JSON object {{"<term>": "<reason>"}}'
            )
        if raw:
            return [(str(term), str(reason)) for term, reason in raw.items()]
    return []


def private_refusal(record: dict[str, Any], specs: Path) -> tuple[str, str] | None:
    """``(message, fix)`` for the first field of *record* the push refuses, else ``None``;
    the terms are the workspace's that holds *specs*, whatever the cwd."""
    if (hit := _privacy.first_private(record, terms(workspace_of(specs)), _baseline())) is None:
        return None
    return (
        f"field {hit[0]!r} carries {hit[1]!r}, which the push refuses — nothing was written",
        "re-run this command with that value rewritten without the private term",
    )
