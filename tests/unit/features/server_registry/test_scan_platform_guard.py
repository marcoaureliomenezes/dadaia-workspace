"""Platform-guard tests for scan_unregistered_listeners.

These tests run on ALL platforms (no pytestmark skipif). They verify that
scan.py returns [] with an INFO log when PLATFORM.has_proc_fs is False,
simulating macOS / Windows behavior — every facet of that single guard is
merged into one test; the per-function guards (_read_cmdline, _read_cwd,
_pid_belongs_to_current_user) are merged into a second parametrized test.
"""

from __future__ import annotations

import logging
import os
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

_NO_PROC_CAPS = replace(PLATFORM, has_proc_fs=False)
_WITH_PROC_CAPS = replace(PLATFORM, has_proc_fs=True)


def _entry(port: int, project: str = "demo") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-17T20:00:00Z",
        expires_at="2026-05-18T04:00:00Z",
    )


def test_scan_inert_when_no_proc_fs(caplog: pytest.LogCaptureFixture) -> None:
    """When PLATFORM.has_proc_fs is False, scan is entirely inert: returns [],
    logs INFO, never invokes ss, and ignores even a non-None _output_provider."""
    called: list[bool] = []

    def _provider() -> str:
        called.append(True)
        return "LISTEN 0 0 0.0.0.0:9999 0.0.0.0:*\n"

    with (
        patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS),
        patch.object(scan_module, "_ss_command_output") as mock_ss,
        caplog.at_level(logging.INFO, logger="dadaia_workspace.features.server_registry.scan"),
    ):
        result = scan_unregistered_listeners([_entry(4999)], _output_provider=_provider)

    assert result == []
    assert called == [], "_output_provider should not have been called"
    mock_ss.assert_not_called()
    assert any(
        "orphan detection disabled" in record.message
        for record in caplog.records
        if record.levelno == logging.INFO
    ), f"Expected INFO 'orphan detection disabled' in logs; got: {caplog.records}"


@pytest.mark.parametrize(
    ("case", "call"),
    [
        pytest.param(
            "read-cmdline",
            lambda: _read_cmdline(99999),
            id="read_cmdline-returns-empty-when-no-proc-fs",
        ),
        pytest.param(
            "read-cwd",
            lambda: _read_cwd(99999),
            id="read_cwd-returns-empty-when-no-proc-fs",
        ),
        pytest.param(
            "pid-belongs",
            lambda: _pid_belongs_to_current_user(99999),
            id="pid_belongs_to_current_user-returns-false-when-no-proc-fs",
        ),
    ],
)
def test_per_function_guards_when_no_proc_fs(case: str, call) -> None:  # type: ignore[no-untyped-def]
    with patch.object(scan_module, "PLATFORM", _NO_PROC_CAPS):
        result = call()
    if case == "pid-belongs":
        assert result is False
    else:
        assert result == ""


def test_pid_belongs_to_current_user_guards_missing_getuid() -> None:
    """_pid_belongs_to_current_user must not raise AttributeError when os.getuid is
    absent (simulates Windows) — the getattr(os, 'getuid', None) guard path."""
    with (
        patch.object(scan_module, "PLATFORM", _WITH_PROC_CAPS),
        patch.object(os, "getuid", None, create=True),
    ):
        result = _pid_belongs_to_current_user(99999)
    assert isinstance(result, bool)
