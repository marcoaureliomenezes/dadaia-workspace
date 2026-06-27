"""Incremental PI (pi-coding-agent) session-store reader (WS-PI-6 / T-30-B-03).

Reads PI session metadata from per-directory JSONL session files under
``~/.pi/agent/sessions/<dir-slug>/<ISO-ts>_<uuid>.jsonl`` and ingests it into the
telemetry store, mirroring ``reader/codex.py``.

PI session-file shape (live-verified 2026-06-26 against the pinned ``pi`` build):
    - Each file is JSONL — one JSON object per line.
    - The FIRST line is the session header:
        ``{"type":"session","version":N,"id":"<uuid>","timestamp":"<ISO>","cwd":"<path>"}``
    - Subsequent lines are events keyed by ``type``:
        * ``model_change``         — carries ``modelId`` + ``provider`` (metadata)
        * ``thinking_level_change``— carries ``thinkingLevel`` (metadata)
        * ``message``              — carries the conversation body in ``message.*``
          (user text, assistant thinking, tool calls, tool results, token usage).

Privacy invariant T1 — METADATA ONLY:
    This reader ingests ONLY metadata: the session id, the cwd (derived from the
    header), the session-file mtime (liveness), and the model id observed on a
    ``model_change`` line. It **never reads, parses, or stores** any message body:
    the ``message`` line type is excluded wholesale, so no ``message.content``,
    no assistant ``thinking``, no tool call/result payloads, and no token-``usage``
    fields are ever touched. There is no per-event pricing for PI, so cost is
    unknown (``cost_micro_usd = NULL``), never faked — the Codex posture.

Graceful degradation:
    Any missing directory, IO error, or malformed/parse failure degrades to an
    empty (or partial) ReadResult — never an exception — exactly like the Codex
    reader. A single corrupt line is skipped; a corrupt file is skipped.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Result dataclass (mirrors reader/codex.py for symmetry)
# ---------------------------------------------------------------------------


@dataclass
class ReadResult:
    """Summary of one PI read cycle."""

    sessions_ingested: int = 0
    events_ingested: int = 0
    events_skipped: int = 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PI_AGENT_NAME = "pi (main)"
_PI_PROVIDER = "pi"
_PI_SESSIONS_DIR = pathlib.Path("~/.pi/agent/sessions").expanduser()

# The line type that carries the conversation body. EXCLUDED wholesale for T1 —
# we never read its ``message`` / content / usage fields.
_PI_CONTENT_LINE_TYPE = "message"
# Line types we are allowed to read — all carry metadata only.
_PI_HEADER_LINE_TYPE = "session"
_PI_METADATA_LINE_TYPES = frozenset({"model_change", "thinking_level_change"})


def _compute_event_id(session_id: str) -> str:
    """Compute idempotent event_id = sha1(pi||session_id)[:20]."""
    digest = hashlib.sha1(f"pi||{session_id}".encode()).hexdigest()
    return digest[:20]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def read_pi_sessions(
    sessions_dir: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
) -> ReadResult:
    """Read all PI session files under *sessions_dir* and ingest into *dao*.

    *sessions_dir* is the ``~/.pi/agent/sessions/`` root; each immediate
    subdirectory is a ``<dir-slug>`` encoding a session cwd, and each ``*.jsonl``
    file inside is one session. Missing directory → empty ReadResult.

    Idempotency: one event per session keyed on ``sha1(pi||session_id)[:20]`` via
    ``insert_event``'s ``INSERT OR IGNORE``.
    """
    result = ReadResult()
    if not sessions_dir.exists():
        logger.debug("PI reader: sessions dir not found at %s — empty result", sessions_dir)
        return result

    try:
        slug_dirs = sorted(p for p in sessions_dir.iterdir() if p.is_dir())
    except OSError as exc:
        logger.warning("PI reader: cannot list %s — %s", sessions_dir, exc)
        return result

    for slug_dir in slug_dirs:
        try:
            files = sorted(slug_dir.glob("*.jsonl"))
        except OSError as exc:
            logger.warning("PI reader: cannot list %s — %s", slug_dir, exc)
            continue
        for jsonl_file in files:
            _read_one_session_file(jsonl_file, dao, now_iso, result)

    return result


def read_pi_session_file(
    path: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
) -> ReadResult:
    """Read a single PI session JSONL file at *path* and ingest into *dao*.

    Convenience entry for the service/tests. Degrades to an empty ReadResult on a
    missing file or any IO/parse failure.
    """
    result = ReadResult()
    if not path.exists():
        return result
    _read_one_session_file(path, dao, now_iso, result)
    return result


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _read_one_session_file(
    path: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
    result: ReadResult,
) -> None:
    """Parse one session file (metadata only) and upsert one session + event.

    T1: only the header (``session``) and metadata event lines
    (``model_change`` / ``thinking_level_change``) are inspected. ``message``
    lines are skipped without touching their body.
    """
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        logger.warning("PI reader: cannot read %s — %s", path, exc)
        return

    session_id: str | None = None
    cwd: str | None = None
    header_ts: str | None = None
    model: str | None = None
    last_ts: str | None = None

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

        line_type = obj.get("type")

        # T1: never inspect the conversation body.
        if line_type == _PI_CONTENT_LINE_TYPE:
            continue

        if line_type == _PI_HEADER_LINE_TYPE:
            sid = obj.get("id")
            if isinstance(sid, str):
                session_id = sid
            cw = obj.get("cwd")
            if isinstance(cw, str):
                cwd = cw
            ts = obj.get("timestamp")
            if isinstance(ts, str):
                header_ts = ts
                last_ts = ts
            continue

        if line_type in _PI_METADATA_LINE_TYPES:
            mid = obj.get("modelId")
            if isinstance(mid, str) and mid:
                model = mid
            ts = obj.get("timestamp")
            if isinstance(ts, str):
                last_ts = ts
            continue

        # Unknown metadata line type — capture its timestamp only, ignore the rest.
        ts = obj.get("timestamp")
        if isinstance(ts, str):
            last_ts = ts

    # A session file with no parseable header carries no usable metadata.
    if session_id is None:
        return

    # Liveness signal: file mtime (metadata) when the body carries no usable ts.
    if last_ts is None:
        last_ts = now_iso
    first_event_at = header_ts or last_ts or now_iso

    dao.upsert_session(
        Session(
            session_id=session_id,
            provider=_PI_PROVIDER,
            agent_name=None,
            ai_title=None,
            entrypoint=None,
            cwd=cwd,
            git_branch=None,
            is_sidechain=0,
            sub_slug=None,
            first_event_at=first_event_at,
            last_event_at=last_ts,
            status="closed",
        )
    )

    dao.upsert_agent(
        Agent(
            name=_PI_AGENT_NAME,
            provider=_PI_PROVIDER,
            is_subagent=0,
            first_seen_at=first_event_at,
            last_seen_at=last_ts,
        )
    )

    event_id = _compute_event_id(session_id)
    dao.insert_event(
        Event(
            event_id=event_id,
            session_id=session_id,
            agent_name=_PI_AGENT_NAME,
            model=model or "pi",
            occurred_at=last_ts,
            tokens_input=0,  # T1: token usage bodies are never read for PI
            tokens_cache_read=0,
            tokens_cache_create=0,
            tokens_output=0,
            cost_micro_usd=None,  # PI has no per-event pricing — never faked
            pricing_version=None,
            suspect=0,
        )
    )
    result.sessions_ingested += 1
    result.events_ingested += 1
