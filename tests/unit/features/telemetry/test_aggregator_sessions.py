"""Unit tests for TelemetryAggregator.aggregate_sessions (v0.1.52 FR1).

The Sessions tab became a server-side aggregate cost dashboard: the per-session
list/detail queries were retired and replaced by ``aggregate_sessions(runtime)``,
which rolls the seeded store up into a single ``SessionAggregate`` envelope.

These tests encode the SPEC §FR1 cost-known matrix (8 cases) against seeded
in-memory stores.  The seeding pattern mirrors the retired list/detail tests
(they knew the store schema); no live telemetry.sqlite is read or touched.

The aggregate's ``cost_known``/``total_cost_usd`` semantics mirror the client
``computeStats`` that this endpoint replaced:
  * a session contributes to ``total_cost_usd`` only when it is *fully*
    cost-known (every event has a known cost) AND its cumulative cost is not
    None;
  * ``cost_known`` is True iff at least one session contributes;
  * ``total_cost_usd`` is None when no session contributes (rendered '—' for a
    cost-tracking runtime, distinct from the client 'N/A' for codex/pi);
  * codex/pi are cost-unknown runtimes: total is forced None and cost_known
    False regardless of stored data.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.schema import apply_migrations
from tests.fakes import shared_connection_factory

# ---------------------------------------------------------------------------
# Time constants
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)
_T1 = (_NOW - timedelta(hours=10)).isoformat()
_T2 = (_NOW - timedelta(hours=5)).isoformat()
_T3 = (_NOW - timedelta(hours=1)).isoformat()
_T4 = (_NOW - timedelta(minutes=30)).isoformat()
_T5 = (_NOW - timedelta(minutes=10)).isoformat()


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _FakeSCS:
    def list_all(self) -> list[object]:
        return []


class _FakePricing:
    PRICING_TABLE: dict[str, list[object]] = {}

    @staticmethod
    def pricing_age_days(models_used: list[str], when: object = None) -> None:
        return None


# ---------------------------------------------------------------------------
# DB helpers (schema mirrors the retired list/detail tests)
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_migrations(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _insert_agent(conn: sqlite3.Connection, name: str, provider: str = "claude") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)"
        " VALUES (?,?,?,?,?)",
        (name, provider, 0, _T1, _T1),
    )


def _insert_session(
    conn: sqlite3.Connection,
    session_id: str,
    provider: str,
    agent_name: str | None,
    sub_slug: str | None = None,
    cwd: str | None = "/workspace",
    first_event_at: str = _T1,
    last_event_at: str = _T2,
    status: str = "closed",
    ai_title: str | None = None,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sessions"
        " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
        "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            session_id,
            provider,
            agent_name,
            ai_title,
            "cli",
            cwd,
            "main",
            0,
            sub_slug,
            first_event_at,
            last_event_at,
            status,
        ),
    )


def _insert_event(
    conn: sqlite3.Connection,
    event_id: str,
    session_id: str,
    agent_name: str | None,
    model: str = "claude-sonnet-4-6",
    occurred_at: str = _T2,
    tokens_input: int = 100,
    tokens_cache_create: int = 0,
    tokens_cache_read: int = 0,
    tokens_output: int = 50,
    cost_micro_usd: int | None = 1000,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            event_id,
            session_id,
            agent_name,
            model,
            occurred_at,
            tokens_input,
            tokens_cache_read,
            tokens_cache_create,
            tokens_output,
            cost_micro_usd,
            "2025-01-01",
            0,
        ),
    )


def _make_aggregator(conn: sqlite3.Connection) -> TelemetryAggregator:
    return TelemetryAggregator(
        connection_factory=shared_connection_factory(conn),
        spec_context_service=_FakeSCS(),
        pricing_module=_FakePricing(),
    )


# ---------------------------------------------------------------------------
# Shape / type contract
# ---------------------------------------------------------------------------


def test_aggregate_shape_and_field_types() -> None:
    """aggregate_sessions returns a SessionAggregate with the FR1 field shape."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s1", "claude", "agent-a", status="active")
    _insert_event(conn, "e1", "s1", "agent-a", cost_micro_usd=3000)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert type(result).__name__ == "SessionAggregate"
    assert result.runtime == "claude"
    assert isinstance(result.total_sessions, int)
    assert isinstance(result.active_sessions, int)
    assert isinstance(result.total_messages, int)
    assert isinstance(result.cost_known, bool)
    assert result.total_cost_usd is None or isinstance(result.total_cost_usd, float)
    assert isinstance(result.generated_at, str) and result.generated_at
    # top_agent is a {name, session_count} object or None.
    assert result.top_agent is not None
    assert result.top_agent.name == "agent-a"
    assert result.top_agent.session_count == 1


# ---------------------------------------------------------------------------
# Matrix case 1 — codex/pi runtimes ⇒ total null + cost_known false
# ---------------------------------------------------------------------------


