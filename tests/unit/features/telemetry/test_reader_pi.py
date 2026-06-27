"""Unit tests for features/telemetry/reader/pi.py (WS-PI-6 / T-30-B-03).

All fixtures are synthesized in-memory from the REAL PI session-file shape
(live-verified 2026-06-26 against ~/.pi/agent/sessions/<dir-slug>/*.jsonl) — NO real
PI data is read. The canned fixture is byte-faithful to the documented record shape:
a ``session`` header line, ``model_change`` + ``thinking_level_change`` metadata
lines, and ``message`` body lines (which the reader MUST ignore for T1).
"""

from __future__ import annotations

import pathlib
import sqlite3

from dadaia_workspace.features.telemetry.reader.pi import (
    ReadResult,
    read_pi_session_file,
    read_pi_sessions,
)
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

NOW_ISO = "2026-06-26T12:00:00Z"

# A sentinel that appears ONLY inside message bodies. If T1 is honored it must
# never reach the telemetry store in any column.
_SECRET_SENTINEL = "TOPSECRET-bind-to-dadaia-workspace-PRIVATE"

# Byte-faithful canned fixture mirroring the real shape (one JSON object per line).
# Header keys: cwd, id, timestamp, type, version.
# Metadata event keys: id, modelId, parentId, provider, timestamp, type.
# message lines carry the conversation body in `message.*` — they MUST be ignored.
_CANNED_SESSION = (
    '{"type":"session","version":3,"id":"019f01a5-3d7b-789a-9d58-9609039392cf",'
    '"timestamp":"2026-06-26T01:57:14.236Z","cwd":"/home/marco/workspace/dadaia"}\n'
    '{"type":"model_change","id":"21ef19be","parentId":null,'
    '"timestamp":"2026-06-26T01:57:18.046Z","provider":"openai-codex","modelId":"gpt-5.5"}\n'
    '{"type":"thinking_level_change","id":"4686c291","parentId":"21ef19be",'
    '"timestamp":"2026-06-26T01:57:18.046Z","thinkingLevel":"medium"}\n'
    '{"type":"message","id":"90c5c6e9","parentId":"4686c291",'
    '"timestamp":"2026-06-26T01:57:26.107Z","message":{"role":"user","content":'
    '[{"type":"text","text":"' + _SECRET_SENTINEL + '"}],"timestamp":1782439046101}}\n'
    '{"type":"message","id":"09af2fc8","parentId":"90c5c6e9",'
    '"timestamp":"2026-06-26T01:57:30.011Z","message":{"role":"assistant","content":'
    '[{"type":"thinking","thinking":"' + _SECRET_SENTINEL + '"}],'
    '"usage":{"input":8350,"output":59,"cost":{"total":0.04352}}}}\n'
)


def _make_dao() -> TelemetryDao:
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _count_table(dao: TelemetryDao, table: str) -> int:
    row = dao._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: SLF001
    return row[0]


def _write_session(root: pathlib.Path, slug: str, filename: str, body: str) -> pathlib.Path:
    """Write a session file under <root>/<slug>/<filename>."""
    slug_dir = root / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    path = slug_dir / filename
    path.write_text(body, encoding="utf-8")
    return path


class TestMissingDir:
    def test_missing_dir_returns_empty(self, tmp_path: pathlib.Path) -> None:
        dao = _make_dao()
        result = read_pi_sessions(tmp_path / "nope", dao, NOW_ISO)
        assert isinstance(result, ReadResult)
        assert result.sessions_ingested == 0
        assert _count_table(dao, "sessions") == 0

    def test_missing_file_returns_empty(self, tmp_path: pathlib.Path) -> None:
        dao = _make_dao()
        result = read_pi_session_file(tmp_path / "no.jsonl", dao, NOW_ISO)
        assert result.sessions_ingested == 0


