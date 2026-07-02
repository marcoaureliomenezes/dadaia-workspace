"""`is_stale` sentinel tolerance for `active_release` (v0.1.50 FR1 — audit F-3).

`hooks/sdd_gate.py` degrades an unreadable ACTIVE.md to the *string* ``"none"``;
that sentinel must never enter the release-mismatch reclaim branch, or an I/O
failure bypasses the pid-veto and a live holder becomes stealable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from dadaia_workspace.core import lock_liveness

pytestmark = pytest.mark.unit

_TTL = 120
_HB = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _stale_clock() -> datetime:
    return _HB + timedelta(seconds=_TTL + 30)


def _rec(release: str, *, pid: int = 4321) -> dict[str, object]:
    return {
        "heartbeat": _HB.isoformat(),
        "ttl": _TTL,
        "pid": pid,
        "session_id": "holder-sess",
        "release": release,
    }


def _alive(_pid: int) -> bool:
    return True


@pytest.mark.parametrize("sentinel", ["none", ""])
def test_sentinel_active_release_preserves_pid_veto(sentinel: str) -> None:
    """A sentinel active_release is treated as None: the live-pid veto holds."""
    verdict = lock_liveness.is_stale(
        _rec("v0.1.50"),
        clock=_stale_clock,
        pid_probe=_alive,
        active_release=sentinel,
    )
    assert verdict is False


def test_real_release_mismatch_still_reclaims() -> None:
    """Release-aware reclaim (T-43-10) is untouched for REAL SemVer mismatches."""
    verdict = lock_liveness.is_stale(
        _rec("v0.1.50"),
        clock=_stale_clock,
        pid_probe=_alive,
        active_release="v0.1.51",
    )
    assert verdict is True
