"""T-43-10 — release-aware lease reclaim (bug lease-pid-veto-ignores-archived-release, AC-8).

The pid-veto in :func:`lock_liveness.is_stale` is release-agnostic by default: a TTL-expired
lease whose holder pid is still alive is treated as live (not stale), so it is never stolen.
That deadlocks the next release when an idle-but-alive session keeps a lease pinned to a
now-archived release. The fix threads the context's ACTIVE release into the verdict: a lease
pinned to a NON-active release is reclaimable regardless of pid, while a lease on the live
ACTIVE release keeps the pid-veto (no false steal).

These tests cover both the pure predicate and the ``lease.steal`` reclaim path, and preserve
the legacy (``active_release is None``) behavior.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import lock_liveness
from dadaia_workspace.features.spec_context import lease

_TTL = 120
_HB = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _stale_clock() -> datetime:
    """A clock well past the heartbeat + TTL → the record is TTL-stale."""
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


def _dead(_pid: int) -> bool:
    return False


# ---------------------------------------------------------------------------
# AC-8 (a) — archived/non-ACTIVE-release lease with a LIVE pid is reclaimable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("active", ["v0.1.43", "none", ""])
def test_archived_release_lease_reclaimable_despite_live_pid(active: str) -> None:
    rec = _rec("v0.1.41")  # pinned to a closed/archived release
    assert (
        lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_alive, active_release=active)
        is True
    )


# ---------------------------------------------------------------------------
# AC-8 (b) — live-ACTIVE-release lease with a LIVE pid is STILL pid-vetoed
# ---------------------------------------------------------------------------


def test_active_release_lease_still_pid_vetoed() -> None:
    rec = _rec("v0.1.43")  # pinned to the live ACTIVE release
    assert (
        lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_alive, active_release="v0.1.43")
        is False
    )


# ---------------------------------------------------------------------------
# Backward-compat + edge cases (preserve existing is_stale semantics)
# ---------------------------------------------------------------------------


def test_legacy_none_active_release_keeps_pid_veto() -> None:
    """active_release=None ⇒ release-agnostic pid-veto, exactly as before."""
    rec = _rec("v0.1.41")
    assert lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_alive) is False


def test_release_bypass_never_makes_fresh_record_stale() -> None:
    """A TTL-fresh record stays live even when its release differs from the active one."""
    rec = _rec("v0.1.41")
    assert (
        lock_liveness.is_stale(rec, clock=lambda: _HB, pid_probe=_alive, active_release="v0.1.43")
        is False
    )


def test_dead_pid_archived_release_reclaimable() -> None:
    """A dead holder is reclaimable on the plain TTL verdict regardless of release."""
    rec = _rec("v0.1.41")
    assert (
        lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_dead, active_release="v0.1.43")
        is True
    )


def test_record_without_release_field_keeps_pid_veto() -> None:
    """A legacy record carrying no release field still gets the pid-veto (nothing to compare)."""
    rec = {"heartbeat": _HB.isoformat(), "ttl": _TTL, "pid": 4321, "session_id": "x"}
    assert (
        lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_alive, active_release="v0.1.43")
        is False
    )


def test_empty_release_field_keeps_pid_veto() -> None:
    """An empty-string release is not a release pin → pid-veto applies (no bypass)."""
    rec = _rec("")
    assert (
        lock_liveness.is_stale(rec, clock=_stale_clock, pid_probe=_alive, active_release="v0.1.43")
        is False
    )


def test_no_probe_archived_release_reclaimable() -> None:
    """pid_probe=None ⇒ TTL-only verdict (reclaimable); release bypass is moot but consistent."""
    rec = _rec("v0.1.41")
    assert lock_liveness.is_stale(rec, clock=_stale_clock, active_release="v0.1.43") is True


# ---------------------------------------------------------------------------
# AC-8 — lease.steal reclaim path is release-aware
# ---------------------------------------------------------------------------


def _plant_record(workspace: Path, ctx: str, record: dict[str, object]) -> None:
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def test_steal_reclaims_archived_release_lease_with_live_pid(tmp_path: Path) -> None:
    ctx = "dadaia-workspace"
    _plant_record(tmp_path, ctx, _rec("v0.1.41"))
    ok, _rec_after = lease.steal(
        tmp_path,
        ctx,
        "new-session",
        clock=_stale_clock,
        pid_probe=_alive,
        active_release="v0.1.43",
        pid=99999,
    )
    assert ok is True
    held = lease.read_record(tmp_path, ctx)
    assert held is not None
    assert held["session_id"] == "new-session"


def test_steal_refuses_active_release_lease_with_live_pid(tmp_path: Path) -> None:
    ctx = "dadaia-workspace"
    _plant_record(tmp_path, ctx, _rec("v0.1.43"))
    ok, rec_after = lease.steal(
        tmp_path,
        ctx,
        "new-session",
        clock=_stale_clock,
        pid_probe=_alive,
        active_release="v0.1.43",
        pid=99999,
    )
    assert ok is False
    assert rec_after is not None
    assert rec_after["session_id"] == "holder-sess"  # untouched — no false steal