class TestBasicIngest:
    def test_canned_fixture_ingests_metadata(self, tmp_path: pathlib.Path) -> None:
        """One real-shape session → 1 session, 1 'pi (main)' agent, 1 event."""
        _write_session(
            tmp_path,
            "--home-marco-workspace-dadaia--",
            "2026-06-26T01-57-14-236Z_019f01a5-3d7b-789a-9d58-9609039392cf.jsonl",
            _CANNED_SESSION,
        )
        dao = _make_dao()

        result = read_pi_sessions(tmp_path, dao, NOW_ISO)

        assert result.sessions_ingested == 1
        assert result.events_ingested == 1
        assert _count_table(dao, "sessions") == 1
        assert _count_table(dao, "events") == 1

        agents = dao.list_agents()
        assert len(agents) == 1
        assert agents[0].name == "pi (main)"
        assert agents[0].provider == "pi"

        sess = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM sessions WHERE session_id = ?",
            ("019f01a5-3d7b-789a-9d58-9609039392cf",),
        ).fetchone()
        assert sess is not None
        assert sess["provider"] == "pi"
        assert sess["cwd"] == "/home/marco/workspace/dadaia"
        assert sess["first_event_at"] == "2026-06-26T01:57:14.236Z"

        ev = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM events WHERE session_id = ?",
            ("019f01a5-3d7b-789a-9d58-9609039392cf",),
        ).fetchone()
        assert ev is not None
        assert ev["model"] == "gpt-5.5"  # from the model_change metadata line
        assert ev["cost_micro_usd"] is None  # PI cost unknown — never faked
        assert ev["tokens_input"] == 0  # token usage bodies never read
        assert ev["tokens_output"] == 0
        assert ev["suspect"] == 0


class TestPrivacyT1:
    def test_no_message_body_reaches_store(self, tmp_path: pathlib.Path) -> None:
        """T1: the sentinel embedded in message bodies appears in NO store column."""
        _write_session(
            tmp_path,
            "--home-marco-workspace-dadaia--",
            "sess.jsonl",
            _CANNED_SESSION,
        )
        dao = _make_dao()
        read_pi_sessions(tmp_path, dao, NOW_ISO)

        for table in ("sessions", "agents", "events"):
            rows = dao._conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            for row in rows:
                for value in tuple(row):
                    assert _SECRET_SENTINEL not in str(value), (
                        f"T1 VIOLATION: message body leaked into {table}: {value!r}"
                    )


class TestGracefulDegradation:
    def test_malformed_lines_skipped(self, tmp_path: pathlib.Path) -> None:
        """A corrupt line is skipped; a valid header still ingests."""
        body = (
            '{"type":"session","version":3,"id":"sid-1",'
            '"timestamp":"2026-06-26T01:00:00.000Z","cwd":"/tmp/x"}\n'
            "{ this is not valid json }\n"
            '{"type":"model_change","id":"m1","timestamp":"2026-06-26T01:00:01.000Z",'
            '"provider":"openai-codex","modelId":"gpt-5.5"}\n'
        )
        _write_session(tmp_path, "--tmp-x--", "s.jsonl", body)
        dao = _make_dao()

        result = read_pi_sessions(tmp_path, dao, NOW_ISO)

        assert result.sessions_ingested == 1
        assert result.events_skipped >= 1
        assert _count_table(dao, "sessions") == 1

    def test_header_only_file_ingests(self, tmp_path: pathlib.Path) -> None:
        """A session with only a header line still ingests (no model → 'pi')."""
        body = (
            '{"type":"session","version":3,"id":"sid-only",'
            '"timestamp":"2026-06-26T02:00:00.000Z","cwd":"/tmp/y"}\n'
        )
        _write_session(tmp_path, "--tmp-y--", "h.jsonl", body)
        dao = _make_dao()

        read_pi_sessions(tmp_path, dao, NOW_ISO)

        ev = dao._conn.execute(  # noqa: SLF001
            "SELECT model FROM events WHERE session_id = 'sid-only'"
        ).fetchone()
        assert ev is not None
        assert ev["model"] == "pi"

    def test_no_header_no_ingest(self, tmp_path: pathlib.Path) -> None:
        """A file with no parseable session header ingests nothing."""
        body = (
            '{"type":"model_change","id":"m1","timestamp":"2026-06-26T01:00:01.000Z",'
            '"provider":"openai-codex","modelId":"gpt-5.5"}\n'
        )
        _write_session(tmp_path, "--tmp-z--", "noheader.jsonl", body)
        dao = _make_dao()

        result = read_pi_sessions(tmp_path, dao, NOW_ISO)
        assert result.sessions_ingested == 0
        assert _count_table(dao, "sessions") == 0


class TestIdempotentReread:
    def test_idempotent_reread(self, tmp_path: pathlib.Path) -> None:
        _write_session(tmp_path, "--tmp-i--", "s.jsonl", _CANNED_SESSION)
        dao = _make_dao()

        read_pi_sessions(tmp_path, dao, NOW_ISO)
        read_pi_sessions(tmp_path, dao, NOW_ISO)

        assert _count_table(dao, "events") == 1
        assert _count_table(dao, "sessions") == 1
