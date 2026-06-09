"""TelemetryRefreshLock Protocol — serializes concurrent telemetry refreshes.

The concrete POSIX implementation lives in
``dadaia_workspace.infrastructure.telemetry_lock_posix``; the Windows
always-acquire no-op lives in
``dadaia_workspace.infrastructure.telemetry_lock_windows``.

``core/`` is zero-I/O — only the Protocol definition lives here.
"""

from __future__ import annotations

from typing import Protocol


class TelemetryRefreshLock(Protocol):
    """Non-blocking exclusive lock for the telemetry refresh cycle.

    Acquire semantics:
    - Returns ``True`` when the lock was acquired (caller should refresh).
    - Returns ``False`` when the lock is held by another process (caller
      should skip refresh silently — see D-AM-11).

    The full fd lifecycle (``os.open``, ``os.write``, ``os.close``,
    ``os.flock(LOCK_UN)``) is hidden inside the concrete adapter.
    ``features/`` never holds a raw file descriptor.

    Tier (POSIX): operational — serializes refreshes; not a security control.
    Tier (Windows, no-op): safe because SQLite WAL mode provides its own
    write serialization; the Windows always-acquire no-op is not a
    correctness risk while WAL mode is enabled.
    """

    def try_acquire(self, lock_path: str) -> bool:
        """Attempt a non-blocking acquire.

        Args:
            lock_path: Absolute path string to the lock file.

        Returns:
            ``True`` if the lock was acquired; ``False`` if already held.
        """
        ...

    def release(self) -> None:
        """Release the currently-held lock (unlock + close fd).

        Must be called exactly once after a successful ``try_acquire``.
        """
        ...
