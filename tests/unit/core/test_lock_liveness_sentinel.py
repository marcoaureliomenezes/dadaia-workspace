"""Veto-release decoupling at the acquire seam (v0.1.50 FR1 — audit F-3).

An UNREADABLE ACTIVE.md (I/O failure) must never weaken the pid-veto: the gate
passes ``active_release=None`` (veto-preserving) while still writing a ``"none"``
record release. A READABLE "none" (between releases, or a fresh context with no
ACTIVE.md) keeps the legitimate release-aware reclaim — the frozen
``test_lock_liveness_release_aware`` contract is untouched.

CRIT: an I/O failure reading ACTIVE.md must never weaken the veto (audit F-3).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.features.spec_context import lease

pytestmark = pytest.mark.unit

_TTL = 120
_T0 = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _old_clock() -> datetime:
    return _T0


def _now_clock() -> datetime:
    return _T0 + timedelta(seconds=_TTL + 30)


def _alive(_pid: int) -> bool:
    return True


def _seed_stale_foreign_holder(workspace: Path) -> None:
    """A TTL-stale holder pinned to a real release, its pid demonstrably alive."""
    status, _ = lease.acquire(
        workspace,
        "ctx",
        "holder-sess",
        "v0.1.50",
        "implementation",
        clock=_old_clock,
        pid_probe=_alive,
        pid=1111,
    )
    assert status == "ACQUIRED"


def test_unreadable_active_preserves_pid_veto(tmp_path: Path) -> None:
    """active_release=None (unreadable ACTIVE.md) ⇒ the live-pid veto HOLDS."""
    _seed_stale_foreign_holder(tmp_path)

    with pytest.raises(LockHeldError):
        lease.acquire(
            tmp_path,
            "ctx",
            "intruder-sess",
            "none",
            "implementation",
            clock=_now_clock,
            pid_probe=_alive,
            pid=2222,
            active_release=None,
        )


@pytest.mark.parametrize(
    ("name", "next_release"),
    [
        # Legit 'none' (readable ACTIVE, no active release) keeps release-aware reclaim.
        ("readable_none_release", "none"),
        # Release-aware reclaim (T-43-10) untouched for REAL SemVer mismatches.
        ("real_release_mismatch", "v0.1.51"),
    ],
)
def test_readable_active_release_still_reclaims(
    tmp_path: Path, name: str, next_release: str
) -> None:
    _seed_stale_foreign_holder(tmp_path)

    status, rec = lease.acquire(
        tmp_path,
        "ctx",
        "next-sess",
        next_release,
        "implementation",
        clock=_now_clock,
        pid_probe=_alive,
        pid=2222,
    )
    assert status == "ACQUIRED"
    assert rec["session_id"] == "next-sess"
