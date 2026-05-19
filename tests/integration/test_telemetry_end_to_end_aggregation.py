"""Integration test — PR4-10: end-to-end telemetry aggregation pipeline.

Seeds synthetic jsonl files with dispatched-subagent events, drives the
reader + aggregator pipeline, and asserts that list_agents() returns at
least one summary with session_count > 0 for the seeded agent persona.

All data is synthetic / fictional — no real operator content is accessed.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
from datetime import date
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.reader.claude import read_session_file
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPricing:
    PRICING_TABLE: dict[str, list] = {}

    @staticmethod
    def compute_cost(usage: dict, model: str, when: date) -> int | None:
        return None

    @staticmethod
    def pricing_age_days(models_used: list[str], when: Any = None) -> int | None:
        return None


class _StubSCS:
    def list_all(self) -> list:
        return []


# ---------------------------------------------------------------------------
# JSONL fixture builders (synthetic/fictional data only)
# ---------------------------------------------------------------------------

_NOW_ISO = "2026-05-19T12:00:00Z"


def _dispatch_event(session_id: str, subagent_type: str, event_uuid: str) -> str:
    """Build a synthetic assistant event that dispatches a subagent."""
    return json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T11:00:00.000Z",
            "type": "assistant",
            "uuid": event_uuid,
            "cwd": "/home/testuser/workspace/dadaia",
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
                        "id": f"toolu_{event_uuid}",
                        "name": "Agent",
                        "input": {
                            "subagent_type": subagent_type,
                            "description": "Implement the feature.",
                            "prompt": "Please implement the feature.",
                        },
                    }
                ],
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        }
    )


def _usage_event(session_id: str, event_uuid: str) -> str:
    """Build a minimal assistant event with usage (generates an event row)."""
    return json.dumps(
        {
            "sessionId": session_id,
            "timestamp": "2026-05-19T11:01:00.000Z",
            "type": "assistant",
            "uuid": event_uuid,
            "cwd": "/home/testuser/workspace/dadaia",
            "gitBranch": "main",
            "isSidechain": False,
            "slug": "",
            "entrypoint": "cli",
            "agentName": None,
            "aiTitle": None,
            "message": {
                "model": "claude-opus-4-7",
                "usage": {
                    "input_tokens": 800,
                    "output_tokens": 300,
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 50,
                },
            },
        }
    )


def _write_synthetic_jsonl(
    path: pathlib.Path,
    session_id: str,
    subagent_type: str,
) -> None:
    """Write a 2-line synthetic jsonl: a dispatch event + a usage event."""
    lines = [
        _dispatch_event(session_id, subagent_type, f"uuid-dispatch-{session_id}"),
        _usage_event(session_id, f"uuid-usage-{session_id}"),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dao(db_path: pathlib.Path) -> TelemetryDao:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return TelemetryDao(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEndToEndAggregation:
    """PR4-10: seed → read → aggregate → assert session_count > 0."""

    def test_single_agent_session_count_nonzero(self, tmp_path: pathlib.Path) -> None:
        """After reading one synthetic jsonl, list_agents returns the seeded
        subagent with session_count >= 1.
        """
        # Set up DB
        db_path = tmp_path / "telemetry.sqlite"
        dao = _make_dao(db_path)

        # Write synthetic jsonl
        jsonl_path = tmp_path / "session-001.jsonl"
        _write_synthetic_jsonl(
            jsonl_path,
            session_id="e2e-session-001",
            subagent_type="software-engineer",
        )

        # Drive the reader
        result = read_session_file(jsonl_path, dao, _NOW_ISO)
        assert result.events_ingested >= 1, (
            f"Expected at least 1 ingested event, got {result.events_ingested}"
        )

        # Aggregate
        aggregator = TelemetryAggregator(
            dao=dao,
            spec_context_service=_StubSCS(),
            pricing_module=_StubPricing(),
        )
        agent_result = aggregator.list_agents(window_days=365)

        # Assert
        agent_ids = [s.agent_id for s in agent_result.agents]
        assert "software-engineer" in agent_ids, (
            f"Expected 'software-engineer' in aggregated agents, got {agent_ids}"
        )

        se = next(s for s in agent_result.agents if s.agent_id == "software-engineer")
        assert se.session_count >= 1, (
            f"Expected session_count >= 1 for software-engineer, got {se.session_count}"
        )

    def test_multiple_agents_all_appear(self, tmp_path: pathlib.Path) -> None:
        """Three distinct subagent sessions each produce a separate aggregated entry."""
        db_path = tmp_path / "telemetry.sqlite"
        dao = _make_dao(db_path)

        personas = ["software-engineer", "product-engineer", "qa-engineer"]
        for idx, persona in enumerate(personas):
            jsonl_path = tmp_path / f"session-{idx:03d}.jsonl"
            _write_synthetic_jsonl(
                jsonl_path,
                session_id=f"e2e-session-{idx:03d}",
                subagent_type=persona,
            )
            read_session_file(jsonl_path, dao, _NOW_ISO)

        aggregator = TelemetryAggregator(
            dao=dao,
            spec_context_service=_StubSCS(),
            pricing_module=_StubPricing(),
        )
        agent_result = aggregator.list_agents(window_days=365)
        agent_ids = {s.agent_id for s in agent_result.agents}

        for persona in personas:
            assert persona in agent_ids, (
                f"Expected {persona!r} in aggregated agents, got {sorted(agent_ids)}"
            )
            summary = next(s for s in agent_result.agents if s.agent_id == persona)
            assert summary.session_count >= 1, (
                f"Expected session_count >= 1 for {persona!r}, got {summary.session_count}"
            )

    def test_idempotent_double_read(self, tmp_path: pathlib.Path) -> None:
        """Reading the same jsonl twice (via byte_offset) does not double-count events."""
        db_path = tmp_path / "telemetry.sqlite"
        dao = _make_dao(db_path)

        jsonl_path = tmp_path / "session-idem.jsonl"
        _write_synthetic_jsonl(
            jsonl_path,
            session_id="e2e-session-idem-001",
            subagent_type="frontend-engineer",
        )

        result1 = read_session_file(jsonl_path, dao, _NOW_ISO)
        result2 = read_session_file(jsonl_path, dao, _NOW_ISO)

        # Second read should ingest 0 new events (byte_offset at EOF)
        assert result2.events_ingested == 0, (
            f"Expected 0 events on second read, got {result2.events_ingested}"
        )

        aggregator = TelemetryAggregator(
            dao=dao,
            spec_context_service=_StubSCS(),
            pricing_module=_StubPricing(),
        )
        agent_result = aggregator.list_agents(window_days=365)
        fe = next((s for s in agent_result.agents if s.agent_id == "frontend-engineer"), None)
        assert fe is not None
        assert fe.session_count == result1.events_ingested or fe.session_count >= 1
