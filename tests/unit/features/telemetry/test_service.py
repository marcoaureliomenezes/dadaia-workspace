"""Tests for TelemetryService (T-AM-12, K8 constructor: store/readers/clock).

All tests use fakes injected via DI — no real filesystem paths, no real
operator data.
"""

from __future__ import annotations

import os
import pathlib
import time
from datetime import date
from typing import Any

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.features.telemetry.service import TelemetryService  # noqa: E402
from dadaia_workspace.features.telemetry.store import TelemetryStore  # noqa: E402


class _FakeSCS:
    def list_all(self) -> list[Any]:
        return []


class _FakePricing:
    class _Row:
        def __init__(self, effective_from: date) -> None:
            self.effective_from = effective_from

    PRICING_TABLE: dict[str, list[_FakePricing._Row]] = {
        "claude-sonnet-4-6": [_Row(date(2025, 1, 1))],
    }

    @staticmethod
    def compute_cost(usage: dict[str, int], model: str, when: date) -> int | None:
        if model not in ("claude-sonnet-4-6",):
            return None
        tok = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return tok * 3  # arbitrary deterministic value


class _FakeReader:
    """Implements Reader.ingest(store, now) — the K8 protocol."""

    def __init__(self) -> None:
        self.call_count = 0

    def ingest(self, store: TelemetryStore, now: str) -> None:
        self.call_count += 1


class _FakeAggregator:
    def __init__(self) -> None:
        self.list_agents_call_count = 0

    def list_agents(self, **kwargs: Any) -> list[Any]:
        self.list_agents_call_count += 1
        return []

    def list_sessions_by_agent(self, agent_id: str, **kwargs: Any) -> list[Any]:
        return []

    def aggregate_sessions(self, **kwargs: Any) -> Any:
        return None


class _FakeRefreshLock:
    """Fake TelemetryRefreshLock that always acquires successfully."""

    def __init__(self, *, always_fail: bool = False) -> None:
        self.acquire_call_count = 0
        self.release_call_count = 0
        self._always_fail = always_fail

    def try_acquire(self, lock_path: str) -> bool:
        self.acquire_call_count += 1
        return not self._always_fail

    def release(self) -> None:
        self.release_call_count += 1


def _make_service(
    *,
    state_dir: pathlib.Path,
    workspace_root: pathlib.Path,
    db_path: pathlib.Path | None = None,
    pricing: Any | None = None,
    aggregator: Any | None = None,
    reader: _FakeReader | None = None,
    refresh_lock: Any | None = None,
    clock: Any = None,
    getuid_fn: Any = None,
) -> tuple[TelemetryService, _FakeReader]:
    r = reader or _FakeReader()
    pricing_mod = pricing or _FakePricing()
    agg = aggregator or _FakeAggregator()
    store = TelemetryStore(db_path or (state_dir / "telemetry.sqlite"))

    svc = TelemetryService(
        store,
        (r,),
        clock or time.monotonic,
        aggregator=agg,
        pricing_module=pricing_mod,
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=_FakeSCS(),
        refresh_lock=refresh_lock,
        _getuid_fn=getuid_fn,
    )
    return svc, r


def test_refuses_uid_zero(tmp_path: pathlib.Path) -> None:
    """TelemetryService constructor raises PermissionError when uid=0."""
    with pytest.raises(PermissionError, match="root"):
        _make_service(
            state_dir=tmp_path / "state",
            workspace_root=tmp_path,
            getuid_fn=lambda: 0,
        )


