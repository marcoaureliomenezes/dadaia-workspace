"""Spec-context implementation/review conflict tests.

This file keeps the cross-mode and race contracts that are not covered by the
core lock lifecycle tests. Simple lock create/release/owner cases belong in
tests/unit/test_spec_context_locking.py.
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


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    """Minimal workspace root with the directories the lock layer needs."""
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
    """Write a fresh BOUND_REVIEW session file."""
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
    """Bind implementation with the same atomic check/create sequence as context.bind."""
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
    """Bind review with the same atomic check/write sequence as context.bind."""
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


def test_impl_and_review_different_releases_coexist(ws: Path) -> None:
    """Implementation and review sessions only conflict within the same release."""
    create_impl_lock(
        ws,
        context="ctx-a",
        release="rel-A",
        session_id="sess_impl_03",
        runtime="test",
        pid=os.getpid(),
    )
    _write_review_session(ws, "ctx-a", "rel-B", "sess_review_03")

    with pytest.raises(ReviewBlockedByImplementationError):
        check_impl_xor_review(ws, "ctx-a", "rel-A", "REVIEW", "sess_review_03b")

    check_impl_xor_review(ws, "ctx-a", "rel-B", "REVIEW", "sess_review_03c")

    with pytest.raises(ImplementationBlockedByReviewError):
        check_impl_xor_review(ws, "ctx-a", "rel-B", "IMPLEMENTATION", "sess_impl_03b")

    check_impl_xor_review(ws, "ctx-a", "rel-A", "IMPLEMENTATION", "sess_impl_03c")


def test_impl_stale_blocks_review_until_reclaim(ws: Path) -> None:
    """A stale implementation lock blocks review until ownership is resolved."""
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

    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.STALE

    with pytest.raises(ReviewBlockedByImplementationError) as exc_info:
        check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_05")

    assert "sess_stale_05" in str(exc_info.value)

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

    release_impl_lock(ws, "ctx-a", "rel-1", "sess_reclaimed_05")
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.FREE
    check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_after")


def test_r_impl_xor_review_only_one_binds(ws: Path) -> None:
    """Concurrent implementation/review bind permits exactly one owner."""
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

    assert len(results) == 2, f"Not all threads reported: {results}"

    successes = sum(1 for v in results.values() if v == "ok")
    assert successes == 1, (
        f"Expected exactly 1 success (workspace_lock serialises the race), got {successes}: "
        f"{results}"
    )

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


def test_r_two_impl_sessions_race(ws: Path) -> None:
    """Concurrent implementation binds permit exactly one owner."""
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

    lock_path = _impl_lock_path(ws, context, release)
    assert lock_path.exists(), "Lock file must exist after a successful create_impl_lock"

    lock_data = json.loads(lock_path.read_text())
    owner = lock_data.get("session_id")
    assert owner in ("sess_impl_08a", "sess_impl_08b"), f"Unexpected lock owner: {owner}"

    state = check_lock_state(ws, context, release)
    assert state == LockState.HELD, f"Expected HELD state after race, got {state}"
