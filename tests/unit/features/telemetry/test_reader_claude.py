"""Unit tests for features/telemetry/reader/claude.py.

Uses in-memory SQLite with full schema applied (via apply_migrations) so
the DAO behaves exactly as in production without touching the filesystem DB.

Fixture files in tests/fixtures/telemetry/ contain ONLY synthesized/fictional
data — no real operator content.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

from dadaia_workspace.features.telemetry.reader.claude import (
    read_session_file,
)
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import (
    apply_migrations,
)

# ---------------------------------------------------------------------------
# Fixtures dir path
# ---------------------------------------------------------------------------

FIXTURES_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "fixtures" / "telemetry"

NOW_ISO = "2026-05-17T10:00:00Z"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dao(tmp_path: pathlib.Path) -> TelemetryDao:
    """Create a fresh in-memory SQLite DAO with migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_migrations(conn)
    return TelemetryDao(conn)


def _count_table(dao: TelemetryDao, table: str) -> int:
    """Count rows in a table via the internal connection."""
    row = dao._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: SLF001
    return row[0]


def _get_session(dao: TelemetryDao, session_id: str):  # type: ignore[return]
    """Fetch a single session row by ID."""
    return dao._conn.execute(  # noqa: SLF001
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()


def _get_all_events(dao: TelemetryDao) -> list:
    """Return all event rows."""
    return dao._conn.execute("SELECT * FROM events").fetchall()  # noqa: SLF001


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicSession:
    def test_reads_basic_session(self, tmp_path: pathlib.Path) -> None:
        """3 events: agent-name, assistant (with usage), ai-title.

        Expected:
        - 1 row in events (only assistant has usage).
        - sessions.agent_name set to 'software-engineer'.
        - sessions.ai_title set to 'Implement telemetry reader'.
        """
        dao = _make_dao(tmp_path)
        path = FIXTURES_DIR / "sample_session_basic.jsonl"
        result = read_session_file(path, dao, NOW_ISO)

        assert result.events_ingested == 1, f"Expected 1 event, got {result.events_ingested}"
        assert _count_table(dao, "events") == 1
        assert _count_table(dao, "sessions") == 1
        assert _count_table(dao, "agents") == 1

        session_row = dao._conn.execute(  # noqa: SLF001
            "SELECT * FROM sessions WHERE session_id = 'test-session-001'"
        ).fetchone()
        assert session_row is not None
        assert session_row["agent_name"] == "software-engineer"
        assert session_row["ai_title"] == "Implement telemetry reader"

    def test_agent_name_in_agents_table(self, tmp_path: pathlib.Path) -> None:
        dao = _make_dao(tmp_path)
        path = FIXTURES_DIR / "sample_session_basic.jsonl"
        read_session_file(path, dao, NOW_ISO)

        agents = dao.list_agents()
        assert len(agents) == 1
        assert agents[0].name == "software-engineer"


class TestTruncatedLine:
    def test_truncated_line_rewinds(self, tmp_path: pathlib.Path) -> None:
        """Partial final line must NOT be consumed.

        After first read: byte_offset is at start of the partial line.
        After appending the rest and re-reading: the partial line is parsed.
        """
        dao = _make_dao(tmp_path)
        # Copy the truncated fixture to tmp_path (we need to append to it)
        src = FIXTURES_DIR / "sample_session_truncated.jsonl"
        target = tmp_path / "session.jsonl"
        target.write_bytes(src.read_bytes())

        result1 = read_session_file(target, dao, NOW_ISO)
        assert result1.partial_final_line is True
        # 2 complete lines: agent-name + assistant (the partial ai-title is NOT consumed)
        assert result1.events_ingested == 1

        # Check offset was saved before the partial line
        state = dao.get_reader_state(str(target))
        assert state is not None
        # offset should be before EOF (partial line not included)
        eof_size = target.stat().st_size
        assert state.byte_offset < eof_size

        # Append completion of partial line to simulate new data arriving
        complete_suffix = b' "Implement telemetry reader"}\n'
        with target.open("ab") as fh:
            fh.write(complete_suffix)

        result2 = read_session_file(target, dao, NOW_ISO)
        # The ai-title line is now complete — but no assistant event in it
        assert result2.events_ingested == 0
        assert result2.partial_final_line is False

    def test_truncated_offset_not_past_partial(self, tmp_path: pathlib.Path) -> None:
        """Byte offset after a truncated read must be at start of partial line."""
        dao = _make_dao(tmp_path)
        src = FIXTURES_DIR / "sample_session_truncated.jsonl"
        target = tmp_path / "session2.jsonl"
        target.write_bytes(src.read_bytes())

        read_session_file(target, dao, NOW_ISO)
        state = dao.get_reader_state(str(target))
        assert state is not None

        # Rewind the file to the saved offset and check what's there
        raw = target.read_bytes()
        remainder = raw[state.byte_offset :]
        # The remainder should start with the partial JSON line
        assert remainder.startswith(b"{"), (
            f"Expected partial JSON at offset {state.byte_offset}, got: {remainder[:40]!r}"
        )


class TestMalformedMidFile:
    def test_malformed_line_skipped(self, tmp_path: pathlib.Path) -> None:
        """Invalid JSON on line 2 is skipped; valid events on lines 1 and 3 are ingested."""
        dao = _make_dao(tmp_path)
        path = FIXTURES_DIR / "sample_session_malformed_mid.jsonl"
        result = read_session_file(path, dao, NOW_ISO)

        assert result.events_skipped >= 1  # the malformed line
        # Line 1 = agent-name (not an event row); line 3 = assistant (1 ingested)
        assert result.events_ingested == 1

    def test_malformed_line_does_not_stop_reader(self, tmp_path: pathlib.Path) -> None:
        """Processing continues after a malformed line — subsequent valid events are ingested."""
        dao = _make_dao(tmp_path)
        path = FIXTURES_DIR / "sample_session_malformed_mid.jsonl"
        read_session_file(path, dao, NOW_ISO)

        events = _get_all_events(dao)
        assert len(events) == 1, "The valid assistant event on line 3 must be ingested"


class TestEmptyFile:
    def test_empty_file_noop(self, tmp_path: pathlib.Path) -> None:
        """Empty file must return ReadResult with 0 ingested and no errors."""
        dao = _make_dao(tmp_path)
        path = FIXTURES_DIR / "sample_session_empty.jsonl"
        result = read_session_file(path, dao, NOW_ISO)

        assert result.events_ingested == 0
        assert result.events_skipped == 0
        assert result.bytes_read == 0
        assert _count_table(dao, "events") == 0


class TestIdempotentReread:
    def test_idempotent_reread(self, tmp_path: pathlib.Path) -> None:
        """Running twice on same file with saved byte_offset → 0 new ingests on second run."""
        dao = _make_dao(tmp_path)
        # Copy basic fixture to tmp so we own the path
        src = FIXTURES_DIR / "sample_session_basic.jsonl"
        target = tmp_path / "session.jsonl"
        target.write_bytes(src.read_bytes())

        result1 = read_session_file(target, dao, NOW_ISO)
        assert result1.events_ingested == 1

        # Second run — offset is at EOF, nothing new
        result2 = read_session_file(target, dao, NOW_ISO)
        assert result2.events_ingested == 0
        assert result2.events_skipped == 0

        # DB counts unchanged
        assert _count_table(dao, "events") == 1
        assert _count_table(dao, "sessions") == 1


class TestInodeRotation:
    def test_inode_rotation_resets_offset(self, tmp_path: pathlib.Path) -> None:
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

        # Persist the old inode
        state_before = dao.get_reader_state(str(target))
        assert state_before is not None
        old_inode = state_before.last_inode

        # "Rotate" the file — delete and recreate (new inode)
        target.unlink()
        target.write_bytes(src.read_bytes())
        new_inode = target.stat().st_ino

        # Inodes might be the same on some filesystems in the same tmp dir.
        # If they are, force the stored inode to be different.
        if old_inode == new_inode:
            # Manually set stored inode to a fake old value
            from dadaia_workspace.features.telemetry.store.models import ReaderState

            dao.upsert_reader_state(
                ReaderState(
                    file_path=str(target),
                    kind="claude_jsonl",
                    byte_offset=state_before.byte_offset,
                    last_mtime=state_before.last_mtime,
                    last_inode=old_inode + 999,  # fake different inode
                    error_count=0,
                    last_ingest_at=NOW_ISO,
                )
            )

        result2 = read_session_file(target, dao, NOW_ISO)
        assert result2.rotated is True

        # Events table should still have only 1 row (INSERT OR IGNORE idempotency)
        assert _count_table(dao, "events") == 1


class TestNoForbiddenFieldsInDb:
    def test_no_forbidden_fields_in_db(self, tmp_path: pathlib.Path) -> None:
        """After ingesting an event with embedded content/thinking fields,
        no forbidden strings must appear in DB session or event rows.
        """
        dao = _make_dao(tmp_path)

        # Synthesize a jsonl with forbidden fields embedded at the raw level
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
                    # Forbidden fields — must be stripped by allowlist
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

        FORBIDDEN_SUBSTRINGS = {
            "SECRET",
            "content",
            "thinking",
            "prompt",
            "messages",
        }

        # Check sessions table
        sessions = dao._conn.execute("SELECT * FROM sessions").fetchall()  # noqa: SLF001
        for row in sessions:
            for col in row.keys():  # noqa: SIM118 — sqlite3.Row iter yields values, not keys
                val = row[col]
                if isinstance(val, str):
                    for forbidden in FORBIDDEN_SUBSTRINGS:
                        assert forbidden not in val, (
                            f"Forbidden substring {forbidden!r} found in sessions.{col}: {val!r}"
                        )

        # Check events table
        events = dao._conn.execute("SELECT * FROM events").fetchall()  # noqa: SLF001
        for row in events:
            for col in row.keys():  # noqa: SIM118 — sqlite3.Row iter yields values, not keys
                val = row[col]
                if isinstance(val, str):
                    for forbidden in FORBIDDEN_SUBSTRINGS:
                        assert forbidden not in val, (
                            f"Forbidden substring {forbidden!r} found in events.{col}: {val!r}"
                        )

        # Check agents table
        agents = dao._conn.execute("SELECT * FROM agents").fetchall()  # noqa: SLF001
        for row in agents:
            for col in row.keys():  # noqa: SIM118 — sqlite3.Row iter yields values, not keys
                val = row[col]
                if isinstance(val, str):
                    for forbidden in FORBIDDEN_SUBSTRINGS:
                        assert forbidden not in val, (
                            f"Forbidden substring {forbidden!r} found in agents.{col}: {val!r}"
                        )


class TestMissingFile:
    def test_missing_file_returns_empty_result(self, tmp_path: pathlib.Path) -> None:
        """Reader must handle a non-existent file gracefully."""
        dao = _make_dao(tmp_path)
        path = tmp_path / "nonexistent.jsonl"
        result = read_session_file(path, dao, NOW_ISO)
        assert result.events_ingested == 0
        assert result.events_skipped == 0


# ---------------------------------------------------------------------------
# Dispatched subagent persona extraction tests
# ---------------------------------------------------------------------------

# Minimal jsonl fixture helpers for inline synthetic dispatch data.
# No real operator content — all values are fictional.


def _make_dispatch_jsonl(
    session_id: str,
    subagent_type: str,
) -> bytes:
    """Build a synthetic jsonl file with:

    1. An assistant event that dispatches a subagent (Agent tool_use with
       subagent_type = *subagent_type*).
    2. An assistant event with usage (so 1 event row is inserted).

    The dispatch event carries the subagent persona.  The usage event
    carries usage tokens that satisfy the event-insertion path.
    """
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
                # content carries the Agent tool_use; allowlist will strip this
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
    """Build a synthetic jsonl file with only top-level (non-dispatching) events.

    Contains one agent-name event (project slug) and one assistant+usage event.
    No Agent tool_use → agent_name should remain None.
    """
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


class TestDispatchedSubagentExtraction:
    """Agent name is extracted from dispatched subagent persona."""

    def test_agent_name_extracted_from_dispatched_subagent(self, tmp_path: pathlib.Path) -> None:
        """Synthetic jsonl with an Agent tool_use carrying subagent_type='software-engineer'
        must yield a session row where agent_name == 'software-engineer'.

        Acceptance criterion: C2 (FR1).
        """
        dao = _make_dao(tmp_path)
        session_id = "dispatch-session-se-001"
        target = tmp_path / "dispatch_se.jsonl"
        target.write_bytes(_make_dispatch_jsonl(session_id, "software-engineer"))

        result = read_session_file(target, dao, NOW_ISO)

        assert result.events_ingested >= 1, (
            f"Expected at least 1 ingested event, got {result.events_ingested}"
        )

        session_row = _get_session(dao, session_id)
        assert session_row is not None, f"Session '{session_id}' not found in DB"
        assert session_row["agent_name"] == "software-engineer", (
            f"Expected agent_name='software-engineer', got {session_row['agent_name']!r}"
        )

    def test_agent_name_extracted_various_subagent_types(self, tmp_path: pathlib.Path) -> None:
        """Verify extraction works for multiple distinct canonical agent names."""
        dao = _make_dao(tmp_path)

        cases = [
            ("dispatch-session-pm-001", "project-manager"),
            ("dispatch-session-pe-001", "product-engineer"),
            ("dispatch-session-qa-001", "qa-engineer"),
        ]

        for session_id, agent_type in cases:
            target = tmp_path / f"dispatch_{agent_type.replace('-', '_')}.jsonl"
            target.write_bytes(_make_dispatch_jsonl(session_id, agent_type))
            read_session_file(target, dao, NOW_ISO)

        for session_id, agent_type in cases:
            row = _get_session(dao, session_id)
            assert row is not None, f"Session '{session_id}' missing"
            assert row["agent_name"] == agent_type, (
                f"For {agent_type}: expected agent_name={agent_type!r}, got {row['agent_name']!r}"
            )

    def test_explore_plan_subagent_types_not_used_as_agent_name(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Non-canonical subtypes 'Explore' and 'Plan' must NOT populate agent_name.

        These are internal Claude Code built-ins, not persona agents.
        """
        dao = _make_dao(tmp_path)

        for non_canonical in ("Explore", "Plan"):
            sid = f"dispatch-session-{non_canonical.lower()}-001"
            target = tmp_path / f"dispatch_{non_canonical.lower()}.jsonl"
            target.write_bytes(_make_dispatch_jsonl(sid, non_canonical))
            read_session_file(target, dao, NOW_ISO)

            row = _get_session(dao, sid)
            assert row is not None, f"Session '{sid}' missing"
            assert row["agent_name"] is None, (
                f"Expected agent_name=None for subagent_type={non_canonical!r}, "
                f"got {row['agent_name']!r}"
            )

    def test_top_level_session_has_null_agent_name(self, tmp_path: pathlib.Path) -> None:
        """Top-level Claude events with no Agent tool_use → agent_name must be None.

        The agent-name event carries a project slug (not a persona), and
        agent_name=None is intentional for operator/main-Claude sessions.

        This protects top-level operator sessions from being misclassified as
        persona-agent sessions.
        """
        dao = _make_dao(tmp_path)
        session_id = "toplevel-session-001"
        target = tmp_path / "toplevel.jsonl"
        target.write_bytes(_make_top_level_jsonl(session_id))

        read_session_file(target, dao, NOW_ISO)

        row = _get_session(dao, session_id)
        assert row is not None, f"Session '{session_id}' missing"
        assert row["agent_name"] is None, (
            f"Expected agent_name=None for top-level session, got {row['agent_name']!r}"
        )
