"""Unit tests for TelemetryAggregator.aggregate_sessions (v0.1.52 FR1).

The Sessions tab became a server-side aggregate cost dashboard: the per-session
list/detail queries were retired and replaced by ``aggregate_sessions(runtime)``,
which rolls the seeded store up into a single ``SessionAggregate`` envelope.

These tests encode the SPEC §FR1 cost-known matrix against seeded in-memory
stores. The seeding pattern mirrors the retired list/detail tests (they knew the
store schema); no live telemetry.sqlite is read or touched.

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

_NOW = datetime.now(tz=UTC)
_T1 = (_NOW - timedelta(hours=10)).isoformat()
_T2 = (_NOW - timedelta(hours=5)).isoformat()
_T3 = (_NOW - timedelta(hours=1)).isoformat()


class _FakeSCS:
    def list_all(self) -> list[object]:
        return []


class _FakePricing:
    PRICING_TABLE: dict[str, list[object]] = {}

    @staticmethod
    def pricing_age_days(models_used: list[str], when: object = None) -> None:
        return None


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
# Kept: a known cost of exactly 0 -> 0.0, not null (0 != null decision)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Cost-nullability cases 1-7 (incl. zero-known-cost-is-zero-not-null) — 1 param
# ---------------------------------------------------------------------------


def test_cost_nullability_matrix() -> None:
    # a known cost of exactly 0 -> 0.0, not null (0 != null decision).
    conn_zero = _make_conn()
    _insert_agent(conn_zero, "agent-a", "claude")
    _insert_session(conn_zero, "s1", "claude", "agent-a")
    _insert_event(conn_zero, "e1", "s1", "agent-a", cost_micro_usd=0)
    conn_zero.commit()
    zero_result = _make_aggregator(conn_zero).aggregate_sessions("claude")
    assert zero_result.total_cost_usd == 0.0
    assert zero_result.total_cost_usd is not None
    assert zero_result.cost_known is True

    # codex/pi: cost forced null + unknown, even with a stray non-null cost row.
    conn_codex = _make_conn()
    _insert_agent(conn_codex, "agent-x", "codex")
    _insert_session(conn_codex, "cx1", "codex", "agent-x")
    _insert_event(conn_codex, "e-cx1", "cx1", "agent-x", cost_micro_usd=None)
    _insert_session(conn_codex, "cx2", "codex", "agent-x")
    _insert_event(conn_codex, "e-cx2", "cx2", "agent-x", cost_micro_usd=999_999)
    conn_codex.commit()
    codex_result = _make_aggregator(conn_codex).aggregate_sessions("codex")
    assert codex_result.total_cost_usd is None
    assert codex_result.cost_known is False
    assert codex_result.total_sessions == 2

    conn_pi = _make_conn()
    _insert_agent(conn_pi, "agent-p", "pi")
    _insert_session(conn_pi, "pi1", "pi", "agent-p")
    _insert_event(conn_pi, "e-pi1", "pi1", "agent-p", cost_micro_usd=None)
    conn_pi.commit()
    pi_result = _make_aggregator(conn_pi).aggregate_sessions("pi")
    assert pi_result.total_cost_usd is None
    assert pi_result.cost_known is False

    # claude, empty store -> zeros + total null.
    conn_empty = _make_conn()
    empty_result = _make_aggregator(conn_empty).aggregate_sessions("claude")
    assert empty_result.total_sessions == 0
    assert empty_result.total_cost_usd is None
    assert empty_result.cost_known is False
    assert empty_result.top_agent is None

    # claude, all rows cost-unknown -> total null ('—' NOT 'N/A'); rows still counted.
    conn_unknown = _make_conn()
    _insert_agent(conn_unknown, "agent-a", "claude")
    _insert_session(conn_unknown, "s1", "claude", "agent-a")
    _insert_event(conn_unknown, "e1", "s1", "agent-a", cost_micro_usd=None)
    _insert_session(conn_unknown, "s2", "claude", "agent-a")
    _insert_event(conn_unknown, "e2", "s2", "agent-a", cost_micro_usd=None)
    conn_unknown.commit()
    unknown_result = _make_aggregator(conn_unknown).aggregate_sessions("claude")
    assert unknown_result.total_sessions == 2
    assert unknown_result.total_cost_usd is None
    assert unknown_result.cost_known is False

    # claude, mixed -> partial sum over fully-cost-known rows only (AC-7(c) sabotage target).
    conn_mixed = _make_conn()
    _insert_agent(conn_mixed, "agent-a", "claude")
    _insert_session(conn_mixed, "s1", "claude", "agent-a")
    _insert_event(conn_mixed, "e1a", "s1", "agent-a", occurred_at=_T2, cost_micro_usd=3000)
    _insert_event(conn_mixed, "e1b", "s1", "agent-a", occurred_at=_T3, cost_micro_usd=1500)
    _insert_session(conn_mixed, "s2", "claude", "agent-a")
    _insert_event(conn_mixed, "e2", "s2", "agent-a", cost_micro_usd=2000)
    _insert_session(conn_mixed, "s3", "claude", "agent-a")
    _insert_event(conn_mixed, "e3", "s3", "agent-a", cost_micro_usd=None)
    _insert_session(conn_mixed, "s4", "claude", "agent-a")
    _insert_event(conn_mixed, "e4a", "s4", "agent-a", occurred_at=_T2, cost_micro_usd=9000)
    _insert_event(conn_mixed, "e4b", "s4", "agent-a", occurred_at=_T3, cost_micro_usd=None)
    conn_mixed.commit()
    mixed_result = _make_aggregator(conn_mixed).aggregate_sessions("claude")
    assert mixed_result.total_cost_usd == pytest.approx((3000 + 1500 + 2000) / 1_000_000)
    assert mixed_result.cost_known is True
    assert mixed_result.total_sessions == 4

    # A 0-event session contributes nothing and does not flip cost-known-ness (alone
    # or alongside a qualifying session).
    conn_zeroev = _make_conn()
    _insert_agent(conn_zeroev, "agent-a", "claude")
    _insert_session(conn_zeroev, "s1", "claude", "agent-a")
    _insert_event(conn_zeroev, "e1", "s1", "agent-a", cost_micro_usd=5000)
    _insert_session(conn_zeroev, "s0", "claude", "agent-a")  # no events
    conn_zeroev.commit()
    zeroev_result = _make_aggregator(conn_zeroev).aggregate_sessions("claude")
    assert zeroev_result.total_cost_usd == pytest.approx(5000 / 1_000_000)
    assert zeroev_result.cost_known is True
    assert zeroev_result.total_sessions == 2

    conn_zeroev_alone = _make_conn()
    _insert_agent(conn_zeroev_alone, "agent-a", "claude")
    _insert_session(conn_zeroev_alone, "s0", "claude", "agent-a")
    conn_zeroev_alone.commit()
    zeroev_alone_result = _make_aggregator(conn_zeroev_alone).aggregate_sessions("claude")
    assert zeroev_alone_result.total_cost_usd is None
    assert zeroev_alone_result.cost_known is False
    assert zeroev_alone_result.total_sessions == 1
    assert zeroev_alone_result.total_messages == 0


# ---------------------------------------------------------------------------
# Counting/filter/top-agent cases — 1 param
# ---------------------------------------------------------------------------


def test_counting_filter_and_top_agent_matrix() -> None:
    # cost-unknown rows still count toward totals/active/top-agent.
    conn = _make_conn()
    _insert_agent(conn, "agent-a", "claude")
    _insert_session(conn, "s1", "claude", "agent-a", status="active")
    _insert_event(conn, "e1a", "s1", "agent-a", cost_micro_usd=None)
    _insert_event(conn, "e1b", "s1", "agent-a", cost_micro_usd=None)
    _insert_event(conn, "e1c", "s1", "agent-a", cost_micro_usd=None)
    conn.commit()
    result = _make_aggregator(conn).aggregate_sessions("claude")
    assert result.total_sessions == 1
    assert result.active_sessions == 1
    assert result.total_messages == 3
    assert result.top_agent is not None
    assert result.top_agent.name == "agent-a"
    assert result.top_agent.session_count == 1
    assert result.total_cost_usd is None
    assert result.cost_known is False

    # ?runtime= filtering scopes every figure.
    conn2 = _make_conn()
    _insert_agent(conn2, "agent-a", "claude")
    _insert_agent(conn2, "agent-b", "codex")
    _insert_session(conn2, "c1", "claude", "agent-a", status="active")
    _insert_event(conn2, "ec1", "c1", "agent-a", cost_micro_usd=4000)
    _insert_session(conn2, "c2", "claude", "agent-a")
    _insert_event(conn2, "ec2", "c2", "agent-a", cost_micro_usd=1000)
    _insert_session(conn2, "x1", "codex", "agent-b")
    _insert_event(conn2, "ex1", "x1", "agent-b", cost_micro_usd=None)
    _insert_session(conn2, "x2", "codex", "agent-b")
    _insert_session(conn2, "x3", "codex", "agent-b")
    conn2.commit()
    agg2 = _make_aggregator(conn2)
    claude = agg2.aggregate_sessions("claude")
    codex = agg2.aggregate_sessions("codex")
    assert claude.total_sessions == 2
    assert claude.active_sessions == 1
    assert claude.total_cost_usd == pytest.approx((4000 + 1000) / 1_000_000)
    assert claude.cost_known is True
    assert codex.total_sessions == 3
    assert codex.active_sessions == 0
    assert codex.total_cost_usd is None
    assert codex.cost_known is False
    assert claude.total_sessions != codex.total_sessions

    # top_agent picks the agent with the most sessions.
    conn3 = _make_conn()
    _insert_agent(conn3, "agent-a", "claude")
    _insert_agent(conn3, "agent-b", "claude")
    for sid in ("a1", "a2", "a3"):
        _insert_session(conn3, sid, "claude", "agent-a")
    _insert_session(conn3, "b1", "claude", "agent-b")
    conn3.commit()
    top_result = _make_aggregator(conn3).aggregate_sessions("claude")
    assert top_result.top_agent is not None
    assert top_result.top_agent.name == "agent-a"
    assert top_result.top_agent.session_count == 3

    # sessions with no agent_name bucket under 'operator'.
    conn4 = _make_conn()
    _insert_session(conn4, "x1", "codex", None)
    _insert_session(conn4, "x2", "codex", None)
    conn4.commit()
    operator_result = _make_aggregator(conn4).aggregate_sessions("codex")
    assert operator_result.top_agent is not None
    assert operator_result.top_agent.name == "operator"
    assert operator_result.top_agent.session_count == 2
