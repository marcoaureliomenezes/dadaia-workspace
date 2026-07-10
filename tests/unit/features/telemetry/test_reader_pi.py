"""Unit tests for features/telemetry/reader/pi.py (WS-PI-6 / T-30-B-03).

All fixtures are synthesized in-memory from the REAL PI session-file shape
(live-verified 2026-06-26 against ~/.pi/agent/sessions/<dir-slug>/*.jsonl) — NO real
PI data is read. The canned fixture is byte-faithful to the documented record shape:
a ``session`` header line, ``model_change`` + ``thinking_level_change`` metadata
lines, and ``message`` body lines (which the reader MUST ignore for T1).

Privacy sentinel (no-message-body-reaches-store) must survive — kept verbatim.
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
    return int(row[0])


def _write_session(root: pathlib.Path, slug: str, filename: str, body: str) -> pathlib.Path:
    """Write a session file under <root>/<slug>/<filename>."""
    slug_dir = root / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    path = slug_dir / filename
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Privacy sentinel — T1: no message body reaches the store. Kept verbatim.
# ---------------------------------------------------------------------------


def test_no_message_body_reaches_store(tmp_path: pathlib.Path) -> None:
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
        rows = dao._conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: SLF001, S608
        for row in rows:
            for value in tuple(row):
                assert _SECRET_SENTINEL not in str(value), (
                    f"T1 VIOLATION: message body leaked into {table}: {value!r}"
                )


# ---------------------------------------------------------------------------
# Ingest/malformed/header-only/missing variants — 1 test
# ---------------------------------------------------------------------------


def test_ingest_malformed_header_only_and_missing_matrix(tmp_path: pathlib.Path) -> None:
    # missing dir / missing file -> empty result, no exception.
    dao_missing_dir = _make_dao()
    missing_dir_result = read_pi_sessions(tmp_path / "nope", dao_missing_dir, NOW_ISO)
    assert isinstance(missing_dir_result, ReadResult)
    assert missing_dir_result.sessions_ingested == 0
    assert _count_table(dao_missing_dir, "sessions") == 0

    dao_missing_file = _make_dao()
    missing_file_result = read_pi_session_file(tmp_path / "no.jsonl", dao_missing_file, NOW_ISO)
    assert missing_file_result.sessions_ingested == 0

    # canned fixture: metadata correctly ingested (1 session, 1 agent, 1 event).
    canned_root = tmp_path / "canned"
    _write_session(
        canned_root,
        "--home-marco-workspace-dadaia--",
        "2026-06-26T01-57-14-236Z_019f01a5-3d7b-789a-9d58-9609039392cf.jsonl",
        _CANNED_SESSION,
    )
    dao_canned = _make_dao()
    canned_result = read_pi_sessions(canned_root, dao_canned, NOW_ISO)
    assert canned_result.sessions_ingested == 1
    assert canned_result.events_ingested == 1
    assert _count_table(dao_canned, "sessions") == 1
    assert _count_table(dao_canned, "events") == 1
    agents = dao_canned.list_agents()
    assert len(agents) == 1
    assert agents[0].name == "pi (main)"
    assert agents[0].provider == "pi"
    sess = dao_canned._conn.execute(  # noqa: SLF001
        "SELECT * FROM sessions WHERE session_id = ?",
        ("019f01a5-3d7b-789a-9d58-9609039392cf",),
    ).fetchone()
    assert sess is not None
    assert sess["provider"] == "pi"
    assert sess["cwd"] == "/home/marco/workspace/dadaia"
    assert sess["first_event_at"] == "2026-06-26T01:57:14.236Z"
    ev = dao_canned._conn.execute(  # noqa: SLF001
        "SELECT * FROM events WHERE session_id = ?",
        ("019f01a5-3d7b-789a-9d58-9609039392cf",),
    ).fetchone()
    assert ev is not None
    assert ev["model"] == "gpt-5.5"
    assert ev["cost_micro_usd"] is None  # PI cost unknown — never faked
    assert ev["tokens_input"] == 0
    assert ev["tokens_output"] == 0
    assert ev["suspect"] == 0

    # malformed line skipped, valid header still ingests.
    malformed_body = (
        '{"type":"session","version":3,"id":"sid-1",'
        '"timestamp":"2026-06-26T01:00:00.000Z","cwd":"/tmp/x"}\n'
        "{ this is not valid json }\n"
        '{"type":"model_change","id":"m1","timestamp":"2026-06-26T01:00:01.000Z",'
        '"provider":"openai-codex","modelId":"gpt-5.5"}\n'
    )
    malformed_root = tmp_path / "malformed"
    _write_session(malformed_root, "--tmp-x--", "s.jsonl", malformed_body)
    dao_malformed = _make_dao()
    malformed_result = read_pi_sessions(malformed_root, dao_malformed, NOW_ISO)
    assert malformed_result.sessions_ingested == 1
    assert malformed_result.events_skipped >= 1
    assert _count_table(dao_malformed, "sessions") == 1

    # header-only file ingests with model 'pi'.
    header_only_body = (
        '{"type":"session","version":3,"id":"sid-only",'
        '"timestamp":"2026-06-26T02:00:00.000Z","cwd":"/tmp/y"}\n'
    )
    header_root = tmp_path / "header"
    _write_session(header_root, "--tmp-y--", "h.jsonl", header_only_body)
    dao_header = _make_dao()
    read_pi_sessions(header_root, dao_header, NOW_ISO)
    header_ev = dao_header._conn.execute(  # noqa: SLF001
        "SELECT model FROM events WHERE session_id = 'sid-only'"
    ).fetchone()
    assert header_ev is not None
    assert header_ev["model"] == "pi"

    # no session header at all -> nothing ingested.
    no_header_body = (
        '{"type":"model_change","id":"m1","timestamp":"2026-06-26T01:00:01.000Z",'
        '"provider":"openai-codex","modelId":"gpt-5.5"}\n'
    )
    noheader_root = tmp_path / "noheader"
    _write_session(noheader_root, "--tmp-z--", "noheader.jsonl", no_header_body)
    dao_noheader = _make_dao()
    no_header_result = read_pi_sessions(noheader_root, dao_noheader, NOW_ISO)
    assert no_header_result.sessions_ingested == 0
    assert _count_table(dao_noheader, "sessions") == 0
