"""Unit tests for WindowsTelemetryRefreshLock.

On Linux/macOS (non-Windows):
  - The Windows no-op adapter can still be imported (it has no platform guard).
  - Tests verify: always-acquire returns True (idempotent), release is a no-op, and
    try_acquire logs at INFO level.

On Windows:
  - The same tests run (the adapter is the production path on Windows), plus a
    real-platform check that no lock file is created (pure no-op).

The WAL-safety-assumption docs (module + class docstring content) are
review-enforced, not test-enforced — no docstring-grep tests here.
"""

from __future__ import annotations

import logging
import sys

import pytest

from dadaia_workspace.infrastructure.telemetry_lock_windows import (
    WindowsTelemetryRefreshLock,
)


def test_noop_behavior_always_acquires_and_release_never_raises(
    tmp_path: str, caplog: pytest.LogCaptureFixture
) -> None:
    """try_acquire always returns True (idempotent, no state tracking); release()
    never raises, with or without a prior try_acquire; and try_acquire emits an
    INFO log explaining the no-op."""
    lock = WindowsTelemetryRefreshLock()
    lock_path = str(tmp_path) + "/telemetry.lock"

    assert lock.try_acquire(lock_path) is True
    assert lock.try_acquire(lock_path) is True  # idempotent

    lock2 = WindowsTelemetryRefreshLock()
    lock2.release()  # no prior acquire — must not raise

    lock.release()  # after acquire — must not raise

    with caplog.at_level(
        logging.INFO, logger="dadaia_workspace.infrastructure.telemetry_lock_windows"
    ):
        lock.try_acquire(lock_path)
    assert len(caplog.records) >= 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert "WindowsTelemetryRefreshLock" in record.message or "no-op" in record.message.lower()


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows no-op telemetry lock behavior test — runs on Windows runner only",
)
def test_windows_noop_does_not_create_lock_file(tmp_path: str) -> None:
    """On Windows, try_acquire should NOT create a lock file (pure no-op)."""
    import os

    lock = WindowsTelemetryRefreshLock()
    lock_path = str(tmp_path) + "/telemetry_windows.lock"
    lock.try_acquire(lock_path)
    assert not os.path.exists(lock_path), "Windows no-op adapter must not create a lock file"
    lock.release()
