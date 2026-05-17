"""Incremental Codex SQLite reader.

Reads thread records from the Codex CLI state database
(``~/.codex/state_5.sqlite``) and ingests them into the telemetry store.

Design decisions:
    D-AM-16 — Codex pre-aggregates tokens (no input/output split).
               tokens_input = tokens_used, tokens_output = 0, cost_micro_usd = NULL.
    D-AM-19 — suspect = 0 (Codex pre-aggregates, no per-line forgery risk).
    R9      — cost_micro_usd = NULL for Codex events.

Privacy invariant: only whitelisted columns are read from the threads table.
No content, no message bodies, no user-visible text beyond thread title.
"""
from __future__ import annotations

import hashlib
import logging
import pathlib
import sqlite3
from dataclasses import dataclass
from typing import Optional

from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.models import (
    Agent,
    Event,
    Session,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass (mirrors reader/claude.py for symmetry)
# ---------------------------------------------------------------------------


@dataclass
class ReadResult:
    """Summary of one Codex read cycle."""

    sessions_ingested: int = 0
    events_ingested: int = 0
    events_skipped: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CODEX_AGENT_NAME = "codex (main)"
_CODEX_PROVIDER = "codex"

# Columns we want from threads — read defensively (a subset may be absent)
_WANTED_COLUMNS = frozenset(
    {
        "id",
        "tokens_used",
        "created_at",
        "updated_at",
        "cwd",
        "title",
        "model",
        "model_provider",
        "git_branch",
        "git_origin_url",
        "agent_nickname",
        "agent_role",
    }
)


def _compute_event_id(thread_id: str) -> str:
    """Compute idempotent event_id = sha1(codex||thread_id)[:20]."""
    digest = hashlib.sha1(f"codex||{thread_id}".encode()).hexdigest()
    return digest[:20]


def _epoch_to_iso(epoch: Optional[int]) -> Optional[str]:
    """Convert UNIX epoch integer (seconds) to ISO-8601 UTC string, or None."""
    if epoch is None:
        return None
    import datetime
    return datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ---------------------------------------------------------------------------
# Core reader function
# ---------------------------------------------------------------------------


def read_codex_db(
    path: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
    *,
    _timeout: float = 5.0,
) -> ReadResult:
    """Read Codex thread records from *path* and ingest them into *dao*.

    Opens the database read-only via the ``file:?mode=ro`` URI scheme.
    Degrades gracefully on:
    - Missing file → returns empty ReadResult.
    - ``sqlite3.OperationalError`` (locked, malformed) → logs warning, returns empty.
    - Missing columns in ``threads`` table → selects only present columns.

    Idempotency is guaranteed by ``insert_event``'s ``INSERT OR IGNORE`` on
    ``event_id`` (which is derived from ``thread_id``).
    """
    result = ReadResult()

    if not path.exists():
        logger.debug("Codex reader: database not found at %s — returning empty result", path)
        return result

    # Open read-only
    uri = f"file:{path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=_timeout)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError as exc:
        logger.warning("Codex reader: cannot open %s — %s", path, exc)
        return result

    try:
        return _ingest(conn, dao, now_iso, result)
    except sqlite3.OperationalError as exc:
        logger.warning("Codex reader: error reading %s — %s", path, exc)
        return ReadResult()
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def _ingest(
    conn: sqlite3.Connection,
    dao: TelemetryDao,
    now_iso: str,
    result: ReadResult,
) -> ReadResult:
    """Execute the ingest logic once a connection is established."""

    # Discover which columns actually exist in the threads table
    try:
        pragma_rows = conn.execute("PRAGMA table_info(threads)").fetchall()
    except sqlite3.OperationalError as exc:
        logger.warning("Codex reader: cannot read threads schema — %s", exc)
        return result

    if not pragma_rows:
        logger.warning("Codex reader: threads table not found or empty schema")
        return result

    present_columns = {row[1] for row in pragma_rows}  # row[1] = column name
    selected = sorted(_WANTED_COLUMNS & present_columns)

    if "id" not in present_columns:
        logger.warning("Codex reader: threads table has no 'id' column — cannot ingest")
        return result

    # Build a safe SELECT with only columns that exist
    cols_sql = ", ".join(selected)
    try:
        rows = conn.execute(f"SELECT {cols_sql} FROM threads").fetchall()  # noqa: S608
    except sqlite3.OperationalError as exc:
        logger.warning("Codex reader: error querying threads — %s", exc)
        return result

    for row in rows:
        r = dict(row)
        thread_id: str = r["id"]

        tokens_used: int = r.get("tokens_used") or 0
        cwd: Optional[str] = r.get("cwd")
        title: Optional[str] = r.get("title")
        model: Optional[str] = r.get("model")
        git_branch: Optional[str] = r.get("git_branch")
        created_at_epoch: Optional[int] = r.get("created_at")
        updated_at_epoch: Optional[int] = r.get("updated_at")

        first_event_at = _epoch_to_iso(created_at_epoch) or now_iso
        last_event_at = _epoch_to_iso(updated_at_epoch) or now_iso

        # Upsert session
        dao.upsert_session(
            Session(
                session_id=thread_id,
                provider=_CODEX_PROVIDER,
                agent_name=None,          # Codex has no sub-agent concept yet
                ai_title=title,
                entrypoint=None,
                cwd=cwd,
                git_branch=git_branch,
                is_sidechain=0,
                sub_slug=None,
                first_event_at=first_event_at,
                last_event_at=last_event_at,
                status="closed",
            )
        )

        # Upsert agent
        dao.upsert_agent(
            Agent(
                name=_CODEX_AGENT_NAME,
                provider=_CODEX_PROVIDER,
                is_subagent=0,
                first_seen_at=first_event_at,
                last_seen_at=last_event_at,
            )
        )

        # Insert event row (idempotent via INSERT OR IGNORE on event_id)
        event_id = _compute_event_id(thread_id)
        dao.insert_event(
            Event(
                event_id=event_id,
                session_id=thread_id,
                agent_name=_CODEX_AGENT_NAME,
                model=model or "codex",
                occurred_at=last_event_at,
                tokens_input=tokens_used,    # D-AM-16: aggregated, no split
                tokens_cache_read=0,
                tokens_cache_create=0,
                tokens_output=0,             # D-AM-16
                cost_micro_usd=None,         # R9: NULL for Codex events
                pricing_version=None,
                suspect=0,                   # D-AM-19: Codex pre-aggregates
            )
        )
        result.sessions_ingested += 1
        result.events_ingested += 1

    return result
