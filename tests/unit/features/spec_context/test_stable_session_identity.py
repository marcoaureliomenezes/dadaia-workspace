"""T-016-11: Stable session identity via .ptr file mechanism (D1 soul-fold, FR-P1-15).

Acceptance criteria tested:
    AC-15 — .ptr created on first acquire; matching session_id → RENEW.
    AC-17 — Yield message does not contain "bind --mode write" / "relaunch" as routine.
    AC-18 — doctor --fix removes orphan .ptr files (no corresponding live lock record).
    AC-19(a) — Relaunched same-identity → RENEW (test_relaunched_same_identity_renews
               is in test_short_heartbeat_triad.py as the AC-19 triad).

All tests use FakeClock; tmp_path workspace; no real time.sleep in test bodies.

Re-classification note (T-011-04 / FR-W1-04, ADR-8 amended): SESSION-record (bind) GC
TTL semantics changed to measure against the heartbeat-renewed ``last_seen_at`` (with
TTL-from-creation fallback for pre-heartbeat records), not the bind-CLI pid. The cases
in THIS module concern the LEASE record (``ctx_locks/<ctx>.lock.json``) and its ``.ptr``
incumbent pointer — a distinct artifact whose liveness is the lease ``heartbeat`` + the
pid veto (T-011-01/02). They are unaffected by the bind ``last_seen_at`` change and remain
asserted as-is here; the bind-record ``last_seen_at`` GC is covered in test_doctor_gc.py.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
from collections.abc import Callable  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.kernel_tunables import LEASE_TTL_SECONDS  # noqa: E402
from dadaia_workspace.features.spec_context import lease  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"
MY_SESSION = "my-session-id"
OTHER_SESSION = "foreign-session-id"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir(parents=True)
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions" / "runtime").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True, exist_ok=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path) -> DoctorService:
    return DoctorService(
        context_store=FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _seed_lock(workspace: Path, session_id: str, heartbeat: datetime) -> None:
    """Write a lock record directly (bypassing CAS, for test setup)."""
    path = lease._record_path(workspace, CTX)
    path.write_text(
        json.dumps(
            {
                "context": CTX,
                "release": "v0.1.6",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": LEASE_TTL_SECONDS,
            }
        ),
        encoding="utf-8",
    )


def test_ptr_match_renews_against_live_foreign_looking_lock(tmp_path: Path) -> None:
    """Acquire when .ptr matches my_session_id and lock record has foreign+live session → RENEW.

    This is the stable-identity scenario: the .ptr recognises the caller as the
    incumbent even though the lock record was written under a different session_id
    (e.g. after a relaunch that changed the session env var).
    """
    ws = _make_workspace(tmp_path)
    _seed_lock(ws, "old-session-that-looks-foreign", BASE)
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")

    status, rec = lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))

    assert status == "RENEWED", f"Incumbent session recognised via .ptr must RENEW, got {status!r}"
    assert rec["session_id"] == MY_SESSION, (
        f"Lock record session_id must be updated to '{MY_SESSION}'"
    )


def test_yield_message_has_no_steal_ceremony(tmp_path: Path) -> None:
    """No-.ptr-match + live foreign lease raises LockHeldError (yield-iff-live-foreign),
    and the message contains NO manual unblock ceremony.

    Operator forbidden-law: the message must never mention 'bind --mode write',
    'relaunch', or 'lock steal' — not even conditionally. reclaim-iff-stale frees a
    finished/dead holder automatically after the heartbeat window, so no manual step
    is ever required.
    """
    from dadaia_workspace.core.exceptions import LockHeldError

    ws = _make_workspace(tmp_path)
    _seed_lock(ws, OTHER_SESSION, BASE)

    msg = ""
    try:
        lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))
    except LockHeldError as exc:
        msg = str(exc)

    assert msg, "Yield-iff-live-foreign block must produce a non-empty message"
    for forbidden in ("bind --mode write", "relaunch", "lock steal"):
        assert forbidden not in msg, f"Yield message must NOT contain {forbidden!r}"


def test_ptr_lifecycle_and_gc_matrix(tmp_path: Path) -> None:
    """.ptr creation on first acquire, no-.ptr fall-through to a normal block, and the
    doctor PTR-GC trio (orphan removed / live kept / stale-lock removed)."""
    from dadaia_workspace.core.exceptions import LockHeldError

    # .ptr created on first acquire with the session_id content.
    ws1 = _make_workspace(tmp_path.parent / (tmp_path.name + "-first-acquire"))
    ptr1 = lease._ptr_path(ws1, CTX)
    assert not ptr1.exists()
    status, _rec = lease.acquire(
        ws1, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE)
    )
    assert status == "ACQUIRED"
    assert ptr1.exists()
    assert ptr1.read_text(encoding="utf-8").strip() == MY_SESSION

    # No .ptr + live foreign lock ⇒ falls through to normal check ⇒ LockHeldError.
    ws2 = _make_workspace(tmp_path.parent / (tmp_path.name + "-no-ptr"))
    _seed_lock(ws2, OTHER_SESSION, BASE)
    with pytest.raises(LockHeldError):
        lease.acquire(ws2, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))

    # Doctor PTR-GC: orphan .ptr (no lock record) removed.
    ws3 = _make_workspace(tmp_path.parent / (tmp_path.name + "-orphan-ptr"))
    ptr3 = lease._ptr_path(ws3, CTX)
    ptr3.write_text(MY_SESSION, encoding="utf-8")
    actions3 = _make_doctor(ws3).fix()
    assert not ptr3.exists()
    assert any("PTR-GC" in a and f"{CTX}.ptr" in a for a in actions3)

    # Doctor PTR-GC: live lock record ⇒ .ptr kept.
    ws4 = _make_workspace(tmp_path.parent / (tmp_path.name + "-live-ptr"))
    _seed_lock(ws4, MY_SESSION, datetime.now(tz=UTC))
    ptr4 = lease._ptr_path(ws4, CTX)
    ptr4.write_text(MY_SESSION, encoding="utf-8")
    actions4 = _make_doctor(ws4).fix()
    assert ptr4.exists()
    assert [a for a in actions4 if "PTR-GC" in a] == []

    # Doctor PTR-GC: stale lock record ⇒ .ptr removed.
    ws5 = _make_workspace(tmp_path.parent / (tmp_path.name + "-stale-ptr"))
    stale_heartbeat = datetime.now(tz=UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 60)
    _seed_lock(ws5, MY_SESSION, stale_heartbeat)
    ptr5 = lease._ptr_path(ws5, CTX)
    ptr5.write_text(MY_SESSION, encoding="utf-8")
    actions5 = _make_doctor(ws5).fix()
    assert not ptr5.exists()
    assert any("PTR-GC" in a and f"{CTX}.ptr" in a for a in actions5)
