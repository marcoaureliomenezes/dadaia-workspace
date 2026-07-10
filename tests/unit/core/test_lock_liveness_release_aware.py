"""T-43-10 — release-aware lease reclaim (bug lease-pid-veto-ignores-archived-release, AC-8).

The pid-veto in :func:`lock_liveness.is_stale` is release-agnostic by default: a TTL-expired
lease whose holder pid is still alive is treated as live (not stale), so it is never stolen.
That deadlocks the next release when an idle-but-alive session keeps a lease pinned to a
now-archived release. The fix threads the context's ACTIVE release into the verdict: a lease
pinned to a NON-active release is reclaimable regardless of pid, while a lease on the live
ACTIVE release keeps the pid-veto (no false steal).

These tests cover both the pure predicate and the ``lease.steal`` reclaim path, and preserve
the legacy (``active_release is None``) behavior.

CRIT: lease pid-veto vs release-aware reclaim. Both tables below keep every row — this is
the no-steal/no-deadlock boundary. The two ``lease.steal`` execution-path tests are kept
standalone (the executed reclaim path, not just the pure predicate).
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


def _rec(release: str | None, *, pid: int = 4321) -> dict[str, object]:
    base: dict[str, object] = {
        "heartbeat": _HB.isoformat(),
        "ttl": _TTL,
        "pid": pid,
        "session_id": "holder-sess",
    }
    if release is not None:
        base["release"] = release
    return base


def _alive(_pid: int) -> bool:
    return True


def _dead(_pid: int) -> bool:
    return False


# ---------------------------------------------------------------------------
# AC-8 (a) — a lease is reclaimable when pinned to a non-active release (any
# active_release value), the pid is dead, or there is no pid probe at all.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "release", "pid_probe", "active_release"),
    [
        ("archived_v0143_active", "v0.1.41", _alive, "v0.1.43"),
        ("archived_none_active", "v0.1.41", _alive, "none"),
        ("archived_empty_active", "v0.1.41", _alive, ""),
        # A dead holder is reclaimable on the plain TTL verdict regardless of release.
        ("dead_pid_archived_release", "v0.1.41", _dead, "v0.1.43"),
        # pid_probe=None ⇒ TTL-only verdict (reclaimable); release bypass is moot but
        # consistent.
        ("no_probe_archived_release", "v0.1.41", None, "v0.1.43"),
    ],
)
def test_reclaim_table(name: str, release: str, pid_probe: object, active_release: str) -> None:
    rec = _rec(release)
    kwargs: dict[str, object] = {"clock": _stale_clock, "active_release": active_release}
    if pid_probe is not None:
        kwargs["pid_probe"] = pid_probe
    assert lock_liveness.is_stale(rec, **kwargs) is True  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-8 (b) + backward-compat — every case where the pid-veto STILL HOLDS (no false
# steal): live-ACTIVE-release, legacy None active_release, TTL-fresh record, no
# release field, empty release field.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "rec_fn", "clock_fn", "active_release"),
    [
        # A lease pinned to the live ACTIVE release is STILL pid-vetoed.
        ("active_release_lease", lambda: _rec("v0.1.43"), _stale_clock, "v0.1.43"),
        # active_release=None ⇒ release-agnostic pid-veto, exactly as before.
        ("legacy_none_active_release", lambda: _rec("v0.1.41"), _stale_clock, None),
        # A TTL-fresh record stays live even when its release differs from the active
        # one.
        ("fresh_record_never_stale", lambda: _rec("v0.1.41"), lambda: _HB, "v0.1.43"),
        # A legacy record carrying no release field still gets the pid-veto (nothing to
        # compare).
        (
            "no_release_field",
            lambda: {"heartbeat": _HB.isoformat(), "ttl": _TTL, "pid": 4321, "session_id": "x"},
            _stale_clock,
            "v0.1.43",
        ),
        # An empty-string release is not a release pin → pid-veto applies (no bypass).
        ("empty_release_field", lambda: _rec(""), _stale_clock, "v0.1.43"),
    ],
)
def test_veto_holds_table(
    name: str, rec_fn: object, clock_fn: object, active_release: str | None
) -> None:
    rec = rec_fn()  # type: ignore[operator]
    kwargs: dict[str, object] = {"clock": clock_fn, "pid_probe": _alive}
    if active_release is not None:
        kwargs["active_release"] = active_release
    assert lock_liveness.is_stale(rec, **kwargs) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-8 — lease.steal reclaim path is release-aware (the executed reclaim path, not
# just the pure predicate).
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
