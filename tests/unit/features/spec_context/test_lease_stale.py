"""T-016-02: `is_stale` branch table (8 rows, all FakeClock, zero real datetime.now)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from dadaia_workspace.core.lock_liveness import is_stale

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def rec(heartbeat: str, ttl: int = 1800) -> dict[str, object]:
    return {
        "context": "c",
        "release": "r",
        "session_id": "s",
        "mode": "IMPLEMENTATION",
        "acquired_at": heartbeat,
        "heartbeat": heartbeat,
        "ttl": ttl,
    }


def test_row1_none_is_stale() -> None:
    assert is_stale(None, clock=fixed(BASE)) is True


def test_row2_missing_fields_is_stale() -> None:
    assert is_stale({}, clock=fixed(BASE)) is True


def test_row3_corrupt_heartbeat_is_stale() -> None:
    assert is_stale({"heartbeat": "not-a-date", "ttl": 1800}, clock=fixed(BASE)) is True


def test_row4_fresh_heartbeat_not_stale() -> None:
    hb = (BASE - timedelta(seconds=1)).isoformat()
    assert is_stale(rec(hb), clock=fixed(BASE)) is False


def test_row5_boundary_exact_ttl_is_stale() -> None:
    hb = (BASE - timedelta(seconds=1800)).isoformat()
    assert is_stale(rec(hb), clock=fixed(BASE)) is True  # boundary inclusive (>=)


def test_row6_past_ttl_is_stale() -> None:
    hb = (BASE - timedelta(seconds=1801)).isoformat()
    assert is_stale(rec(hb), clock=fixed(BASE)) is True


def test_row7_injected_clock_is_deterministic() -> None:
    r = rec(BASE.isoformat())
    assert is_stale(r, clock=fixed(BASE + timedelta(seconds=100))) is False
    assert is_stale(r, clock=fixed(BASE + timedelta(seconds=2000))) is True


def test_row8_ttl_zero_is_stale() -> None:
    assert is_stale(rec(BASE.isoformat(), ttl=0), clock=fixed(BASE)) is True
