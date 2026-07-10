"""Unit tests for the Windows file-lock adapters.

On Linux/macOS (non-Windows):
  - The module raises ``PlatformCapabilityError`` at import time.
  - These tests verify the import-guard behavior (tests run on Linux).

On Windows:
  - The full behavior test runs (acquire, is_locked, release, re-entrant
    acquire is not a silent no-op, workspace-lock acquire end-to-end).

The behavior test that requires a Windows runner is marked with
``skipif != win32`` — it PASSES ON A WINDOWS RUNNER but skips on Linux/macOS.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PlatformCapabilityError


def test_import_guard_on_non_windows() -> None:
    """Importing file_lock_windows on non-Windows must raise PlatformCapabilityError."""
    if sys.platform == "win32":
        pytest.skip("This test is for non-Windows platforms only")

    with pytest.raises(PlatformCapabilityError) as exc_info:
        import importlib

        importlib.import_module("dadaia_workspace.infrastructure.file_lock_windows")

    assert exc_info.value.feature_name == "msvcrt_file_lock"
    assert exc_info.value.platform == sys.platform


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows file-lock behavior tests require a Windows runner",
)
def test_windows_lock_acquire_release_noop_and_workspace_lock(tmp_path: Path) -> None:
    """WindowsFileLock: acquire → is_locked True → release → is_locked False; a
    re-entrant acquire is never a silent no-op (raises OSError); and
    WindowsWorkspaceLock.acquire works end-to-end as a context manager."""
    from dadaia_workspace.infrastructure.file_lock_windows import (
        WindowsFileLock,
        WindowsWorkspaceLock,
    )

    lock = WindowsFileLock()
    lock_path = tmp_path / "test.lock"

    fd = lock._lock_file(lock_path)
    assert lock.is_locked(lock_path) is True

    # Re-entrant acquire should fail with OSError (not silently succeed).
    with pytest.raises(OSError):
        fd2 = lock._lock_file(lock_path)
        lock._unlock_file(fd2)

    lock._unlock_file(fd)
    # After release, should no longer be locked.
    assert lock.is_locked(lock_path) is False

    ws_lock = WindowsWorkspaceLock()
    with ws_lock.acquire(tmp_path):
        ws_lock_path = tmp_path / ".dadaia" / "states" / ".ws_lock"
        assert ws_lock_path.exists()
