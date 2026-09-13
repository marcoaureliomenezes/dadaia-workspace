"""One governance verb, one governance event (0.4.7 FR2).

A governance record used to change with no trace of WHO changed it or HOW: a hand edit
and a verb left the same file. That is how an invalid archived release and an archived
`[-]` task reached the tree unnoticed. This module is the trace — the ONE place a verb
records that it changed a record, so `dadaia doctor` can later ask whether the committed
record still hashes to the last event (a hand edit is a WARNING, never a block).

The event carries no content: the record's canonical JSON is hashed, never stored. It
carries no commit sha (a verb never runs git) and no agent name (`sessions.agent_name`
joins on `session_id`).

**An event never fails a verb.** Every failure mode of the store — a root uid, a
read-only home, a corrupt or locked SQLite file, a missing dependency — is logged and
swallowed: observability is not a gate.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from dadaia_workspace.core.models.telemetry import GovernanceEvent

__all__ = ["record_governance_event"]

logger = logging.getLogger(__name__)


def record_hash(record: Mapping[str, object]) -> str:
    """The sha256 of the record's canonical JSON — byte-for-byte the line a JSONL
    ledger writes (``json.dumps(..., sort_keys=True, ensure_ascii=False)``), so the
    hash can be recomputed from the committed file alone."""
    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_governance_event(
    *, verb: str, ledger: str, record_id: str, record: Mapping[str, object]
) -> None:
    """Write one event for the record *verb* just changed. Never raises."""
    from dadaia_workspace import container

    event = GovernanceEvent(
        event_id=str(uuid.uuid4()),
        ts=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        session_id=os.environ.get("DADAIA_SESSION_ID", ""),
        context=os.environ.get("DADAIA_CONTEXT", ""),
        verb=verb,
        ledger=ledger,
        record_id=record_id,
        record_hash=record_hash(record),
    )
    store = None
    try:
        store = container.build_telemetry_store()
        store.open_write().migrate()
        store.insert_governance_event(event)
    except (OSError, sqlite3.Error, ImportError) as exc:
        logger.warning("governance event not recorded (%s %s): %s", verb, record_id, exc)
    finally:
        if store is not None:
            store.close()
