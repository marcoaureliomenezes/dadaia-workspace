"""Core telemetry models — `core/models/telemetry.py`.

API-shaped frozen dataclasses for the telemetry aggregator. These are pure
data-transfer objects (no behavior, stdlib-only) serialised to JSON by the
panel HTTP handler. Their shapes match SPEC § "Contratos de endpoint" exactly —
no content fields are present (privacy invariant D-AM-03, T1).

They live in `core/models` so cross-feature consumers (the panel view layer)
depend on a core type rather than importing `features.telemetry` directly
(NEW-01 / AR-03 boundary). `features.telemetry.aggregator.models` re-exports
every name here for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TokenTotals:
    """Aggregated token counts across a scope (agent, session, …)."""

    input: int
    cache_creation: int
    cache_read: int
    output: int


@dataclass(frozen=True)
class ContextBreakdown:
    """Cost/session breakdown for one Spec Context Project bucket."""

    context_slug: str | None  # None  → unassigned bucket
    context_name: str  # display name, e.g. "dadaia-workspace" or "unassigned"
    session_count: int
    cost_usd: float | None  # None when cost is unknown for all sessions (Codex)
    cost_fraction: float | None  # 0.0..1.0; None when total cost is unknown


@dataclass(frozen=True)
class RecentSession:
    """One session row in an agent's recent_sessions list."""

    session_id_prefix: str  # first 8 chars (devops T9 — anti-enumeration)
    date: str  # ISO date YYYY-MM-DD
    cost_usd: float | None
    entrypoint: str | None
    git_branch: str | None
    context_slug: str | None
    token_counts: TokenTotals


@dataclass(frozen=True)
class AgentSummary:
    """Full summary for one agent, including breakdown and recent sessions."""

    agent_id: str  # canonical agent name
    display_name: str
    providers: list[str]  # e.g. ['claude'] or ['codex'] or both
    dominant_model: str | None
    is_subagent: bool
    session_count: int
    total_cost_usd: float | None  # None when cost_known=False
    cost_known: bool
    last_activity_at: str  # ISO timestamp
    token_totals: TokenTotals
    context_breakdown: list[ContextBreakdown]
    recent_sessions: list[RecentSession]
    suspect_count: int  # D-AM-19 — count of events with suspect=1


@dataclass(frozen=True)
class AgentListResult:
    """Top-level response for GET /api/agents."""

    generated_at: str  # ISO timestamp
    window_days: int
    pricing_age_days: int | None
    pricing_model_date: str | None  # ISO date of newest effective_from
    agents: list[AgentSummary]


@dataclass(frozen=True)
class WorkflowSummary:
    """One workflow card — no cost numbers (frontend D-01)."""

    workflow_id: str
    display_name: str
    description: str | None
    source: str  # ".claude/skills/" or ".agents/skills/"
    agent_ids: list[str]


@dataclass(frozen=True)
class WorkflowListResult:
    """Top-level response for GET /api/workflows."""

    generated_at: str
    source_hint: str
    workflows: list[WorkflowSummary]


# ---------------------------------------------------------------------------
# Session-level dataclasses (panel-r5-v1 FR1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionRow:
    """One session row for the Sessions panel tab.

    Fields per SPEC §FR1.  No content fields — privacy invariant enforced.

    context_size_tokens: input + cache_creation + cache_read tokens from the
        most recent assistant event for the session (the working set the model
        received; naked input_tokens is misleading once cache warms).
    message_count: COUNT(events) for the session — rendered as "AI Turns".
    cumulative_cost_usd: None when cost is not tracked (Codex).
    cost_known: False for Codex rows or when cost cannot be computed.
    status: "active" | "idle" | "ended" — resolved by the RuntimeAdapter.
    agent_name: None for pre-backfill historical rows.
    ai_title: operator-generated label for the session, None when absent.
    """

    session_id: str
    runtime: str
    project: str | None
    cwd: str | None
    model: str | None
    started_at: str
    last_activity_at: str
    message_count: int
    context_size_tokens: int
    cumulative_cost_usd: float | None
    cost_known: bool
    status: Literal["active", "idle", "ended"]
    agent_name: str | None
    ai_title: str | None


@dataclass(frozen=True)
class SessionDetail(SessionRow):
    """Enriched detail for a single session — extends SessionRow.

    Adds a summary of recent event references (timestamps only; no content).
    event_count mirrors message_count for consumers that need the raw integer.
    """

    event_timestamps: tuple[str, ...]  # ISO timestamps of all events, asc


@dataclass(frozen=True)
class SessionListResult:
    """Top-level response for list_sessions().

    sessions: ordered by last_activity_at DESC.
    runtime: the runtime filter that was applied.
    project: the project filter that was applied (None = no filter).
    limit: the limit that was applied (None = no limit).
    generated_at: ISO UTC timestamp when the result was built.
    total_count: total rows before limit was applied.
    """

    sessions: list[SessionRow]
    runtime: str
    project: str | None
    limit: int | None
    generated_at: str
    total_count: int
