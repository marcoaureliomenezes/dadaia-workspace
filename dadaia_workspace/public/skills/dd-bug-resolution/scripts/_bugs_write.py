#!/usr/bin/env python3
"""The bug record's own transition law — what `bugs.py` applies to a ledger's records.

Each function takes the ledger's records and returns the new list; nothing here touches
disk. The three field categories of bug-record-v1 (`x-mutability`) are the whole of the
governance contract, read from the schema: immutable core never changes, write-once
refuses a differing second write, and a field a verb owns is never `update`'s.
"""

from __future__ import annotations

import datetime as _dt
import difflib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_check import TERMINAL, load_schema  # noqa: E402
from _bugs_store import Records, Refusal, by_id  # noqa: E402
from _specs import script  # noqa: E402

_MUTABILITY = {k: v["x-mutability"] for k, v in load_schema()["properties"].items()}
CORE = tuple(k for k, v in _MUTABILITY.items() if v == "immutable-core")
GOVERNANCE = tuple(k for k, v in _MUTABILITY.items() if v == "mutable-governance")
WRITE_ONCE = tuple(k for k, v in _MUTABILITY.items() if v == "write-once")
#: The fields a verb owns, so `update` refuses them and names the verb.
_TRANSITIONS = ("resolve", "supersede", "defer", "reject")
_VERB_OWNED = {"status": _TRANSITIONS, "closed_at": _TRANSITIONS, "superseded_by": ("supersede",)}
_SCRIPT = script(Path(__file__).parent / "bugs.py")
_NEW_ID = f"Operator action: choose a bug id no record holds and run `{_SCRIPT} append` with it"


def now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def candidates(records: Records, surface: object) -> list[str]:
    """The records a new bug on *surface* is judged against (ADR 0127): the open ones and
    those resolved in the last 30 days, a recurrence."""
    since = (_dt.datetime.now(tz=_dt.UTC) - _dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return sorted(str(r["id"]) for r in records if r.get("surface") == surface and (
        r.get("status") == "open" or r.get("status") == "resolved" and str(r.get("closed_at")) >= since))  # fmt: skip


def append(records: Records, values: dict[str, Any], dirs: set[str]) -> Records:
    """One brand-new record, `status: "open"`. Refuses a duplicate id, a surface that is
    not one tracked directory name (F011), and a record naming no ledger ids or `none` as
    its correlation (ADR 0127); the schema check does the rest."""
    bug_id = values["id"]
    if any(r.get("id") == bug_id for r in records):
        raise Refusal(
            f"bug id {bug_id!r} already exists — a reopen is a NEW record declaring "
            "'caused_by: <prior-id>' at resolve, never a second record under this id",
            _NEW_ID,
        )
    surface = str(values.get("surface"))
    if surface not in dirs:
        close = ", ".join(difflib.get_close_matches(surface, sorted(dirs), 5, 0)) or "none"
        raise Refusal(
            f"surface {surface!r} is not the name of a directory tracked in this repo",
            f"Operator action: run `{_SCRIPT} append` with --surface set to a tracked "
            f"directory name (closest: {close})",
        )
    correlates = values.get("correlates")
    ids = [] if correlates == "none" else str(correlates or "").split(",")
    if not set(ids) <= {r.get("id") for r in records}:
        raise Refusal(
            "name the ledger ids this bug correlates with — the candidates are listed above",
            f"Operator action: run `{_SCRIPT} append` with --correlates set to the "
            "comma-separated ids it correlates with, or none",
        )
    record = {key: values.get(key) for key in CORE} | {"correlates": ids}
    record.update({key: None for key in GOVERNANCE})
    record["status"] = "open"
    return [*records, record]


def _set(record: dict[str, Any], key: str, value: Any) -> None:
    if key in WRITE_ONCE and record.get(key) is not None and record[key] != value:
        raise Refusal(
            f"bug-record field {key!r} is write-once and already set — a second write "
            "with a different value is refused",
            f"{_SCRIPT} status --all",
        )
    if key in CORE and record.get(key) != value:
        raise Refusal(
            f"bug-record field {key!r} is immutable-core and cannot be changed",
            _NEW_ID,
        )
    record[key] = value


def apply_update(records: Records, bug_id: str, changes: dict[str, str]) -> Records:
    """The one governance-write seam for every field no verb owns — each refusal names
    the subcommand that DOES own the field."""
    for key in changes:
        if key in _VERB_OWNED:
            verbs = ", ".join(_VERB_OWNED[key])
            raise Refusal(
                f"bug-record field {key!r} is written only by {verbs}",
                f"Operator action: choose the verb ({verbs}) for {bug_id} and run it with {_SCRIPT}",
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
