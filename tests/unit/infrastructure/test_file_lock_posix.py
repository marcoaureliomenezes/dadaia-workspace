"""Unit tests for PosixWorkspaceLock, PosixContextLock, and _acquire_flock.

These tests run only on POSIX platforms (fcntl is not available on Windows).
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="fcntl file locks are only available on POSIX platforms",
)

from dadaia_workspace.core.exceptions import WorkspaceLockTimeoutError
from dadaia_workspace.infrastructure.file_lock_posix import (
    PosixContextLock,
    PosixWorkspaceLock,
    _acquire_flock,
)


# ---------------------------------------------------------------------------
# _acquire_flock — unit tests
# ---------------------------------------------------------------------------


def test_acquire_flock_succeeds_on_free_file(tmp_path: Path) -> None:
    """_acquire_flock acquires the lock when the file is free."""
    import fcntl
    import os

    lock_file = tmp_path / ".ws_lock"
    fd = os.open(str(lock_file), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        _acquire_flock(fd, str(lock_file))
        # If we got here, lock was acquired. Release it.
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def test_acquire_flock_times_out_when_held(tmp_path: Path) -> None:
    """_acquire_flock raises WorkspaceLockTimeoutError when lock is held."""
    import fcntl
    import os

    lock_file = tmp_path / ".ws_lock"
    # Open and hold the lock in the main thread.
    holder_fd = os.open(str(lock_file), os.O_WRONLY | os.O_CREAT, 0o600)
    fcntl.flock(holder_fd, fcntl.LOCK_EX)

    # Try to acquire from a second fd — should time out fast.
    contender_fd = os.open(str(lock_file), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        with pytest.raises(WorkspaceLockTimeoutError):
            _acquire_flock(contender_fd, str(lock_file), timeout=0.1)
    finally:
        os.close(contender_fd)
        fcntl.flock(holder_fd, fcntl.LOCK_UN)
        os.close(holder_fd)


# ---------------------------------------------------------------------------
# PosixWorkspaceLock — context manager tests
# ---------------------------------------------------------------------------


def test_workspace_lock_creates_lock_file(tmp_path: Path) -> None:
    """PosixWorkspaceLock.acquire creates the .ws_lock file if absent."""
    lock_dir = tmp_path / ".dadaia" / "states"
    # Do not pre-create the directory — acquire should mkdir.
    lock = PosixWorkspaceLock()
    with lock.acquire(tmp_path):
        assert (lock_dir / ".ws_lock").exists()


def test_workspace_lock_releases_after_exit(tmp_path: Path) -> None:
    """A second acquire succeeds immediately after the first context exits."""
    lock = PosixWorkspaceLock()
    with lock.acquire(tmp_path):
        pass
    # Should not raise — lock was released.
    with lock.acquire(tmp_path):
        pass


def test_workspace_lock_exclusive_blocks_concurrent(tmp_path: Path) -> None:
    """Concurrent workspace locks on the same root are serialized."""
    lock = PosixWorkspaceLock()
    results: list[str] = []
    barrier = threading.Barrier(2)

    def holder() -> None:
        with lock.acquire(tmp_path):
            barrier.wait()  # signal: I hold the lock
            time.sleep(0.1)
            results.append("holder_done")

    def waiter() -> None:
        barrier.wait()  # wait until holder has the lock
        with lock.acquire(tmp_path):
            results.append("waiter_acquired")

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=waiter)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert results[0] == "holder_done", "Waiter must not acquire before holder releases"
    assert results[1] == "waiter_acquired"


# ---------------------------------------------------------------------------
# PosixContextLock — context manager tests
# ---------------------------------------------------------------------------


def test_context_lock_creates_lock_file(tmp_path: Path) -> None:
    """PosixContextLock.acquire creates the slug lock file."""
    lock = PosixContextLock()
    with lock.acquire(tmp_path, "my-project"):
        lock_path = tmp_path / ".dadaia" / "states" / "ctx_locks" / "my-project.lock"
        assert lock_path.exists()


def test_context_lock_independent_slugs(tmp_path: Path) -> None:
    """Locks for different slugs are independent and can be held simultaneously."""
    lock = PosixContextLock()
    # Both should succeed without deadlock.
    with lock.acquire(tmp_path, "slug-a"), lock.acquire(tmp_path, "slug-b"):
        pass


def test_context_lock_same_slug_releases(tmp_path: Path) -> None:
    """Re-acquiring a context lock on the same slug succeeds after release."""
    lock = PosixContextLock()
    with lock.acquire(tmp_path, "my-project"):
        pass
    # Should not raise — lock was released.
    with lock.acquire(tmp_path, "my-project"):
        pass
