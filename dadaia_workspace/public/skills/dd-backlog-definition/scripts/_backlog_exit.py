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
from _backlog_write import redact, today  # noqa: E402

#: The status a release-lane exit requires: an item a release closed is an item a
#: release picked. Exiting an 'idea' as delivered launders unworked scope as shipped.
PICKED = "picked"
#: Which evidence flag each terminal word must carry — the histo record is the only
#: surviving trace of why the item left.
REQUIRED_EVIDENCE = {"delivered": "release", "superseded": "release", "rejected": "reason"}


def _known_release(specs: Path, release: str) -> bool:
    releases = specs / "releases"
    return (releases / release).is_dir() or (releases / "_archive" / release).is_dir()


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
    if disposition not in DISPOSITIONS:
        raise Refusal(
            f"unknown disposition {disposition!r}: a backlog item exits as one of "
            f"{'|'.join(DISPOSITIONS)}",
            f"{SCRIPT} exit {slug} --disposition rejected --reason '<why it was refused>'",
        )
    required = REQUIRED_EVIDENCE[disposition]
    supplied = {"release": release, "reason": reason}[required]
    if not (supplied or "").strip():
        example = "--release <release-id>" if required == "release" else "--reason '<why>'"
        raise Refusal(
            f"disposition {disposition!r} requires --{required}: the histo record is the "
            f"only surviving trace of why {slug!r} left active[]",
            f"{SCRIPT} exit {slug} --disposition {disposition} {example}",
        )
    if required == "release":
        _check_release_lane(specs, entry, slug, disposition, str(release))
    return entry


def _check_release_lane(
    specs: Path, entry: dict[str, Any], slug: str, disposition: str, release: str
) -> None:
    if not _known_release(specs, release):
        raise Refusal(
            f"release {release!r} names neither a live nor an archived release under "
            f"specs/releases/ — a {disposition} item names the release that closed it",
            f"ls {specs / 'releases'}",
        )
    if entry.get("status") != PICKED:
        raise Refusal(
            f"{slug!r} is {entry.get('status')!r}, not {PICKED!r}: only an entry a release "
            f"picked can exit as {disposition!r}; an item no release took exits as 'rejected'",
            f"{SCRIPT} exit {slug} --disposition rejected --reason '<why no release took it>'",
        )


def histo_record(entry: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """The one histo-record-v1 shape: ``entry`` IS the removed object, redacted."""
    record: dict[str, Any] = redact(
        {
            "id": entry["id"],
            "ts": values.get("ts") or today(),
            "disposition": values["disposition"],
            "release": values["release"],
            "reason": values["reason"],
            "summary": values.get("summary"),
            "entry": entry,
        }
    )
    return record
