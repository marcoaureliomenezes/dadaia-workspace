"""Unit tests for features/telemetry/reader/kimi.py (T-50-14, FR3.4).

The reader had no test file before this task. All fixtures are synthesized
in-memory / on tmp_path — NO real Kimi Code session data is read.

Privacy invariant T1 (see the module docstring): only sessionId/workDir and the
session directory's mtime are read; the per-session directory CONTENT is never
opened. This file additionally proves the FR3.4 hardening: ``sessionDir`` is
lexically contained against ``index_path.parent`` BEFORE ``Path(...).stat()`` is
ever called — an escaping value must never reach the filesystem call at all.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sqlite3

import pytest

from dadaia_workspace.features.telemetry.reader.kimi import ReadResult, read_kimi_sessions
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

NOW_ISO = "2026-05-17T10:00:00Z"


def _make_dao() -> TelemetryDao:
    """Create a fresh in-memory SQLite DAO with migrations applied."""
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _count_table(dao: TelemetryDao, table: str) -> int:
    row = dao._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: SLF001
    return int(row[0])


def _get_session(dao: TelemetryDao, session_id: str) -> sqlite3.Row | None:
    row = dao._conn.execute(  # noqa: SLF001
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    return row  # type: ignore[no-any-return]


def _write_index(index_path: pathlib.Path, lines: list[str]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")


# ---------------------------------------------------------------------------
# Missing index — graceful, no exception.
# ---------------------------------------------------------------------------


def test_missing_index_degrades_to_empty_result(tmp_path: pathlib.Path) -> None:
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"

    result = read_kimi_sessions(index_path, dao, NOW_ISO)

    assert isinstance(result, ReadResult)
    assert result.sessions_ingested == 0
    assert result.events_ingested == 0
    assert result.events_skipped == 0
    assert _count_table(dao, "sessions") == 0
    assert _count_table(dao, "events") == 0


def test_index_unreadable_degrades_to_empty_result(tmp_path: pathlib.Path) -> None:
    """A directory in place of the index file makes ``read_text`` raise OSError."""
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"
    index_path.mkdir()  # a directory, not a file — read_text() raises IsADirectoryError

    result = read_kimi_sessions(index_path, dao, NOW_ISO)

    assert isinstance(result, ReadResult)
    assert result.sessions_ingested == 0
    assert result.events_ingested == 0


# ---------------------------------------------------------------------------
# Malformed-line skip paths.
# ---------------------------------------------------------------------------


def test_malformed_lines_are_skipped_valid_lines_still_ingest(tmp_path: pathlib.Path) -> None:
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"
    session_dir = tmp_path / "sessions" / "kimi-session-good"
    session_dir.mkdir(parents=True)

    lines = [
        "not json at all {{{",
        "   ",  # blank after strip — skipped silently, not counted
        json.dumps(["not", "a", "dict"]),
        json.dumps({"sessionDir": str(session_dir)}),  # missing sessionId
        json.dumps({"sessionId": "", "sessionDir": str(session_dir)}),  # empty sessionId
        json.dumps({"sessionId": 42, "sessionDir": str(session_dir)}),  # non-string sessionId
        json.dumps(
            {
                "sessionId": "kimi-session-good",
                "sessionDir": str(session_dir),
                "workDir": "/home/operator/workspace",
            }
        ),
    ]
    _write_index(index_path, lines)

    result = read_kimi_sessions(index_path, dao, NOW_ISO)

    assert result.sessions_ingested == 1
    assert result.events_ingested == 1
    # 5 bad lines: malformed JSON, non-dict, no sessionId, empty sessionId, int sessionId.
    assert result.events_skipped == 5
    assert _count_table(dao, "sessions") == 1

    row = _get_session(dao, "kimi-session-good")
    assert row is not None
    assert row["cwd"] == "/home/operator/workspace"


# ---------------------------------------------------------------------------
# Happy path: basic ingest, event_id derivation, idempotent re-read.
# ---------------------------------------------------------------------------


def test_basic_ingest_event_id_and_idempotent_reread(tmp_path: pathlib.Path) -> None:
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"
    session_dir = tmp_path / "sessions" / "session_aaa"
    session_dir.mkdir(parents=True)

    _write_index(
        index_path,
        [
            json.dumps(
                {
                    "sessionId": "session_aaa",
                    "sessionDir": str(session_dir),
                    "workDir": "/home/operator/repo",
                }
            )
        ],
    )

    result = read_kimi_sessions(index_path, dao, NOW_ISO)
    assert result.sessions_ingested == 1
    assert result.events_ingested == 1
    assert _count_table(dao, "sessions") == 1
    assert _count_table(dao, "agents") == 1
    assert _count_table(dao, "events") == 1

    agents = dao.list_agents()
    assert agents[0].name == "kimi (main)"
    assert agents[0].provider == "kimi-code"

    event_row = dao._conn.execute(  # noqa: SLF001
        "SELECT * FROM events WHERE session_id = 'session_aaa'"
    ).fetchone()
    assert event_row is not None
    assert event_row["cost_micro_usd"] is None
    assert event_row["tokens_input"] == 0
    assert event_row["tokens_output"] == 0

    expected_event_id = hashlib.sha1(b"kimi||session_aaa").hexdigest()[:20]
    assert event_row["event_id"] == expected_event_id

    # Idempotent re-read: INSERT OR IGNORE contract, no duplicate rows.
    read_kimi_sessions(index_path, dao, NOW_ISO)
    assert _count_table(dao, "events") == 1
    assert _count_table(dao, "sessions") == 1


def test_session_dir_mtime_used_as_liveness_signal(tmp_path: pathlib.Path) -> None:
    """A contained, existing ``sessionDir`` yields ``last_event_at`` derived from
    its mtime, not the fallback ``now_iso``."""
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"
    session_dir = tmp_path / "sessions" / "session_live"
    session_dir.mkdir(parents=True)

    _write_index(
        index_path,
        [json.dumps({"sessionId": "session_live", "sessionDir": str(session_dir)})],
    )

    read_kimi_sessions(index_path, dao, NOW_ISO)

    row = _get_session(dao, "session_live")
    assert row is not None
    expected_mtime_iso = datetime.datetime.fromtimestamp(
        session_dir.stat().st_mtime, tz=datetime.UTC
    ).isoformat()
    assert row["last_event_at"] == expected_mtime_iso
    assert row["last_event_at"] != NOW_ISO


def test_missing_or_non_string_session_dir_degrades_to_now_iso(tmp_path: pathlib.Path) -> None:
    """No ``sessionDir`` at all (or a non-string value) is not a containment
    failure — it is simply absent, so ``last_event_at`` falls back to now_iso."""
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"

    _write_index(
        index_path,
        [
            json.dumps({"sessionId": "session-no-dir"}),
            json.dumps({"sessionId": "session-int-dir", "sessionDir": 12345}),
        ],
    )

    result = read_kimi_sessions(index_path, dao, NOW_ISO)
    assert result.sessions_ingested == 2

    for session_id in ("session-no-dir", "session-int-dir"):
        row = _get_session(dao, session_id)
        assert row is not None
        assert row["last_event_at"] == NOW_ISO


# ---------------------------------------------------------------------------
# FR3.4 — lexical containment BEFORE Path(...).stat(). RED-first: an escaping
# sessionDir must never reach stat() at all.
# ---------------------------------------------------------------------------


def test_nonexistent_session_dir_within_parent_degrades_via_existing_oserror(
    tmp_path: pathlib.Path,
) -> None:
    """A contained but nonexistent sessionDir still takes the pre-existing OSError
    degrade branch (FileNotFoundError on stat()) — containment does not add a new
    failure mode, it only guards what may reach the filesystem call."""
    dao = _make_dao()
    index_path = tmp_path / "session_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    missing_session_dir = tmp_path / "sessions" / "does-not-exist"

    _write_index(
        index_path,
        [json.dumps({"sessionId": "session-missing-dir", "sessionDir": str(missing_session_dir)})],
    )

    result = read_kimi_sessions(index_path, dao, NOW_ISO)
    assert result.sessions_ingested == 1

    row = _get_session(dao, "session-missing-dir")
    assert row is not None
    assert row["last_event_at"] == NOW_ISO


@pytest.mark.parametrize(
    ("case", "escaping_session_dir_factory"),
    [
        ("absolute-outside-sibling", lambda tmp_path: str(tmp_path / "outside" / "loot")),
        ("absolute-outside-root", lambda tmp_path: "/etc"),
        ("dotdot-escape", lambda tmp_path: "../../etc/passwd"),
        (
            "dotdot-escape-within-absolute",
            lambda tmp_path: str(tmp_path / "kimi_index_dir" / ".." / ".." / "etc" / "passwd"),
        ),
    ],
)
def test_escaping_session_dir_never_reaches_stat(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    escaping_session_dir_factory: object,
) -> None:
    """FR3.4 (RED-first): ``sessionDir`` is lexically contained against
    ``index_path.parent`` BEFORE ``Path(...).stat()`` is invoked. Proven by
    monkeypatching ``Path.stat`` to fail the test outright if it is ever called
    with a path outside ``index_path.parent`` — the containment check must reject
    the escaping candidate before the filesystem call, not after it. Containment
    failure takes the EXISTING OSError degrade branch: the session still folds,
    with ``last_event_at == now_iso``, never a traceback and never the escaping
    path's real mtime.
    """
    index_dir = tmp_path / "kimi_index_dir"
    index_dir.mkdir()
    index_path = index_dir / "session_index.jsonl"
    (tmp_path / "outside").mkdir()

    escaping_session_dir = escaping_session_dir_factory(tmp_path)  # type: ignore[operator]

    _write_index(
        index_path,
        [json.dumps({"sessionId": f"escape-{case}", "sessionDir": escaping_session_dir})],
    )

    # Narrow guard: only the EXACT injected escaping candidate is forbidden from
    # reaching stat() — every other Path.stat() call in the process (pytest's own
    # machinery, unrelated fixtures, traceback formatting) passes through
    # untouched. A broad "anything outside index_dir" guard is unsafe here: pytest
    # itself stats dozens of unrelated paths (repo root, source files, tmp roots)
    # during collection/teardown/failure-reporting.
    real_stat = pathlib.Path.stat
    forbidden = str(pathlib.Path(escaping_session_dir))

    def _guarded_stat(self: pathlib.Path, *args: object, **kwargs: object) -> object:
        if str(self) == forbidden:
            raise AssertionError(
                f"containment leak: Path.stat() reached the escaping candidate "
                f"{self!r} for case {case!r}"
            )
        return real_stat(self, *args, **kwargs)  # type: ignore[no-any-return]

    monkeypatch.setattr(pathlib.Path, "stat", _guarded_stat)

    dao = _make_dao()
    result = read_kimi_sessions(index_path, dao, NOW_ISO)

    assert result.sessions_ingested == 1
    row = _get_session(dao, f"escape-{case}")
    assert row is not None
    assert row["last_event_at"] == NOW_ISO


def test_session_dir_equal_to_index_parent_is_contained(
    tmp_path: pathlib.Path,
) -> None:
    """The boundary case: ``sessionDir == index_path.parent`` itself is contained
    (not an escape) and its mtime is used."""
    dao = _make_dao()
    index_dir = tmp_path / "kimi_index_dir"
    index_dir.mkdir()
    index_path = index_dir / "session_index.jsonl"

    _write_index(
        index_path,
        [json.dumps({"sessionId": "session-parent-itself", "sessionDir": str(index_dir)})],
    )

    read_kimi_sessions(index_path, dao, NOW_ISO)

    row = _get_session(dao, "session-parent-itself")
    assert row is not None
    expected_mtime_iso = datetime.datetime.fromtimestamp(
        index_dir.stat().st_mtime, tz=datetime.UTC
    ).isoformat()
    assert row["last_event_at"] == expected_mtime_iso
