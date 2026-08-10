"""Incremental Kimi Code session-index reader.

Reads Kimi CLI session METADATA from ``~/.kimi-code/session_index.jsonl`` and
ingests it into the telemetry store, mirroring ``reader/codex.py``'s posture.

Kimi session-store shape (live-verified 2026-08-10 against the installed CLI):
    - ``~/.kimi-code/session_index.jsonl`` — one JSON object per line:
      ``{"sessionId": "session_<uuid>", "sessionDir": "<abs path>", "workDir": "<cwd>"}``
    - ``sessionDir`` points to a per-session directory whose mtime is the
      liveness signal.

Privacy invariant T1 — METADATA ONLY:
    Only the session id, the workDir (cwd) and the session directory's mtime are
    read. The per-session directories' CONTENT (conversation, tool traffic) is
    never opened. Kimi has no per-event pricing feed here, so cost is unknown
    (``cost_micro_usd = NULL``), never faked — the Codex/PI posture carried over.

Graceful degradation:
    Missing index, IO error, or a malformed line degrades to an empty (or
    partial) ReadResult — never an exception. A corrupt line is skipped.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import pathlib
from dataclasses import dataclass

from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.models import (
    Agent,
    Event,
    Session,
)

logger = logging.getLogger(__name__)


@dataclass
class ReadResult:
    """Summary of one Kimi read cycle."""

    sessions_ingested: int = 0
    events_ingested: int = 0
    events_skipped: int = 0


_KIMI_AGENT_NAME = "kimi (main)"
_KIMI_PROVIDER = "kimi-code"


def _compute_event_id(session_id: str) -> str:
    """Compute idempotent event_id = sha1(kimi||session_id)[:20]."""
    digest = hashlib.sha1(f"kimi||{session_id}".encode()).hexdigest()
    return digest[:20]


def read_kimi_sessions(
    index_path: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
) -> ReadResult:
    """Read the Kimi session index at *index_path* and ingest into *dao*.

    Idempotency: one event per session keyed on ``sha1(kimi||session_id)[:20]``
    via ``insert_event``'s ``INSERT OR IGNORE``. Missing index → empty result.
    """
    result = ReadResult()
    if not index_path.exists():
        logger.debug("Kimi reader: session index not found at %s — empty result", index_path)
        return result

    try:
        raw_lines = index_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        logger.warning("Kimi reader: cannot read %s — %s", index_path, exc)
        return result

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            result.events_skipped += 1
            continue
        if not isinstance(obj, dict):
            result.events_skipped += 1
            continue
        session_id = obj.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            result.events_skipped += 1
            continue
        cwd = obj.get("workDir") if isinstance(obj.get("workDir"), str) else None

        # Liveness signal: the session directory's mtime (metadata only — the
        # directory content is never opened).
        last_ts = now_iso
        session_dir = obj.get("sessionDir")
        if isinstance(session_dir, str) and session_dir:
            try:
                mtime = pathlib.Path(session_dir).stat().st_mtime
                last_ts = datetime.datetime.fromtimestamp(mtime, tz=datetime.UTC).isoformat()
            except OSError:
                pass

        dao.upsert_session(
            Session(
                session_id=session_id,
                provider=_KIMI_PROVIDER,
                agent_name=None,
                ai_title=None,
                entrypoint=None,
                cwd=cwd,
                git_branch=None,
                is_sidechain=0,
                sub_slug=None,
                first_event_at=last_ts,
                last_event_at=last_ts,
                status="closed",
            )
        )
        dao.upsert_agent(
            Agent(
                name=_KIMI_AGENT_NAME,
                provider=_KIMI_PROVIDER,
                is_subagent=0,
                first_seen_at=last_ts,
                last_seen_at=last_ts,
            )
        )
        dao.insert_event(
            Event(
                event_id=_compute_event_id(session_id),
                session_id=session_id,
                agent_name=_KIMI_AGENT_NAME,
                model="moonshotai/kimi-k2.5",
                occurred_at=last_ts,
                tokens_input=0,  # T1: session content is never read for Kimi
                tokens_cache_read=0,
                tokens_cache_create=0,
                tokens_output=0,
                cost_micro_usd=None,  # Kimi has no per-event pricing — never faked
                pricing_version=None,
                suspect=0,
            )
        )
        result.sessions_ingested += 1
        result.events_ingested += 1

    return result