def test_case1_codex_runtime_cost_forced_null_and_unknown() -> None:
    """codex ⇒ total_cost_usd null, cost_known false — even with a stray cost row."""
    conn = _make_conn()
    _insert_agent(conn, "agent-x", "codex")
    _insert_session(conn, "cx1", "codex", "agent-x")
    _insert_event(conn, "e-cx1", "cx1", "agent-x", cost_micro_usd=None)
    # A stray non-null cost must NOT flip codex into cost-known territory.
    _insert_session(conn, "cx2", "codex", "agent-x")
    _insert_event(conn, "e-cx2", "cx2", "agent-x", cost_micro_usd=999_999)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("codex")

    assert result.total_cost_usd is None
    assert result.cost_known is False
    assert result.total_sessions == 2  # rows still counted


def test_case1_pi_runtime_cost_forced_null_and_unknown() -> None:
    """pi ⇒ total_cost_usd null, cost_known false."""
    conn = _make_conn()
    _insert_agent(conn, "agent-p", "pi")
    _insert_session(conn, "pi1", "pi", "agent-p")
    _insert_event(conn, "e-pi1", "pi1", "agent-p", cost_micro_usd=None)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("pi")

    assert result.total_cost_usd is None
    assert result.cost_known is False
    assert result.total_sessions == 1


# ---------------------------------------------------------------------------
# Matrix case 2 — claude, empty store ⇒ zeros + total null
# ---------------------------------------------------------------------------


def test_case2_claude_empty_store() -> None:
    """claude, empty store ⇒ total_sessions 0, total_cost_usd null, top_agent None."""
    conn = _make_conn()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.total_sessions == 0
    assert result.active_sessions == 0
    assert result.total_messages == 0
    assert result.total_cost_usd is None
    assert result.cost_known is False
    assert result.top_agent is None


# ---------------------------------------------------------------------------
# Matrix case 3 — claude, all rows cost-unknown ⇒ total null ('—' NOT 'N/A')
# ---------------------------------------------------------------------------


def test_case3_claude_all_cost_unknown_total_null() -> None:
    """claude, every session all-unknown ⇒ total null, cost_known false; rows counted."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s1", "claude", "agent-a")
    _insert_event(conn, "e1", "s1", "agent-a", cost_micro_usd=None)
    _insert_session(conn, "s2", "claude", "agent-a")
    _insert_event(conn, "e2", "s2", "agent-a", cost_micro_usd=None)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.total_sessions == 2  # rows still counted
    assert result.total_cost_usd is None  # '—' (claude-null), NOT 'N/A'
    assert result.cost_known is False


# ---------------------------------------------------------------------------
# Matrix case 4 — claude, mixed ⇒ partial sum over fully-cost-known rows only
# (AC-7(c) sabotage target: dropping the cost_known filter changes this sum)
# ---------------------------------------------------------------------------


def test_case4_claude_mixed_partial_sum_over_cost_known_rows_only() -> None:
    """Sum only rows where cost_known AND cumulative_cost_usd IS NOT NULL."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    # s1: fully known (3000 + 1500)
    _insert_session(conn, "s1", "claude", "agent-a")
    _insert_event(conn, "e1a", "s1", "agent-a", occurred_at=_T2, cost_micro_usd=3000)
    _insert_event(conn, "e1b", "s1", "agent-a", occurred_at=_T3, cost_micro_usd=1500)
    # s2: fully known (2000)
    _insert_session(conn, "s2", "claude", "agent-a")
    _insert_event(conn, "e2", "s2", "agent-a", cost_micro_usd=2000)
    # s3: all-null ⇒ cost_known false ⇒ excluded
    _insert_session(conn, "s3", "claude", "agent-a")
    _insert_event(conn, "e3", "s3", "agent-a", cost_micro_usd=None)
    # s4: mixed within the session (one known, one null) ⇒ cost_known false ⇒ excluded
    _insert_session(conn, "s4", "claude", "agent-a")
    _insert_event(conn, "e4a", "s4", "agent-a", occurred_at=_T2, cost_micro_usd=9000)
    _insert_event(conn, "e4b", "s4", "agent-a", occurred_at=_T3, cost_micro_usd=None)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    # Only s1 + s2 contribute; s3 (all-null) and s4 (mixed) are excluded.
    assert result.total_cost_usd == pytest.approx((3000 + 1500 + 2000) / 1_000_000)
    assert result.cost_known is True
    assert result.total_sessions == 4  # every session counted toward totals


# ---------------------------------------------------------------------------
# Matrix case 5 — claude, a known cost of exactly 0 ⇒ 0.0 (not null)
# ---------------------------------------------------------------------------


