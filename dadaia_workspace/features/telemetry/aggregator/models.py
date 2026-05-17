"""API-shaped frozen dataclasses for the telemetry aggregator.

These types are serialised to JSON by the HTTP handler in P7.  Their shapes
match SPEC § "Contratos de endpoint" exactly.  No content fields are present —
the privacy invariant (D-AM-03, T1) is enforced here.
"""

from __future__ import annotations

from dataclasses import dataclass


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
