"""POSIX file-lock adapters — WorkspaceLock and ContextLock implementations.

This module owns the full low-level fd lifecycle for workspace/context locking:
  - ``os.open`` / ``os.write`` / ``os.close``
  - ``fcntl.flock(LOCK_EX | LOCK_NB)`` / ``fcntl.flock(LOCK_UN)``

``_acquire_flock`` is the polling retry loop.  It is NOT re-exported from
``features/spec_context/locking.py``; tests that need it import it from here
directly.

Consumers (``features/``) call only ``workspace_lock()`` and
``context_lock()`` from ``features/spec_context/locking.py``, which delegate
to the adapters injected at call time via a lazy platform default.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceLockTimeoutError

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_POLL_INTERVAL = 0.05  # 50 ms between retries


def _acquire_flock(fd: int, path: str, timeout: float = _LOCK_TIMEOUT_SECONDS) -> None:
    """Attempt to acquire ``LOCK_EX | LOCK_NB`` in a retry loop.

    Polls every ``_LOCK_POLL_INTERVAL`` seconds rather than sleeping for long
    intervals so the total wait stays bounded and the code stays testable.

    Args:
        fd:      Open file descriptor.
        path:    Path string of the lock file (for error messages only).
        timeout: Maximum seconds to wait before raising.

    Raises:
        WorkspaceLockTimeoutError: Lock not acquired within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            pass
        if time.monotonic() >= deadline:
            # Best-effort: read holder PID from lock file content.
            holder_pid: int | None = None
            with contextlib.suppress(Exception), open(path) as fh:
                holder_pid = int(fh.read().strip())
            raise WorkspaceLockTimeoutError(
                f"Could not acquire workspace lock '{path}' within {timeout}s. "
                + (f"Holder PID: {holder_pid}." if holder_pid else "Holder PID unknown.")
            )
        time.sleep(_LOCK_POLL_INTERVAL)


class PosixWorkspaceLock:
    """POSIX adapter for the workspace-wide exclusive lock.

    File: ``.dadaia/states/.ws_lock``
    Backed by ``fcntl.flock`` with a 5-second polling timeout.
    """

    @contextmanager
    def acquire(self, workspace_root: Path) -> Generator[None, None, None]:
        """Acquire the workspace-wide lock for the duration of the ``with`` block.

        Args:
            workspace_root: Root directory of the initialized dadaia workspace.

        Raises:
            WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
        """
        lock_path = workspace_root / ".dadaia" / "states" / ".ws_lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            os.write(fd, str(os.getpid()).encode())
            _acquire_flock(fd, str(lock_path))
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


class PosixContextLock:
    """POSIX adapter for the per-context exclusive lock.

    File: ``.dadaia/states/ctx_locks/<repo_slug>.lock``
    Two different slugs lock independently; same slug is exclusive.
    Backed by ``fcntl.flock`` with a 5-second polling timeout.
    """

    @contextmanager
    def acquire(self, workspace_root: Path, repo_slug: str) -> Generator[None, None, None]:
        """Acquire the per-context lock for the duration of the ``with`` block.

        Args:
            workspace_root: Root directory of the initialized dadaia workspace.
            repo_slug:      Context identifier (repo slug).

        Raises:
            WorkspaceLockTimeoutError: Lock not acquired within 5 seconds.
        """
        lock_path = workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{repo_slug}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            os.write(fd, str(os.getpid()).encode())
            _acquire_flock(fd, str(lock_path))
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
