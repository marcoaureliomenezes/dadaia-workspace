"""Windows telemetry-refresh lock adapter — always-acquire no-op.

Tier 2 degradation (SPEC §5): the Windows telemetry refresh lock is always
acquired immediately (no blocking, no actual serialization).  This is safe
because SQLite WAL mode provides its own write serialization; this no-op is
not a correctness risk.

IMPORTANT SAFETY ASSUMPTION: this adapter's correctness depends on SQLite WAL
mode being enabled on the telemetry database.  WAL mode serializes concurrent
writers internally, so the absence of an OS-level advisory lock does not
create data corruption risk.  If WAL mode is ever disabled, this adapter MUST
be revisited — a proper Windows locking mechanism (e.g. ``msvcrt.locking``)
would be required.

This is a Tier 2 degradation: non-security feature, logged at INFO level.
Contrast with Tier 1 (FAIL LOUD) for ``WindowsFilePermissionSetter``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WindowsTelemetryRefreshLock:
    """Windows always-acquire no-op implementation of ``TelemetryRefreshLock``.

    ``try_acquire`` always returns ``True`` (no real locking).
    ``release`` is a no-op.

    Safety assumption: safe because SQLite WAL mode provides its own write
    serialization; this no-op is not a correctness risk.  If WAL mode is ever
    disabled, this adapter must be revisited.
    """

    def try_acquire(self, lock_path: str) -> bool:
        """Always returns ``True`` (no-op lock on Windows).

        Args:
            lock_path: Ignored on Windows — no file is opened or locked.

        Returns:
            Always ``True``.
        """
        logger.info(
            "WindowsTelemetryRefreshLock: no-op lock on Windows for %s. "
            "Correctness relies on SQLite WAL mode write serialization.",
            lock_path,
        )
        return True

    def release(self) -> None:
        """No-op on Windows — no file descriptor was opened."""
