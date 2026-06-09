"""Unit tests for OsProcessProbe.is_pid_alive semantics (v0.1.1 / Bug C).

Coverage matrix:
    PID type                          Expected result
    --------------------------------  ---------------
    Own PID (os.getpid())             alive (True)
    Definitely-missing PID (large)    dead (False)
    Root-owned PID (init = 1)         alive (True) via PermissionError → True

PID 0 is kernel; documented as xfail because its behaviour varies by
platform (Linux raises ProcessLookupError on Python 3.12 but the manual
page says EPERM). We do not assert specific behaviour for it.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# Migration note (T-018-03): OsProcessProbe moved to infrastructure.process_probe_adapter.
# This import path is updated here; the full FILE DELETE of test_process_probe.py is
# deferred until tests/unit/infrastructure/test_process_probe_adapter.py is green in CI.
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe


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
    raises PermissionError. The probe MUST treat that as alive — this is the
    core of Bug C.
    """
    probe = OsProcessProbe()
    assert probe.is_pid_alive(1) is True


def test_permission_error_is_treated_as_alive(caplog: pytest.LogCaptureFixture) -> None:
    """Direct mock: regardless of how PermissionError happens, return True
    and do NOT log a warning (PermissionError is the expected case for
    cross-user PIDs)."""
    probe = OsProcessProbe()
    with patch("os.kill", side_effect=PermissionError(1, "Operation not permitted")):
        assert probe.is_pid_alive(12345) is True
    # No warning emitted for PermissionError — it's expected, not anomalous.
    assert not any("unexpected OSError" in rec.message for rec in caplog.records)


def test_process_lookup_error_is_treated_as_dead() -> None:
    probe = OsProcessProbe()
    with patch("os.kill", side_effect=ProcessLookupError(3, "No such process")):
        assert probe.is_pid_alive(12345) is False


def test_unexpected_oserror_is_treated_as_alive_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Conservative default: any other OSError (EINTR, EINVAL, EBUSY...)
    means we cannot determine — assume alive and warn. Better false-active
    than false-stale."""
    import logging

    probe = OsProcessProbe()
    with (
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
