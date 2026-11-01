#!/usr/bin/env python3
"""The bug record's own transition law — what `bugs.py` applies to a ledger's records.

Each function takes the ledger's records and returns the new list; nothing here touches
disk. The three field categories of bug-record-v1 (`x-mutability`) are the whole of the
governance contract, read from the schema: immutable core never changes, write-once
refuses a differing second write, and a field a verb owns is never `update`'s.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _bugs_check import OPEN, TERMINAL, load_schema
from _bugs_store import Records, Refusal, by_id
from _clock import now_iso as now_iso
from _git import fix_commit, fix_files
from _specs import choice, context_repos, script

_MUTABILITY = {k: v["x-mutability"] for k, v in load_schema()["properties"].items()}
_OBJECTS = frozenset(k for k, v in load_schema()["properties"].items() if v.get("type") == "object")
CORE = tuple(k for k, v in _MUTABILITY.items() if v == "immutable-core")
GOVERNANCE = tuple(k for k, v in _MUTABILITY.items() if v == "mutable-governance")
WRITE_ONCE = tuple(k for k, v in _MUTABILITY.items() if v == "write-once")
#: The fields a verb owns, so `update` refuses them and names the verb.
_TRANSITIONS = ("resolve", "supersede", "reject")
_VERB_OWNED = {"status": _TRANSITIONS, "closed_at": _TRANSITIONS, "superseded_by": ("supersede",),
               }  # fmt: skip
_SCRIPT = script(Path(__file__).parent / "bugs.py")


def by_file(records: Records, repo: Path) -> dict[str, dict[str, str]]:
    """Each path some record fixed, with the id -> fix sha of the records that fixed it, by id; the fix of a record is the commit of its id line, its paths read from that commit in one `diff-tree` per repo of *repo*'s context."""
    commits = fix_commit(context_repos(repo), [str(r["id"]) for r in records])
    touched: dict[str, list[str]] = {}
    for each in {at for at, _ in commits.values()}:
        touched |= fix_files(each, [sha for at, sha in commits.values() if at == each])
    found: dict[str, dict[str, str]] = {}
    for bug, (_, sha) in commits.items():
        for path in touched.get(sha, []):
            found.setdefault(path, {})[bug] = sha
    return {path: dict(sorted(by_id.items())) for path, by_id in sorted(found.items())}


def under(path: str, top: str) -> bool:
    return path == top or path.startswith(top + "/")


def named_paths(component: str | None, tracked: list[str]) -> list[str]:
    """The tracked files or directories a free-text *component* names, in order, once each; a trailing `/` or `.` is dropped, and a token with no `/` is dropped when some named token contains one."""
    tokens = dict.fromkeys(t.rstrip("/.") for t in re.split(r"[\s#:,;()'\"`]+", component or ""))
    named = [t for t in tokens if t and any(under(p, t) for p in tracked)]
    slashed = any("/" in t for t in named)
    return [t for t in named if "/" in t or not slashed]


def append(
    records: Records,
    values: dict[str, Any],
    tracked: list[str],
    known: set[str],
    taken: frozenset[str] = frozenset(),
) -> Records:
    """One brand-new record, `status: "open"`. Refuses a duplicate id, a component text that
    names no tracked path, and a `correlates` that is not `none` or ledger/archive ids
    (*known*); an id is a duplicate when a live record or one of *taken* (the archive's plain
    records) holds it; the schema check does the rest."""
    bug_id = values["id"]
    if bug_id in taken or any(r.get("id") == bug_id for r in records):
        raise choice(Refusal(f"bug id {bug_id!r} already exists — a reopen is a NEW record declaring "
                     "'caused_by: <prior-id>' at resolve, never a second record under this id"),
                     "with --bug-id set to an id no record holds", "--bug-id")  # fmt: skip
    if not named_paths(values.get("component"), tracked):
        raise choice(Refusal(f"component {values.get('component') or ''!r} names no tracked path"),
                     "with --component set to a file or directory tracked in the repo",
                     "--component")  # fmt: skip
    record = {key: values[key] for key in CORE if values.get(key) is not None}
    record.update({key: None for key in GOVERNANCE})
    record["correlates"] = _correlates(values.get("correlates") or [], known)
    record["status"] = OPEN
    return [*records, record]


def _correlates(given: list[str], known: set[str]) -> list[str]:
    """The ids of the repeated or comma-joined *given*, `none` meaning no id; refuses any id *known* lacks."""
    ids = [i for item in given for i in item.split(",")]
    if not ids or not set(ids) - {"none"} <= known or ("none" in ids and len(ids) > 1):
        raise choice(Refusal("name the ledger or archive ids this bug correlates with"),
                     "with --correlates set to the ids (repeat the flag or comma-separate them), or none",
                     "--correlates")  # fmt: skip
    return [] if ids == ["none"] else ids


def _set(record: dict[str, Any], key: str, value: Any) -> None:
    if key in WRITE_ONCE and record.get(key) is not None and record[key] != value:
        raise Refusal(
            f"bug-record field {key!r} is write-once and already set — a second write "
            "with a different value is refused",
            _SCRIPT("status", "--all"),
        )
    if key in CORE and record.get(key) != value:
        raise choice(Refusal(f"bug-record field {key!r} is immutable-core and cannot be changed",
                     _SCRIPT("append")),
                     "with a new --bug-id, filing the changed value as a new record")  # fmt: skip
    record[key] = value


def apply_update(
    records: Records, bug_id: str, changes: dict[str, str], known: set[str]
) -> Records:
    """The one governance-write seam for every field no verb owns — each refusal names
    the subcommand that DOES own the field."""
    for key in changes:
        if key in _VERB_OWNED:
            verb, *twins = _VERB_OWNED[key]
            hint = (
                "with --by set to the bug superseding it"
                if verb == "supersede"
                else "with the fields it requires"
            )
            raise choice(Refusal(f"bug-record field {key!r} is written only by {verb}"
                         + "".join(f", {t}" for t in twins),
                         _SCRIPT(verb, bug_id)),
                         f"or its {', '.join(twins)} twin, {hint}" if twins else hint)  # fmt: skip
        if key not in _MUTABILITY:
            raise Refusal(f"unknown bug-record field {key!r}", _SCRIPT("update", "--help"))
    record = by_id(records, bug_id)
    updated = dict(record)
    for key, value in changes.items():
        _set(updated, key, _parsed(key, value, known))
    return [updated if r is record else r for r in records]


def _parsed(key: str, value: str, known: set[str]) -> Any:
    """*value* as its field's type: the id list for `correlates`, JSON for an object-typed field, else the string."""
    if key == "correlates":
        return _correlates([value], known)
    if key not in _OBJECTS:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise Refusal(
            f"--set {key}= must be a JSON object ({exc.msg})", _SCRIPT("update", "--help")
        ) from None


def archive(records: Records, ids: list[str]) -> Records:
    """The ledger without exactly the named terminal records."""
    moving = [by_id(records, bug_id) for bug_id in ids]
    if still := [str(r["id"]) for r in moving if r.get("status") not in TERMINAL]:
        raise Refusal(f"{', '.join(still)} still open — only a terminal record is archived",
                      _SCRIPT("status"))  # fmt: skip
    return [r for r in records if r not in moving]


def parse_set_options(raw: list[str]) -> dict[str, str]:
    """`--set field=value` pairs, the one place the option shape is parsed."""
    changes: dict[str, str] = {}
    for item in raw:
        field, sep, value = item.partition("=")
        if not sep or not field.strip():
            raise Refusal(f"--set {item!r} must be 'field=value'", _SCRIPT("update", "--help"))
        changes[field.strip()] = value
    return changes
