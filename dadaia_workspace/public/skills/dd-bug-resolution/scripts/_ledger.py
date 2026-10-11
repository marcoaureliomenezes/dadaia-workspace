#!/usr/bin/env python3
"""What every ledger script shares: schema read, validation, the owners' names (`replace`,
`records`, `finding`, `stamp`, `workspace_of`) and `private_refusal` (the push gate's own question)."""

from __future__ import annotations

import contextlib
import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import _atomic
import _git
import _jsonl
import _privacy
from _commit import stamp as stamp
from _findings import finding as finding
from _root import STATES as _STATES
from _root import workspace_of as workspace_of

_HERE = Path(__file__).resolve().parent
LineError = _jsonl.LineError
records = _jsonl.read
parse = _jsonl.load


JSON_TYPES: dict[str, Any] = {"string": str, "object": dict, "array": list, "boolean": bool,
                              "null": type(None), "integer": int, "number": (int, float)}  # fmt: skip


_SCHEMA_OWNERS = {
    "bug-record-v1": "dd-bug-resolution",
    "backlog-v1": "dd-backlog-definition",
    "histo-record-v1": "dd-backlog-definition",
    "release-state-v1": "dd-release-implementation",
    "finding-record-v1": "dd-audit-project",
}


def load_schema(name: str) -> dict[str, Any]:
    """``schemas/<name>.schema.json`` beside the script, else its writer skill's, else the shipped one."""
    own = _HERE / "schemas" / f"{name}.schema.json"
    if name in _SCHEMA_OWNERS:
        owned = _HERE.parents[1] / _SCHEMA_OWNERS[name] / "scripts" / "schemas" / own.name
        path = own if own.is_file() else owned
    else:
        path = own if own.is_file() else next((_HERE.parents[2] / "schemas").rglob(own.name), own)
    return dict(json.loads(path.read_text("utf-8")))


