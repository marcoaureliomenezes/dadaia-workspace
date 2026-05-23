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
    return conn.execute("PRAGMA user_version").fetchone()[0]


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


class TestSchemaMigrations:
    def test_apply_migrations_sets_correct_user_version(self, mem_conn: sqlite3.Connection) -> None:
        assert _user_version(mem_conn) == 0
        apply_migrations(mem_conn)
        assert _user_version(mem_conn) == SCHEMA_VERSION

    def test_apply_migrations_twice_is_stable(self, mem_conn: sqlite3.Connection) -> None:
        apply_migrations(mem_conn)
        apply_migrations(mem_conn)
        assert _user_version(mem_conn) == SCHEMA_VERSION

    def test_apply_migrations_twice_raises_no_error(self, mem_conn: sqlite3.Connection) -> None:
        # Must not raise any exception on re-apply.
        apply_migrations(mem_conn)
        apply_migrations(mem_conn)

    def test_all_expected_tables_created(self, mem_conn: sqlite3.Connection) -> None:
        apply_migrations(mem_conn)
        assert EXPECTED_TABLES.issubset(_tables(mem_conn))

    def test_all_expected_indices_created(self, mem_conn: sqlite3.Connection) -> None:
        apply_migrations(mem_conn)
        assert EXPECTED_INDICES.issubset(_indices(mem_conn))

    def test_schema_version_constant(self) -> None:
        assert SCHEMA_VERSION == 6

    def test_migration_6_drops_dead_tables(self, mem_conn: sqlite3.Connection) -> None:
        """Migration 6 removes workflows and workflow_agents (marked DEAD in migration 5)."""
        # Apply only migrations 1–5 so the dead tables exist beforehand.
        _apply_up_to_version(mem_conn, 5)
        tables_after_5 = _tables(mem_conn)
        assert "workflows" in tables_after_5, "workflows must exist after migration 5"
        assert "workflow_agents" in tables_after_5, "workflow_agents must exist after migration 5"

        # Now apply migration 6 incrementally via the public API.
        apply_migrations(mem_conn)
        assert _user_version(mem_conn) == 6

        # Dead tables must be gone.
        surviving = _tables(mem_conn)
        dead_surviving = DEAD_TABLES & surviving
        assert not dead_surviving, (
            f"Expected dead tables to be dropped by migration 6, "
            f"but still present: {dead_surviving}"
        )

    def test_migration_6_preserves_core_tables(self, mem_conn: sqlite3.Connection) -> None:
        """Migration 6 must not drop the four core tables."""
        apply_migrations(mem_conn)
        assert EXPECTED_TABLES.issubset(_tables(mem_conn)), "Core tables must survive migration 6"

    def test_migration_6_sqlite_master_query(self, mem_conn: sqlite3.Connection) -> None:
        """Verify via sqlite_master that dead tables are absent after full migration."""
        apply_migrations(mem_conn)
        rows = mem_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('workflows', 'workflow_agents')"
        ).fetchall()
        assert rows == [], f"sqlite_master still contains dead tables after migration 6: {rows}"
