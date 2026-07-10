"""Unit tests for features/telemetry/reader/claude.py.

Uses in-memory SQLite with full schema applied (via apply_migrations) so
the DAO behaves exactly as in production without touching the filesystem DB.

Fixture files in tests/fixtures/telemetry/ contain ONLY synthesized/fictional
data — no real operator content.

Privacy-critical: no-forbidden-in-db is the only executed-path guarantee that
prompts/content never persist — kept verbatim.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from dadaia_workspace.features.telemetry.reader.claude import read_session_file
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

FIXTURES_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "fixtures" / "telemetry"

NOW_ISO = "2026-05-17T10:00:00Z"


def _make_dao(tmp_path: pathlib.Path) -> TelemetryDao:
    """Create a fresh in-memory SQLite DAO with migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
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


def _get_all_events(dao: TelemetryDao) -> list[sqlite3.Row]:
    return dao._conn.execute("SELECT * FROM events").fetchall()  # noqa: SLF001


# ---------------------------------------------------------------------------
# Basic/agents-table/empty/missing/malformed-continue — 1 param
# ---------------------------------------------------------------------------


def test_basic_empty_missing_and_malformed_mid_file_matrix(tmp_path: pathlib.Path) -> None:
    # Basic: 3 events (agent-name, assistant with usage, ai-title). Expected: 1 row in
    # events (only assistant has usage); sessions.agent_name/ai_title populated; the
    # agents table also carries the persona row.
    dao_basic = _make_dao(tmp_path)
    basic_path = FIXTURES_DIR / "sample_session_basic.jsonl"
    basic_result = read_session_file(basic_path, dao_basic, NOW_ISO)

    assert basic_result.events_ingested == 1
    assert _count_table(dao_basic, "events") == 1
    assert _count_table(dao_basic, "sessions") == 1
    assert _count_table(dao_basic, "agents") == 1

    session_row = _get_session(dao_basic, "test-session-001")
    assert session_row is not None
    assert session_row["agent_name"] == "software-engineer"
    assert session_row["ai_title"] == "Implement telemetry reader"

    agents = dao_basic.list_agents()
    assert len(agents) == 1
    assert agents[0].name == "software-engineer"

    # Empty file: no-op, no errors.
    dao_empty = _make_dao(tmp_path)
    empty_result = read_session_file(
        FIXTURES_DIR / "sample_session_empty.jsonl", dao_empty, NOW_ISO
    )
    assert empty_result.events_ingested == 0
    assert empty_result.events_skipped == 0
    assert empty_result.bytes_read == 0
    assert _count_table(dao_empty, "events") == 0

    # Missing file: handled gracefully.
    dao_missing = _make_dao(tmp_path)
    missing_result = read_session_file(tmp_path / "nonexistent.jsonl", dao_missing, NOW_ISO)
    assert missing_result.events_ingested == 0
    assert missing_result.events_skipped == 0

    # Malformed mid-file line: skipped, processing continues to the valid event after it.
    dao_malformed = _make_dao(tmp_path)
    malformed_result = read_session_file(
        FIXTURES_DIR / "sample_session_malformed_mid.jsonl", dao_malformed, NOW_ISO
    )
    assert malformed_result.events_skipped >= 1
    assert malformed_result.events_ingested == 1
    assert len(_get_all_events(dao_malformed)) == 1

    # Idempotent re-read: second run over the same offset ingests nothing new.
    dao_idem = _make_dao(tmp_path)
    src = FIXTURES_DIR / "sample_session_basic.jsonl"
    target = tmp_path / "session-idem.jsonl"
    target.write_bytes(src.read_bytes())
    result1 = read_session_file(target, dao_idem, NOW_ISO)
    assert result1.events_ingested == 1
    result2 = read_session_file(target, dao_idem, NOW_ISO)
    assert result2.events_ingested == 0
    assert result2.events_skipped == 0
    assert _count_table(dao_idem, "events") == 1
    assert _count_table(dao_idem, "sessions") == 1


# ---------------------------------------------------------------------------
# Truncated-line rewind + offset — kept named
# ---------------------------------------------------------------------------


