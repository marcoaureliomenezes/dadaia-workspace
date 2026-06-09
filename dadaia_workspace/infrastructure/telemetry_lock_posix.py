"""POSIX telemetry-refresh lock adapter.

This module owns the full fd lifecycle for the telemetry non-blocking lock:
  - ``os.open(lock_path, O_CREAT | O_WRONLY, 0o600)`` — open/create lock file
  - ``fcntl.flock(fd, LOCK_EX | LOCK_NB)`` — try to acquire (non-blocking)
  - ``fcntl.flock(fd, LOCK_UN)`` + ``os.close(fd)`` — release

After this module ships (T-018-04), ``features/telemetry/service.py`` must
not hold a raw file descriptor.  The ``refresh()`` method calls
``try_acquire()`` / ``release()`` on the injected ``TelemetryRefreshLock``
protocol instance instead.
"""

from __future__ import annotations

import fcntl
import logging
import os

logger = logging.getLogger(__name__)


class PosixTelemetryRefreshLock:
    """POSIX implementation of the ``TelemetryRefreshLock`` protocol.

    Non-blocking exclusive lock via ``fcntl.flock(LOCK_EX | LOCK_NB)`` on a
    dedicated ``telemetry.lock`` file.

    The full fd lifecycle is encapsulated here so ``features/`` never touches
    a raw file descriptor (LV-5 in SPEC §4.2).

    Usage::

        lock = PosixTelemetryRefreshLock()
        if lock.try_acquire(str(lock_path)):
            try:
                ...  # do refresh
            finally:
                lock.release()
        else:
            logger.debug("another process is refreshing; skipping")
    """

    def __init__(self) -> None:
        self._fd: int | None = None
        self._lock_path: str | None = None

    def try_acquire(self, lock_path: str) -> bool:
        """Attempt a non-blocking exclusive lock on *lock_path*.

        Args:
            lock_path: Absolute path string to the lock file.

        Returns:
            ``True`` if the lock was acquired successfully.
            ``False`` if another process holds the lock (``BlockingIOError``).
        """
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o600)
        except OSError as exc:
            logger.warning("PosixTelemetryRefreshLock: cannot open lock file: %s", exc)
            return False

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return False

        self._fd = fd
        self._lock_path = lock_path
        return True

    def release(self) -> None:
        """Unlock and close the file descriptor acquired by ``try_acquire``.

        No-op if the lock is not currently held (defensive).
        """
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            self._lock_path = None
