"""T-016-12: AC-19 short-heartbeat E2E triad (D1 + OQ-1 operator decision 2026-06-06).

Three behaviors asserted — all using FakeClock, tmp_path workspace, no real time.sleep:

(a) test_relaunched_same_identity_renews
    Simulate relaunched session with same session_id (.ptr file contains my_session_id).
    acquire() with a lock record showing a foreign-looking session_id → RENEW (ALLOW).
    No freeze, no block.

(b) test_abandoned_foreign_lease_reclaims_after_ttl
    Lock record heartbeat set to now − LEASE_TTL_SECONDS − 1 via FakeClock.
    acquire() from a different session (no .ptr match) → succeeds (reclaim: ACQUIRED).
    Parameterised: elapsed = LEASE_TTL_SECONDS + 1 → stale; elapsed = LEASE_TTL_SECONDS − 1 → live.

(c) test_live_foreign_yields_informatively
    Lock record heartbeat fresh (now). acquire() from different session (no .ptr) →
    raises LockHeldError with informative yield-iff-live-foreign message.
    Message does NOT contain "bind --mode write" / "relaunch" / routine "lock steal".
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.core.kernel_tunables import LEASE_TTL_SECONDS
from dadaia_workspace.features.spec_context import lease

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "triad-ctx"
MY_SESSION = "my-session-abc123"
FOREIGN_SESSION = "foreign-session-xyz"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _make_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace structure under tmp_path."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions" / "runtime").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True, exist_ok=True)
    return ws


def _seed_lock(
    ws: Path, session_id: str, heartbeat: datetime, ttl: int = LEASE_TTL_SECONDS
) -> None:
    """Write a lock record directly (bypass CAS, for test setup only)."""
    path = lease._record_path(ws, CTX)
    path.write_text(
        json.dumps(
            {
                "context": CTX,
                "release": "v0.1.6",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": ttl,
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# (a) Relaunched same-identity → RENEW
# ---------------------------------------------------------------------------


def test_relaunched_same_identity_renews(tmp_path: Path) -> None:
    """AC-19(a): relaunched session with same session_id (.ptr matches) → RENEW; no freeze.

    Simulates a session that was relaunched and the lock record now shows a
    foreign-looking session_id (due to env var drift or process restart). With
    a matching .ptr, acquire() recognises the caller as the incumbent and RENEWs.
    FakeClock used; no time.sleep.
    """
    ws = _make_workspace(tmp_path)
    # Seed the lock record with a "foreign-looking" session_id (simulating relaunch drift).
    _seed_lock(ws, "old-looking-session-id", BASE)
    # Write .ptr for MY_SESSION — signals MY_SESSION is the incumbent for this context.
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")

    status, rec = lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))

    assert status == "RENEWED", (
        f"Relaunched session with matching .ptr must RENEW; got {status!r}. "
        "No freeze, no block (AC-19a, D1 soul-fold)."
    )
    assert rec["session_id"] == MY_SESSION, (
        f"Lock record session_id must be updated to '{MY_SESSION}'"
    )
    # .ptr must still be present and unchanged.
    assert ptr.read_text(encoding="utf-8").strip() == MY_SESSION


# ---------------------------------------------------------------------------
# (b) Abandoned foreign lease reclaims after TTL (parameterised boundary)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed_seconds", "expected_status"),
    [
        (LEASE_TTL_SECONDS + 1, "ACQUIRED"),  # stale: elapsed > TTL → reclaim
        (LEASE_TTL_SECONDS - 1, None),  # live: elapsed < TTL → block (LockHeldError)
    ],
    ids=["stale_reclaims", "live_blocks"],
)
def test_abandoned_foreign_lease_reclaims_after_ttl(
    elapsed_seconds: int, expected_status: str | None, tmp_path: Path
) -> None:
    """AC-19(b): abandoned foreign lease (heartbeat set via FakeClock) reclaims at TTL+1 boundary.

    Uses FakeClock to advance time by elapsed_seconds past the heartbeat.
    - elapsed = LEASE_TTL_SECONDS + 1 → stale → ACQUIRED (reclaim).
    - elapsed = LEASE_TTL_SECONDS - 1 → live → LockHeldError (yield-iff-live-foreign).
    The constant LEASE_TTL_SECONDS (120) is the sole boundary reference.
    """
    ws = _make_workspace(tmp_path)
    # Heartbeat is fixed at BASE; FakeClock reports "now" as BASE + elapsed_seconds.
    heartbeat = BASE
    now = BASE + timedelta(seconds=elapsed_seconds)
    _seed_lock(ws, FOREIGN_SESSION, heartbeat)
    # No .ptr for MY_SESSION.

    if expected_status == "ACQUIRED":
        status, _rec = lease.acquire(
            ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(now)
        )
        assert status == "ACQUIRED", (
            f"Elapsed={elapsed_seconds}s (> LEASE_TTL_SECONDS={LEASE_TTL_SECONDS}): "
            f"stale lease must be reclaimed (ACQUIRED); got {status!r}"
        )
        # New record carries MY_SESSION.
        updated = lease.read_record(ws, CTX)
        assert updated is not None and updated.get("session_id") == MY_SESSION
    else:
        # Live: expect LockHeldError.
        raised = False
        try:
            lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(now))
        except LockHeldError:
            raised = True
        assert raised, (
            f"Elapsed={elapsed_seconds}s (< LEASE_TTL_SECONDS={LEASE_TTL_SECONDS}): "
            "live foreign lease must block with LockHeldError (yield-iff-live-foreign)"
        )


# ---------------------------------------------------------------------------
# (c) Live foreign → informative yield message; no routine steal/relaunch/bind
# ---------------------------------------------------------------------------


def test_live_foreign_yields_informatively(tmp_path: Path) -> None:
    """AC-19(c): live foreign lease → yield-iff-live-foreign message; no routine instructions.

    Message must:
    - Be non-empty and contain the foreign session_id.
    - NOT contain "bind --mode write".
    - NOT contain "relaunch".
    - If "lock steal" appears: only in conditional form ("only if you are certain it is dead").
    """
    ws = _make_workspace(tmp_path)
    # Fresh lock (heartbeat = BASE, now = BASE → elapsed = 0 → live).
    _seed_lock(ws, FOREIGN_SESSION, BASE)
    # No .ptr for MY_SESSION.

    msg = ""
    raised = False
    try:
        lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))
    except LockHeldError as exc:
        msg = str(exc)
        raised = True

    assert raised, "Live foreign lease must raise LockHeldError (yield-iff-live-foreign, AC-19c)"
    assert msg, "Yield-iff-live-foreign block must produce a non-empty, actionable message"
    assert "bind --mode write" not in msg, (
        "AC-17: yield message must NOT contain 'bind --mode write'"
    )
    assert "relaunch" not in msg, "AC-17: yield message must NOT contain 'relaunch'"
    assert "lock steal" not in msg, (
        "AC-17 / operator forbidden-law: yield message must NOT mention 'lock steal' "
        "at all — reclaim-iff-stale auto-frees a dead holder after the heartbeat window, "
        "so there is no manual unblock ceremony"
    )
    # Message should reference the foreign session for debuggability.
    assert FOREIGN_SESSION in msg or "actively mutating" in msg, (
        "Yield message must be informative (reference the holder or state)"
    )
