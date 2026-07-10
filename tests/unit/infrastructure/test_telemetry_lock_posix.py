"""Unit tests for PosixTelemetryRefreshLock.

These tests run only on POSIX platforms (fcntl is not available on Windows).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Collection-safe guard (F-14): the infrastructure import below pulls in fcntl at
# import time, before any skipif mark applies — importorskip skips the whole module
# on platforms without fcntl (Windows) instead of erroring collection.
pytest.importorskip("fcntl")

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="fcntl telemetry locks are only available on POSIX platforms",
)

from dadaia_workspace.infrastructure.telemetry_lock_posix import PosixTelemetryRefreshLock


def test_try_acquire_returns_false_when_held(tmp_path: Path) -> None:
    """Non-blocking contention: a second instance sees the lock as held and gets
    False immediately; after the holder releases, the contender can acquire."""
    lock_path = str(tmp_path / "telemetry.lock")

    holder = PosixTelemetryRefreshLock()
    assert holder.try_acquire(lock_path) is True

    contender = PosixTelemetryRefreshLock()
    assert contender.try_acquire(lock_path) is False

    holder.release()
    assert contender.try_acquire(lock_path) is True
    contender.release()


def test_lock_lifecycle_and_fd_encapsulation(tmp_path: Path) -> None:
    """Create / release / re-acquire lifecycle, no-op release when not held, and
    the full fd lifecycle (os.open, fcntl.flock, os.close) stays fully encapsulated
    behind try_acquire/release — a caller never manages a raw fd (LV-5)."""
    lock = PosixTelemetryRefreshLock()
    lock_path = str(tmp_path / "telemetry.lock")

    # Not-yet-held release is a no-op.
    lock.release()

    assert lock._fd is None
    assert lock.try_acquire(lock_path) is True
    assert Path(lock_path).exists()
    assert lock._fd is not None
    lock.release()
    assert lock._fd is None

    # Re-acquiring after release succeeds.
    assert lock.try_acquire(lock_path) is True
    lock.release()
