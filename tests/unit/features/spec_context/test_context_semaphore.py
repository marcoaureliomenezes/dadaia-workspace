"""Unit tests for T-R1-02: per-context semaphore (ctx_locks JSON).

Tests verify:
- acquire: creates .dadaia/states/ctx_locks/<context>.lock with correct fields
- renew: updates heartbeat field atomically
- release: removes the lock file
- deny-second-holder: second acquire attempt raises while first is held
- read-not-blocked: read/spec phases never blocked by semaphore

The semaphore is a JSON state file (distinct from the fcntl-based context_lock
in locking.py and the per-release implementation lock).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.semaphore import (
    ContextSemaphoreError,
    acquire_context_semaphore,
    release_context_semaphore,
    renew_context_semaphore,
    SemaphoreAlreadyHeldError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _semaphore_path(workspace: Path, context: str) -> Path:
    return workspace / ".dadaia" / "states" / "ctx_locks" / f"{context}.semaphore.json"


def _make_stale_ts(seconds_ago: int = 400) -> str:
    return (datetime.now(tz=UTC) - timedelta(seconds=seconds_ago)).isoformat()


def _make_fresh_ts() -> str:
    return datetime.now(tz=UTC).isoformat()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


# ---------------------------------------------------------------------------
# AC-1: acquire creates the semaphore lock file with correct fields
# ---------------------------------------------------------------------------


def test_tr102_acquire_creates_semaphore_with_fields(workspace: Path) -> None:
    """AC-1: acquire_context_semaphore creates the JSON semaphore with all required fields."""
    context = "my-proj"
    session_id = "sess_acquire01"
    release = "v0.1.5"
    phase = "IMPLEMENTATION"
    write_set = ["dadaia_workspace/**"]

    acquire_context_semaphore(
        workspace,
        context=context,
        session_id=session_id,
        phase=phase,
        release=release,
        write_set=write_set,
    )

    sem_path = _semaphore_path(workspace, context)
    assert sem_path.exists(), f"Semaphore file should exist at {sem_path}"

    data = json.loads(sem_path.read_text())
    assert data["owner"] == session_id
    assert data["phase"] == phase
    assert data["release"] == release
    assert data["write_set"] == write_set
    assert "acquired_at" in data
    assert "ttl" in data
    assert "heartbeat" in data
    # Verify timestamps are valid ISO format
    datetime.fromisoformat(data["acquired_at"])
    datetime.fromisoformat(data["heartbeat"])


# ---------------------------------------------------------------------------
# AC-2: renew updates heartbeat atomically
# ---------------------------------------------------------------------------


def test_tr102_renew_updates_heartbeat(workspace: Path) -> None:
    """AC-2: renew_context_semaphore updates the heartbeat field."""
    context = "my-proj"
    session_id = "sess_renew01"

    acquire_context_semaphore(workspace, context=context, session_id=session_id)

    sem_path = _semaphore_path(workspace, context)
    before_data = json.loads(sem_path.read_text())
    old_heartbeat = before_data["heartbeat"]

    # Force a small delay-equivalent by backdating the heartbeat
    before_data["heartbeat"] = _make_stale_ts(60)
    sem_path.write_text(json.dumps(before_data))

    before_renew = datetime.now(tz=UTC)
    renewed = renew_context_semaphore(workspace, context=context, session_id=session_id)
    after_renew = datetime.now(tz=UTC)

    assert renewed, "renew should return True for the owning session"

    updated = json.loads(sem_path.read_text())
    new_heartbeat_dt = datetime.fromisoformat(updated["heartbeat"])
    assert new_heartbeat_dt >= before_renew
    assert new_heartbeat_dt <= after_renew + timedelta(seconds=1)
    assert updated["heartbeat"] != old_heartbeat


# ---------------------------------------------------------------------------
# AC-3: release removes the semaphore file
# ---------------------------------------------------------------------------


def test_tr102_release_removes_semaphore(workspace: Path) -> None:
    """AC-3: release_context_semaphore removes the JSON semaphore file."""
    context = "my-proj"
    session_id = "sess_release01"

    acquire_context_semaphore(workspace, context=context, session_id=session_id)
    assert _semaphore_path(workspace, context).exists()

    released = release_context_semaphore(workspace, context=context, session_id=session_id)
    assert released, "release should return True"
    assert not _semaphore_path(workspace, context).exists(), "Semaphore file should be removed"


def test_tr102_release_returns_false_when_not_owner(workspace: Path) -> None:
    """AC-3b: release by non-owner returns False (does not remove file)."""
    context = "my-proj"
    session_id = "sess_owner01"
    other_id = "sess_other01"

    acquire_context_semaphore(workspace, context=context, session_id=session_id)
    released = release_context_semaphore(workspace, context=context, session_id=other_id)

    assert not released
    assert _semaphore_path(workspace, context).exists(), "File should remain"


# ---------------------------------------------------------------------------
# AC-4: deny second holder while first is active
# ---------------------------------------------------------------------------


def test_tr102_deny_second_holder(workspace: Path) -> None:
    """AC-4: second acquire while semaphore held → SemaphoreAlreadyHeldError
    with the holder's session_id in the error message.
    """
    context = "my-proj"
    first_session = "sess_first01"
    second_session = "sess_second01"

    acquire_context_semaphore(workspace, context=context, session_id=first_session)

    with pytest.raises(SemaphoreAlreadyHeldError) as exc_info:
        acquire_context_semaphore(workspace, context=context, session_id=second_session)

    error_msg = str(exc_info.value)
    assert first_session in error_msg, (
        f"Error message should name the holder '{first_session}', got: {error_msg!r}"
    )


def test_tr102_second_holder_allowed_after_release(workspace: Path) -> None:
    """AC-4b: after release, a second session can acquire the semaphore."""
    context = "my-proj"
    first_session = "sess_first02"
    second_session = "sess_second02"

    acquire_context_semaphore(workspace, context=context, session_id=first_session)
    release_context_semaphore(workspace, context=context, session_id=first_session)
    # Should not raise
    acquire_context_semaphore(workspace, context=context, session_id=second_session)
    assert _semaphore_path(workspace, context).exists()
    data = json.loads(_semaphore_path(workspace, context).read_text())
    assert data["owner"] == second_session


def test_tr102_stale_semaphore_can_be_reclaimed(workspace: Path) -> None:
    """AC-4c: a stale semaphore (heartbeat > TTL) can be overwritten by a new acquire."""
    context = "my-proj"
    stale_session = "sess_stale01"
    new_session = "sess_new01"

    acquire_context_semaphore(workspace, context=context, session_id=stale_session, ttl=300)

    # Backdate heartbeat to make it stale
    sem_path = _semaphore_path(workspace, context)
    data = json.loads(sem_path.read_text())
    data["heartbeat"] = _make_stale_ts(400)
    data["acquired_at"] = _make_stale_ts(400)
    sem_path.write_text(json.dumps(data))

    # Should succeed — stale semaphore is reclaimed
    acquire_context_semaphore(workspace, context=context, session_id=new_session, ttl=300)
    updated = json.loads(sem_path.read_text())
    assert updated["owner"] == new_session


# ---------------------------------------------------------------------------
# AC-5: read/spec phases never blocked by semaphore
# ---------------------------------------------------------------------------


def test_tr102_read_phase_never_blocked(workspace: Path) -> None:
    """AC-5a: acquire with phase=READ never raises even when semaphore is held."""
    context = "my-proj"
    impl_session = "sess_impl01"
    read_session = "sess_read01"

    # First: implementation holds the semaphore
    acquire_context_semaphore(
        workspace, context=context, session_id=impl_session, phase="BOUND_IMPLEMENTATION"
    )

    # Second: read-mode bind NEVER blocks (no acquire needed for read)
    # read/spec phases bypass the semaphore entirely
    is_blocked = _check_phase_blocked(workspace, context, read_session, "READ")
    assert not is_blocked, "READ phase should never be blocked by the semaphore"


def test_tr102_spec_phase_never_blocked(workspace: Path) -> None:
    """AC-5b: acquire with phase=SPEC never raises even when semaphore is held."""
    context = "my-proj"
    impl_session = "sess_impl02"
    spec_session = "sess_spec01"

    acquire_context_semaphore(
        workspace, context=context, session_id=impl_session, phase="BOUND_IMPLEMENTATION"
    )

    is_blocked = _check_phase_blocked(workspace, context, spec_session, "SPEC")
    assert not is_blocked, "SPEC phase should never be blocked by the semaphore"


def test_tr102_review_blocked_while_impl_held(workspace: Path) -> None:
    """AC-5c: BOUND_REVIEW IS blocked while BOUND_IMPLEMENTATION holds the semaphore."""
    context = "my-proj"
    impl_session = "sess_impl03"
    review_session = "sess_review01"

    acquire_context_semaphore(
        workspace, context=context, session_id=impl_session, phase="BOUND_IMPLEMENTATION"
    )

    with pytest.raises(SemaphoreAlreadyHeldError):
        acquire_context_semaphore(
            workspace, context=context, session_id=review_session, phase="BOUND_REVIEW"
        )


# ---------------------------------------------------------------------------
# Helpers for phase checks
# ---------------------------------------------------------------------------


def _check_phase_blocked(workspace: Path, context: str, session_id: str, phase: str) -> bool:
    """Return True if the phase would be blocked, False if not blocked."""
    try:
        acquire_context_semaphore(workspace, context=context, session_id=session_id, phase=phase)
        return False
    except SemaphoreAlreadyHeldError:
        return True


# ---------------------------------------------------------------------------
# AC-6: renew returns False for non-owner
# ---------------------------------------------------------------------------


def test_tr102_renew_returns_false_for_nonowner(workspace: Path) -> None:
    """AC-6: renew by non-owner returns False."""
    context = "my-proj"
    owner = "sess_owner02"
    other = "sess_other02"

    acquire_context_semaphore(workspace, context=context, session_id=owner)
    result = renew_context_semaphore(workspace, context=context, session_id=other)
    assert not result
