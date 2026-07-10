"""Unit tests for features/telemetry/reader/codex.py (T-AM-07).

All fixtures are synthesized in-memory — NO real Codex data is read.
"""

from __future__ import annotations

import hashlib
import pathlib
import sqlite3

from dadaia_workspace.features.telemetry.reader.codex import ReadResult, read_codex_db
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

NOW_ISO = "2026-05-17T10:00:00Z"


def _make_dao() -> TelemetryDao:
    """Create a fresh in-memory SQLite DAO with migrations applied."""
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _make_codex_db(tmp_path: pathlib.Path, rows: list[dict[str, object]]) -> pathlib.Path:
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
    return int(row[0])


# ---------------------------------------------------------------------------
# Kept: locked-db graceful degrade
# ---------------------------------------------------------------------------


def test_locked_db_degrades(tmp_path: pathlib.Path) -> None:
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

    conn_lock.execute("BEGIN EXCLUSIVE")

    dao = _make_dao()
    result = read_codex_db(db_path, dao, NOW_ISO, _timeout=0.01)

    assert isinstance(result, ReadResult)
    assert result.events_ingested == 0
    assert _count_table(dao, "events") == 0

    conn_lock.rollback()
    conn_lock.close()


# ---------------------------------------------------------------------------
# Basic/partial-schema/event-id/missing — 1 test
# ---------------------------------------------------------------------------


def test_basic_partial_schema_event_id_and_missing_matrix(tmp_path: pathlib.Path) -> None:
    # Missing file: empty result, no exception.
    dao_missing = _make_dao()
    missing_path = tmp_path / "nonexistent_codex_state_5.sqlite"
    missing_result = read_codex_db(missing_path, dao_missing, NOW_ISO)
    assert isinstance(missing_result, ReadResult)
    assert missing_result.sessions_ingested == 0
    assert missing_result.events_ingested == 0
    assert missing_result.events_skipped == 0
    assert _count_table(dao_missing, "sessions") == 0
    assert _count_table(dao_missing, "events") == 0

    # Partial schema: threads(id, tokens_used) only, no model/started_at — parses defensively.
    partial_db = tmp_path / "partial.sqlite"
    partial_conn = sqlite3.connect(str(partial_db))
    partial_conn.execute(
        "CREATE TABLE threads (id TEXT PRIMARY KEY, tokens_used INTEGER NOT NULL DEFAULT 0)"
    )
    partial_conn.execute("INSERT INTO threads VALUES ('partial-thread-001', 500)")
    partial_conn.commit()
    partial_conn.close()
    dao_partial = _make_dao()
    partial_result = read_codex_db(partial_db, dao_partial, NOW_ISO)
    assert partial_result.events_ingested == 1
    assert _count_table(dao_partial, "sessions") == 1
    assert _count_table(dao_partial, "events") == 1
    row = dao_partial._conn.execute(  # noqa: SLF001
        "SELECT * FROM events WHERE session_id = 'partial-thread-001'"
    ).fetchone()
    assert row is not None
    assert row["cost_micro_usd"] is None
    assert row["tokens_input"] == 500
    assert row["tokens_output"] == 0

    # Basic ingest: 2 threads -> 2 sessions, 1 'codex (main)' agent, 2 events.
    rows = [
        {"id": "thread-aaa", "tokens_used": 1000, "model": "o3"},
        {"id": "thread-bbb", "tokens_used": 2500, "model": "gpt-4o"},
    ]
    basic_dir = tmp_path / "basic"
    basic_dir.mkdir()
    db_path = _make_codex_db(basic_dir, rows)
    dao_basic = _make_dao()
    basic_result = read_codex_db(db_path, dao_basic, NOW_ISO)
    assert basic_result.sessions_ingested == 2
    assert basic_result.events_ingested == 2
    assert _count_table(dao_basic, "sessions") == 2
    assert _count_table(dao_basic, "agents") == 1
    agents = dao_basic.list_agents()
    assert agents[0].name == "codex (main)"
    assert agents[0].provider == "codex"
    assert _count_table(dao_basic, "events") == 2
    for thread_id, tokens in [("thread-aaa", 1000), ("thread-bbb", 2500)]:
        event_row = dao_basic._conn.execute(  # noqa: SLF001
            "SELECT * FROM events WHERE session_id = ?", (thread_id,)
        ).fetchone()
        assert event_row is not None, f"Event for {thread_id} not found"
        assert event_row["cost_micro_usd"] is None
        assert event_row["tokens_input"] == tokens
        assert event_row["tokens_output"] == 0
        assert event_row["suspect"] == 0

    # event_id derivation: sha1(codex||thread_id)[:20].
    eventid_dir = tmp_path / "eventid"
    eventid_dir.mkdir()
    single_db = _make_codex_db(eventid_dir, [{"id": "thread-xyz", "tokens_used": 42}])
    dao_id = _make_dao()
    read_codex_db(single_db, dao_id, NOW_ISO)
    expected_event_id = hashlib.sha1(b"codex||thread-xyz").hexdigest()[:20]
    id_row = dao_id._conn.execute(  # noqa: SLF001
        "SELECT event_id FROM events WHERE session_id = 'thread-xyz'"
    ).fetchone()
    assert id_row["event_id"] == expected_event_id

    # Idempotent re-read (single representative, INSERT OR IGNORE contract).
    idem_dir = tmp_path / "idem"
    idem_dir.mkdir()
    idem_db = _make_codex_db(idem_dir, [{"id": "thread-idem-001", "tokens_used": 300}])
    dao_idem = _make_dao()
    idem_result1 = read_codex_db(idem_db, dao_idem, NOW_ISO)
    assert idem_result1.events_ingested == 1
    read_codex_db(idem_db, dao_idem, NOW_ISO)
    assert _count_table(dao_idem, "events") == 1
    assert _count_table(dao_idem, "sessions") == 1
