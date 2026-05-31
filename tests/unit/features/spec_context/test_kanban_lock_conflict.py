"""AC-3 — Impl-XOR-Review lock-conflict and race tests (panel-kanban-v1 §8 AC-3).

Acceptance criteria covered:
    AC-3.1  test_impl_held_blocks_review_bind
    AC-3.2  test_review_held_blocks_impl_bind
    AC-3.3  test_impl_and_review_different_releases_coexist
    AC-3.4  test_impl_released_allows_review_bind
    AC-3.5  test_impl_stale_blocks_review_until_reclaim
    AC-3.6  test_two_impl_binds_same_release_raises
    AC-3.7  test_r_impl_xor_review_only_one_binds   (threading.Barrier race)
    AC-3.8  test_r_two_impl_sessions_race            (threading.Barrier race)

All tests use real filesystem on tmp_path — no FakeContextStore.
No sleep calls (CI grep gate enforced).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    ImplementationBlockedByReviewError,
    LockHeldError,
    ReviewBlockedByImplementationError,
)
from dadaia_workspace.features.spec_context.locking import (
    LockState,
    _impl_lock_path,
    check_impl_xor_review,
    check_lock_state,
    create_impl_lock,
    reclaim_impl_lock,
    release_impl_lock,
    workspace_lock,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    """Minimal workspace root — only the directories the lock layer needs."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / ".dadaia" / "states").mkdir(parents=True)
    return root


# ---------------------------------------------------------------------------
# Helpers that replicate the bind() sequences from context.py
# ---------------------------------------------------------------------------


def _write_review_session(
    ws: Path,
    context: str,
    release: str,
    session_id: str,
    *,
    last_seen_at: str | None = None,
    ttl_seconds: int = 300,
) -> Path:
    """Write a fresh BOUND_REVIEW session file to .dadaia/sessions/<sid>.json.

    Mirrors the session_data dict written by bind() in context.py for REVIEW mode.
    """
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    session_data = {
        "session_id": session_id,
        "context": context,
        "mode": "BOUND_REVIEW",
        "release": release,
        "runtime": "test",
        "pid": os.getpid(),
        "bound_at": now,
        "last_seen_at": last_seen_at if last_seen_at is not None else now,
        "ttl_seconds": ttl_seconds,
        "is_stale": False,
    }
    session_file = sessions_dir / f"{session_id}.json"
    session_file.write_text(json.dumps(session_data, indent=2))
    return session_file


def _bind_impl(
    ws: Path,
    context: str,
    release: str,
    session_id: str,
) -> dict:  # type: ignore[type-arg]
    """Replicate the IMPLEMENTATION bind sequence from context.py bind() (fixed).

    Mirrors the fixed bind() critical section: check_impl_xor_review +
    create_impl_lock are both inside a single workspace_lock block, making the
    check-then-act sequence atomic.

    1. workspace_lock: check_impl_xor_review + create_impl_lock (atomic)
    2. Write session file (outside lock, mirrors bind() behaviour)

    Raises:
        ImplementationBlockedByReviewError: if a BOUND_REVIEW session is active.
        LockHeldError: if the impl lock is already HELD.
    """
    with workspace_lock(ws):
        check_impl_xor_review(ws, context, release, "IMPLEMENTATION", session_id)
        lock_data = create_impl_lock(
            ws,
            context=context,
            release=release,
            session_id=session_id,
            runtime="test",
            pid=os.getpid(),
        )
    # Write the session file outside the lock (mirrors bind() behaviour)
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    session_data = {
        "session_id": session_id,
        "context": context,
        "mode": "BOUND_IMPLEMENTATION",
        "release": release,
        "runtime": "test",
        "pid": os.getpid(),
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }
    (sessions_dir / f"{session_id}.json").write_text(json.dumps(session_data, indent=2))
    return lock_data


def _bind_review(
    ws: Path,
    context: str,
    release: str,
    session_id: str,
) -> Path:
    """Replicate the REVIEW bind sequence from context.py bind() (fixed).

    Mirrors the fixed bind() critical section: check_impl_xor_review +
    session-file write are both inside a single workspace_lock block, making
    the check-then-act sequence atomic.

    Raises:
        ReviewBlockedByImplementationError: if impl lock is HELD or STALE.
    """
    sessions_dir = ws / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    session_data = {
        "session_id": session_id,
        "context": context,
        "mode": "BOUND_REVIEW",
        "release": release,
        "runtime": "test",
        "pid": os.getpid(),
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }
    with workspace_lock(ws):
        check_impl_xor_review(ws, context, release, "REVIEW", session_id)
        session_file = sessions_dir / f"{session_id}.json"
        session_file.write_text(json.dumps(session_data, indent=2))
    return session_file


