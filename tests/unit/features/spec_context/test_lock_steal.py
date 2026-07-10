"""Unit tests for lease.steal — audit logging + absent-record handling (T-016-05).

The stale/fresh TTL decision rows are covered by test_lease_pid_liveness.py (the
gate-side pid-veto decision table) and test_lease_main_probe.py (the CLI-wiring
proof) — kept there as the single owner to avoid duplicated coverage. This file
keeps the two facets unique to ``steal`` itself: absence-as-stale creation, and the
audit trail a successful steal writes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.features.spec_context.lease import _record_path, steal


class FakeClock:
    """Injectable wall-clock for deterministic TTL tests."""

    def __init__(self, dt: datetime) -> None:
        self._dt = dt

    def __call__(self) -> datetime:
        return self._dt

    def advance(self, **kwargs: int | float) -> FakeClock:
        """Return a new FakeClock advanced by the given timedelta kwargs."""
        return FakeClock(self._dt + timedelta(**kwargs))


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    return ws


def _write_record(ws: Path, ctx: str, data: dict[str, object]) -> Path:
    path = _record_path(ws, ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _make_record(
    ctx: str,
    session_id: str,
    *,
    heartbeat: datetime,
    ttl: int = 1800,
    release: str = "v0.1.6",
    mode: str = "BOUND_IMPLEMENTATION",
) -> dict[str, object]:
    now_iso = heartbeat.isoformat()
    return {
        "context": ctx,
        "release": release,
        "session_id": session_id,
        "mode": mode,
        "acquired_at": now_iso,
        "heartbeat": now_iso,
        "ttl": ttl,
    }


def test_steal_absent_record_creates_new(tmp_path: Path) -> None:
    """No record at all → steal treats absence as stale and creates a new record."""
    ws = _make_workspace(tmp_path)
    ctx = "newctx"
    clock_now = FakeClock(datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))

    new_session = "fresh-sess"
    ok, rec = steal(ws, ctx, new_session, clock=clock_now)

    assert ok is True
    assert rec is not None
    assert rec.get("session_id") == new_session


def test_steal_audit_log_written_on_success(tmp_path: Path) -> None:
    """A successful steal appends an audit entry to lock-events.jsonl."""
    ws = _make_workspace(tmp_path)
    ctx = "auditctx"
    ttl = 1800
    clock_now = FakeClock(datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))
    stale_hb = clock_now._dt - timedelta(seconds=ttl + 60)

    old_rec = _make_record(ctx, "old-sess", heartbeat=stale_hb, ttl=ttl)
    old_rec["heartbeat"] = stale_hb.isoformat()
    _write_record(ws, ctx, old_rec)

    ok, _ = steal(ws, ctx, "new-sess", clock=clock_now)
    assert ok is True

    log_path = ws / ".dadaia" / "logs" / "lock-events.jsonl"
    assert log_path.exists(), "Audit log not created after steal"
    events = [json.loads(ln)["event"] for ln in log_path.read_text().splitlines() if ln.strip()]
    assert "steal" in events, f"Expected 'steal' event in audit log, got: {events}"
