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
# ReaderState
# ---------------------------------------------------------------------------


class TestReaderState:
    def test_get_reader_state_missing_returns_none(self, dao: TelemetryDao) -> None:
        result = dao.get_reader_state("/nonexistent/path.jsonl")
        assert result is None

    def test_upsert_and_get_reader_state_round_trip(self, dao: TelemetryDao) -> None:
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
        fetched = dao.get_reader_state(state.file_path)
        assert fetched == state

    def test_upsert_reader_state_updates_existing(self, dao: TelemetryDao) -> None:
        state = ReaderState(
            file_path="/home/op/.claude/projects/x/session.jsonl",
            kind="claude_jsonl",
            byte_offset=0,
            last_mtime=0.0,
            last_inode=0,
            error_count=0,
            last_ingest_at="2026-05-17T05:00:00Z",
        )
        dao.upsert_reader_state(state)
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
        fetched = dao.get_reader_state(state.file_path)
        assert fetched == updated


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class TestAgent:
    def test_upsert_and_list_agents(self, dao: TelemetryDao) -> None:
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

    def test_list_agents_returns_dataclass_not_row(self, dao: TelemetryDao) -> None:
        dao.upsert_agent(
            Agent(
                name="qa-engineer",
                provider="claude",
                is_subagent=1,
                first_seen_at="2026-05-10T00:00:00Z",
                last_seen_at="2026-05-10T00:00:00Z",
            )
        )
        agents = dao.list_agents()
        assert isinstance(agents[0], Agent)
        # Must not be sqlite3.Row
        assert not isinstance(agents[0], sqlite3.Row)

    def test_list_agents_ordered_by_name(self, dao: TelemetryDao) -> None:
        for name in ("zebra-agent", "alpha-agent", "middle-agent"):
            dao.upsert_agent(
                Agent(
                    name=name,
                    provider="claude",
                    is_subagent=0,
                    first_seen_at="2026-05-01T00:00:00Z",
                    last_seen_at="2026-05-01T00:00:00Z",
                )
            )
        agents = dao.list_agents()
        names = [a.name for a in agents]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class TestSession:
    _AGENT = Agent(
        name="software-engineer",
        provider="claude",
        is_subagent=0,
        first_seen_at="2026-05-01T00:00:00Z",
        last_seen_at="2026-05-17T00:00:00Z",
    )

    def _make_session(self, session_id: str, first: str, last: str) -> Session:
        return Session(
            session_id=session_id,
            provider="claude",
            agent_name="software-engineer",
            ai_title="Claude",
            entrypoint="cli",
            cwd="/home/op/workspace",
            git_branch="main",
            is_sidechain=0,
            sub_slug=None,
            first_event_at=first,
            last_event_at=last,
            status="closed",
        )

    @pytest.fixture(autouse=True)
    def insert_agent(self, dao: TelemetryDao) -> None:
        dao.upsert_agent(self._AGENT)

    def test_upsert_and_list_sessions_by_agent(self, dao: TelemetryDao) -> None:
        session = self._make_session("sess-001", "2026-05-10T00:00:00Z", "2026-05-10T01:00:00Z")
        dao.upsert_session(session)
        sessions = dao.list_sessions_by_agent("software-engineer")
        assert len(sessions) == 1
        assert sessions[0] == session

    def test_list_sessions_by_agent_returns_dataclasses(self, dao: TelemetryDao) -> None:
        dao.upsert_session(
            self._make_session("sess-002", "2026-05-11T00:00:00Z", "2026-05-11T01:00:00Z")
        )
        sessions = dao.list_sessions_by_agent("software-engineer")
        assert isinstance(sessions[0], Session)

    def test_list_sessions_by_agent_ordered_by_first_event(self, dao: TelemetryDao) -> None:
        for sid, first in [
            ("sess-z", "2026-05-15T00:00:00Z"),
            ("sess-a", "2026-05-12T00:00:00Z"),
            ("sess-m", "2026-05-13T00:00:00Z"),
        ]:
            dao.upsert_session(self._make_session(sid, first, first))
        sessions = dao.list_sessions_by_agent("software-engineer")
        first_events = [s.first_event_at for s in sessions]
        assert first_events == sorted(first_events)

    def test_list_sessions_by_agent_empty_for_unknown_agent(self, dao: TelemetryDao) -> None:
        result = dao.list_sessions_by_agent("nonexistent-agent")
        assert result == []


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class TestEvent:
    _AGENT = Agent(
        name="product-engineer",
        provider="claude",
        is_subagent=0,
        first_seen_at="2026-05-01T00:00:00Z",
        last_seen_at="2026-05-17T00:00:00Z",
    )
    _SESSION = Session(
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

    @pytest.fixture(autouse=True)
    def insert_prereqs(self, dao: TelemetryDao) -> None:
        dao.upsert_agent(self._AGENT)
        dao.upsert_session(self._SESSION)

    def _make_event(self, event_id: str) -> Event:
        return Event(
            event_id=event_id,
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

    def test_insert_event_round_trip(self, dao: TelemetryDao) -> None:
        event = self._make_event("evt-abc123")
        dao.insert_event(event)
        # Verify via direct query since there is no read-single method in scope.
        conn = dao._conn
        row = conn.execute("SELECT * FROM events WHERE event_id = ?", ("evt-abc123",)).fetchone()
        assert row is not None
        assert row["tokens_input"] == 1000
        assert row["cost_micro_usd"] == 42

    def test_insert_event_duplicate_is_no_op(self, dao: TelemetryDao) -> None:
        event = self._make_event("evt-dup-001")
        dao.insert_event(event)
        # Second insert must not raise and must not change the row.
        dao.insert_event(event)
        conn = dao._conn
        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_id = ?", ("evt-dup-001",)
        ).fetchone()[0]
        assert count == 1

    def test_insert_event_null_cost(self, dao: TelemetryDao) -> None:
        event = Event(
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
        dao.insert_event(event)
        conn = dao._conn
        row = conn.execute(
            "SELECT cost_micro_usd FROM events WHERE event_id = ?",
            ("evt-null-cost",),
        ).fetchone()
        assert row["cost_micro_usd"] is None


# ---------------------------------------------------------------------------
# Migration 6 — dead table drop (T-12)
# ---------------------------------------------------------------------------


class TestMigration6:
    def test_workflows_table_absent_after_migrations(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        apply_migrations(conn)
        tables = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "workflows" not in tables
        assert "workflow_agents" not in tables