# ---------------------------------------------------------------------------
# AC-3.1 — HELD impl lock blocks review bind
# ---------------------------------------------------------------------------


def test_impl_held_blocks_review_bind(ws: Path) -> None:
    """AC-3.1: create_impl_lock then check_impl_xor_review(...,"REVIEW",...) raises
    ReviewBlockedByImplementationError."""
    create_impl_lock(
        ws,
        context="ctx-a",
        release="rel-1",
        session_id="sess_impl_01",
        runtime="test",
        pid=os.getpid(),
    )
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.HELD

    with pytest.raises(ReviewBlockedByImplementationError) as exc_info:
        check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_01")

    # Error message must identify the impl lock owner
    assert "sess_impl_01" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-3.2 — HELD review session blocks impl bind
# ---------------------------------------------------------------------------


def test_review_held_blocks_impl_bind(ws: Path) -> None:
    """AC-3.2: write a fresh BOUND_REVIEW session then check_impl_xor_review(...,"IMPLEMENTATION",...)
    raises ImplementationBlockedByReviewError."""
    _write_review_session(ws, "ctx-a", "rel-1", "sess_review_02")

    with pytest.raises(ImplementationBlockedByReviewError) as exc_info:
        check_impl_xor_review(ws, "ctx-a", "rel-1", "IMPLEMENTATION", "sess_impl_02")

    assert "sess_review_02" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-3.3 — Impl lock on release-A + review session on release-B coexist
# ---------------------------------------------------------------------------


def test_impl_and_review_different_releases_coexist(ws: Path) -> None:
    """AC-3.3: impl lock on rel-A and review session on rel-B for the same context
    do not conflict — different releases have independent guard checks."""
    create_impl_lock(
        ws,
        context="ctx-a",
        release="rel-A",
        session_id="sess_impl_03",
        runtime="test",
        pid=os.getpid(),
    )
    _write_review_session(ws, "ctx-a", "rel-B", "sess_review_03")

    # Review bind on rel-A is blocked (impl lock on rel-A)
    with pytest.raises(ReviewBlockedByImplementationError):
        check_impl_xor_review(ws, "ctx-a", "rel-A", "REVIEW", "sess_review_03b")

    # Review bind on rel-B proceeds without raising (impl lock is on rel-A, not rel-B)
    check_impl_xor_review(ws, "ctx-a", "rel-B", "REVIEW", "sess_review_03c")

    # Impl bind on rel-B is blocked by review session on rel-B
    with pytest.raises(ImplementationBlockedByReviewError):
        check_impl_xor_review(ws, "ctx-a", "rel-B", "IMPLEMENTATION", "sess_impl_03b")

    # Impl bind on rel-A is NOT blocked by the review session (which is on rel-B)
    # (rel-A impl lock is HELD, so a second impl bind would raise LockHeldError,
    # but the XOR check itself passes)
    check_impl_xor_review(ws, "ctx-a", "rel-A", "IMPLEMENTATION", "sess_impl_03c")


# ---------------------------------------------------------------------------
# AC-3.4 — After release_impl_lock, review bind succeeds
# ---------------------------------------------------------------------------


def test_impl_released_allows_review_bind(ws: Path) -> None:
    """AC-3.4: create_impl_lock, then release_impl_lock, then review check passes (no raise)."""
    create_impl_lock(
        ws,
        context="ctx-a",
        release="rel-1",
        session_id="sess_impl_04",
        runtime="test",
        pid=os.getpid(),
    )
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.HELD

    released = release_impl_lock(ws, "ctx-a", "rel-1", "sess_impl_04")
    assert released is True
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.FREE

    # Now review bind must succeed without raising
    check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_04")


# ---------------------------------------------------------------------------
# AC-3.5 — Stale impl lock behavior w.r.t. review bind and reclaim
# ---------------------------------------------------------------------------


