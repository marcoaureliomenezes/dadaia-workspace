"""``consumed_backlog`` ledger reader — BL-STALE feed (SPEC §3.6, ADR-C; v0.5.0
T-050-13A, A5.5).

BL-STALE keys on a **structured** ledger fixed to one machine-readable record per
archived release. Each record lists ``{slug, shipped_anchors[]}`` entries keyed by the
verified subject-anchor set actually shipped in that release. BL-STALE matches by
**exact slug membership** — never NLP prose.

**Relocation (v0.5.0 T-050-13A, A5.5).** Through v0.4.x this reader globbed 18 per-release
sidecar files at ``specs/_archive/<release-id>/consumed_backlog.json``. FR6 (T-050-14)
deletes that root archive tree; deleting the sidecars first would have made this
BL-STALE condition go permanently quiet without ever failing — the exact "documented
convention with no data behind it" shape FR13 condemns. T-050-13A relocated all 18 into
one append-only file, ``specs/backlog/_archive/consumed_backlog_histo.jsonl`` (one
:class:`~dadaia_workspace.core.models.backlog.ConsumedBacklogHistoRecord` per release),
through the SAME generic
:class:`~dadaia_workspace.core.protocols.record_store.RecordStore` seam FR5 (T-050-13)
already uses for ``backlog_histo.jsonl`` — DI via ``core.protocols`` (the concrete store
is composed at ``container.build_consumed_backlog_histo_store``); this module never
imports ``infrastructure`` directly (``features-no-infrastructure`` lint contract).

R1 obligations: **read** the ledger mechanically, tolerating absence (no store injected,
or its ledger holds no records → ``{}`` → BL-STALE is a no-op, never a false ERROR —
acceptance §3.7.6). R1 does NOT write it; the writer is R2's release-definition/closure.
"""

from __future__ import annotations

from dadaia_workspace.core.models.backlog import ConsumedBacklogHistoRecord
from dadaia_workspace.core.protocols.record_store import RecordStore

__all__ = ["read_consumed"]


def read_consumed(store: RecordStore[ConsumedBacklogHistoRecord] | None) -> dict[str, set[str]]:
    """Iterate the relocated consumed-backlog histo store → ``{slug: shipped_anchors}``.

    Returns ``{}`` when *store* is ``None`` (no ledger injected) or its ledger holds no
    records — the SAME degrade-to-``{}`` no-op the pre-relocation directory-glob reader
    carried (never a false ERROR, ADR-C/A5.5). A malformed record is already skipped by
    the generic ``JsonlRecordStore`` (WARN-logged); this reader only walks each
    surviving release record's ``consumed[]`` entries. When the same slug appears in
    multiple releases' records, its ``shipped_anchors`` sets are unioned (unchanged
    from the pre-relocation behaviour).
    """
    consumed: dict[str, set[str]] = {}
    if store is None:
        return consumed
    for record in store.iter_records():
        for entry in record.consumed:
            slug = entry.get("slug")
            if not isinstance(slug, str) or not slug:
                continue
            anchors = entry.get("shipped_anchors")
            anchor_set = consumed.setdefault(slug, set())
            if isinstance(anchors, list):
                anchor_set.update(a for a in anchors if isinstance(a, str) and a)
    return consumed
