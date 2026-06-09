"""Windows file-lock adapters — WorkspaceLock and ContextLock implementations.

On Windows, ``fcntl`` is not available.  This module uses ``msvcrt.locking``
(stdlib, zero new PyPI dependencies) per ADR-2.

If ``msvcrt`` is unavailable (e.g. non-CPython runtime), construction raises
``PlatformCapabilityError`` immediately rather than providing a silent no-op.
A no-op lock is worse than no lock — it creates false serialization confidence
(ADR-2, SPEC §5 Tier 1).

Import guard: this module is imported only on Windows (``sys.platform == 'win32'``)
or when explicitly requested.  On non-Windows it raises ``PlatformCapabilityError``
at import time so the container can gate selection by ``PLATFORM.has_fcntl``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from dadaia_workspace.core.exceptions import PlatformCapabilityError

# Raise immediately on non-Windows so the container / tests get a clean error.
if sys.platform != "win32":  # pragma: no cover
    raise PlatformCapabilityError(
        "file_lock_windows is only available on Windows (sys.platform == 'win32'). "
        "Use file_lock_posix on POSIX platforms.",
        feature_name="msvcrt_file_lock",
        platform=sys.platform,
    )

try:
    import msvcrt
except ImportError as exc:  # pragma: no cover
    raise PlatformCapabilityError(
        "msvcrt is not available on this Python runtime. "
        "Cannot provide file locking on Windows without msvcrt.",
        feature_name="msvcrt_file_lock",
        platform="win32",
    ) from exc

_LOCK_BYTES = 1  # Number of bytes to lock with msvcrt.locking


class WindowsFileLock:
    """Windows exclusive file lock backed by ``msvcrt.locking``.

    ``msvcrt.locking`` provides byte-range locking within a file.  We lock
    1 byte at offset 0 to simulate an exclusive lock (common pattern for
    Windows advisory locks).

    Never a silent no-op: if ``msvcrt`` is absent, construction raises
    ``PlatformCapabilityError`` (see module-level import guard).
    """

    def __init__(self) -> None:
        # Verify msvcrt is importable.  The module-level guard above already
        # does this, but we keep a constructor check so subclasses / tests can
        # instantiate cleanly.
        try:
            import msvcrt as _m  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise PlatformCapabilityError(
                "msvcrt is not available; cannot create WindowsFileLock.",
                feature_name="msvcrt_file_lock",
                platform="win32",
            ) from exc

    def _lock_file(self, path: Path) -> int:
        """Open *path* for read/write and acquire an exclusive byte-range lock.

        Returns the file descriptor (caller must unlock and close).
        """
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT)
        # Seek to offset 0, then lock 1 byte exclusively.
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, _LOCK_BYTES)
        except OSError:
            os.close(fd)
            raise
        return fd

    def _unlock_file(self, fd: int) -> None:
        """Unlock and close *fd*."""
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, _LOCK_BYTES)
        finally:
            os.close(fd)

    def is_locked(self, path: Path) -> bool:
        """Return ``True`` if *path* is currently locked by any process.

        Attempts a non-blocking lock; if it fails, the file is locked.
        Does NOT acquire the lock persistently.
        """
        try:
            fd = self._lock_file(path)
        except OSError:
            return True
        self._unlock_file(fd)
        return False


class WindowsWorkspaceLock:
    """Windows adapter for the workspace-wide exclusive lock.

    Uses ``msvcrt.locking`` on ``.dadaia/states/.ws_lock``.
    Never a silent no-op — raises ``PlatformCapabilityError`` if ``msvcrt``
    is unavailable.
    """

    def __init__(self) -> None:
        self._impl = WindowsFileLock()

    @contextmanager
    def acquire(self, workspace_root: Path) -> Generator[None, None, None]:
        """Acquire the workspace-wide lock for the duration of the ``with`` block."""
        lock_path = workspace_root / ".dadaia" / "states" / ".ws_lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = self._impl._lock_file(lock_path)
        try:
            yield
        finally:
            self._impl._unlock_file(fd)


class WindowsContextLock:
    """Windows adapter for the per-context exclusive lock.

    Uses ``msvcrt.locking`` on ``.dadaia/states/ctx_locks/<repo_slug>.lock``.
    Never a silent no-op — raises ``PlatformCapabilityError`` if ``msvcrt``
    is unavailable.
    """

    def __init__(self) -> None:
        self._impl = WindowsFileLock()

    @contextmanager
    def acquire(self, workspace_root: Path, repo_slug: str) -> Generator[None, None, None]:
        """Acquire the per-context lock for the duration of the ``with`` block."""
        lock_path = workspace_root / ".dadaia" / "states" / "ctx_locks" / f"{repo_slug}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = self._impl._lock_file(lock_path)
        try:
            yield
        finally:
            self._impl._unlock_file(fd)
