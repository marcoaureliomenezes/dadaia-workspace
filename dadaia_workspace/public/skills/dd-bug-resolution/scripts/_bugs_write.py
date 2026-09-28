#!/usr/bin/env python3
"""The bug record's own transition law — what `bugs.py` applies to a ledger's records.

Each function takes the ledger's records and returns the new list; nothing here touches
disk. The three field categories of bug-record-v1 (`x-mutability`) are the whole of the
governance contract, read from the schema: immutable core never changes, write-once
refuses a differing second write, and a field a verb owns is never `update`'s.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_check import TERMINAL, load_schema  # noqa: E402
from _bugs_store import Records, Refusal, by_id  # noqa: E402

_MUTABILITY = {k: v["x-mutability"] for k, v in load_schema()["properties"].items()}
CORE = tuple(k for k, v in _MUTABILITY.items() if v == "immutable-core")
GOVERNANCE = tuple(k for k, v in _MUTABILITY.items() if v == "mutable-governance")
WRITE_ONCE = tuple(k for k, v in _MUTABILITY.items() if v == "write-once")
#: The fields a verb owns, so `update` refuses them and names the verb.
_TRANSITIONS = ("resolve|supersede|defer|reject", "")
_VERB_OWNED = {"status": _TRANSITIONS, "closed_at": _TRANSITIONS,
               "caused_by": ("resolve", "--caused-by <bug-id|none> "),
               "superseded_by": ("supersede", "--by <slug> ")}  # fmt: skip
_SCRIPT = Path(__file__).parent / "bugs.py"


def now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(records: Records, values: dict[str, Any]) -> Records:
    """One brand-new record, `status: "open"`. Refuses a duplicate id and the legacy
    `unknown` surface sentinel; the schema check on the candidate bytes does the rest."""
    bug_id = values["id"]
    if any(r.get("id") == bug_id for r in records):
        raise Refusal(
            f"bug id {bug_id!r} already exists — a reopen is a NEW record declaring "
            "'caused_by: <prior-id>' at resolve, never a second record under this id",
            f"{_SCRIPT} append --bug-id <new-id> --specs <specs>",
        )
    if values.get("surface") == "unknown":
        raise Refusal(
            "surface 'unknown' is a legacy sentinel, valid only on records that already carry it",
            f"{_SCRIPT} append --surface <the-unit-that-broke> --specs <specs>",
        )
    record = {key: values.get(key) for key in CORE}
    record.update({key: None for key in GOVERNANCE})
    record["status"] = "open"
    return [*records, record]


def _set(record: dict[str, Any], key: str, value: Any) -> None:
    if key in WRITE_ONCE and record.get(key) is not None and record[key] != value:
        raise Refusal(
            f"bug-record field {key!r} is write-once and already set — a second write "
            "with a different value is refused",
            f"{_SCRIPT} status --all --specs <specs>",
        )
    if key in CORE and record.get(key) != value:
        raise Refusal(
            f"bug-record field {key!r} is immutable-core and cannot be changed",
            f"{_SCRIPT} append --bug-id <new-id> --specs <specs>",
        )
    record[key] = value


def apply_update(records: Records, bug_id: str, changes: dict[str, str]) -> Records:
    """The one governance-write seam for every field no verb owns — each refusal names
    the subcommand that DOES own the field."""
    for key in changes:
        if key in _VERB_OWNED:
            verb, option = _VERB_OWNED[key]
            raise Refusal(
                f"bug-record field {key!r} is written only by {verb}",
                f"{_SCRIPT} {verb} {bug_id} {option}--specs <specs>",
            )
        if key not in _MUTABILITY:
            raise Refusal(f"unknown bug-record field {key!r}", f"{_SCRIPT} update --help")
    record = by_id(records, bug_id)
    updated = dict(record)
    for key, value in changes.items():
        _set(updated, key, value)
    return [updated if r is record else r for r in records]


def archivable(records: Records, cutoff: str) -> set[str]:
    """The ids of every record CLOSED before *cutoff* — ageing is by `closed_at`, the
    date the record actually closed, never by the filing date `ts`."""
    return {
        str(r["id"])
        for r in records
        if r.get("status") in TERMINAL and isinstance(r.get("closed_at"), str)
        and r["closed_at"] < cutoff
    }  # fmt: skip


def parse_set_options(raw: list[str]) -> dict[str, str]:
    """`--set field=value` pairs, the one place the option shape is parsed."""
    changes: dict[str, str] = {}
    for item in raw:
        field, sep, value = item.partition("=")
        if not sep or not field.strip():
            raise Refusal(f"--set {item!r} must be 'field=value'", f"{_SCRIPT} update --help")
        changes[field.strip()] = value
    return changes
