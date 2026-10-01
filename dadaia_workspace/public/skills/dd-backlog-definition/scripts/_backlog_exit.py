#!/usr/bin/env python3
"""The exit's refusals and its terminal record — the ONE path out of ``active[]``.

Every refusal is raised BEFORE anything is written, so an item is never removed by a
call that then fails to record why it left. An exit is once-only and terminal: the
slug it names must be LIVE, and liveness is asked first, because a slug that already
exited must be told so rather than diagnosed for a status it no longer has.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_schema import DISPOSITIONS  # noqa: E402
from _backlog_store import SCRIPT, Items, Refusal  # noqa: E402
from _backlog_write import today  # noqa: E402
from _bugs_store import read_records  # noqa: E402
from _release_schema import origin  # noqa: E402

#: Which evidence flag each terminal word must carry — the histo record is the only
#: surviving trace of why the item left.
REQUIRED_EVIDENCE = {
    "delivered": "release",
    "superseded": "release",
    "rejected": "reason",
    "to-bug": "reason",  # the id of the bug record that carries the item on (ADR 0137)
}


def _picks(specs: Path, slug: str) -> list[str]:
    """Each release whose candidate SPEC (``rc-<N>/``, ADR 0150) carries *slug* in its
    Origin's `backlog:` clause — read by `release.py`'s one parser (ADR 0161)."""
    picks = []
    for spec in (specs / "releases").glob("*/rc-*/SPEC.md"):
        try:
            if slug in origin(spec.read_text(encoding="utf-8")).get("backlog", []):
                picks.append(spec.parents[1].name)
        except ValueError:
            continue  # a malformed Origin picks nothing; `release.py check` reports it
    return sorted(set(picks), key=lambda v: [int(p) if p.isdigit() else -1 for p in v.split(".")])


def check_exit(specs: Path, active: Items, slug: str, values: dict[str, Any]) -> dict[str, Any]:
    """Refuse, before any write, an exit whose subject is not live or whose evidence does
    not match its disposition. Returns the entry the exit will remove."""
    disposition, release, reason = values["disposition"], values["release"], values["reason"]
    entry = next((item for item in active if item.get("id") == slug), None)
    if entry is None:
        raise Refusal(
            f"{slug!r} does not name a live active[] entry — an item is retained forever, "
            "so a slug missing from active[] has already exited",
            f"grep {slug} specs/backlog/_archive/backlog_histo.jsonl",
        )
    picks = _picks(specs, slug)
    # The exit this entry can take: the latest picking release's; with none, the operator's.
    fix = (f"{SCRIPT} exit {slug} --disposition delivered --release {picks[-1]}" if picks
           else f"Operator action: name {slug} in the `backlog:` clause of a candidate SPEC's "
                f"first `**Origin:**` line under {specs / 'releases'}, then rerun this exit.")  # fmt: skip
    if disposition not in DISPOSITIONS:
        raise Refusal(
            f"unknown disposition {disposition!r}: a backlog item exits as one of "
            f"{'|'.join(DISPOSITIONS)}",
            fix,
        )
    required = REQUIRED_EVIDENCE[disposition]
    if not ({"release": release, "reason": reason}[required] or "").strip():
        raise Refusal(
            f"disposition {disposition!r} requires --{required}: the histo record is the "
            f"only surviving trace of why {slug!r} left active[]",
            fix,
        )
    if required == "release" and release not in picks:
        raise Refusal(
            f"no releases/{release}/rc-<N>/SPEC.md names {slug!r} in its first `**Origin:**` "
            f"line's backlog clause — only a release that picked an item can exit it as {disposition!r}",
            fix,
        )
    bugs = specs / "bugs" / "BUGS.jsonl"
    if disposition == "to-bug" and reason not in {r.get("id") for r in read_records(bugs)}:
        raise Refusal(
            f"{reason!r} names no record of {bugs} — `to-bug` hands {slug!r} to a registered bug",
            f"Operator action: register {reason} with bugs.py append (dd-bug-registration), "
            "then rerun this exit.",
        )
    return entry


def histo_record(entry: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """The one histo-record-v1 shape: ``entry`` IS the removed object."""
    return {
        "id": entry["id"],
        "ts": values.get("ts") or today(),
        "disposition": values["disposition"],
        "release": values["release"],
        "reason": values["reason"],
        "summary": values.get("summary"),
        "entry": entry,
    }