def test_refresh_ttl_concurrency_and_di_lock_matrix(tmp_path: pathlib.Path) -> None:
    # TTL cache: calling refresh twice within TTL skips a second ingest cycle.
    # Clock starts well above CACHE_TTL_SECONDS (30) so the first refresh is
    # never mistaken for a cache hit against the _last_refresh=0.0 initial value.
    _time = [100.0]

    def _fake_now() -> float:
        return _time[0]

    svc, r = _make_service(
        state_dir=tmp_path / "ttl" / "state",
        workspace_root=tmp_path / "ttl",
        clock=_fake_now,
    )
    svc.refresh()
    first_count = r.call_count
    assert first_count == 1
    _time[0] = 110.0  # +10s, < 30s TTL
    svc.refresh()
    assert r.call_count == first_count

    # readers: refresh() calls the reader at least once.
    svc2, r2 = _make_service(
        state_dir=tmp_path / "readers" / "state",
        workspace_root=tmp_path / "readers",
    )
    svc2.refresh()
    assert r2.call_count >= 1

    # concurrent refresh: a lock held externally means no readers run.
    import fcntl

    state_dir = tmp_path / "concurrent" / "state"
    state_dir.mkdir(parents=True)
    lock_path = state_dir / "telemetry.lock"
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        svc3, r3 = _make_service(state_dir=state_dir, workspace_root=tmp_path / "concurrent")
        svc3.refresh()
        assert r3.call_count == 0
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

    # list_agents passthrough: triggers refresh and delegates to the aggregator.
    fake_agg = _FakeAggregator()
    svc4, _ = _make_service(
        state_dir=tmp_path / "passthrough" / "state",
        workspace_root=tmp_path / "passthrough",
        aggregator=fake_agg,
    )
    svc4.list_agents()
    assert fake_agg.list_agents_call_count == 1

    # DI refresh_lock: injected lock is used (acquire+release) and its failure skips readers.
    fake_lock = _FakeRefreshLock()
    svc5, r5 = _make_service(
        state_dir=tmp_path / "dilock" / "state",
        workspace_root=tmp_path / "dilock",
        refresh_lock=fake_lock,
    )
    svc5.refresh()
    assert fake_lock.acquire_call_count == 1
    assert fake_lock.release_call_count == 1
    assert r5.call_count == 1

    fake_lock_fail = _FakeRefreshLock(always_fail=True)
    svc6, r6 = _make_service(
        state_dir=tmp_path / "dilockfail" / "state",
        workspace_root=tmp_path / "dilockfail",
        refresh_lock=fake_lock_fail,
    )
    svc6.refresh()
    assert r6.call_count == 0
    assert fake_lock_fail.release_call_count == 0


def test_cost_backfill(tmp_path: pathlib.Path) -> None:
    """refresh() fills cost_micro_usd for events with known model and NULL cost."""
    db_file = tmp_path / "backfill.sqlite"

    seed = TelemetryStore(db_file)
    seed.open_write()
    seed.migrate()
    seed._conn.execute(  # noqa: SLF001 — test-only seed via raw SQL
        "INSERT OR REPLACE INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)"
        " VALUES ('claude (main)', 'claude', 0, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
    )
    seed._conn.execute(  # noqa: SLF001
        "INSERT OR REPLACE INTO sessions"
        " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
        "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
        " VALUES ('sess-abc', 'claude', 'claude (main)', NULL, 'cli', '/tmp', NULL,"
        "  0, NULL, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 'closed')"
    )
    seed._conn.execute(  # noqa: SLF001
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES ('ev-abc', 'sess-abc', 'claude (main)', 'claude-sonnet-4-6',"
        "  '2026-01-01T00:00:00+00:00', 100, 0, 0, 50, NULL, NULL, 0)"
    )
    seed.commit()
    seed.close()

    svc, _ = _make_service(
        state_dir=tmp_path / "state",
        workspace_root=tmp_path,
        db_path=db_file,
    )

    svc.refresh()

    check = TelemetryStore(db_file)
    read_conn = check.open_read()
    try:
        row = read_conn.execute(
            "SELECT cost_micro_usd FROM events WHERE event_id = 'ev-abc'"
        ).fetchone()
    finally:
        read_conn.close()
    assert row[0] is not None
    assert row[0] > 0