def test_case5_claude_zero_known_cost_is_zero_not_null() -> None:
    """A known cost of 0 ⇒ total_cost_usd 0.0 ('$0.00' — 0 ≠ null)."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s1", "claude", "agent-a")
    _insert_event(conn, "e1", "s1", "agent-a", cost_micro_usd=0)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.total_cost_usd == 0.0
    assert result.total_cost_usd is not None
    assert result.cost_known is True


# ---------------------------------------------------------------------------
# Matrix case 6 — a cost_known=1 / cumulative=null row (a 0-event session)
# contributes NOTHING and does not flip cost-known-ness
# ---------------------------------------------------------------------------


def test_case6_zero_event_session_contributes_nothing_and_does_not_flip() -> None:
    """A 0-event session (session-level cost_known, cumulative None) adds nothing."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    # A qualifying session establishes cost-known-ness.
    _insert_session(conn, "s1", "claude", "agent-a")
    _insert_event(conn, "e1", "s1", "agent-a", cost_micro_usd=5000)
    # A 0-event session: session-level cost_known True, cumulative None.
    _insert_session(conn, "s0", "claude", "agent-a")  # no events
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    # s0 contributes nothing to the sum and does not flip cost_known.
    assert result.total_cost_usd == pytest.approx(5000 / 1_000_000)
    assert result.cost_known is True
    assert result.total_sessions == 2  # s0 still counted toward totals


def test_case6_zero_event_session_alone_yields_null_cost() -> None:
    """A store of only 0-event sessions ⇒ total null, cost_known false; still counted."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s0", "claude", "agent-a")  # no events
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.total_cost_usd is None
    assert result.cost_known is False
    assert result.total_sessions == 1
    assert result.total_messages == 0


# ---------------------------------------------------------------------------
# Matrix case 7 — cost_known=false rows still count toward totals/active/top-agent
# ---------------------------------------------------------------------------


def test_case7_cost_unknown_rows_still_count_toward_totals() -> None:
    """A cost-unknown session still counts for sessions/messages/active/top-agent."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s1", "claude", "agent-a", status="active")
    _insert_event(conn, "e1a", "s1", "agent-a", cost_micro_usd=None)
    _insert_event(conn, "e1b", "s1", "agent-a", cost_micro_usd=None)
    _insert_event(conn, "e1c", "s1", "agent-a", cost_micro_usd=None)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.total_sessions == 1
    assert result.active_sessions == 1  # counted despite unknown cost
    assert result.total_messages == 3  # counted despite unknown cost
    assert result.top_agent is not None
    assert result.top_agent.name == "agent-a"  # counted toward top-agent
    assert result.top_agent.session_count == 1
    assert result.total_cost_usd is None
    assert result.cost_known is False


# ---------------------------------------------------------------------------
# Matrix case 8 — ?runtime= filtering scopes every figure
# ---------------------------------------------------------------------------


def test_case8_runtime_filter_scopes_every_figure() -> None:
    """Each aggregate figure is scoped to the requested runtime."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_agent(conn, "agent-b", "codex")
    # 2 claude sessions, both fully cost-known.
    _insert_session(conn, "c1", "claude", "agent-a", status="active")
    _insert_event(conn, "ec1", "c1", "agent-a", cost_micro_usd=4000)
    _insert_session(conn, "c2", "claude", "agent-a")
    _insert_event(conn, "ec2", "c2", "agent-a", cost_micro_usd=1000)
    # 3 codex sessions.
    _insert_session(conn, "x1", "codex", "agent-b")
    _insert_event(conn, "ex1", "x1", "agent-b", cost_micro_usd=None)
    _insert_session(conn, "x2", "codex", "agent-b")
    _insert_session(conn, "x3", "codex", "agent-b")
    conn.commit()

    agg = _make_aggregator(conn)
    claude = agg.aggregate_sessions("claude")
    codex = agg.aggregate_sessions("codex")

    assert claude.total_sessions == 2
    assert claude.active_sessions == 1
    assert claude.total_cost_usd == pytest.approx((4000 + 1000) / 1_000_000)
    assert claude.cost_known is True

    assert codex.total_sessions == 3
    assert codex.active_sessions == 0
    assert codex.total_cost_usd is None
    assert codex.cost_known is False

    # The two runtimes yield distinct figures — scoping is real.
    assert claude.total_sessions != codex.total_sessions


# ---------------------------------------------------------------------------
# Top-agent selection
# ---------------------------------------------------------------------------


def test_top_agent_picks_agent_with_most_sessions() -> None:
    """top_agent is the agent with the highest session_count."""
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_agent(conn, "agent-b", "claude")
    for sid in ("a1", "a2", "a3"):
        _insert_session(conn, sid, "claude", "agent-a")
    _insert_session(conn, "b1", "claude", "agent-b")
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("claude")

    assert result.top_agent is not None
    assert result.top_agent.name == "agent-a"
    assert result.top_agent.session_count == 3


def test_top_agent_null_agent_name_bucketed_as_operator() -> None:
    """Sessions with no agent_name bucket under the 'operator' label."""
    conn = _make_conn()
    _insert_session(conn, "x1", "codex", None)
    _insert_session(conn, "x2", "codex", None)
    conn.commit()

    result = _make_aggregator(conn).aggregate_sessions("codex")

    assert result.top_agent is not None
    assert result.top_agent.name == "operator"
    assert result.top_agent.session_count == 2
