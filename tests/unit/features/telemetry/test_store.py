"""Unit tests for dadaia_workspace.features.telemetry.store::TelemetryStore.

Intent: CONTRACT — K8 (0.5.1), the store interface: open_write/open_read/
migrate/integrity_check/quarantine on a tmp sqlite, plus CRUD roundtrips.
Replaces tests/unit/features/telemetry/test_dao.py (TelemetryDao CRUD) and
test_schema.py (migrations) — merged onto the one interface both now live
behind. Also owns the concurrent-open_read-while-a-write-is-held repro for
the deferred bug panel-telemetry-sqlite-corrupts-under-concurrent-access
(now has an owner: this store never lets two callers share one connection).
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from dadaia_workspace.features.telemetry.store import (
    Agent,
    Event,
    ReaderState,
    Session,
    TelemetryStore,
)

pytestmark = pytest.mark.unit

# After migration 6 the dead tables are dropped; only these four survive.
EXPECTED_TABLES = {"reader_state", "sessions", "agents", "events"}
DEAD_TABLES = {"workflows", "workflow_agents"}


def _store(tmp_path: pathlib.Path, name: str = "telemetry.sqlite") -> TelemetryStore:
    return TelemetryStore(tmp_path / name)


# ---------------------------------------------------------------------------
# Connection lifecycle: open_write/open_read/migrate/close — 1 test
# ---------------------------------------------------------------------------


def test_open_write_migrate_open_read_and_close(tmp_path: pathlib.Path) -> None:
    store = _store(tmp_path)
    store.open_write()
    store.migrate()

    tables = {
        r[0]
        for r in store._conn.execute(  # noqa: SLF001 — test-only introspection
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert EXPECTED_TABLES.issubset(tables)
    assert not (DEAD_TABLES & tables)
    store.close()

    # open_read() gives a NEW, independent read-only connection every call —
    # never the same object, never the write connection.
    read_conn = store.open_read()
    try:
        assert read_conn is not store._conn  # noqa: SLF001
        row = read_conn.execute("SELECT COUNT(*) FROM agents").fetchone()
        assert row[0] == 0
        with pytest.raises(sqlite3.OperationalError):
            read_conn.execute("INSERT INTO agents VALUES ('x','claude',0,'a','a')")
    finally:
        read_conn.close()


def test_migration_idempotent_and_reaches_schema_version(tmp_path: pathlib.Path) -> None:
    from dadaia_workspace.features.telemetry.store import SCHEMA_VERSION

    store = _store(tmp_path)
    store.open_write()
    store.migrate()
    store.migrate()  # idempotent — re-applying raises nothing
    version = store._conn.execute("PRAGMA user_version").fetchone()[0]  # noqa: SLF001
    assert version == SCHEMA_VERSION == 6
    store.close()


# ---------------------------------------------------------------------------
# integrity_check + quarantine — 1 test
# ---------------------------------------------------------------------------


def test_integrity_check_and_quarantine(tmp_path: pathlib.Path) -> None:
    store = _store(tmp_path)
    # No file yet — an absent DB is not corrupt.
    assert store.integrity_check() is True

    store.open_write()
    store.migrate()
    store.close()
    assert store.integrity_check() is True

    # Corrupt the file directly (truncate to garbage bytes) and re-check.
    db_path = tmp_path / "telemetry.sqlite"
    db_path.write_bytes(b"not a sqlite file")
    assert store.integrity_check() is False

    quarantine_path = store.quarantine()
    assert quarantine_path is not None
    assert quarantine_path.name.startswith("telemetry.sqlite.corrupt.")
    assert quarantine_path.exists()
    assert not db_path.exists()


# ---------------------------------------------------------------------------
# Concurrent open_read() while a write is held — the deferred corruption
# bug's repro, now owned by this store (each caller gets its own connection).
# ---------------------------------------------------------------------------


def test_concurrent_open_read_while_write_is_held_does_not_corrupt(
    tmp_path: pathlib.Path,
) -> None:
    store = _store(tmp_path)
    store.open_write()
    store.migrate()
    store.upsert_agent(
        Agent(
            name="software-engineer",
            provider="claude",
            is_subagent=0,
            first_seen_at="2026-01-01T00:00:00Z",
            last_seen_at="2026-01-01T00:00:00Z",
        )
    )
    # DO NOT close the write connection — simulate a live writer.

    # Several concurrent readers, each its OWN connection (never shared).
    readers = [store.open_read() for _ in range(4)]
    try:
        for reader in readers:
            row = reader.execute("SELECT COUNT(*) FROM agents").fetchone()
            assert row[0] == 1
    finally:
        for reader in readers:
            reader.close()

    store.close()
    assert store.integrity_check() is True


# ---------------------------------------------------------------------------
# CRUD roundtrips (from_connection — direct in-memory construction) — 2 tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mem_store() -> TelemetryStore:
    conn = sqlite3.connect(":memory:")
    store = TelemetryStore.from_connection(conn)
    from dadaia_workspace.features.telemetry.store import apply_migrations

    apply_migrations(conn)
    return store


def test_reader_state_agent_session_roundtrip_and_update(mem_store: TelemetryStore) -> None:
    assert mem_store.get_reader_state("/nonexistent/path.jsonl") is None

    state = ReaderState(
        file_path="/" + "home/op/.claude/projects/x/session.jsonl",
        kind="claude_jsonl",
        byte_offset=1024,
        last_mtime=1716000000.0,
        last_inode=42,
        error_count=0,
        last_ingest_at="2026-05-17T06:00:00Z",
    )
    mem_store.upsert_reader_state(state)
    assert mem_store.get_reader_state(state.file_path) == state

    updated = ReaderState(
        file_path=state.file_path,
        kind="claude_jsonl",
        byte_offset=4096,
        last_mtime=1716001000.0,
        last_inode=43,
        error_count=1,
        last_ingest_at="2026-05-17T07:00:00Z",
    )
    mem_store.upsert_reader_state(updated)
    assert mem_store.get_reader_state(state.file_path) == updated

    agent = Agent(
        name="software-architect",
        provider="claude",
        is_subagent=1,
        first_seen_at="2026-05-01T00:00:00Z",
        last_seen_at="2026-05-17T00:00:00Z",
    )
    mem_store.upsert_agent(agent)
    agents = mem_store.list_agents()
    assert len(agents) == 1
    assert agents[0] == agent

    session = Session(
        session_id="sess-001",
        provider="claude",
        agent_name="software-architect",
        ai_title="Claude",
        entrypoint="cli",
        cwd="/" + "home/op/workspace",
        git_branch="main",
        is_sidechain=0,
        sub_slug=None,
        first_event_at="2026-05-10T00:00:00Z",
        last_event_at="2026-05-10T01:00:00Z",
        status="closed",
    )
    mem_store.upsert_session(session)
    sessions = mem_store.list_sessions_by_agent("software-architect")
    assert len(sessions) == 1
    assert sessions[0] == session
    assert mem_store.list_sessions_by_agent("nonexistent-agent") == []


def test_event_roundtrip_dup_noop_null_cost_and_backfill_iteration(
    mem_store: TelemetryStore,
) -> None:
    mem_store.upsert_agent(
        Agent(
            name="product-engineer",
            provider="claude",
            is_subagent=0,
            first_seen_at="2026-05-01T00:00:00Z",
            last_seen_at="2026-05-17T00:00:00Z",
        )
    )
    mem_store.upsert_session(
        Session(
            session_id="sess-evt-001",
            provider="claude",
            agent_name="product-engineer",
            ai_title="Claude",
            entrypoint="cli",
            cwd="/" + "home/op",
            git_branch="main",
            is_sidechain=0,
            sub_slug=None,
            first_event_at="2026-05-17T00:00:00Z",
            last_event_at="2026-05-17T01:00:00Z",
            status="closed",
        )
    )

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
    mem_store.insert_event(event)
    row = mem_store._conn.execute(  # noqa: SLF001
        "SELECT * FROM events WHERE event_id = ?", ("evt-abc123",)
    ).fetchone()
    assert row is not None
    assert row["tokens_input"] == 1000
    assert row["cost_micro_usd"] == 42

    # Duplicate insert is a no-op (same event_id, same content).
    mem_store.insert_event(event)
    count = mem_store._conn.execute(  # noqa: SLF001
        "SELECT COUNT(*) FROM events WHERE event_id = ?", ("evt-abc123",)
    ).fetchone()[0]
    assert count == 1

    # Null cost/pricing-version persists as NULL, not coerced, and shows up
    # in iter_events_missing_cost() for the service's backfill loop.
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
    mem_store.insert_event(null_cost_event)
    missing = mem_store.iter_events_missing_cost()
    assert [r.event_id for r in missing] == ["evt-null-cost"]

    mem_store.update_event_cost("evt-null-cost", 99, "2025-01-01")
    mem_store.commit()
    assert mem_store.iter_events_missing_cost() == []
    backfilled = mem_store._conn.execute(  # noqa: SLF001
        "SELECT cost_micro_usd, pricing_version FROM events WHERE event_id = ?",
        ("evt-null-cost",),
    ).fetchone()
    assert backfilled["cost_micro_usd"] == 99
    assert backfilled["pricing_version"] == "2025-01-01"
