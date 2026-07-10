"""T-016-02: `is_stale` branch table (8 rows, all FakeClock, zero real datetime.now)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

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


@pytest.mark.parametrize(
    ("record", "clock_dt", "expected"),
    [
        pytest.param(None, BASE, True, id="row1-none-is-stale"),
        pytest.param({}, BASE, True, id="row2-missing-fields-is-stale"),
        pytest.param(
            {"heartbeat": "not-a-date", "ttl": 1800},
            BASE,
            True,
            id="row3-corrupt-heartbeat-is-stale",
        ),
        pytest.param(
            rec((BASE - timedelta(seconds=1)).isoformat()),
            BASE,
            False,
            id="row4-fresh-heartbeat-not-stale",
        ),
        pytest.param(
            rec((BASE - timedelta(seconds=1800)).isoformat()),
            BASE,
            True,
            id="row5-boundary-exact-ttl-is-stale",  # boundary inclusive (>=)
        ),
        pytest.param(
            rec((BASE - timedelta(seconds=1801)).isoformat()),
            BASE,
            True,
            id="row6-past-ttl-is-stale",
        ),
        pytest.param(
            rec(BASE.isoformat()),
            BASE + timedelta(seconds=100),
            False,
            id="row7a-injected-clock-fresh",
        ),
        pytest.param(
            rec(BASE.isoformat()),
            BASE + timedelta(seconds=2000),
            True,
            id="row7b-injected-clock-stale",
        ),
        pytest.param(rec(BASE.isoformat(), ttl=0), BASE, True, id="row8-ttl-zero-is-stale"),
    ],
)
def test_is_stale_branch_table(
    record: dict[str, object] | None, clock_dt: datetime, expected: bool
) -> None:
    assert is_stale(record, clock=fixed(clock_dt)) is expected
