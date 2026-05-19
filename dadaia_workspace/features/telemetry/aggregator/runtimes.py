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

import json
import pathlib
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionRow,
)
from dadaia_workspace.features.telemetry import pricing as _pricing_module


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
# Codex adapter (stub — Phase A; full impl lives in Phase E)
# ---------------------------------------------------------------------------


class CodexRuntimeAdapter:
    """Enrichment + liveness stub for Codex sessions.

    Phase A delivers a stub only:
    - enrich_row sets cumulative_cost_usd=None and cost_known=False.
    - liveness returns "idle" unconditionally.

    The full liveness implementation (history.jsonl tail + threads.updated_at
    delta + threads.archived flag) is delivered in Phase E (PR5-E1).
    """

    def enrich_row(self, row: SessionRow) -> SessionRow:
        """Codex: cost is not tracked; set cumulative_cost_usd=None, cost_known=False."""
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
        """Stub: Phase E will implement real liveness from ~/.codex/state_5.sqlite."""
        return "idle"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

#: Default adapter registry.  Callers may override for testing.
ADAPTER_REGISTRY: dict[str, RuntimeAdapter] = {
    "claude": ClaudeRuntimeAdapter(),
    "codex": CodexRuntimeAdapter(),
}


def get_adapter(runtime: str) -> RuntimeAdapter:
    """Return the adapter for *runtime*, or raise KeyError for unknown runtimes."""
    return ADAPTER_REGISTRY[runtime]
