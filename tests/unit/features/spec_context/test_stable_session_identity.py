"""T-016-11: Stable session identity via .ptr file mechanism (D1 soul-fold, FR-P1-15).

Acceptance criteria tested:
    AC-15 — .ptr created on first acquire; matching session_id → RENEW.
    AC-17 — Yield message does not contain "bind --mode write" / "relaunch" as routine.
    AC-18 — doctor --fix removes orphan .ptr files (no corresponding live lock record).
    AC-19(a) — Relaunched same-identity → RENEW (test_relaunched_same_identity_renews
               is in test_short_heartbeat_triad.py as the AC-19 triad).

All tests use FakeClock; tmp_path workspace; no real time.sleep in test bodies.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import inspect  # noqa: E402
import json  # noqa: E402
from collections.abc import Callable  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context import lease  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.features.spec_context.lease import LEASE_TTL_SECONDS  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"
MY_SESSION = "my-session-id"
OTHER_SESSION = "foreign-session-id"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
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


# ---------------------------------------------------------------------------
# test_lease_ttl_constant_is_120
# ---------------------------------------------------------------------------


def test_lease_ttl_constant_is_120() -> None:
    """LEASE_TTL_SECONDS must be 120 (OQ-1 operator decision 2026-06-06)."""
    assert LEASE_TTL_SECONDS == 120, f"LEASE_TTL_SECONDS must be 120; got {LEASE_TTL_SECONDS}"


def test_no_inline_1800_in_lease_py() -> None:
    """No string literal '1800' appears in lease.py source (zero inline magic numbers)."""
    source = inspect.getsource(lease)
    # Allow '1800' only if it appears in comments/strings that are test-facing;
    # in practice, the production liveness path must reference LEASE_TTL_SECONDS only.
    # Scan the full source for the substring.
    assert "1800" not in source, (
        "lease.py contains inline '1800' — replace with LEASE_TTL_SECONDS constant"
    )


# ---------------------------------------------------------------------------
# test_ptr_created_on_first_acquire
# ---------------------------------------------------------------------------


def test_ptr_created_on_first_acquire(tmp_path: Path) -> None:
    """On first acquire with no prior .ptr, the .ptr file is written with session_id."""
    ws = _make_workspace(tmp_path)
    ptr = lease._ptr_path(ws, CTX)
    assert not ptr.exists(), "Precondition: .ptr must not exist before first acquire"

    status, rec = lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))
    assert status == "ACQUIRED"
    assert ptr.exists(), ".ptr file must be created on first acquire"
    assert ptr.read_text(encoding="utf-8").strip() == MY_SESSION, (
        f".ptr content must be the session_id '{MY_SESSION}'"
    )


# ---------------------------------------------------------------------------
# test_ptr_renews_on_matching_session
# ---------------------------------------------------------------------------


def test_ptr_renews_on_matching_session(tmp_path: Path) -> None:
    """Acquire when .ptr matches my_session_id and lock record has foreign+live session → RENEW.

    This is the stable-identity scenario: the .ptr recognises the caller as the
    incumbent even though the lock record was written under a different session_id
    (e.g. after a relaunch that changed the session env var).
    """
    ws = _make_workspace(tmp_path)
    # Write lock record with a foreign-looking session_id (simulating drift from relaunch).
    _seed_lock(ws, "old-session-that-looks-foreign", BASE)
    # Write .ptr for MY_SESSION — signals that MY_SESSION is the incumbent.
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")

    status, rec = lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))

    assert status == "RENEWED", f"Incumbent session recognised via .ptr must RENEW, got {status!r}"
    assert rec["session_id"] == MY_SESSION, (
        f"Lock record session_id must be updated to '{MY_SESSION}'"
    )


# ---------------------------------------------------------------------------
# test_ptr_absent_falls_through_to_normal_check
# ---------------------------------------------------------------------------


def test_ptr_absent_falls_through_to_normal_check(tmp_path: Path) -> None:
    """Acquire when no .ptr + lock record has foreign+live session → yield-iff-live-foreign block."""
    from dadaia_workspace.core.exceptions import LockHeldError

    ws = _make_workspace(tmp_path)
    # Write a live lock record with a foreign session (no .ptr).
    _seed_lock(ws, OTHER_SESSION, BASE)

    # acquire() must raise LockHeldError (the gate interprets this as a BLOCK).
    raised = False
    try:
        lease.acquire(ws, CTX, MY_SESSION, "v0.1.6", "IMPLEMENTATION", clock=fixed(BASE))
    except LockHeldError:
        raised = True

    assert raised, (
        "No-.ptr-match + live foreign lease must raise LockHeldError (yield-iff-live-foreign)"
    )


# ---------------------------------------------------------------------------
# test_yield_message_does_not_contain_routine_steal_instruction
# ---------------------------------------------------------------------------


def test_yield_message_does_not_contain_routine_steal_instruction(tmp_path: Path) -> None:
    """Yield-iff-live-foreign message must contain NO manual unblock ceremony.

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


# ---------------------------------------------------------------------------
# test_doctor_gc_removes_orphan_ptr
# ---------------------------------------------------------------------------


def test_doctor_gc_removes_orphan_ptr(tmp_path: Path) -> None:
    """AC-18: doctor --fix removes orphan .ptr files for contexts with no active lock record."""
    ws = _make_workspace(tmp_path)
    # Write a .ptr file with no corresponding lock record (orphan).
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")
    assert ptr.exists(), "Precondition: orphan .ptr must exist before fix"

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not ptr.exists(), f"Orphan .ptr file must be removed by doctor --fix. Actions: {actions}"
    assert any("PTR-GC" in a and f"{CTX}.ptr" in a for a in actions), (
        f"Expected PTR-GC action for {CTX}.ptr, got: {actions}"
    )


def test_doctor_gc_keeps_ptr_with_live_lock(tmp_path: Path) -> None:
    """AC-18 negative case: doctor --fix keeps .ptr when the lock record is live."""
    ws = _make_workspace(tmp_path)
    # Write a live lock record and its .ptr.
    _seed_lock(ws, MY_SESSION, datetime.now(tz=UTC))
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert ptr.exists(), "Live .ptr with a live lock record must NOT be deleted by doctor --fix"
    ptr_gc_actions = [a for a in actions if "PTR-GC" in a]
    assert ptr_gc_actions == [], f"Unexpected PTR-GC actions: {ptr_gc_actions}"


def test_doctor_gc_removes_ptr_with_stale_lock(tmp_path: Path) -> None:
    """AC-18: doctor --fix removes .ptr when the lock record is stale (expired)."""
    ws = _make_workspace(tmp_path)
    stale_heartbeat = datetime.now(tz=UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 60)
    _seed_lock(ws, MY_SESSION, stale_heartbeat)
    ptr = lease._ptr_path(ws, CTX)
    ptr.write_text(MY_SESSION, encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not ptr.exists(), f"Stale-lock .ptr must be deleted by doctor --fix. Actions: {actions}"
    assert any("PTR-GC" in a and f"{CTX}.ptr" in a for a in actions), (
        f"Expected PTR-GC action for {CTX}.ptr, got: {actions}"
    )