def _combinators(value: object, spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    for member in [spec, *spec.get("allOf", ())]:
        if "if" in member and not any(validate(value, member["if"], root, where)):
            yield from validate(value, member["then"], root, where)
    if "not" in spec and not any(validate(value, spec["not"], root, where)):
        yield f"{where} must not match {spec['not']}"


def _type(value: object, spec: dict[str, Any], where: str) -> Any:
    declared = spec.get("type")
    allowed = declared if isinstance(declared, list) else [declared] if declared else []
    if allowed and not any(isinstance(value, JSON_TYPES[name]) for name in allowed):
        yield f"{where} must be of type {declared}"


def _const(value: object, spec: dict[str, Any], where: str) -> Any:
    if "const" in spec and value != spec["const"]:
        yield f"{where} must be {spec['const']!r}, got {value!r}"


def _string(value: str, spec: dict[str, Any], where: str) -> Any:
    if spec.get("enum") and value not in spec["enum"]:
        yield f"{where} must be one of {sorted(spec['enum'])}, got {value!r}"
    if "pattern" in spec and re.search(spec["pattern"], value) is None:
        yield f"{where} value {value!r} does not match {spec['pattern']}"
    if len(value) < spec.get("minLength", 0):
        yield f"{where} is shorter than its minLength of {spec['minLength']}"
    if len(value) > spec.get("maxLength", len(value)):
        yield f"{where} is longer than its maxLength of {spec['maxLength']}"


def _array(value: list[Any], spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    if len(value) < spec.get("minItems", 0):
        yield f"{where} carries fewer than its minItems of {spec['minItems']}"
    for index, item in enumerate(value if "items" in spec else []):
        yield from validate(item, spec["items"], root, f"{where}[{index}]")


def _object(value: dict[str, Any], spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    properties: dict[str, Any] = spec.get("properties", {})
    yield from (f"{where} is missing required field {k!r}"
                for k in spec.get("required", ()) if k not in value)  # fmt: skip
    if spec.get("additionalProperties") is False:
        for key in sorted(set(value) - set(properties)):
            yield f"{where} carries field {key!r}, which the schema does not allow"
    for key, child in value.items():
        if key in properties:
            yield from validate(child, properties[key], root, f"{where}.{key}")


#: The checks by the kind of value they judge, run after the type gate passes.
_BY_KIND: tuple[tuple[type, Any], ...] = (
    (str, lambda v, s, r, w: _string(v, s, w)),
    (list, _array),
    (dict, _object),
)


def validate(value: object, spec: dict[str, Any], root: dict[str, Any], where: str) -> Any:
    """The JSON-Schema subset the ledgers use: ``$ref`` into ``$defs``, type, const, enum,
    pattern, min/maxLength, minItems, items, required, ``additionalProperties: false``,
    if/then, allOf, not."""
    spec = root["$defs"][spec["$ref"].rsplit("/", 1)[-1]] if "$ref" in spec else spec
    yield from _combinators(value, spec, root, where)
    wrong = list(_type(value, spec, where))
    yield from wrong
    if wrong:
        return
    yield from _const(value, spec, where)
    for kind, check in _BY_KIND:
        if isinstance(value, kind):
            yield from check(value, spec, root, where)


#: Where a fix names a ledger when no tree is given: a write's own candidate bytes.
SPECS = Path("specs")


#: A whole-document finding's label: its message already names every key.
NAMED = "the keys this finding names"


def unwritten(file: Path, at: int | str, verbs: str, law: str) -> str:
    """The fix for content no verb wrote: no verb rewrites it and *law* forbids a hand edit.
    *at* is a JSONL line number, or a JSON document's entry/key label — a document has no
    line one commit owns, so its commits are listed whole."""
    if isinstance(at, int):
        what = f"line {at} of {file} was not written by {verbs} ({law})"
        finder = f"`git log -L {at},{at}:{file}` finds it"
    else:
        what, finder = f"{file} fails at {at} ({law})", f"`git log -p -- {file}` lists them"
    return (f"Operator action: {what} — if {file} has uncommitted changes, discard them "
            f"(`git checkout -- {file}`); otherwise revert the commit that introduced it "
            f"({finder}), then redo the change through {verbs}")  # fmt: skip


def replace(path: Path, text: str) -> None:
    """Write *text* to *path* atomically, in LF; a symlinked *path* raises ``SymlinkRefusedError``."""
    _atomic.atomic_write(path, text, ensure_parent=True)


def terms(root: Path | None) -> list[tuple[str, str]]:
    """The operator denylist, ONE loader: `$DADAIA_PRIVACY_DENYLIST`, else
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
                f"fix: Operator action: rewrite {path} as one JSON object mapping each term to "
                "its reason"
            )
        if raw:
            return [(str(term), str(reason)) for term, reason in raw.items()]
    return []


def _published_text(path: Path) -> str | None:
    """*path*'s text at the first publication boundary carrying it (the push's prior text,
    ``_privacy.publication_boundaries``); ``None`` outside git, when none carries it, or when
    git fails — no amnesty, as the push's adapter raises on the same failure."""

    def run(*args: str) -> str:
        return _git.git(path.parent, *args)

    try:
        rel = path.resolve().relative_to(
            Path(run("rev-parse", "--show-toplevel").strip()).resolve()
        )
        for base in _privacy.publication_boundaries(lambda a: run(*a).splitlines(), "HEAD"):
            with contextlib.suppress(RuntimeError):
                return run("cat-file", "blob", f"{base}:{rel.as_posix()}")
    except (RuntimeError, OSError, ValueError):
        pass
    return None


def private_refusal(records: Iterable[dict[str, Any]], path: Path) -> tuple[str, str] | None:
    """``(message, fix)`` for the first field of the write's *records* the push refuses — a
    match the published text of *path* (the ledger file) does not already carry — else
    ``None``; terms and published text are read once per write, from the workspace holding
    *path*, whatever the cwd."""
    found, patterns = terms(workspace_of(path)), _privacy.load_baseline()
    published = _privacy.published_matches(_published_text(path), found, patterns)
    for key, value in (item for record in records for item in record.items()):
        text = json.dumps(value, ensure_ascii=False)
        for hit, _source, _reason in _privacy.fresh_matches(text, published, found, patterns):
            return (
                f"field {key!r} carries {_privacy.mask(hit)!r}, which the push refuses — "
                "nothing was written",
                "Operator action: re-run this command with that value rewritten without the "
                "private term",
            )
    return None