def test_impl_stale_blocks_review_until_reclaim(ws: Path) -> None:
    """AC-3.5 (rewritten for r2-lock-toctou-hardening-v1): a STALE impl lock
    blocks a review bind — OQ-1 resolved as Option A.

    Fixed behavior (post-patch):
    check_impl_xor_review(..., "REVIEW", ...) raises ReviewBlockedByImplementationError
    for BOTH HELD and STALE impl lock states. A STALE lock means the implementation
    session died mid-work; allowing review over a half-done implementation violates
    the Impl-XOR-Review invariant. The operator must explicitly reclaim or release.

    This test asserts:
    1. A lock with expired TTL is STALE (check_lock_state).
    2. check_impl_xor_review with "REVIEW" RAISES ReviewBlockedByImplementationError
       for a STALE lock (Option A fix — was NOT raising before patch).
    3. The error message names the stale session_id.
    4. After reclaim + release, review is unblocked.
    """
    # Create a lock file with last_seen_at well beyond its TTL and a dead PID
    old_time = (datetime.now(tz=UTC) - timedelta(minutes=20)).isoformat()
    lock_path = _impl_lock_path(ws, "ctx-a", "rel-1")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stale_lock_data = {
        "lock_type": "implementation",
        "context": "ctx-a",
        "release": "rel-1",
        "session_id": "sess_stale_05",
        "runtime": "test",
        "pid": 999999999,  # guaranteed dead PID
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": old_time,
        "last_seen_at": old_time,
        "ttl_seconds": 300,
        "task_path": "",
        "owner_note": "",
    }
    lock_path.write_text(json.dumps(stale_lock_data, indent=2))

    # Confirm the lock is STALE (not HELD)
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.STALE

    # FIXED BEHAVIOR (Option A): STALE lock DOES block review.
    # Before patch: this call would NOT raise for STALE (bug).
    # After patch: raises ReviewBlockedByImplementationError for STALE.
    with pytest.raises(ReviewBlockedByImplementationError) as exc_info:
        check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_05")

    # Error message must identify the stale session
    assert "sess_stale_05" in str(exc_info.value)

    # After reclaim, review is still blocked (new HELD owner)
    new_data = reclaim_impl_lock(
        ws,
        context="ctx-a",
        release="rel-1",
        new_session_id="sess_reclaimed_05",
        runtime="test",
        pid=os.getpid(),
        reason="reclaiming stale lock for test",
    )
    assert new_data["session_id"] == "sess_reclaimed_05"
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.HELD

    with pytest.raises(ReviewBlockedByImplementationError) as exc_info2:
        check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_05b")
    assert "sess_reclaimed_05" in str(exc_info2.value)

    # After release, review is unblocked
    release_impl_lock(ws, "ctx-a", "rel-1", "sess_reclaimed_05")
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.FREE
    # Now review bind passes without raising
    check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_after")


# ---------------------------------------------------------------------------
# AC-3.6 — Two BOUND_IMPLEMENTATION binds same release raises LockHeldError
# ---------------------------------------------------------------------------


def test_two_impl_binds_same_release_raises(ws: Path) -> None:
    """AC-3.6: create_impl_lock twice on the same context/release → second raises LockHeldError."""
    create_impl_lock(
        ws,
        context="ctx-a",
        release="rel-1",
        session_id="sess_impl_06a",
        runtime="test",
        pid=os.getpid(),
    )
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.HELD

    with pytest.raises(LockHeldError) as exc_info:
        create_impl_lock(
            ws,
            context="ctx-a",
            release="rel-1",
            session_id="sess_impl_06b",
            runtime="test",
            pid=os.getpid(),
        )

    # Error should identify the first session as the holder
    assert "sess_impl_06a" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-3.7 — RACE: impl vs review bind — exactly one succeeds
# ---------------------------------------------------------------------------


