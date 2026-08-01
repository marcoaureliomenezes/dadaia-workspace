"""``consumed_backlog`` ledger reader — BL-STALE feed (SPEC §3.6, ADR-C).

BL-STALE keys on a **structured** ledger fixed to a machine-readable JSON sidecar at
``specs/_archive/<release-id>/consumed_backlog.json`` (one file per archived release). Each
file lists ``{slug, shipped_anchors[]}`` entries keyed by the verified subject-anchor set
actually shipped in that release. BL-STALE matches by **exact slug membership** — never NLP
prose.

R1 obligations: **read** the ledger mechanically, tolerating absence (no archived ledger →
``{}`` → BL-STALE is a no-op, never a false ERROR — acceptance §3.7.6). R1 does NOT write it;
the writer is R2's release-definition/closure. ``archive_root`` is injected (SPEC §3.8 #6).

Sidecar JSON shape::

    {
      "release": "v0.1.20",
      "consumed": [
        {"slug": "old-feature", "shipped_anchors": ["path/mod.py#Sym", "INV-foo"]}
      ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["LEDGER_FILENAME", "read_consumed"]

#: The fixed sidecar filename (ADR-C); one per archived release directory.
LEDGER_FILENAME = "consumed_backlog.json"


def _release_still_in_flight(specs_dir: Path | None, release_id: str) -> bool:
    """Whether *release_id* is still open — its directory present and not yet closed.

    ``release-definition`` writes the consumed ledger at DEFINITION time while the item is
    removed at CLOSURE, so between the two the ledger records intent, not completion. Bug
    ``r25-release-definition-leaves-consumed-backlog-stale``: reading it as completion made
    ``backlog doctor`` fail on a tree the workflow had just produced correctly.

    A release with no live directory has been archived away and its ledger is final; a
    release carrying ``CLOSURE.md`` is finished, which keeps
    ``r18-closure-leaves-consumed-backlog-item`` — a CLOSED release that left its item
    behind — reported exactly as before.
    """
    if specs_dir is None:
        return False
    release_dir = specs_dir / "releases" / release_id
    if not release_dir.is_dir():
        return False
    return not (release_dir / "CLOSURE.md").is_file()


def read_consumed(archive_root: Path, *, specs_dir: Path | None = None) -> dict[str, set[str]]:
    """Scan ``<archive_root>/*/consumed_backlog.json`` → ``{slug: shipped_anchors}``.

    Returns ``{}`` when ``archive_root`` is absent or holds no ledgers (no-op, never a false
    ERROR — ADR-C). Malformed or unreadable ledgers are skipped (never crash the doctor).
    When the same slug appears in multiple releases, its shipped-anchor sets are unioned.

    *specs_dir* is optional so every existing caller keeps working unchanged; when given,
    ledgers belonging to a release that is still in flight are skipped (see
    :func:`_release_still_in_flight`).
    """
    consumed: dict[str, set[str]] = {}
    if not archive_root.is_dir():
        return consumed
    for ledger in sorted(archive_root.glob(f"*/{LEDGER_FILENAME}")):
        if _release_still_in_flight(specs_dir, ledger.parent.name):
            continue
        try:
            data = json.loads(ledger.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        entries = data.get("consumed")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            slug = entry.get("slug")
            if not isinstance(slug, str) or not slug:
                continue
            anchors = entry.get("shipped_anchors")
            anchor_set = consumed.setdefault(slug, set())
            if isinstance(anchors, list):
                anchor_set.update(a for a in anchors if isinstance(a, str) and a)
    return consumed
