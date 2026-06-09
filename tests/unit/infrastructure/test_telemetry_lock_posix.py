"""Unit tests for PosixTelemetryRefreshLock.

These tests run only on POSIX platforms (fcntl is not available on Windows).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="fcntl telemetry locks are only available on POSIX platforms",
)

from dadaia_workspace.infrastructure.telemetry_lock_posix import PosixTelemetryRefreshLock


# ---------------------------------------------------------------------------
# try_acquire / release — basic behavior
# ---------------------------------------------------------------------------


def test_try_acquire_returns_true_on_free_file(tmp_path: Path) -> None:
    """try_acquire returns True when the lock file is free."""
    lock = PosixTelemetryRefreshLock()
    lock_path = str(tmp_path / "telemetry.lock")

    acquired = lock.try_acquire(lock_path)
    assert acquired is True
    # Clean up
    lock.release()


def test_try_acquire_creates_lock_file(tmp_path: Path) -> None:
    """try_acquire creates the lock file if it does not exist."""
    lock = PosixTelemetryRefreshLock()
    lock_path = str(tmp_path / "telemetry.lock")

    lock.try_acquire(lock_path)
    assert Path(lock_path).exists()
    lock.release()


def test_release_after_acquire(tmp_path: Path) -> None:
    """release() clears internal state; re-acquire on same path succeeds."""
    lock = PosixTelemetryRefreshLock()
    lock_path = str(tmp_path / "telemetry.lock")

    assert lock.try_acquire(lock_path) is True
    lock.release()

    # After release, re-acquiring should succeed.
    assert lock.try_acquire(lock_path) is True
    lock.release()


def test_release_noop_when_not_held(tmp_path: Path) -> None:
    """release() is a no-op when the lock is not currently held."""
    lock = PosixTelemetryRefreshLock()
    # Should not raise.
    lock.release()


# ---------------------------------------------------------------------------
# Non-blocking: a second lock instance sees the lock as held
# ---------------------------------------------------------------------------


def test_try_acquire_returns_false_when_held(tmp_path: Path) -> None:
    """try_acquire returns False when another instance holds the lock."""
    lock_path = str(tmp_path / "telemetry.lock")

    holder = PosixTelemetryRefreshLock()
    assert holder.try_acquire(lock_path) is True

    contender = PosixTelemetryRefreshLock()
    # Non-blocking: should return False immediately.
    assert contender.try_acquire(lock_path) is False

    holder.release()
    # After the holder releases, the contender can acquire.
    assert contender.try_acquire(lock_path) is True
    contender.release()


# ---------------------------------------------------------------------------
# Full fd lifecycle — LV-5 compliance
# ---------------------------------------------------------------------------


def test_full_fd_lifecycle_encapsulated(tmp_path: Path) -> None:
    """The full fd lifecycle (os.open, fcntl.flock, os.close) is inside the adapter.

    This test confirms that a caller never needs to manage a raw fd —
    the adapter exposes only try_acquire/release as the public interface.
    """
    lock = PosixTelemetryRefreshLock()
    lock_path = str(tmp_path / "telemetry.lock")

    # Internal state should be None before acquiring.
    assert lock._fd is None

    lock.try_acquire(lock_path)
    # Internal fd should be populated after acquiring.
    assert lock._fd is not None

    lock.release()
    # Internal fd cleared after release.
    assert lock._fd is None
