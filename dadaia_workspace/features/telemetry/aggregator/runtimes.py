"""RuntimeAdapter protocol and implementations for Claude + Codex runtimes.

Panel-r5-v1 FR2 — per-runtime adapter registry.

Each adapter handles two concerns:
1. Enrichment — fills in runtime-specific fields on SessionRow / SessionDetail.
2. Liveness — classifies a session as active / idle / ended.

The TelemetryAggregator resolves the right adapter via a {runtime: adapter}
mapping and delegates enrichment per row before returning the dataclass.

Security:
- Liveness reads only metadata (file mtime, JSON fields from ~/.claude/sessions/)
  — no content is read or logged (privacy invariant T1).
- All filesystem / SQLite accesses are wrapped in try/except; failures degrade
  gracefully to "idle" rather than crashing the aggregator.
"""

from __future__ import annotations

import collections
import contextlib
import json
import pathlib
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionRow,
)

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Protocol for per-runtime enrichment and liveness classification."""

    def enrich_row(self, row: SessionRow) -> SessionRow:
        """Return a new (frozen) SessionRow with runtime-specific fields set.

        Implementations must return a new instance — SessionRow is frozen.
        """
        ...

    def enrich_detail(self, detail: SessionDetail) -> SessionDetail:
        """Return a new (frozen) SessionDetail with runtime-specific fields set."""
        ...

    def liveness(self, session_id: str, cwd: str) -> Literal["active", "idle", "ended"]:
        """Classify a session as active / idle / ended.

        active: last activity within 5 minutes.
        idle:   last activity within 60 minutes.
        ended:  no activity for more than 60 minutes, or session file absent.
        """
        ...


# ---------------------------------------------------------------------------
# Claude adapter
# ---------------------------------------------------------------------------

_CLAUDE_ACTIVE_MINUTES = 5
_CLAUDE_IDLE_MINUTES = 60


class ClaudeRuntimeAdapter:
    """Enrichment + liveness for Claude Code sessions.

    Liveness: reads ~/.claude/sessions/<session_id>.json (if present) and
    uses the file's mtime as the last-activity signal.  Falls back to
    "ended" when the file is absent; "idle" on any parse / IO failure.

    Enrichment: calls pricing.compute_cost for cumulative_cost_usd using the
    model and event-level usage extracted from the aggregator query.  The cost
    is passed in via the SessionRow fields; this adapter recomputes from scratch
    only when the row's cost_known is False and the model is known.

    Note: for list_sessions the aggregator already computes cumulative cost from
    event rows.  The adapter's enrich_row therefore only forces cost_known=True
    when cost data is already present (validating the pipeline) or patches the
    row when the aggregator could not compute it.  In Phase A the adapter trusts
    the row's cumulative_cost_usd when it is not None and simply marks
    cost_known=True.
    """

    def enrich_row(self, row: SessionRow) -> SessionRow:
        """Set cost_known=True for Claude rows that already have a cost value.

        If cumulative_cost_usd is None, the row had no events with known cost
        (e.g. an unknown model); cost_known stays False in that case.
        """
        if row.cumulative_cost_usd is not None:
            return SessionRow(
                session_id=row.session_id,
                runtime=row.runtime,
                project=row.project,
                cwd=row.cwd,
                model=row.model,
                started_at=row.started_at,
                last_activity_at=row.last_activity_at,
                message_count=row.message_count,
                context_size_tokens=row.context_size_tokens,
                cumulative_cost_usd=row.cumulative_cost_usd,
                cost_known=True,
                status=row.status,
                agent_name=row.agent_name,
                ai_title=row.ai_title,
            )
        # Try to compute cost from usage if model is known.
        # In list_sessions context we don't have per-event usage here; the
        # aggregator already summed it.  If cost is None → model unknown or no
        # events; leave cost_known=False.
        return row

    def enrich_detail(self, detail: SessionDetail) -> SessionDetail:
        """Same logic as enrich_row but returns a SessionDetail."""
        if detail.cumulative_cost_usd is not None:
            return SessionDetail(
                session_id=detail.session_id,
                runtime=detail.runtime,
                project=detail.project,
                cwd=detail.cwd,
                model=detail.model,
                started_at=detail.started_at,
                last_activity_at=detail.last_activity_at,
                message_count=detail.message_count,
                context_size_tokens=detail.context_size_tokens,
                cumulative_cost_usd=detail.cumulative_cost_usd,
                cost_known=True,
                status=detail.status,
                agent_name=detail.agent_name,
                ai_title=detail.ai_title,
                event_timestamps=detail.event_timestamps,
            )
        return detail

    def liveness(self, session_id: str, cwd: str) -> Literal["active", "idle", "ended"]:
        """Classify session liveness by reading ~/.claude/sessions/<id>.json mtime.

        Returns:
        - "active"  if mtime delta ≤ 5 minutes
        - "idle"    if mtime delta ≤ 60 minutes
        - "ended"   if delta > 60 minutes or file absent
        - "idle"    on any parse / IO failure (graceful degradation)
        """
        sessions_dir = pathlib.Path.home() / ".claude" / "sessions"
        session_file = sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return "ended"

        try:
            mtime = session_file.stat().st_mtime
            last_active = datetime.fromtimestamp(mtime, tz=UTC)
            delta = datetime.now(tz=UTC) - last_active

            if delta <= timedelta(minutes=_CLAUDE_ACTIVE_MINUTES):
                return "active"
            if delta <= timedelta(minutes=_CLAUDE_IDLE_MINUTES):
                return "idle"
            return "ended"
        except (OSError, ValueError):
            return "idle"


# ---------------------------------------------------------------------------
# Codex adapter — Phase E full implementation
# ---------------------------------------------------------------------------

_CODEX_DB_PATH = pathlib.Path.home() / ".codex" / "state_5.sqlite"
_CODEX_HISTORY_PATH = pathlib.Path.home() / ".codex" / "history.jsonl"
_CODEX_ACTIVE_MINUTES = 5
_CODEX_IDLE_MINUTES = 60
# Number of tail lines to scan in history.jsonl to find the most recent ts.
_CODEX_HISTORY_TAIL_LINES = 200


class CodexRuntimeAdapter:
    """Enrichment + liveness for Codex sessions.

    Enrichment (PR5-E2 invariant):
    - enrich_row sets cumulative_cost_usd=None and cost_known=False.
    - compute_cost is NEVER called for Codex rows (Codex does not expose
      per-event token cost; the pricing function is Claude-only).

    Liveness (PR5-E1):
    - Reads ~/.codex/state_5.sqlite threads.updated_at and threads.archived.
    - Tails ~/.codex/history.jsonl for the most recent ts matching session_id.
    - delta = now - max(updated_at_dt, history_ts_dt)  (whichever is newer).
    - Classification:
        archived == 1            → "ended"
        delta > 60 min           → "ended"
        delta > 5 min            → "idle"
        delta ≤ 5 min            → "active"
    - File missing / session absent / parse failure → "idle"
      (graceful degradation; preserves "we don't know but it might still work").

    Security note: reads only metadata fields (timestamps, archived flag).
    Content columns (title, first_user_message, rollout_path) are never read
    or logged (privacy invariant T1 from SPEC §3).
    """

    def enrich_row(self, row: SessionRow) -> SessionRow:
        """Codex: cost is not tracked; set cumulative_cost_usd=None, cost_known=False.

        IMPORTANT: compute_cost is NOT called here. Codex does not have
        per-event token pricing; setting cumulative_cost_usd=None directly
        is the correct and final behaviour (PR5-E2 invariant).
        """
        return SessionRow(
            session_id=row.session_id,
            runtime=row.runtime,
            project=row.project,
            cwd=row.cwd,
            model=row.model,
            started_at=row.started_at,
            last_activity_at=row.last_activity_at,
            message_count=row.message_count,
            context_size_tokens=row.context_size_tokens,
            cumulative_cost_usd=None,
            cost_known=False,
            status=row.status,
            agent_name=row.agent_name,
            ai_title=row.ai_title,
        )

    def enrich_detail(self, detail: SessionDetail) -> SessionDetail:
        """Codex: cost not tracked; set cumulative_cost_usd=None, cost_known=False."""
        return SessionDetail(
            session_id=detail.session_id,
            runtime=detail.runtime,
            project=detail.project,
            cwd=detail.cwd,
            model=detail.model,
            started_at=detail.started_at,
            last_activity_at=detail.last_activity_at,
            message_count=detail.message_count,
            context_size_tokens=detail.context_size_tokens,
            cumulative_cost_usd=None,
            cost_known=False,
            status=detail.status,
            agent_name=detail.agent_name,
            ai_title=detail.ai_title,
            event_timestamps=detail.event_timestamps,
        )

    def liveness(self, session_id: str, cwd: str) -> Literal["active", "idle", "ended"]:
        """Classify Codex session liveness from ~/.codex/state_5.sqlite + history.jsonl.

        Returns:
        - "active"  if max(updated_at, history_ts) delta ≤ 5 minutes
        - "idle"    if max delta ≤ 60 minutes (and not archived)
        - "ended"   if delta > 60 minutes OR threads.archived = 1
        - "idle"    on any IO / parse / DB error (graceful degradation)
        """
        try:
            return self._classify_liveness(session_id)
        except Exception:  # noqa: BLE001 — catch-all for graceful degradation
            return "idle"

    def _classify_liveness(self, session_id: str) -> Literal["active", "idle", "ended"]:
        """Inner liveness logic; caller wraps in try/except for degradation."""
        home = pathlib.Path.home()
        db_path = home / ".codex" / "state_5.sqlite"
        history_path = home / ".codex" / "history.jsonl"

        # --- Read threads row (updated_at + archived) ---
        if not db_path.exists():
            return "idle"

        updated_at_unix: int | None = None
        archived: int = 0

        # Open read-only using URI mode to avoid write-lock on the live DB.
        # contextlib.closing: sqlite3's own context manager commits/rolls back but
        # never closes — the leaked handle blocks tempdir deletion on Windows.
        uri = f"file:{db_path}?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as con:
            row = con.execute(
                "SELECT updated_at, archived FROM threads WHERE id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            # Session not found in threads → we have no data; degrade gracefully.
            return "idle"

        updated_at_unix = int(row[0])
        archived = int(row[1])

        if archived:
            return "ended"

        # --- Compute delta from threads.updated_at ---
        now = datetime.now(tz=UTC)
        updated_at_dt = datetime.fromtimestamp(updated_at_unix, tz=UTC)
        most_recent_dt = updated_at_dt

        # --- Tail history.jsonl for a more recent ts ---
        if history_path.exists():
            history_ts = self._tail_history_ts(history_path, session_id)
            if history_ts is not None:
                history_dt = datetime.fromtimestamp(history_ts, tz=UTC)
                if history_dt > most_recent_dt:
                    most_recent_dt = history_dt

        # --- Classify by delta ---
        delta = now - most_recent_dt
        if delta <= timedelta(minutes=_CODEX_ACTIVE_MINUTES):
            return "active"
        if delta <= timedelta(minutes=_CODEX_IDLE_MINUTES):
            return "idle"
        return "ended"

    @staticmethod
    def _tail_history_ts(history_path: pathlib.Path, session_id: str) -> int | None:
        """Return the most recent `ts` value in history.jsonl for *session_id*.

        Reads the last _CODEX_HISTORY_TAIL_LINES lines using a deque (O(1) memory
        relative to file size).  Skips malformed JSON lines silently.

        Returns None when no matching line is found.
        """
        with history_path.open("r", encoding="utf-8", errors="replace") as fh:
            tail = collections.deque(fh, maxlen=_CODEX_HISTORY_TAIL_LINES)

        latest_ts: int | None = None
        for line in tail:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip malformed lines; graceful degradation
            if entry.get("session_id") != session_id:
                continue
            ts = entry.get("ts")
            if isinstance(ts, (int, float)):
                ts_int = int(ts)
                if latest_ts is None or ts_int > latest_ts:
                    latest_ts = ts_int

        return latest_ts


# ---------------------------------------------------------------------------
# Kimi Code adapter
# ---------------------------------------------------------------------------

_KIMI_SESSIONS_DIR = pathlib.Path.home() / ".kimi-code" / "sessions"
_KIMI_ACTIVE_MINUTES = 5
_KIMI_IDLE_MINUTES = 60


class KimiRuntimeAdapter:
    """Enrichment + liveness for Kimi Code sessions.

    Enrichment (cost posture mirrors Codex — "no fake telemetry"):
    - enrich_row / enrich_detail set cumulative_cost_usd=None and cost_known=False.
    - Kimi has no per-event token pricing here, so cost is unknown and never faked.

    Liveness:
    - Kimi persists one directory per session under
      ``~/.kimi-code/sessions/<wd-slug>/<session-id>/``; the directory mtime is
      the last-activity signal.
    - Classification (mirrors the Claude/Codex posture):
        delta ≤ 5 min   → "active"
        delta ≤ 60 min  → "idle"
        delta > 60 min  → "ended"
        dir absent       → "ended"
        any IO failure   → "idle" (graceful degradation)

    Security note (privacy invariant T1): liveness reads only directory metadata
    (mtime). No session content is opened, read, or logged.
    """

    def enrich_row(self, row: SessionRow) -> SessionRow:
        """Kimi: cost is not tracked; set cumulative_cost_usd=None, cost_known=False."""
        return SessionRow(
            session_id=row.session_id,
            runtime=row.runtime,
            project=row.project,
            cwd=row.cwd,
            model=row.model,
            started_at=row.started_at,
            last_activity_at=row.last_activity_at,
            message_count=row.message_count,
            context_size_tokens=row.context_size_tokens,
            cumulative_cost_usd=None,
            cost_known=False,
            status=row.status,
            agent_name=row.agent_name,
            ai_title=row.ai_title,
        )

    def enrich_detail(self, detail: SessionDetail) -> SessionDetail:
        """Kimi: cost is not tracked; set cumulative_cost_usd=None, cost_known=False."""
        return SessionDetail(
            session_id=detail.session_id,
            runtime=detail.runtime,
            project=detail.project,
            cwd=detail.cwd,
            model=detail.model,
            started_at=detail.started_at,
            last_activity_at=detail.last_activity_at,
            message_count=detail.message_count,
            context_size_tokens=detail.context_size_tokens,
            cumulative_cost_usd=None,
            cost_known=False,
            status=detail.status,
            agent_name=detail.agent_name,
            ai_title=detail.ai_title,
            event_timestamps=detail.event_timestamps,
        )

    def liveness(self, session_id: str, cwd: str) -> Literal["active", "idle", "ended"]:
        """Classify liveness from the session directory's mtime (metadata only)."""
        try:
            match: pathlib.Path | None = None
            if _KIMI_SESSIONS_DIR.is_dir():
                for wd_dir in _KIMI_SESSIONS_DIR.iterdir():
                    candidate = wd_dir / session_id
                    if candidate.is_dir():
                        match = candidate
                        break
            if match is None:
                return "ended"
            mtime = datetime.fromtimestamp(match.stat().st_mtime, tz=UTC)
            now = datetime.now(tz=UTC)
            delta_minutes = (now - mtime).total_seconds() / 60
            if delta_minutes <= _KIMI_ACTIVE_MINUTES:
                return "active"
            if delta_minutes <= _KIMI_IDLE_MINUTES:
                return "idle"
            return "ended"
        except OSError:
            return "idle"


ADAPTER_REGISTRY: dict[str, RuntimeAdapter] = {
    "claude": ClaudeRuntimeAdapter(),
    "codex": CodexRuntimeAdapter(),
    "kimi-code": KimiRuntimeAdapter(),
}


def get_adapter(runtime: str) -> RuntimeAdapter:
    """Return the adapter for *runtime*, or raise KeyError for unknown runtimes."""
    return ADAPTER_REGISTRY[runtime]
