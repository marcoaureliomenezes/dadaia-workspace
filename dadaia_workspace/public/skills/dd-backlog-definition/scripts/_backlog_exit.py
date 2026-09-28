#!/usr/bin/env python3
"""The exit's refusals and its terminal record — the ONE path out of ``active[]``.

Every refusal is raised BEFORE anything is written, so an item is never removed by a
call that then fails to record why it left. An exit is once-only and terminal: the
slug it names must be LIVE, and liveness is asked first, because a slug that already
exited must be told so rather than diagnosed for a status it no longer has.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_schema import DISPOSITIONS  # noqa: E402
from _backlog_store import SCRIPT, Items, Refusal  # noqa: E402
from _backlog_write import today  # noqa: E402

#: Which evidence flag each terminal word must carry — the histo record is the only
#: surviving trace of why the item left.
REQUIRED_EVIDENCE = {"delivered": "release", "superseded": "release", "rejected": "reason"}


def _origin_cites(specs: Path, release: str, slug: str) -> bool:
    """Whether the release's SPEC names *slug* on its `**Origin:** backlog:` line — the pick."""
    spec = specs / "releases" / release / "SPEC.md"
    text = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    match = re.search(r"^\*\*Origin:\*\*\s*backlog:(.+)$", text, re.MULTILINE)
    return match is not None and slug in (s.strip() for s in match.group(1).split(","))


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
    if required == "release" and not _origin_cites(specs, str(release), slug):
        raise Refusal(
            f"releases/{release}/SPEC.md does not name {slug!r} on its `**Origin:** backlog:` "
            f"line — only a release that picked an item can exit it as {disposition!r}",
            f"{SCRIPT} exit {slug} --disposition {disposition} --release <the release whose Origin names {slug}>",
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
