"""Unit tests for WindowsTelemetryRefreshLock.

On Linux/macOS (non-Windows):
  - The Windows no-op adapter can still be imported (it has no platform guard).
  - Tests verify: always-acquire returns True, release is a no-op,
    try_acquire logs at INFO level, docstring documents the SQLite WAL
    safety assumption.

On Windows:
  - The same tests run (the adapter is the production path on Windows).

Behavior tests that require Windows behavior are marked with
``skipif != win32`` if they exercise real Windows semantics.  The no-op
tests below run on all platforms because the no-op adapter is importable
everywhere.
"""

from __future__ import annotations

import logging
import sys

import pytest

from dadaia_workspace.infrastructure.telemetry_lock_windows import (
    WindowsTelemetryRefreshLock,
)


# ---------------------------------------------------------------------------
# Always-acquire behavior (verifiable on all platforms)
# ---------------------------------------------------------------------------


def test_try_acquire_always_returns_true(tmp_path: str) -> None:
    """WindowsTelemetryRefreshLock.try_acquire always returns True (no-op lock)."""
    lock = WindowsTelemetryRefreshLock()
    result = lock.try_acquire(str(tmp_path) + "/telemetry.lock")
    assert result is True


def test_try_acquire_second_call_also_returns_true(tmp_path: str) -> None:
    """Multiple calls to try_acquire all return True (no state tracking)."""
    lock = WindowsTelemetryRefreshLock()
    lock_path = str(tmp_path) + "/telemetry.lock"
    assert lock.try_acquire(lock_path) is True
    assert lock.try_acquire(lock_path) is True


def test_release_is_noop(tmp_path: str) -> None:
    """release() does not raise — it is a no-op on Windows."""
    lock = WindowsTelemetryRefreshLock()
    lock.release()  # Should not raise, even without a prior try_acquire.


def test_release_after_acquire_does_not_raise(tmp_path: str) -> None:
    """release() after try_acquire does not raise."""
    lock = WindowsTelemetryRefreshLock()
    lock.try_acquire(str(tmp_path) + "/telemetry.lock")
    lock.release()  # Should not raise.


# ---------------------------------------------------------------------------
# INFO log on try_acquire
# ---------------------------------------------------------------------------


def test_try_acquire_logs_info(tmp_path: str, caplog: pytest.LogCaptureFixture) -> None:
    """try_acquire emits an INFO log explaining the no-op and WAL assumption."""
    lock = WindowsTelemetryRefreshLock()
    lock_path = str(tmp_path) + "/telemetry.lock"

    with caplog.at_level(
        logging.INFO, logger="dadaia_workspace.infrastructure.telemetry_lock_windows"
    ):
        lock.try_acquire(lock_path)

    assert len(caplog.records) >= 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    # The log message should mention the lock path and WAL assumption.
    assert "WindowsTelemetryRefreshLock" in record.message or "no-op" in record.message.lower()


# ---------------------------------------------------------------------------
# SQLite WAL safety assumption — docstring presence
# ---------------------------------------------------------------------------


def test_windows_telemetry_lock_docstring_documents_wal_assumption() -> None:
    """WindowsTelemetryRefreshLock docstring MUST document the SQLite WAL safety assumption.

    Per SPEC §5 Tier 2: 'The WindowsTelemetryRefreshLock adapter docstring MUST
    document this assumption explicitly: safe because SQLite WAL mode provides its
    own write serialization; this no-op is not a correctness risk.'
    """
    doc = WindowsTelemetryRefreshLock.__doc__
    assert doc is not None, "WindowsTelemetryRefreshLock must have a docstring"
    doc_lower = doc.lower()
    # The docstring must mention both WAL mode and correctness/safety.
    assert "wal" in doc_lower, (
        "WindowsTelemetryRefreshLock docstring must mention 'WAL' mode (SQLite WAL safety assumption)"
    )
    assert "correctness" in doc_lower or "serializ" in doc_lower, (
        "WindowsTelemetryRefreshLock docstring must document the WAL serialization safety rationale"
    )


def test_module_docstring_documents_wal_assumption() -> None:
    """The module docstring MUST also document the SQLite WAL safety assumption.

    Per SPEC §5 Tier 2 and the done-criterion for T-018-04.
    """
    import dadaia_workspace.infrastructure.telemetry_lock_windows as module

    doc = module.__doc__
    assert doc is not None, "telemetry_lock_windows module must have a docstring"
    doc_lower = doc.lower()
    assert "wal" in doc_lower, (
        "telemetry_lock_windows module docstring must mention 'WAL' (SQLite WAL safety assumption)"
    )


# ---------------------------------------------------------------------------
# Windows-specific behavior (skip on non-Windows; run on Windows runner)
# ---------------------------------------------------------------------------


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
    # The no-op adapter should not create a lock file.
    assert not os.path.exists(lock_path), "Windows no-op adapter must not create a lock file"
    lock.release()
