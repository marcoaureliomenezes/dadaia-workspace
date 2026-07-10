"""Unit tests for dadaia_workspace.features.telemetry.store.schema."""

from __future__ import annotations

import sqlite3

import pytest

from dadaia_workspace.features.telemetry.store.schema import (
    _MIGRATIONS,
    SCHEMA_VERSION,
    apply_migrations,
)

# After migration 6 the dead tables are dropped; only these four survive.
EXPECTED_TABLES = {
    "reader_state",
    "sessions",
    "agents",
    "events",
}

EXPECTED_INDICES = {
    "idx_sessions_agent",
    "idx_sessions_provider_first",
    "idx_sessions_cwd",
    "idx_events_session",
    "idx_events_agent_time",
    "idx_events_occurred",
}

# Tables that must NOT be present after migration 6.
DEAD_TABLES = {"workflows", "workflow_agents"}


@pytest.fixture
def mem_conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def _indices(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {r[0] for r in rows}


def _apply_up_to_version(conn: sqlite3.Connection, target: int) -> None:
    """Apply only the first *target* migrations, leaving user_version = target."""
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    for idx, sql_block in enumerate(_MIGRATIONS[:target]):
        version = idx + 1
        if current >= version:
            continue
        conn.executescript(sql_block)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
        current = version


def test_migration_idempotence_and_version(mem_conn: sqlite3.Connection) -> None:
    assert _user_version(mem_conn) == 0
    apply_migrations(mem_conn)
    assert _user_version(mem_conn) == SCHEMA_VERSION == 6

    # Re-applying is stable and raises nothing.
    apply_migrations(mem_conn)
    assert _user_version(mem_conn) == SCHEMA_VERSION


def test_tables_indices_and_migration6_drops_dead_tables(mem_conn: sqlite3.Connection) -> None:
    apply_migrations(mem_conn)
    assert EXPECTED_TABLES.issubset(_tables(mem_conn))
    assert EXPECTED_INDICES.issubset(_indices(mem_conn))

    # Migration 6 drops the dead tables (workflows/workflow_agents) while preserving
    # the four core tables — verified both via applying only through migration 5
    # (dead tables exist) and via a direct sqlite_master query after full migration.
    fresh_conn = sqlite3.connect(":memory:")
    _apply_up_to_version(fresh_conn, 5)
    tables_after_5 = _tables(fresh_conn)
    assert "workflows" in tables_after_5
    assert "workflow_agents" in tables_after_5

    apply_migrations(fresh_conn)
    assert _user_version(fresh_conn) == 6
    surviving = _tables(fresh_conn)
    assert not (DEAD_TABLES & surviving), f"dead tables still present: {DEAD_TABLES & surviving}"
    assert EXPECTED_TABLES.issubset(surviving), "Core tables must survive migration 6"

    rows = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('workflows', 'workflow_agents')"
    ).fetchall()
    assert rows == []
