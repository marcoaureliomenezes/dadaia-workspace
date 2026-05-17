"""Unit tests for dadaia_workspace.features.telemetry.store.schema."""
from __future__ import annotations

import sqlite3

import pytest

from dadaia_workspace.features.telemetry.store.schema import (
    SCHEMA_VERSION,
    apply_migrations,
)

EXPECTED_TABLES = {
    "reader_state",
    "sessions",
    "agents",
    "events",
    "workflows",
    "workflow_agents",
}

EXPECTED_INDICES = {
    "idx_sessions_agent",
    "idx_sessions_provider_first",
    "idx_sessions_cwd",
    "idx_events_session",
    "idx_events_agent_time",
    "idx_events_occurred",
}


@pytest.fixture
def mem_conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def _indices(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()
    return {r[0] for r in rows}


class TestSchemaMigrations:
    def test_apply_migrations_sets_correct_user_version(
        self, mem_conn: sqlite3.Connection
    ) -> None:
        assert _user_version(mem_conn) == 0
        apply_migrations(mem_conn)
        assert _user_version(mem_conn) == SCHEMA_VERSION

    def test_apply_migrations_twice_is_stable(
        self, mem_conn: sqlite3.Connection
    ) -> None:
        apply_migrations(mem_conn)
        apply_migrations(mem_conn)
        assert _user_version(mem_conn) == SCHEMA_VERSION

    def test_apply_migrations_twice_raises_no_error(
        self, mem_conn: sqlite3.Connection
    ) -> None:
        # Must not raise any exception on re-apply.
        apply_migrations(mem_conn)
        apply_migrations(mem_conn)

    def test_all_expected_tables_created(
        self, mem_conn: sqlite3.Connection
    ) -> None:
        apply_migrations(mem_conn)
        assert EXPECTED_TABLES.issubset(_tables(mem_conn))

    def test_all_expected_indices_created(
        self, mem_conn: sqlite3.Connection
    ) -> None:
        apply_migrations(mem_conn)
        assert EXPECTED_INDICES.issubset(_indices(mem_conn))

    def test_schema_version_constant(self) -> None:
        assert SCHEMA_VERSION == 5
