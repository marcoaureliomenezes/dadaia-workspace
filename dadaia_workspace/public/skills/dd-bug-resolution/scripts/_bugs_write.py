#!/usr/bin/env python3
"""The bug record's own transition law — what `bugs.py` applies to a ledger's records.

Each function takes the ledger's records and returns the new list; nothing here touches
disk. The three field categories of bug-record-v1 (`x-mutability`) are the whole of the
governance contract: immutable core never changes, write-once refuses a differing second
write, and `status`/`closed_at` belong to the transitions — never to `update`.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_check import TERMINAL  # noqa: E402
from _bugs_store import Records, Refusal, by_id  # noqa: E402

CORE = ("id", "ts", "reported_by", "title", "severity", "surface", "component",
        "context", "symptom", "repro", "expected")  # fmt: skip
GOVERNANCE = ("status", "cause", "caused_by", "resolved_release", "audited", "closed_at")
WRITE_ONCE = ("solution", "evidence_loop", "evidence_seam", "evidence_diff",
              "diff_direction", "superseded_by")  # fmt: skip
TRANSITION_OWNED = ("status", "closed_at")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")
_UNSAFE_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")
_SCRIPT = Path(__file__).parent / "bugs.py"


def now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact(value: Any) -> Any:
    """Strip control/format characters, then mask operator-local home paths and IPv4
    addresses — the same three passes the CLI's write seam ran before committing."""
    if not isinstance(value, str):
        return value
    out = _UNSAFE_RE.sub("", value)
    out = _IPV4_RE.sub("[REDACTED-IP]", out)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    return _WIN_HOME_RE.sub(r"\1[REDACTED]", out)


def _redacted(record: dict[str, Any]) -> dict[str, Any]:
    """Every field but the three identity fields (`id`/`ts`/`reported_by`)."""
    keep = ("id", "ts", "reported_by")
    return {k: (v if k in keep else redact(v)) for k, v in record.items()}


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
            f"{_SCRIPT} append --surface <feature-package-or-layer> --specs <specs>",
        )
    record = {key: values.get(key) for key in CORE}
    record.update({key: None for key in GOVERNANCE})
    record["status"] = "open"
    return [*records, _redacted(record)]


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
    """The one governance-write seam for every field OTHER than the transition-owned
    pair and `caused_by` — each refusal names the subcommand that DOES own the field."""
    for key in changes:
        if key in TRANSITION_OWNED:
            raise Refusal(
                f"bug-record field {key!r} belongs to the status transition itself",
                f"{_SCRIPT} resolve|supersede|defer|reject {bug_id} --specs <specs>",
            )
        if key == "caused_by":
            raise Refusal(
                "bug-record field 'caused_by' is unreachable through update — lineage is "
                "declared at resolve and nowhere else",
                f"{_SCRIPT} resolve {bug_id} --caused-by <bug-id|none> --specs <specs>",
            )
        if key not in (*CORE, *GOVERNANCE, *WRITE_ONCE):
            raise Refusal(f"unknown bug-record field {key!r}", f"{_SCRIPT} update --help")
    record = by_id(records, bug_id)
    updated = dict(record)
    for key, value in changes.items():
        _set(updated, key, value)
    return [_redacted(updated) if r is record else r for r in records]


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