def test_r_impl_xor_review_only_one_binds(ws: Path) -> None:
    """AC-3.7 (rewritten for r2-lock-toctou-hardening-v1): threading.Barrier(2) race
    between one impl bind and one review bind on same context/release.

    Fixed behavior (post-patch):
    _bind_impl and _bind_review now wrap their check-then-act sequence inside a
    single workspace_lock critical section, serialising the race. Exactly ONE thread
    wins; the other raises a LockConflictError subclass (never two successes).

    Asserts:
    1. Both threads terminate within timeout (no deadlock/hang).
    2. Exactly one success and one LockConflictError subclass — never two successes.
    3. Structural invariants: impl lock (if created) has exactly one owner;
       review session file (if created) has mode BOUND_REVIEW.
    """
    context = "ctx-race-07"
    release = "rel-race-07"
    results: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def do_impl_bind() -> None:
        barrier.wait(timeout=5)
        try:
            _bind_impl(ws, context, release, "sess_impl_07")
            results["impl"] = "ok"
        except (
            LockHeldError,
            ReviewBlockedByImplementationError,
            ImplementationBlockedByReviewError,
        ) as exc:
            results["impl"] = type(exc).__name__

    def do_review_bind() -> None:
        barrier.wait(timeout=5)
        try:
            _bind_review(ws, context, release, "sess_review_07")
            results["review"] = "ok"
        except (
            LockHeldError,
            ReviewBlockedByImplementationError,
            ImplementationBlockedByReviewError,
        ) as exc:
            results["review"] = type(exc).__name__

    t_impl = threading.Thread(target=do_impl_bind)
    t_review = threading.Thread(target=do_review_bind)
    t_impl.start()
    t_review.start()
    t_impl.join(timeout=10)
    t_review.join(timeout=10)

    assert not t_impl.is_alive(), "impl thread did not complete within 10 s"
    assert not t_review.is_alive(), "review thread did not complete within 10 s"

    # Both threads must have reported a result
    assert len(results) == 2, f"Not all threads reported: {results}"

    # Exactly one success — never two
    successes = sum(1 for v in results.values() if v == "ok")
    assert successes == 1, (
        f"Expected exactly 1 success (workspace_lock serialises the race), got {successes}: "
        f"{results}"
    )

    # Structural invariants
    lock_path = _impl_lock_path(ws, context, release)
    if lock_path.exists():
        lock_data = json.loads(lock_path.read_text())
        assert lock_data.get("session_id") == "sess_impl_07", (
            f"Unexpected impl lock owner: {lock_data.get('session_id')}"
        )

    sessions_dir = ws / ".dadaia" / "sessions"
    review_session_file = sessions_dir / "sess_review_07.json"
    if review_session_file.exists():
        rev_data = json.loads(review_session_file.read_text())
        assert rev_data.get("mode") == "BOUND_REVIEW"


# ---------------------------------------------------------------------------
# AC-3.8 — RACE: two impl sessions competing for same lock
# ---------------------------------------------------------------------------


def test_r_two_impl_sessions_race(ws: Path) -> None:
    """AC-3.8 (rewritten for r2-lock-toctou-hardening-v1): threading.Barrier(2) race
    where two threads both attempt an IMPLEMENTATION bind for the same context/release.

    Fixed behavior (post-patch):
    _bind_impl wraps check_impl_xor_review + create_impl_lock inside workspace_lock,
    serialising the race. Per-call UUID tmp names ensure the loser sees HELD (not FREE
    from a stale check) and raises LockHeldError — never FileNotFoundError.

    Asserts:
    1. Both threads terminate within timeout (no hang/deadlock).
    2. Exactly one success and one LockHeldError — loser NEVER raises FileNotFoundError.
    3. Lock file exists with exactly one owner after the race.
    4. check_lock_state returns HELD.
    """
    context = "ctx-race-08"
    release = "rel-race-08"
    results: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def do_bind(session_id: str) -> None:
        barrier.wait(timeout=5)
        try:
            _bind_impl(ws, context, release, session_id)
            results[session_id] = "ok"
        except LockHeldError:
            results[session_id] = "LockHeldError"
        except Exception as exc:
            results[session_id] = type(exc).__name__

    t1 = threading.Thread(target=do_bind, args=("sess_impl_08a",))
    t2 = threading.Thread(target=do_bind, args=("sess_impl_08b",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not t1.is_alive(), "Thread 1 did not complete within 10 s"
    assert not t2.is_alive(), "Thread 2 did not complete within 10 s"

    assert len(results) == 2, f"Not all threads reported: {results}"

    assert "ok" in results.values(), f"Expected one success: {results}"
    assert "LockHeldError" in results.values(), f"Expected LockHeldError for loser: {results}"
    assert "FileNotFoundError" not in results.values(), (
        f"Loser must not raise FileNotFoundError (UUID tmp fix): {results}"
    )

    # Lock file must exist with exactly one owner
    lock_path = _impl_lock_path(ws, context, release)
    assert lock_path.exists(), "Lock file must exist after a successful create_impl_lock"

    lock_data = json.loads(lock_path.read_text())
    owner = lock_data.get("session_id")
    assert owner in ("sess_impl_08a", "sess_impl_08b"), f"Unexpected lock owner: {owner}"

    # Verify state is HELD
    state = check_lock_state(ws, context, release)
    assert state == LockState.HELD, f"Expected HELD state after race, got {state}"
