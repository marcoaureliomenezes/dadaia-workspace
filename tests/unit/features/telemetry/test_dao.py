"""Unit tests for dadaia_workspace.features.telemetry.store.dao."""

from __future__ import annotations

import sqlite3

import pytest

from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.models import (
    Agent,
    Event,
    ReaderState,
    Session,
)
from dadaia_workspace.features.telemetry.store.schema import apply_migrations


@pytest.fixture
def dao() -> TelemetryDao:
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


# ---------------------------------------------------------------------------
# ReaderState + Agent + Session — roundtrip / update — 1 test
# ---------------------------------------------------------------------------


def test_reader_state_agent_session_roundtrip_and_update(dao: TelemetryDao) -> None:
    # ReaderState: missing -> None; upsert -> roundtrip; second upsert -> updates.
    assert dao.get_reader_state("/nonexistent/path.jsonl") is None

    state = ReaderState(
        file_path="/home/op/.claude/projects/x/session.jsonl",
        kind="claude_jsonl",
        byte_offset=1024,
        last_mtime=1716000000.0,
        last_inode=42,
        error_count=0,
        last_ingest_at="2026-05-17T06:00:00Z",
    )
    dao.upsert_reader_state(state)
    assert dao.get_reader_state(state.file_path) == state

    updated = ReaderState(
        file_path=state.file_path,
        kind="claude_jsonl",
        byte_offset=4096,
        last_mtime=1716001000.0,
        last_inode=43,
        error_count=1,
        last_ingest_at="2026-05-17T07:00:00Z",
    )
    dao.upsert_reader_state(updated)
    assert dao.get_reader_state(state.file_path) == updated

    # Agent: upsert + list roundtrip.
    agent = Agent(
        name="software-architect",
        provider="claude",
        is_subagent=1,
        first_seen_at="2026-05-01T00:00:00Z",
        last_seen_at="2026-05-17T00:00:00Z",
    )
    dao.upsert_agent(agent)
    agents = dao.list_agents()
    assert len(agents) == 1
    assert agents[0] == agent

    # Session: upsert + list-by-agent roundtrip, empty for unknown agent.
    session = Session(
        session_id="sess-001",
        provider="claude",
        agent_name="software-architect",
        ai_title="Claude",
        entrypoint="cli",
        cwd="/home/op/workspace",
        git_branch="main",
        is_sidechain=0,
        sub_slug=None,
        first_event_at="2026-05-10T00:00:00Z",
        last_event_at="2026-05-10T01:00:00Z",
        status="closed",
    )
    dao.upsert_session(session)
    sessions = dao.list_sessions_by_agent("software-architect")
    assert len(sessions) == 1
    assert sessions[0] == session
    assert dao.list_sessions_by_agent("nonexistent-agent") == []


# ---------------------------------------------------------------------------
# Event: roundtrip / dup-noop / null-cost — 1 test
# ---------------------------------------------------------------------------


def test_event_roundtrip_dup_noop_and_null_cost(dao: TelemetryDao) -> None:
    agent = Agent(
        name="product-engineer",
        provider="claude",
        is_subagent=0,
        first_seen_at="2026-05-01T00:00:00Z",
        last_seen_at="2026-05-17T00:00:00Z",
    )
    session = Session(
        session_id="sess-evt-001",
        provider="claude",
        agent_name="product-engineer",
        ai_title="Claude",
        entrypoint="cli",
        cwd="/home/op",
        git_branch="main",
        is_sidechain=0,
        sub_slug=None,
        first_event_at="2026-05-17T00:00:00Z",
        last_event_at="2026-05-17T01:00:00Z",
        status="closed",
    )
    dao.upsert_agent(agent)
    dao.upsert_session(session)

    event = Event(
        event_id="evt-abc123",
        session_id="sess-evt-001",
        agent_name="product-engineer",
        model="claude-sonnet-4-6",
        occurred_at="2026-05-17T00:30:00Z",
        tokens_input=1000,
        tokens_cache_read=500,
        tokens_cache_create=200,
        tokens_output=300,
        cost_micro_usd=42,
        pricing_version="2025-01-01",
        suspect=0,
    )
    dao.insert_event(event)
    conn = dao._conn  # noqa: SLF001
    row = conn.execute("SELECT * FROM events WHERE event_id = ?", ("evt-abc123",)).fetchone()
    assert row is not None
    assert row["tokens_input"] == 1000
    assert row["cost_micro_usd"] == 42

    # Duplicate insert is a no-op (same event_id, same content).
    dao.insert_event(event)
    count = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_id = ?", ("evt-abc123",)
    ).fetchone()[0]
    assert count == 1

    # Null cost/pricing-version persists as NULL, not coerced.
    null_cost_event = Event(
        event_id="evt-null-cost",
        session_id="sess-evt-001",
        agent_name="product-engineer",
        model="unknown-model",
        occurred_at="2026-05-17T00:45:00Z",
        tokens_input=100,
        tokens_cache_read=0,
        tokens_cache_create=0,
        tokens_output=50,
        cost_micro_usd=None,
        pricing_version=None,
        suspect=0,
    )
    dao.insert_event(null_cost_event)
    null_row = conn.execute(
        "SELECT cost_micro_usd FROM events WHERE event_id = ?", ("evt-null-cost",)
    ).fetchone()
    assert null_row["cost_micro_usd"] is None
