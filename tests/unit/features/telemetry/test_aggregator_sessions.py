"""Unit tests for TelemetryAggregator.list_sessions and get_session.

All fixtures are built in-memory via sqlite3 INSERT statements — no live
telemetry.sqlite is read or touched.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionListResult,
)
from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

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
    def list_all(self) -> list[Any]:
        return []


class _FakePricing:
    PRICING_TABLE: dict[str, list[Any]] = {}

    @staticmethod
    def pricing_age_days(models_used: list[str], when: Any = None) -> None:
        return None


# ---------------------------------------------------------------------------
# DB helpers
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
    agent_name: str,
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
    agent_name: str,
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
    dao = TelemetryDao(conn)
    return TelemetryAggregator(
        dao=dao,
        spec_context_service=_FakeSCS(),
        pricing_module=_FakePricing(),
    )


# ---------------------------------------------------------------------------
# Fixture: seeded DB with Claude + Codex rows across two projects
#
#  Claude sessions:
#    - claude-s1: project=alpha, 2 events (cost known)
#    - claude-s2: project=alpha, 1 event (cost known)
#    - claude-s3: project=beta,  1 event (cost known)
#  Codex sessions:
#    - codex-s1: project=alpha, 1 event (cost_micro_usd=NULL)
#    - codex-s2: project=beta,  0 events
# ---------------------------------------------------------------------------


def _seed_mixed(conn: sqlite3.Connection) -> None:
    _insert_agent(conn, "agent-a", "claude")
    _insert_agent(conn, "agent-b", "codex")

    _insert_session(
        conn,
        "claude-s1",
        "claude",
        "agent-a",
        sub_slug="alpha",
        first_event_at=_T1,
        last_event_at=_T3,
    )
    _insert_session(
        conn,
        "claude-s2",
        "claude",
        "agent-a",
        sub_slug="alpha",
        first_event_at=_T2,
        last_event_at=_T4,
    )
    _insert_session(
        conn,
        "claude-s3",
        "claude",
        "agent-a",
        sub_slug="beta",
        first_event_at=_T2,
        last_event_at=_T5,
    )
    _insert_session(
        conn,
        "codex-s1",
        "codex",
        "agent-b",
        sub_slug="alpha",
        first_event_at=_T1,
        last_event_at=_T2,
    )
    _insert_session(
        conn, "codex-s2", "codex", "agent-b", sub_slug="beta", first_event_at=_T3, last_event_at=_T4
    )

    _insert_event(
        conn,
        "ev-c1-1",
        "claude-s1",
        "agent-a",
        occurred_at=_T2,
        tokens_input=500,
        cost_micro_usd=3000,
    )
    _insert_event(
        conn,
        "ev-c1-2",
        "claude-s1",
        "agent-a",
        occurred_at=_T3,
        tokens_input=200,
        cost_micro_usd=1500,
    )
    _insert_event(
        conn,
        "ev-c2-1",
        "claude-s2",
        "agent-a",
        occurred_at=_T4,
        tokens_input=300,
        cost_micro_usd=2000,
    )
    _insert_event(
        conn,
        "ev-c3-1",
        "claude-s3",
        "agent-a",
        occurred_at=_T5,
        tokens_input=100,
        cost_micro_usd=800,
    )
    _insert_event(conn, "ev-x1-1", "codex-s1", "agent-b", occurred_at=_T2, cost_micro_usd=None)
    conn.commit()


# ---------------------------------------------------------------------------
# Tests — list_sessions basic
# ---------------------------------------------------------------------------


def test_list_sessions_no_filter_returns_claude_only() -> None:
    """list_sessions(runtime='claude') returns only claude sessions."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude")

    assert isinstance(result, SessionListResult)
    assert result.runtime == "claude"
    assert result.project is None
    assert all(s.runtime == "claude" for s in result.sessions)
    assert len(result.sessions) == 3
    assert result.total_count == 3


def test_list_sessions_returns_codex_only() -> None:
    """list_sessions(runtime='codex') returns only codex sessions."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("codex")

    assert result.runtime == "codex"
    assert all(s.runtime == "codex" for s in result.sessions)
    assert len(result.sessions) == 2
    assert result.total_count == 2


def test_list_sessions_runtime_discriminator_excludes_opposite() -> None:
    """Claude rows excluded when runtime='codex' and vice versa."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    claude_ids = {s.session_id for s in agg.list_sessions("claude").sessions}
    codex_ids = {s.session_id for s in agg.list_sessions("codex").sessions}

    assert claude_ids.isdisjoint(codex_ids)
    assert "claude-s1" in claude_ids
    assert "claude-s1" not in codex_ids
    assert "codex-s1" in codex_ids
    assert "codex-s1" not in claude_ids


# ---------------------------------------------------------------------------
# Tests — project filter
# ---------------------------------------------------------------------------


def test_list_sessions_project_filter_drops_non_matching() -> None:
    """project='alpha' returns only alpha sessions; beta sessions excluded."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude", project="alpha")

    assert result.project == "alpha"
    ids = [s.session_id for s in result.sessions]
    assert "claude-s1" in ids
    assert "claude-s2" in ids
    assert "claude-s3" not in ids


def test_list_sessions_project_filter_unknown_returns_empty() -> None:
    """project='unknown' yields empty list."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude", project="unknown")

    assert result.sessions == []
    assert result.total_count == 0


