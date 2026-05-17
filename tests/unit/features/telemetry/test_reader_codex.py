"""Unit tests for features/telemetry/reader/codex.py (T-AM-07).

All fixtures are synthesized in-memory — NO real Codex data is read.
"""
from __future__ import annotations

import pathlib
import sqlite3
import threading
import time

import pytest

from dadaia_workspace.features.telemetry.reader.codex import ReadResult, read_codex_db
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

NOW_ISO = "2026-05-17T10:00:00Z"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dao() -> TelemetryDao:
    """Create a fresh in-memory SQLite DAO with migrations applied."""
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _make_codex_db(tmp_path: pathlib.Path, rows: list[dict]) -> pathlib.Path:
    """Create a minimal Codex-style SQLite DB with a threads table."""
    db_path = tmp_path / "state_5.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            cwd TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            model TEXT,
            model_provider TEXT NOT NULL DEFAULT 'openai',
            git_branch TEXT
        )
        """
    )
    for row in rows:
        conn.execute(
            "INSERT INTO threads (id, tokens_used, created_at, updated_at, cwd, title, model, model_provider, git_branch) "
            "VALUES (:id, :tokens_used, :created_at, :updated_at, :cwd, :title, :model, :model_provider, :git_branch)",
            {
                "id": row.get("id", "thread-001"),
                "tokens_used": row.get("tokens_used", 0),
                "created_at": row.get("created_at", 1716000000),
                "updated_at": row.get("updated_at", 1716003600),
                "cwd": row.get("cwd", "/home/op/workspace"),
                "title": row.get("title", "Test thread"),
                "model": row.get("model", "o3"),
                "model_provider": row.get("model_provider", "openai"),
                "git_branch": row.get("git_branch"),
            },
        )
    conn.commit()
    conn.close()
    return db_path


def _count_table(dao: TelemetryDao, table: str) -> int:
    row = dao._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: SLF001
    return row[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMissingFile:
    def test_missing_file_returns_empty(self) -> None:
        """Non-existent path → ReadResult with 0 ingests, no exception."""
        dao = _make_dao()
        path = pathlib.Path("/tmp/nonexistent_codex_state_5.sqlite")
        result = read_codex_db(path, dao, NOW_ISO)

        assert isinstance(result, ReadResult)
        assert result.sessions_ingested == 0
        assert result.events_ingested == 0
        assert result.events_skipped == 0
        assert _count_table(dao, "sessions") == 0
        assert _count_table(dao, "events") == 0


class TestPartialSchema:
    def test_partial_schema_threads_only(self, tmp_path: pathlib.Path) -> None:
        """DB with threads(id, tokens_used) only — no model, no started_at.

        Reader must parse defensively and not crash.
        """
        db_path = tmp_path / "partial.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE threads (id TEXT PRIMARY KEY, tokens_used INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute("INSERT INTO threads VALUES ('partial-thread-001', 500)")
        conn.commit()
        conn.close()

        dao = _make_dao()
        result = read_codex_db(db_path, dao, NOW_ISO)

        assert result.events_ingested == 1
        assert _count_table(dao, "sessions") == 1
        assert _count_table(dao, "events") == 1

        # No crash — that's the main assertion; also verify NULL-safe fields
        row = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM events WHERE session_id = 'partial-thread-001'"
        ).fetchone()
        assert row is not None
        assert row["cost_micro_usd"] is None
        assert row["tokens_input"] == 500
        assert row["tokens_output"] == 0


class TestLockedDb:
    def test_locked_db_degrades(self, tmp_path: pathlib.Path) -> None:
        """Reader must degrade gracefully when the DB is locked.

        We open the DB in exclusive mode in a background thread and call the
        reader with a very short timeout so it hits OperationalError.
        """
        db_path = tmp_path / "locked.sqlite"
        conn_lock = sqlite3.connect(str(db_path))
        conn_lock.execute(
            "CREATE TABLE threads (id TEXT PRIMARY KEY, tokens_used INTEGER NOT NULL DEFAULT 0)"
        )
        conn_lock.execute("INSERT INTO threads VALUES ('locked-thread', 100)")
        conn_lock.commit()

        # Begin an exclusive transaction that holds the lock
        conn_lock.execute("BEGIN EXCLUSIVE")

        dao = _make_dao()
        # Use timeout=0.01 to force immediate failure on any DB lock
        result = read_codex_db(db_path, dao, NOW_ISO, _timeout=0.01)

        # Must degrade: returns empty result, no crash
        assert isinstance(result, ReadResult)
        assert result.events_ingested == 0
        assert _count_table(dao, "events") == 0

        conn_lock.rollback()
        conn_lock.close()


class TestBasicIngest:
    def test_basic_ingest(self, tmp_path: pathlib.Path) -> None:
        """2 threads → 2 sessions, 1 'codex (main)' agent, 2 events."""
        rows = [
            {"id": "thread-aaa", "tokens_used": 1000, "model": "o3"},
            {"id": "thread-bbb", "tokens_used": 2500, "model": "gpt-4o"},
        ]
        db_path = _make_codex_db(tmp_path, rows)
        dao = _make_dao()

        result = read_codex_db(db_path, dao, NOW_ISO)

        assert result.sessions_ingested == 2
        assert result.events_ingested == 2

        assert _count_table(dao, "sessions") == 2
        # Only one distinct agent: "codex (main)"
        assert _count_table(dao, "agents") == 1
        agents = dao.list_agents()
        assert agents[0].name == "codex (main)"
        assert agents[0].provider == "codex"

        assert _count_table(dao, "events") == 2

        # Verify per-event properties
        for thread_id, tokens in [("thread-aaa", 1000), ("thread-bbb", 2500)]:
            row = dao._conn.execute(  # noqa: SLF001
                "SELECT * FROM events WHERE session_id = ?", (thread_id,)
            ).fetchone()
            assert row is not None, f"Event for {thread_id} not found"
            assert row["cost_micro_usd"] is None
            assert row["tokens_input"] == tokens
            assert row["tokens_output"] == 0
            assert row["suspect"] == 0

    def test_event_id_derived_from_thread_id(self, tmp_path: pathlib.Path) -> None:
        """event_id is sha1(codex||thread_id)[:20]."""
        import hashlib

        db_path = _make_codex_db(tmp_path, [{"id": "thread-xyz", "tokens_used": 42}])
        dao = _make_dao()
        read_codex_db(db_path, dao, NOW_ISO)

        expected_event_id = hashlib.sha1(b"codex||thread-xyz").hexdigest()[:20]
        row = dao._conn.execute(  # noqa: SLF001
            "SELECT event_id FROM events WHERE session_id = 'thread-xyz'"
        ).fetchone()
        assert row["event_id"] == expected_event_id


class TestIdempotentReread:
    def test_idempotent_reread(self, tmp_path: pathlib.Path) -> None:
        """Running twice ingests same threads only once (event_id PK + INSERT OR IGNORE)."""
        rows = [{"id": "thread-idem-001", "tokens_used": 300}]
        db_path = _make_codex_db(tmp_path, rows)
        dao = _make_dao()

        result1 = read_codex_db(db_path, dao, NOW_ISO)
        assert result1.events_ingested == 1

        result2 = read_codex_db(db_path, dao, NOW_ISO)
        # Second run returns non-zero sessions_ingested (upsert), but events
        # are idempotent via INSERT OR IGNORE.
        assert _count_table(dao, "events") == 1
        assert _count_table(dao, "sessions") == 1
