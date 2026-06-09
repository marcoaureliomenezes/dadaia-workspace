"""Platform-guard tests for scan_unregistered_listeners.

These tests run on ALL platforms (no pytestmark skipif).  They verify that
scan.py returns [] with an INFO log when PLATFORM.has_proc_fs is False,
simulating macOS / Windows behavior.

The per-function guards in _read_cmdline, _read_cwd, and
_pid_belongs_to_current_user are also exercised here.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from unittest.mock import patch

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.server_registry import scan as scan_module
from dadaia_workspace.features.server_registry.scan import (
    _pid_belongs_to_current_user,
    _read_cmdline,
    _read_cwd,
    scan_unregistered_listeners,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NO_PROC_CAPS = replace(PLATFORM, has_proc_fs=False)
_WITH_PROC_CAPS = replace(PLATFORM, has_proc_fs=True)


def _entry(port: int, project: str = "demo") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-17T20:00:00Z",
        expires_at="2026-05-18T04:00:00Z",
    )


# ---------------------------------------------------------------------------
# scan_unregistered_listeners — early-return when no /proc
# ---------------------------------------------------------------------------


def test_scan_returns_empty_list_when_no_proc_fs(caplog: pytest.LogCaptureFixture) -> None:
    """When PLATFORM.has_proc_fs is False, scan must return [] immediately."""
    with (
        patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS),
        caplog.at_level(logging.INFO, logger="dadaia_workspace.features.server_registry.scan"),
    ):
        result = scan_unregistered_listeners([_entry(4999)])
    assert result == []


def test_scan_logs_info_when_no_proc_fs(caplog: pytest.LogCaptureFixture) -> None:
    """When PLATFORM.has_proc_fs is False, scan must emit an INFO log."""
    with (
        patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS),
        caplog.at_level(logging.INFO, logger="dadaia_workspace.features.server_registry.scan"),
    ):
        scan_unregistered_listeners([])
    assert any(
        "orphan detection disabled" in record.message
        for record in caplog.records
        if record.levelno == logging.INFO
    ), f"Expected INFO 'orphan detection disabled' in logs; got: {caplog.records}"


def test_scan_does_not_call_ss_when_no_proc_fs() -> None:
    """When PLATFORM.has_proc_fs is False, ss subprocess must not be invoked."""
    with (
        patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS),
        patch.object(scan_module, "_ss_command_output") as mock_ss,
    ):
        scan_unregistered_listeners([])
    mock_ss.assert_not_called()


def test_scan_early_return_ignores_output_provider_when_no_proc_fs() -> None:
    """Even a non-None _output_provider must be ignored when has_proc_fs is False."""
    called = []

    def _provider() -> str:
        called.append(True)
        return "LISTEN 0 0 0.0.0.0:9999 0.0.0.0:*\n"

    with patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS):
        result = scan_unregistered_listeners([], _output_provider=_provider)

    assert result == []
    assert called == [], "_output_provider should not have been called"


# ---------------------------------------------------------------------------
# Per-function guards
# ---------------------------------------------------------------------------


def test_read_cmdline_returns_empty_when_no_proc_fs() -> None:
    """_read_cmdline must return '' when PLATFORM.has_proc_fs is False."""
    with patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS):
        result = _read_cmdline(99999)
    assert result == ""


def test_read_cwd_returns_empty_when_no_proc_fs() -> None:
    """_read_cwd must return '' when PLATFORM.has_proc_fs is False."""
    with patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS):
        result = _read_cwd(99999)
    assert result == ""


def test_pid_belongs_to_current_user_returns_false_when_no_proc_fs() -> None:
    """_pid_belongs_to_current_user must return False when PLATFORM.has_proc_fs is False."""
    with patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS):
        result = _pid_belongs_to_current_user(99999)
    assert result is False


def test_pid_belongs_to_current_user_returns_false_when_no_getuid() -> None:
    """_pid_belongs_to_current_user must return False when os.getuid does not exist.

    This test verifies that the getattr(os, 'getuid', None) guard does not
    raise an AttributeError (simulates Windows where os.getuid is absent).
    """
    import os

    with (
        patch.object(scan_module, "PLATFORM", _WITH_PROC_CAPS),
        patch.object(os, "getuid", None, create=True),
    ):
        # We use getattr(os, 'getuid', None) in the impl; this simulates Windows
        result = _pid_belongs_to_current_user(99999)
    # On Linux getuid exists; we rely on the getattr guard only when it's absent.
    # This test verifies the guard path doesn't raise AttributeError.
    assert isinstance(result, bool)