# ---------------------------------------------------------------------------
# Tests — limit
# ---------------------------------------------------------------------------


def test_list_sessions_limit_caps_result() -> None:
    """limit=2 returns at most 2 rows but total_count reflects full set."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude", limit=2)

    assert result.limit == 2
    assert len(result.sessions) == 2
    assert result.total_count == 3  # 3 claude sessions in total


def test_list_sessions_limit_none_returns_all() -> None:
    """No limit → all rows returned."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude", limit=None)

    assert result.limit is None
    assert len(result.sessions) == 3


def test_list_sessions_ordered_by_last_activity_desc() -> None:
    """Sessions returned in descending order of last_activity_at."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude")
    times = [s.last_activity_at for s in result.sessions]

    assert times == sorted(times, reverse=True)


# ---------------------------------------------------------------------------
# Tests — SessionRow field values
# ---------------------------------------------------------------------------


def test_list_sessions_row_fields_populated() -> None:
    """SessionRow has expected field values from the seeded DB."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude", project="alpha")
    # claude-s1 has 2 events; claude-s2 has 1 event.
    by_id = {s.session_id: s for s in result.sessions}

    s1 = by_id["claude-s1"]
    assert s1.runtime == "claude"
    assert s1.project == "alpha"
    assert s1.message_count == 2
    assert s1.cost_known is True
    assert s1.cumulative_cost_usd == pytest.approx((3000 + 1500) / 1_000_000)
    # context_size_tokens from most recent event (ev-c1-2): input=200, cache_create=0, cache_read=0
    assert s1.context_size_tokens == 200


def test_list_sessions_codex_cost_unknown() -> None:
    """Codex session with all-NULL cost has cost_known=False."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("codex")
    by_id = {s.session_id: s for s in result.sessions}

    x1 = by_id["codex-s1"]
    assert x1.cost_known is False
    assert x1.cumulative_cost_usd is None


def test_list_sessions_session_with_no_events() -> None:
    """Session with zero events has message_count=0, context_size_tokens=0."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.list_sessions("codex")
    by_id = {s.session_id: s for s in result.sessions}

    x2 = by_id["codex-s2"]
    assert x2.message_count == 0
    assert x2.context_size_tokens == 0
    assert x2.model is None


# ---------------------------------------------------------------------------
# Tests — get_session hit
# ---------------------------------------------------------------------------


def test_get_session_hit_returns_detail() -> None:
    """get_session returns SessionDetail for an existing session."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    detail = agg.get_session("claude", "claude-s1")

    assert detail is not None
    assert isinstance(detail, SessionDetail)
    assert detail.session_id == "claude-s1"
    assert detail.runtime == "claude"
    assert detail.message_count == 2
    assert len(detail.event_timestamps) == 2


def test_get_session_hit_event_timestamps_ordered_asc() -> None:
    """event_timestamps in SessionDetail are in ascending order."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    detail = agg.get_session("claude", "claude-s1")
    assert detail is not None
    ts = list(detail.event_timestamps)
    assert ts == sorted(ts)


def test_get_session_hit_context_size_from_last_event() -> None:
    """context_size_tokens = input+cache_create+cache_read of the most recent event."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    # claude-s1 events:
    #   ev-c1-1: occurred_at=_T2, tokens_input=500, cache_create=0, cache_read=0
    #   ev-c1-2: occurred_at=_T3, tokens_input=200, cache_create=0, cache_read=0
    # Most recent is ev-c1-2 → context_size = 200
    detail = agg.get_session("claude", "claude-s1")
    assert detail is not None
    assert detail.context_size_tokens == 200


def test_get_session_hit_cost_computed() -> None:
    """get_session computes cumulative_cost_usd correctly."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    detail = agg.get_session("claude", "claude-s1")
    assert detail is not None
    assert detail.cost_known is True
    assert detail.cumulative_cost_usd == pytest.approx((3000 + 1500) / 1_000_000)


# ---------------------------------------------------------------------------
# Tests — get_session miss
# ---------------------------------------------------------------------------


def test_get_session_miss_returns_none() -> None:
    """get_session returns None for an unknown session_id."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    result = agg.get_session("claude", "nonexistent-session-id")
    assert result is None


def test_get_session_wrong_runtime_returns_none() -> None:
    """get_session returns None when session exists but runtime doesn't match."""
    conn = _make_conn()
    _seed_mixed(conn)
    agg = _make_aggregator(conn)

    # claude-s1 is a Claude session; querying with runtime='codex' → None.
    result = agg.get_session("codex", "claude-s1")
    assert result is None


# ---------------------------------------------------------------------------
# Tests — empty DB edge cases
# ---------------------------------------------------------------------------


def test_list_sessions_empty_db_returns_empty_result() -> None:
    """list_sessions on empty DB returns empty SessionListResult."""
    conn = _make_conn()
    agg = _make_aggregator(conn)

    result = agg.list_sessions("claude")

    assert isinstance(result, SessionListResult)
    assert result.sessions == []
    assert result.total_count == 0


def test_get_session_empty_db_returns_none() -> None:
    """get_session on empty DB returns None."""
    conn = _make_conn()
    agg = _make_aggregator(conn)

    result = agg.get_session("claude", "anything")
    assert result is None
