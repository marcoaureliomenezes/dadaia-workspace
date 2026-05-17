"""Tests for TelemetryService (T-AM-12).

All tests use fakes injected via DI — no real filesystem paths, no real
SQLite files, no real operator data.
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
from datetime import date
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.service import TelemetryService
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeSCS:
    def list_all(self) -> list:
        return []


class _FakePricing:
    class _Row:
        def __init__(self, effective_from: date) -> None:
            self.effective_from = effective_from

    PRICING_TABLE: dict[str, list] = {
        "claude-sonnet-4-6": [_Row(date(2025, 1, 1))],
    }

    @staticmethod
    def compute_cost(usage: dict, model: str, when: date) -> int | None:
        if model not in ("claude-sonnet-4-6",):
            return None
        tok = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return tok * 3  # arbitrary deterministic value

    @staticmethod
    def pricing_age_days(models_used: list[str], when: Any = None) -> int | None:
        return 100 if models_used else None


class _FakeClaudeReader:
    def __init__(self) -> None:
        self.call_count = 0

    def read_session_file(self, path: Any, dao: Any, now_iso: str) -> None:
        self.call_count += 1


class _FakeCodexReader:
    def __init__(self) -> None:
        self.call_count = 0

    def read_sessions(self, path: Any, dao: Any, now_iso: str) -> None:
        self.call_count += 1


class _FakeWorkflowsReader:
    def __init__(self) -> None:
        self.call_count = 0

    def read_workflows(self, root: Any, dao: Any, agents: list, now_iso: str) -> None:
        self.call_count += 1


class _FakeAggregator:
    def __init__(self) -> None:
        self.list_agents_call_count = 0

    def list_agents(self, **kwargs: Any) -> list:
        self.list_agents_call_count += 1
        return []

    def list_workflows(self) -> list:
        return []

    def list_sessions_by_agent(self, agent_id: str, **kwargs: Any) -> list:
        return []


# ---------------------------------------------------------------------------
# Helper to build a service with injectable parts
# ---------------------------------------------------------------------------


def _make_service(
    *,
    state_dir: pathlib.Path,
    workspace_root: pathlib.Path,
    pricing: Any | None = None,
    aggregator: Any | None = None,
    claude_reader: _FakeClaudeReader | None = None,
    codex_reader: _FakeCodexReader | None = None,
    workflows_reader: _FakeWorkflowsReader | None = None,
    now_fn: Any = None,
    getuid_fn: Any = None,
) -> tuple[TelemetryService, _FakeClaudeReader, _FakeCodexReader, _FakeWorkflowsReader]:
    cr = claude_reader or _FakeClaudeReader()
    cdx = codex_reader or _FakeCodexReader()
    wfr = workflows_reader or _FakeWorkflowsReader()
    pricing_mod = pricing or _FakePricing()

    def _reader_factory() -> tuple[Any, Any, Any]:
        return (cr, cdx, wfr)

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_migrations(conn)
    dao_instance = TelemetryDao(conn)

    agg = aggregator or _FakeAggregator()

    def _dao_factory() -> TelemetryDao:
        # Return the same in-memory DAO each time.
        return dao_instance

    svc = TelemetryService(
        dao_factory=_dao_factory,
        aggregator=agg,
        reader_factory=_reader_factory,
        pricing_module=pricing_mod,
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=_FakeSCS(),
        _now_fn=now_fn,
        _getuid_fn=getuid_fn,
    )
    return svc, cr, cdx, wfr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_refuses_uid_zero(tmp_path: pathlib.Path) -> None:
    """TelemetryService constructor raises PermissionError when uid=0."""
    with pytest.raises(PermissionError, match="root"):
        _make_service(
            state_dir=tmp_path / "state",
            workspace_root=tmp_path,
            getuid_fn=lambda: 0,
        )


def test_state_dir_created(tmp_path: pathlib.Path) -> None:
    """Service init creates state_dir if it does not exist."""
    state_dir = tmp_path / "deep" / "nested" / "state"
    assert not state_dir.exists()

    _make_service(
        state_dir=state_dir,
        workspace_root=tmp_path,
    )

    assert state_dir.exists()
    assert state_dir.is_dir()


def test_refresh_cached_within_ttl(tmp_path: pathlib.Path) -> None:
    """Calling refresh twice within TTL does not trigger a second ingest cycle."""
    _time = [0.0]

    def _fake_now() -> float:
        return _time[0]

    svc, cr, cdx, wfr = _make_service(
        state_dir=tmp_path / "state",
        workspace_root=tmp_path,
        now_fn=_fake_now,
    )

    # First refresh — should run.
    svc.refresh()
    first_count = cr.call_count

    # Advance time by 10 s (less than 30s TTL).
    _time[0] = 10.0
    svc.refresh()

    # Reader should not have been called again.
    assert cr.call_count == first_count


def test_refresh_runs_all_readers(tmp_path: pathlib.Path) -> None:
    """refresh() calls all three readers."""
    svc, cr, cdx, wfr = _make_service(
        state_dir=tmp_path / "state",
        workspace_root=tmp_path,
    )
    svc.refresh()

    # codex and workflows readers are always called once per cycle.
    assert cdx.call_count >= 1
    assert wfr.call_count >= 1


def test_concurrent_refresh_no_op(tmp_path: pathlib.Path) -> None:
    """A second service instance with the same lock file skips refresh."""
    import fcntl

    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    lock_path = state_dir / "telemetry.lock"

    # Pre-acquire the lock as if another process holds it.
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    try:
        svc, cr, cdx, wfr = _make_service(
            state_dir=state_dir,
            workspace_root=tmp_path,
        )
        svc.refresh()
        # Lock was held externally, so no readers should have run.
        assert cr.call_count == 0
        assert cdx.call_count == 0
        assert wfr.call_count == 0
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def test_list_agents_passthrough(tmp_path: pathlib.Path) -> None:
    """service.list_agents() triggers refresh and delegates to aggregator."""
    fake_agg = _FakeAggregator()
    svc, _, _, _ = _make_service(
        state_dir=tmp_path / "state",
        workspace_root=tmp_path,
        aggregator=fake_agg,
    )

    svc.list_agents()

    assert fake_agg.list_agents_call_count == 1


def test_cost_backfill(tmp_path: pathlib.Path) -> None:
    """refresh() fills cost_micro_usd for events with known model and NULL cost."""

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_migrations(conn)

    # Seed a session + agent + event with NULL cost.
    conn.execute(
        "INSERT OR REPLACE INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)"
        " VALUES ('claude (main)', 'claude', 0, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT OR REPLACE INTO sessions"
        " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
        "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
        " VALUES ('sess-abc', 'claude', 'claude (main)', NULL, 'cli', '/tmp', NULL,"
        "  0, NULL, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 'closed')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES ('ev-abc', 'sess-abc', 'claude (main)', 'claude-sonnet-4-6',"
        "  '2026-01-01T00:00:00+00:00', 100, 0, 0, 50, NULL, NULL, 0)"
    )
    conn.commit()

    dao_instance = TelemetryDao(conn)

    def _dao_factory() -> TelemetryDao:
        return dao_instance

    svc = TelemetryService(
        dao_factory=_dao_factory,
        aggregator=_FakeAggregator(),
        reader_factory=lambda: (_FakeClaudeReader(), _FakeCodexReader(), _FakeWorkflowsReader()),
        pricing_module=_FakePricing(),
        workspace_root=tmp_path,
        state_dir=tmp_path / "state",
        spec_context_service=_FakeSCS(),
    )

    svc.refresh()

    # Check that cost_micro_usd is now set.
    row = conn.execute("SELECT cost_micro_usd FROM events WHERE event_id = 'ev-abc'").fetchone()
    assert row[0] is not None
    assert row[0] > 0