def test_truncated_line_rewinds_and_offset_stays_before_partial(tmp_path: pathlib.Path) -> None:
    """Partial final line must NOT be consumed; the saved byte_offset points at the
    start of the partial line so a later append completes it correctly."""
    dao = _make_dao(tmp_path)
    src = FIXTURES_DIR / "sample_session_truncated.jsonl"
    target = tmp_path / "session.jsonl"
    target.write_bytes(src.read_bytes())

    result1 = read_session_file(target, dao, NOW_ISO)
    assert result1.partial_final_line is True
    assert result1.events_ingested == 1

    state = dao.get_reader_state(str(target))
    assert state is not None
    eof_size = target.stat().st_size
    assert state.byte_offset < eof_size

    raw = target.read_bytes()
    remainder = raw[state.byte_offset :]
    assert remainder.startswith(b"{"), (
        f"Expected partial JSON at offset {state.byte_offset}, got: {remainder[:40]!r}"
    )

    complete_suffix = b' "Implement telemetry reader"}\n'
    with target.open("ab") as fh:
        fh.write(complete_suffix)

    result2 = read_session_file(target, dao, NOW_ISO)
    assert result2.events_ingested == 0
    assert result2.partial_final_line is False


# ---------------------------------------------------------------------------
# Inode rotation reset — kept named
# ---------------------------------------------------------------------------


def test_inode_rotation_resets_offset(tmp_path: pathlib.Path) -> None:
    """When inode changes, reader resets to offset 0 and re-ingests events.

    Duplicate events are NOT inserted because event_id PK + INSERT OR IGNORE
    guarantees idempotency.
    """
    dao = _make_dao(tmp_path)
    src = FIXTURES_DIR / "sample_session_basic.jsonl"
    target = tmp_path / "session.jsonl"
    target.write_bytes(src.read_bytes())

    result1 = read_session_file(target, dao, NOW_ISO)
    assert result1.events_ingested == 1
    assert result1.rotated is False

    state_before = dao.get_reader_state(str(target))
    assert state_before is not None
    old_inode = state_before.last_inode

    target.unlink()
    target.write_bytes(src.read_bytes())
    new_inode = target.stat().st_ino

    if old_inode == new_inode:
        from dadaia_workspace.features.telemetry.store.models import ReaderState

        dao.upsert_reader_state(
            ReaderState(
                file_path=str(target),
                kind="claude_jsonl",
                byte_offset=state_before.byte_offset,
                last_mtime=state_before.last_mtime,
                last_inode=old_inode + 999,
                error_count=0,
                last_ingest_at=NOW_ISO,
            )
        )

    result2 = read_session_file(target, dao, NOW_ISO)
    assert result2.rotated is True
    assert _count_table(dao, "events") == 1


# ---------------------------------------------------------------------------
# Privacy: no forbidden fields ever land in the DB — CRITICAL, kept verbatim.
# ---------------------------------------------------------------------------


def test_no_forbidden_fields_in_db(tmp_path: pathlib.Path) -> None:
    """After ingesting an event with embedded content/thinking fields, no
    forbidden strings must appear in DB session or event rows."""
    dao = _make_dao(tmp_path)

    adversarial_line = (
        json.dumps(
            {
                "sessionId": "adv-session-001",
                "timestamp": "2026-05-17T11:00:00.000Z",
                "type": "assistant",
                "uuid": "adv-uuid-001",
                "cwd": "/home/operator/adv",
                "gitBranch": "main",
                "isSidechain": False,
                "slug": "",
                "entrypoint": "cli",
                "agentName": None,
                "aiTitle": None,
                "content": "SECRET: adversarial content",
                "thinking": "SECRET: chain of thought",
                "prompt": "SECRET: system prompt",
                "messages": ["SECRET: msg"],
                "message": {
                    "model": "claude-opus-4-7",
                    "content": "SECRET: message.content",
                    "thinking": "SECRET: message.thinking",
                    "usage": {
                        "input_tokens": 500,
                        "output_tokens": 100,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "thinking": "SECRET: usage.thinking",
                    },
                },
            }
        )
        + "\n"
    )

    target = tmp_path / "adversarial.jsonl"
    target.write_bytes(adversarial_line.encode())

    read_session_file(target, dao, NOW_ISO)

    forbidden_substrings = {"SECRET", "content", "thinking", "prompt", "messages"}

    for table in ("sessions", "events", "agents"):
        rows = dao._conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: SLF001
        for row in rows:
            for col in row.keys():  # noqa: SIM118
                val = row[col]
                if isinstance(val, str):
                    for forbidden in forbidden_substrings:
                        assert forbidden not in val, (
                            f"Forbidden substring {forbidden!r} found in {table}.{col}: {val!r}"
                        )


