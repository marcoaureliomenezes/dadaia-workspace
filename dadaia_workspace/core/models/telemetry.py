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

import hashlib
import json
from collections.abc import Mapping
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
    """Top-level response shape for a session-list query.

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


# ---------------------------------------------------------------------------
# Session-aggregate dataclasses (panel-plumbing v0.1.52 FR1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopAgent:
    """The busiest agent in a runtime's aggregate — no cost, no content."""

    name: str  # agent_name, or "operator" when the session has no agent_name
    session_count: int


@dataclass(frozen=True)
class SessionAggregate:
    """Server-side aggregate cost summary for GET /api/sessions.

    Replaces the per-session list/detail payload with the 4-card dashboard's
    numbers computed server-side (panel-plumbing v0.1.52 FR1). No content
    fields — privacy invariant preserved.

    total_cost_usd: sum over sessions that are *fully* cost-known (every event
        has a known cost) with a non-None cumulative cost; None when no session
        contributes (rendered '—' for a cost-tracking runtime, distinct from the
        client 'N/A' for cost-unknown runtimes).
    cost_known: True iff at least one session contributes a known cost. Forced
        False for cost-unknown runtimes (codex/kimi), which never track cost.
    active_sessions / total_messages / top_agent: computed from every session in
        the runtime, including cost-unknown ones.
    """

    runtime: str
    total_sessions: int
    active_sessions: int
    total_cost_usd: float | None
    cost_known: bool
    total_messages: int
    top_agent: TopAgent | None
    generated_at: str  # ISO UTC timestamp


@dataclass(frozen=True)
class GovernanceEvent:
    """One governance record change, as observed by the verb that made it (0.4.7 FR2).

    Carries NO content — only the hash of the record the verb left on disk, so a hand
    edit is measurable (the committed record no longer hashes to the latest event)
    without the store ever holding a second copy of the ledger. There is no ``agent``
    field: ``sessions.agent_name`` joins on ``session_id``. There is no commit sha: a
    governance verb never runs git.
    """

    event_id: str
    ts: str
    session_id: str
    context: str
    verb: str
    ledger: str
    record_id: str
    record_hash: str


def record_hash(record: Mapping[str, object]) -> str:
    """The sha256 of a governance record's canonical JSON — byte-for-byte the line a
    JSONL ledger writes (``json.dumps(..., sort_keys=True, ensure_ascii=False)``), so
    the hash can be recomputed from the committed file alone.

    Lives HERE, beside :class:`GovernanceEvent`, because the verb that writes the hash
    (``cli/_governance_event.py``) and the doctor rule that recomputes it
    (``features/specs/{ledgers,release_tree}.py``) must agree byte-for-byte. Two homes
    would be two hash functions, and the mismatch would read as a hand edit forever.
    """
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class GovernanceBaseline:
    """The governance-event state a doctor rule needs, read ONCE into plain data.

    The whole hand-edit judgment lives here — the ledger rules and the release-tree
    rule ask :meth:`hand_edit` and render its answer, so "what is a hand edit" is
    decided in one place and ``features/specs`` never imports ``features/telemetry``
    (the CLI composition root reads the store and passes this record in, exactly as
    ``live_shas`` travels).

    ``events`` is the LATEST event per ``(ledger, record_id)``, already scoped to one
    spec context. Absent store, unreadable store, or a session with no context = no
    baseline at all (``None`` at the call site), and every rule is silent: a consumer
    without telemetry is not a consumer with drift.
    """

    events: tuple[GovernanceEvent, ...]

    @property
    def first_ts(self) -> str:
        """The oldest event this baseline holds — the measurement horizon. A record
        older than it predates the verbs and is never a hand edit (SPEC 0.4.7 §5):
        the 564 existing bug records enter measurement only when a verb touches them.
        """
        return min(event.ts for event in self.events)

    def hand_edit(
        self,
        *,
        ledger: str,
        record_id: str,
        record: Mapping[str, object],
        record_ts: str | None = None,
    ) -> str | None:
        """The message for a record no verb wrote, or ``None`` when the record and the
        events agree.

        Two shapes, one question — "did a verb write THIS?":
        a matching event whose ``record_hash`` differs (the record changed after the
        verb), or no event at all for a record newer than :attr:`first_ts` (the record
        appeared without a verb). ``record_ts=None`` opts out of the second shape for a
        record class that carries no timestamp of its own (``_RELEASE.json``).
        """
        if not self.events:
            return None
        for event in self.events:
            if event.ledger == ledger and event.record_id == record_id:
                if event.record_hash == record_hash(record):
                    return None
                return (
                    f"record changed after `{event.verb}` ({event.ts}) wrote it — "
                    "hand edit, not a verb"
                )
        if record_ts is not None and record_ts > self.first_ts:
            return (
                f"no governance verb ever wrote this record, and it is newer than the "
                f"first governance event ({self.first_ts}) — hand edit, not a verb"
            )
        return None
