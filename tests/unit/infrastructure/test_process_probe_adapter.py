"""Unit tests for OsProcessProbe (infrastructure layer, T-018-11).

All 7 tests from tests/unit/core/test_process_probe.py are migrated here now
that OsProcessProbe lives in infrastructure/process_probe_adapter.py.

Two new tests are added:
  - test_probe_returns_false_for_process_lookup_error  (covers ProcessLookupError)
  - test_workflow_launcher_delegates_is_alive_to_probe (T-018-11 delegation)
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from dadaia_workspace.core.platform import detect
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe
from dadaia_workspace.infrastructure.workflow_launcher_adapter import SubprocessWorkflowLauncher

# These tests exercise the POSIX os.kill(pid, 0) liveness semantics by mocking
# os.kill. On Windows the probe takes the OpenProcess branch instead (os.kill is
# not a safe probe there), so force the POSIX capability via the PLATFORM seam so
# the mocked-os.kill path runs on every host.
_FORCE_POSIX = patch(
    "dadaia_workspace.infrastructure.process_probe_adapter.PLATFORM", detect("linux")
)

# ---------------------------------------------------------------------------
# 1–7: Migrated from test_process_probe.py
# ---------------------------------------------------------------------------


def test_own_pid_is_alive() -> None:
    probe = OsProcessProbe()
    assert probe.is_pid_alive(os.getpid()) is True


def test_missing_pid_is_dead() -> None:
    probe = OsProcessProbe()
    # 99_999_999 is well above any realistic PID on Linux (default pid_max is
    # 4_194_304). ProcessLookupError → False.
    assert probe.is_pid_alive(99_999_999) is False


@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="Test is meaningful only as non-root user on POSIX",
)
def test_root_owned_pid_is_alive_via_permission_error() -> None:
    """PID 1 (init/systemd) is root-owned. As a non-root user, os.kill(1, 0)
    raises PermissionError. The probe MUST treat that as alive (Bug C fix).
    """
    probe = OsProcessProbe()
    assert probe.is_pid_alive(1) is True


def test_permission_error_is_treated_as_alive(caplog: pytest.LogCaptureFixture) -> None:
    """Direct mock: regardless of how PermissionError happens, return True
    and do NOT log a warning (PermissionError is expected for cross-user PIDs).
    """
    probe = OsProcessProbe()
    with _FORCE_POSIX, patch("os.kill", side_effect=PermissionError(1, "Operation not permitted")):
        assert probe.is_pid_alive(12345) is True
    # No warning emitted for PermissionError — it's expected, not anomalous.
    assert not any("unexpected OSError" in rec.message for rec in caplog.records)


def test_process_lookup_error_is_treated_as_dead() -> None:
    probe = OsProcessProbe()
    with _FORCE_POSIX, patch("os.kill", side_effect=ProcessLookupError(3, "No such process")):
        assert probe.is_pid_alive(12345) is False


def test_unexpected_oserror_is_treated_as_alive_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Conservative default: any other OSError means we cannot determine —
    assume alive and warn. Better false-active than false-stale.
    """
    import logging

    probe = OsProcessProbe()
    with (
        _FORCE_POSIX,
        caplog.at_level(logging.WARNING),
        patch("os.kill", side_effect=OSError(99, "Some weird error")),
    ):
        assert probe.is_pid_alive(12345) is True
    assert any("unexpected OSError" in rec.message for rec in caplog.records)


@pytest.mark.xfail(reason="PID 0 behaviour is platform-defined; we do not assert.")
def test_pid_zero_documented_as_xfail() -> None:
    probe = OsProcessProbe()
    # Either True or False is acceptable for PID 0. We just exercise the path.
    probe.is_pid_alive(0)


# ---------------------------------------------------------------------------
# New test 8: probe returns False for ProcessLookupError (explicit coverage)
# ---------------------------------------------------------------------------


def test_probe_returns_false_for_process_lookup_error() -> None:
    """ProcessLookupError from os.kill must produce False, not True."""
    probe = OsProcessProbe()
    with patch("os.kill", side_effect=ProcessLookupError()):
        assert probe.is_pid_alive(42) is False


# ---------------------------------------------------------------------------
# New test 9: SubprocessWorkflowLauncher.is_alive delegates to OsProcessProbe
# ---------------------------------------------------------------------------


def test_workflow_launcher_delegates_is_alive_to_probe() -> None:
    """T-018-11: is_alive must delegate to OsProcessProbe, not re-implement os.kill."""
    launcher = SubprocessWorkflowLauncher()

    # Monkeypatch the module-level _probe in the adapter module so we can
    # observe delegation.
    import dadaia_workspace.infrastructure.workflow_launcher_adapter as _wla

    class _TracingProbe:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def is_pid_alive(self, pid: int) -> bool:
            self.calls.append(pid)
            return True

    tracer = _TracingProbe()
    original_probe = _wla._probe
    _wla._probe = tracer  # type: ignore[assignment]
    try:
        result = launcher.is_alive(12345)
    finally:
        _wla._probe = original_probe

    assert result is True
    assert tracer.calls == [12345], "is_alive must delegate to the probe with the given pid"


@pytest.mark.skipif(
    not hasattr(os, "kill"),
    reason="os.kill not available on this platform",
)
def test_workflow_launcher_is_alive_true_for_self() -> None:
    """is_alive must return True for the current process's PID."""
    launcher = SubprocessWorkflowLauncher()
    assert launcher.is_alive(os.getpid()) is True


@pytest.mark.skipif(
    not hasattr(os, "kill"),
    reason="os.kill not available on this platform",
)
def test_workflow_launcher_is_alive_false_for_dead_pid() -> None:
    """is_alive must return False for a PID that definitely doesn't exist."""
    launcher = SubprocessWorkflowLauncher()
    assert launcher.is_alive(2**22 - 1) is False