# ---------------------------------------------------------------------------
# Agent-name extraction (dispatched subagent persona) — merged into 1 param
# ---------------------------------------------------------------------------


def _make_dispatch_jsonl(session_id: str, subagent_type: str) -> bytes:
    dispatch_event = json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T08:00:00.000Z",
            "type": "assistant",
            "uuid": f"uuid-dispatch-{session_id}",
            "cwd": "/home/operator/workspace",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-7",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_test_001",
                        "name": "Agent",
                        "input": {
                            "subagent_type": subagent_type,
                            "description": "Implement the feature",
                            "prompt": "Please implement...",
                        },
                    }
                ],
                "usage": {
                    "input_tokens": 800,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        }
    )
    usage_event = json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T08:01:00.000Z",
            "type": "assistant",
            "uuid": f"uuid-usage-{session_id}",
            "cwd": "/home/operator/workspace",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
            "message": {
                "model": "claude-opus-4-7",
                "usage": {
                    "input_tokens": 1200,
                    "output_tokens": 400,
                    "cache_creation_input_tokens": 300,
                    "cache_read_input_tokens": 150,
                },
            },
        }
    )
    return (dispatch_event + "\n" + usage_event + "\n").encode()


def _make_top_level_jsonl(session_id: str) -> bytes:
    agent_name_event = json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T09:00:00.000Z",
            "type": "agent-name",
            "uuid": f"uuid-agentname-{session_id}",
            "cwd": "/home/operator/workspace",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
        }
    )
    usage_event = json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T09:01:00.000Z",
            "type": "assistant",
            "uuid": f"uuid-top-usage-{session_id}",
            "cwd": "/home/operator/workspace",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
            "message": {
                "model": "claude-opus-4-7",
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        }
    )
    return (agent_name_event + "\n" + usage_event + "\n").encode()


@pytest.mark.parametrize(
    ("case", "session_id", "build_jsonl", "expected_agent_name"),
    [
        pytest.param(
            "dispatched-software-engineer",
            "dispatch-session-se-001",
            lambda sid: _make_dispatch_jsonl(sid, "software-engineer"),
            "software-engineer",
            id="dispatched-software-engineer",
        ),
        pytest.param(
            "dispatched-project-manager",
            "dispatch-session-pm-001",
            lambda sid: _make_dispatch_jsonl(sid, "project-manager"),
            "project-manager",
            id="dispatched-project-manager",
        ),
        pytest.param(
            "dispatched-product-engineer",
            "dispatch-session-pe-001",
            lambda sid: _make_dispatch_jsonl(sid, "product-engineer"),
            "product-engineer",
            id="dispatched-product-engineer",
        ),
        pytest.param(
            "dispatched-qa-engineer",
            "dispatch-session-qa-001",
            lambda sid: _make_dispatch_jsonl(sid, "qa-engineer"),
            "qa-engineer",
            id="dispatched-qa-engineer",
        ),
        pytest.param(
            "explore-not-canonical",
            "dispatch-session-explore-001",
            lambda sid: _make_dispatch_jsonl(sid, "Explore"),
            None,
            id="explore-subtype-not-used-as-agent-name",
        ),
        pytest.param(
            "plan-not-canonical",
            "dispatch-session-plan-001",
            lambda sid: _make_dispatch_jsonl(sid, "Plan"),
            None,
            id="plan-subtype-not-used-as-agent-name",
        ),
        pytest.param(
            "top-level-null",
            "toplevel-session-001",
            _make_top_level_jsonl,
            None,
            id="top-level-session-null-agent-name",
        ),
    ],
)
def test_agent_name_extraction_matrix(  # type: ignore[no-untyped-def]
    tmp_path: pathlib.Path,
    case: str,
    session_id: str,
    build_jsonl,
    expected_agent_name: str | None,
) -> None:
    dao = _make_dao(tmp_path)
    target = tmp_path / f"{case}.jsonl"
    target.write_bytes(build_jsonl(session_id))

    read_session_file(target, dao, NOW_ISO)

    row = _get_session(dao, session_id)
    assert row is not None, f"Session {session_id!r} missing"
    assert row["agent_name"] == expected_agent_name
