"""Unit tests for PosixWorkspaceLock, PosixContextLock, and _acquire_flock.

These tests run only on POSIX platforms (fcntl is not available on Windows).
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

# Collection-safe guard (F-14): the infrastructure imports below pull in fcntl at
# import time, before any skipif mark applies — importorskip skips the whole module
# on platforms without fcntl (Windows) instead of erroring collection.
pytest.importorskip("fcntl")

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


def test_acquire_flock_times_out_when_held(tmp_path: Path) -> None:
    """_acquire_flock raises WorkspaceLockTimeoutError when the lock is held by
    another fd — real fcntl contention, not a mock."""
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


def test_workspace_lock_exclusive_blocks_concurrent(tmp_path: Path) -> None:
    """Concurrent workspace locks on the same root are serialized (real thread
    contention, not a mock)."""
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


@pytest.mark.parametrize(
    "case",
    [
        "acquire-flock-succeeds-on-free-file",
        "workspace-lock-creates-file",
        "workspace-lock-releases-after-exit",
        "context-lock-creates-slug-file",
        "context-lock-independent-slugs",
        "context-lock-same-slug-releases",
    ],
)
def test_lock_lifecycle(tmp_path: Path, case: str) -> None:
    """Create / release / re-acquire lifecycle for both PosixWorkspaceLock and
    PosixContextLock (identical acquire/release contract, different scope)."""
    if case == "acquire-flock-succeeds-on-free-file":
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

    elif case == "workspace-lock-creates-file":
        lock_dir = tmp_path / ".dadaia" / "states"
        # Do not pre-create the directory — acquire should mkdir.
        lock = PosixWorkspaceLock()
        with lock.acquire(tmp_path):
            assert (lock_dir / ".ws_lock").exists()

    elif case == "workspace-lock-releases-after-exit":
        lock = PosixWorkspaceLock()
        with lock.acquire(tmp_path):
            pass
        # Should not raise — lock was released.
        with lock.acquire(tmp_path):
            pass

    elif case == "context-lock-creates-slug-file":
        lock = PosixContextLock()
        with lock.acquire(tmp_path, "my-project"):
            lock_path = tmp_path / ".dadaia" / "states" / "ctx_locks" / "my-project.lock"
            assert lock_path.exists()

    elif case == "context-lock-independent-slugs":
        lock = PosixContextLock()
        # Both should succeed without deadlock.
        with lock.acquire(tmp_path, "slug-a"), lock.acquire(tmp_path, "slug-b"):
            pass

    else:  # context-lock-same-slug-releases
        lock = PosixContextLock()
        with lock.acquire(tmp_path, "my-project"):
            pass
        # Should not raise — lock was released.
        with lock.acquire(tmp_path, "my-project"):
            pass
