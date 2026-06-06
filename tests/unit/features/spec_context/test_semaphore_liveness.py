"""Unit tests for T-SEMA-01: semaphore liveness reclaim.

Verifies that _is_stale returns True when:
1. The owner's PID is not alive (checked via os.kill(pid, 0)).
2. The owner's session file does not exist.
3. TTL is expired (existing behavior preserved).
4. Returns False for a live holder with a recent heartbeat.

And that acquire_context_semaphore:
5. Silently reclaims a stale-by-liveness semaphore (log audit entry, then acquire).
6. Still blocks on a LIVE holder.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.semaphore import (
    SemaphoreAlreadyHeldError,
    _is_stale,
    acquire_context_semaphore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dead_pid() -> int:
    """Return a PID that is guaranteed not to be alive on this OS."""
    # Use a very high unlikely PID; we verify via os.kill below.
    candidate = 9999999
    try:
        os.kill(candidate, 0)
        # Unexpectedly alive — fall back to a different value
        return 9999998
    except ProcessLookupError:
        return candidate
    except (PermissionError, OSError):
        # If we get permission error, the PID exists — try another
        return 9999998


def _make_semaphore_data(
    owner: str = "sess_test",
    pid: int | None = None,
    session_file_exists: bool = True,
    heartbeat_offset_seconds: float = 0.0,
    ttl: int = 300,
) -> dict:  # type: ignore[type-arg]
    """Build a semaphore data dict for testing."""
    heartbeat_dt = datetime.now(tz=UTC) + timedelta(seconds=heartbeat_offset_seconds)
    data: dict = {  # type: ignore[type-arg]
        "owner": owner,
        "phase": "BOUND_IMPLEMENTATION",
        "release": "v0.1.5",
        "write_set": [],
        "acquired_at": heartbeat_dt.isoformat(),
        "ttl": ttl,
        "heartbeat": heartbeat_dt.isoformat(),
    }
    if pid is not None:
        data["pid"] = pid
    return data


def _write_semaphore(workspace_root: Path, context: str, data: dict) -> Path:  # type: ignore[type-arg]
    """Write semaphore data to the canonical path."""
    sem_path = workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{context}.semaphore.json"
    sem_path.parent.mkdir(parents=True, exist_ok=True)
    sem_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return sem_path


def _write_session_file(workspace_root: Path, session_id: str) -> Path:
    """Write a minimal session file."""
    sessions_dir = workspace_root / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_path = sessions_dir / f"{session_id}.json"
    session_path.write_text(
        json.dumps({"session_id": session_id, "pid": os.getpid(), "mode": "BOUND_IMPLEMENTATION"}),
        encoding="utf-8",
    )
    return session_path


# ---------------------------------------------------------------------------
# Tests for _is_stale
# ---------------------------------------------------------------------------


class TestIsStale:
    """Tests for the extended _is_stale function (T-SEMA-01)."""

    def test_dead_pid_returns_stale(self, tmp_path: Path) -> None:
        """T-SEMA-01 AC-1: _is_stale returns True when the owner PID is not alive."""
        dead = _dead_pid()
        data = _make_semaphore_data(pid=dead)
        # Confirm the PID is actually dead before asserting
        try:
            os.kill(dead, 0)
            pytest.skip(f"PID {dead} unexpectedly alive — skip this test")
        except ProcessLookupError:
            pass

        workspace = tmp_path / "ws"
        workspace.mkdir()
        result = _is_stale(data, workspace_root=workspace)
        assert result is True, "Expected stale=True for dead-PID semaphore"

    def test_missing_session_file_returns_stale(self, tmp_path: Path) -> None:
        """T-SEMA-01 AC-2: _is_stale returns True when owner session file does not exist."""
        workspace = tmp_path / "ws"
        workspace.mkdir()
        data = _make_semaphore_data(owner="sess_ghost", pid=os.getpid())
        # Session file for sess_ghost does NOT exist
        result = _is_stale(data, workspace_root=workspace)
        assert result is True, "Expected stale=True for missing-session semaphore"

    def test_ttl_expired_returns_stale(self, tmp_path: Path) -> None:
        """T-SEMA-01 AC-3: _is_stale returns True when TTL is exceeded (existing behavior)."""
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # heartbeat 400 seconds in the past, TTL=300
        data = _make_semaphore_data(
            owner="sess_old",
            pid=os.getpid(),
            heartbeat_offset_seconds=-400.0,
            ttl=300,
        )
        # Write session file so missing-session doesn't trigger first
        _write_session_file(workspace, "sess_old")
        result = _is_stale(data, workspace_root=workspace)
        assert result is True, "Expected stale=True for TTL-expired semaphore"

    def test_live_holder_recent_heartbeat_not_stale(self, tmp_path: Path) -> None:
        """T-SEMA-01 AC-4: _is_stale returns False for live holder with recent heartbeat."""
        workspace = tmp_path / "ws"
        workspace.mkdir()
        live_pid = os.getpid()
        data = _make_semaphore_data(
            owner="sess_live",
            pid=live_pid,
            heartbeat_offset_seconds=0.0,
            ttl=300,
        )
        _write_session_file(workspace, "sess_live")
        result = _is_stale(data, workspace_root=workspace)
        assert result is False, "Expected stale=False for live holder with recent heartbeat"

    def test_no_pid_field_falls_back_to_ttl(self, tmp_path: Path) -> None:
        """_is_stale without pid field falls back to TTL check only."""
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # Fresh heartbeat, no pid field → not stale via TTL
        data = _make_semaphore_data(owner="sess_nopid", heartbeat_offset_seconds=0.0, ttl=300)
        # Remove pid field if present
        data.pop("pid", None)
        _write_session_file(workspace, "sess_nopid")
        result = _is_stale(data, workspace_root=workspace)
        assert result is False, "Expected stale=False when no pid field and TTL fresh"


# ---------------------------------------------------------------------------
# Tests for acquire_context_semaphore reclaim behavior
# ---------------------------------------------------------------------------


class TestAcquireReclaim:
    """T-SEMA-01 AC-5: acquire_context_semaphore reclaims dead-owner semaphores."""

    def test_dead_pid_reclaims_immediately(self, tmp_path: Path) -> None:
        """T-SEMA-01: acquire reclaims a semaphore held by a dead PID."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        dead = _dead_pid()
        try:
            os.kill(dead, 0)
            pytest.skip(f"PID {dead} unexpectedly alive")
        except ProcessLookupError:
            pass

        # Write a stale semaphore with a dead PID
        old_data = _make_semaphore_data(owner="sess_dead", pid=dead)
        _write_semaphore(workspace, "myctx", old_data)
        # Write a session file for the dead owner so only PID triggers staleness
        _write_session_file(workspace, "sess_dead")

        # New session should be able to acquire
        new_session = "sess_new"
        result = acquire_context_semaphore(
            workspace, "myctx", new_session, phase="BOUND_IMPLEMENTATION"
        )
        assert result.get("owner") == new_session, (
            f"Expected new owner '{new_session}', got {result.get('owner')!r}"
        )

    def test_missing_session_reclaims_immediately(self, tmp_path: Path) -> None:
        """T-SEMA-01: acquire reclaims a semaphore whose session file is absent."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        live_pid = os.getpid()
        # Stale because session file missing (even though PID appears alive)
        old_data = _make_semaphore_data(owner="sess_ghost", pid=live_pid)
        _write_semaphore(workspace, "myctx", old_data)
        # No session file for sess_ghost

        new_session = "sess_new"
        result = acquire_context_semaphore(
            workspace, "myctx", new_session, phase="BOUND_IMPLEMENTATION"
        )
        assert result.get("owner") == new_session

    def test_live_holder_still_blocks(self, tmp_path: Path) -> None:
        """T-SEMA-01: acquire raises SemaphoreAlreadyHeldError for a live holder."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        live_pid = os.getpid()
        live_session = "sess_live"
        # Fresh heartbeat, live PID, session file present → LIVE
        old_data = _make_semaphore_data(
            owner=live_session, pid=live_pid, heartbeat_offset_seconds=0.0, ttl=300
        )
        _write_semaphore(workspace, "myctx", old_data)
        _write_session_file(workspace, live_session)

        with pytest.raises(SemaphoreAlreadyHeldError):
            acquire_context_semaphore(
                workspace, "myctx", "sess_other", phase="BOUND_IMPLEMENTATION"
            )

    def test_ttl_still_reclaims_after_expiry(self, tmp_path: Path) -> None:
        """T-SEMA-01 AC-3: TTL-expired semaphore is reclaimed by acquire."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        live_pid = os.getpid()
        old_session = "sess_expired"
        old_data = _make_semaphore_data(
            owner=old_session,
            pid=live_pid,
            heartbeat_offset_seconds=-400.0,  # 400s ago, TTL=300 → stale
            ttl=300,
        )
        _write_semaphore(workspace, "myctx", old_data)
        _write_session_file(workspace, old_session)

        new_session = "sess_fresh"
        result = acquire_context_semaphore(
            workspace, "myctx", new_session, phase="BOUND_IMPLEMENTATION"
        )
        assert result.get("owner") == new_session
