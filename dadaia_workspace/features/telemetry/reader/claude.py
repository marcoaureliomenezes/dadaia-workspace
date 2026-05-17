"""Incremental Claude Code jsonl reader with byte-offset checkpoint.

Reads Claude Code session jsonl files from ~/.claude/projects/ incrementally,
persisting a byte-offset checkpoint in the telemetry SQLite database so that
subsequent calls only process new lines (tail strategy).

Privacy invariant: ALL events pass through allowlist_event() before any DB
write.  Content fields never reach the DB (T1 CRITICAL).

Decision references:
    D-AM-01  — Python stdlib only
    D-AM-03  — Allowlist reader (not denylist)
    D-AM-11  — Lazy on-request, no daemon
    D-AM-13  — usage in event.message.usage.*; model in event.message.model
    D-AM-19  — Mark suspect events (not drop)
"""
from __future__ import annotations

import hashlib
import json
import logging
import pathlib
from dataclasses import dataclass
from typing import Optional

from dadaia_workspace.features.telemetry import budget as _budget
from dadaia_workspace.features.telemetry.reader.allowlist import allowlist_event
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.models import (
    Agent,
    Event,
    ReaderState,
    Session,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Budget constants — imported from features/telemetry/budget.py (T-AM-08).
# ---------------------------------------------------------------------------

MAX_BYTES_PER_CYCLE: int = _budget.MAX_BYTES_PER_FILE_PER_CYCLE
MAX_LINE_LENGTH: int = _budget.MAX_LINE_LENGTH
MAX_EVENTS_PER_CYCLE: int = _budget.MAX_EVENTS_PER_CYCLE


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReadResult:
    """Summary of one read cycle for a single jsonl file."""

    events_ingested: int = 0
    events_skipped: int = 0
    bytes_read: int = 0
    partial_final_line: bool = False
    rotated: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_event_id(session_id: str, uuid: str) -> str:
    """Compute the idempotent event_id = sha1(sessionId||uuid)[:20]."""
    digest = hashlib.sha1(f"{session_id}||{uuid}".encode()).hexdigest()
    return digest[:20]


def _derive_agent_name(
    session_agent_name: Optional[str],
    is_sidechain: bool,
    sub_slug: Optional[str],
    provider: str = "claude",
) -> str:
    """Determine the canonical agent name for the agents table.

    Logic (per SPEC § Schema, around line 132):
    1. If the session has an agent_name (from type=agent-name event) → use it.
    2. Else if is_sidechain and sub_slug is set → use sub_slug.
    3. Else → "<provider> (main)".
    """
    if session_agent_name:
        return session_agent_name
    if is_sidechain and sub_slug:
        return sub_slug
    return f"{provider} (main)"


# ---------------------------------------------------------------------------
# Per-session accumulator (used within one read_session_file call)
# ---------------------------------------------------------------------------


@dataclass
class _SessionAcc:
    """Mutable accumulator for per-session state within one read cycle."""

    first_event_at: str
    last_event_at: str
    agent_name: Optional[str] = None
    ai_title: Optional[str] = None
    cwd: Optional[str] = None
    git_branch: Optional[str] = None
    entrypoint: Optional[str] = None
    is_sidechain: int = 0
    sub_slug: Optional[str] = None


# ---------------------------------------------------------------------------
# Core reader function
# ---------------------------------------------------------------------------


def read_session_file(
    path: pathlib.Path,
    dao: TelemetryDao,
    now_iso: str,
) -> ReadResult:
    """Incrementally read *path* (a Claude Code jsonl file) into *dao*.

    Uses the byte-offset checkpoint stored in ``reader_state`` to seek
    forward from the last known-good position.  Only fully-terminated
    lines (ending with ``\\n``) are parsed; a partial final line causes the
    offset to be rewound to the start of that incomplete line so the next
    cycle retries it.

    Inode rotation detection: if ``stat().st_ino`` differs from the stored
    ``last_inode``, the file was rotated/recreated and reading restarts
    from byte 0.

    Budget enforcement stops processing early (but saves the current offset)
    when any of the following limits are reached:
    - Bytes read this cycle exceed ``MAX_BYTES_PER_CYCLE``.
    - Events processed this cycle exceed ``MAX_EVENTS_PER_CYCLE``.
    - A line exceeds ``MAX_LINE_LENGTH`` (line skipped, offset advanced).
    """
    result = ReadResult()

    # ------------------------------------------------------------------
    # Guard: file must exist
    # ------------------------------------------------------------------
    if not path.exists():
        logger.warning("Claude reader: file not found: %s", path)
        return result

    stat = path.stat()
    current_inode = stat.st_ino
    current_mtime = stat.st_mtime
    str_path = str(path)

    # ------------------------------------------------------------------
    # Load or initialise reader state
    # ------------------------------------------------------------------
    state: Optional[ReaderState] = dao.get_reader_state(str_path)
    byte_offset: int = 0

    if state is not None:
        if state.last_inode != 0 and state.last_inode != current_inode:
            # File was rotated / recreated — reset offset and re-read
            logger.info(
                "Claude reader: inode changed for %s (was %d, now %d) — resetting offset",
                path,
                state.last_inode,
                current_inode,
            )
            byte_offset = 0
            result.rotated = True
        else:
            byte_offset = state.byte_offset

    # ------------------------------------------------------------------
    # Parse lines from file starting at byte_offset.
    # Accumulate per-session metadata; process events immediately.
    # ------------------------------------------------------------------
    events_processed = 0
    bytes_this_cycle = 0
    session_acc: dict[str, _SessionAcc] = {}
    # Collect all events for post-processing after session state is stable
    pending_events: list[tuple[str, dict]] = []  # (session_id, clean)

    lines_data: list[tuple[int, bytes]] = []   # (line_start, raw_line)

    with open(path, "rb") as fh:
        fh.seek(byte_offset)

        while True:
            # Budget: bytes
            if bytes_this_cycle >= MAX_BYTES_PER_CYCLE:
                logger.debug(
                    "Claude reader: byte budget exhausted for %s at offset %d",
                    path,
                    byte_offset,
                )
                break

            # Budget: events
            if events_processed >= MAX_EVENTS_PER_CYCLE:
                logger.debug(
                    "Claude reader: event budget exhausted for %s at offset %d",
                    path,
                    byte_offset,
                )
                break

            line_start = fh.tell()
            raw_line = fh.readline()

            if not raw_line:
                # EOF
                break

            # Incomplete line (no trailing \n) — rewind and stop
            if not raw_line.endswith(b"\n"):
                fh.seek(line_start)
                result.partial_final_line = True
                break

            line_len = len(raw_line)
            bytes_this_cycle += line_len
            result.bytes_read += line_len

            # Budget: line length
            if line_len > MAX_LINE_LENGTH:
                logger.warning(
                    "Claude reader: line too long (%d bytes) at offset %d in %s — skipping",
                    line_len,
                    line_start,
                    path,
                )
                byte_offset = fh.tell()
                result.events_skipped += 1
                continue

            # Skip blank lines
            stripped = raw_line.strip()
            if not stripped:
                byte_offset = fh.tell()
                continue

            # Parse JSON
            try:
                raw_event = json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning(
                    "Claude reader: JSON parse error at offset %d in %s — skipping",
                    line_start,
                    path,
                )
                byte_offset = fh.tell()
                result.events_skipped += 1
                continue

            # Allowlist filter (T1 CRITICAL — must come before any DB write)
            clean = allowlist_event(raw_event)
            if clean is None:
                byte_offset = fh.tell()
                result.events_skipped += 1
                continue

            # Accumulate session metadata
            session_id: str = clean["sessionId"]
            occurred_at: str = clean.get("timestamp", now_iso)
            event_type: str = clean.get("type", "")
            is_sidechain_raw = clean.get("isSidechain", False)
            is_sidechain_int = 1 if is_sidechain_raw else 0
            sub_slug = clean.get("slug") or None

            if session_id not in session_acc:
                session_acc[session_id] = _SessionAcc(
                    first_event_at=occurred_at,
                    last_event_at=occurred_at,
                    cwd=clean.get("cwd"),
                    git_branch=clean.get("gitBranch"),
                    entrypoint=clean.get("entrypoint"),
                    is_sidechain=is_sidechain_int,
                    sub_slug=sub_slug,
                )
            else:
                sc = session_acc[session_id]
                sc.last_event_at = occurred_at
                if clean.get("cwd") and not sc.cwd:
                    sc.cwd = clean.get("cwd")
                if clean.get("gitBranch") and not sc.git_branch:
                    sc.git_branch = clean.get("gitBranch")

            sc = session_acc[session_id]

            if event_type == "agent-name":
                sc.agent_name = clean.get("agentName")
            elif event_type == "ai-title":
                sc.ai_title = clean.get("aiTitle")

            # Defer assistant event insertion until after session state is built
            pending_events.append((session_id, clean))
            events_processed += 1
            byte_offset = fh.tell()

    # ------------------------------------------------------------------
    # Write sessions and agents to DB (with accumulated state)
    # ------------------------------------------------------------------
    for session_id, sc in session_acc.items():
        agent_canonical = _derive_agent_name(
            sc.agent_name,
            bool(sc.is_sidechain),
            sc.sub_slug,
            provider="claude",
        )

        dao.upsert_session(
            Session(
                session_id=session_id,
                provider="claude",
                agent_name=sc.agent_name,
                ai_title=sc.ai_title,
                entrypoint=sc.entrypoint,
                cwd=sc.cwd,
                git_branch=sc.git_branch,
                is_sidechain=sc.is_sidechain,
                sub_slug=sc.sub_slug,
                first_event_at=sc.first_event_at,
                last_event_at=sc.last_event_at,
                status="closed",
            )
        )

        dao.upsert_agent(
            Agent(
                name=agent_canonical,
                provider="claude",
                is_subagent=1 if (bool(sc.is_sidechain) or sc.agent_name) else 0,
                first_seen_at=sc.first_event_at,
                last_seen_at=sc.last_event_at,
            )
        )

    # ------------------------------------------------------------------
    # Insert event rows (only assistant events with usage)
    # ------------------------------------------------------------------
    for session_id, clean in pending_events:
        event_type = clean.get("type", "")
        if event_type != "assistant":
            continue

        usage = clean.get("usage")
        model = clean.get("model", "")
        uuid = clean.get("uuid", "")

        if not (usage and model and uuid):
            result.events_skipped += 1
            continue

        # Resolve the canonical agent name from accumulated session state
        sc = session_acc[session_id]
        agent_canonical = _derive_agent_name(
            sc.agent_name,
            bool(sc.is_sidechain),
            sc.sub_slug,
            provider="claude",
        )

        event_id = _compute_event_id(session_id, uuid)
        suspect = 1 if clean.get("_suspect") else 0

        dao.insert_event(
            Event(
                event_id=event_id,
                session_id=session_id,
                agent_name=agent_canonical,
                model=model,
                occurred_at=clean.get("timestamp", now_iso),
                tokens_input=usage.get("input_tokens", 0),
                tokens_cache_read=usage.get("cache_read_input_tokens", 0),
                tokens_cache_create=usage.get("cache_creation_input_tokens", 0),
                tokens_output=usage.get("output_tokens", 0),
                cost_micro_usd=None,       # P5 pricing module fills this
                pricing_version=None,      # P5 pricing module fills this
                suspect=suspect,
            )
        )
        result.events_ingested += 1

    # ------------------------------------------------------------------
    # Persist reader state checkpoint
    # ------------------------------------------------------------------
    dao.upsert_reader_state(
        ReaderState(
            file_path=str_path,
            kind="claude_jsonl",
            byte_offset=byte_offset,
            last_mtime=current_mtime,
            last_inode=current_inode,
            error_count=0,
            last_ingest_at=now_iso,
        )
    )

    return result
