"""Unit tests for OsProcessProbe (infrastructure layer, T-018-11).

All 7 tests from tests/unit/core/test_process_probe.py are migrated here now
that OsProcessProbe lives in infrastructure/process_probe_adapter.py.

One new test is added:
  - test_probe_returns_false_for_process_lookup_error  (covers ProcessLookupError)
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from dadaia_workspace.core.platform import detect
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

# These tests exercise the POSIX os.kill(pid, 0) liveness semantics by mocking
# os.kill. On Windows the probe takes the OpenProcess branch instead (os.kill is
# not a safe probe there), so force the POSIX capability via the PLATFORM seam so
# the mocked-os.kill path runs on every host.
_FORCE_POSIX = patch(
    "dadaia_workspace.infrastructure.process_probe_adapter.PLATFORM", detect("linux")
)
_FORCE_WINDOWS = patch(
    "dadaia_workspace.infrastructure.process_probe_adapter.PLATFORM", detect("win32")
)


# ---------------------------------------------------------------------------
# Windows OpenProcess probe — branch coverage via a fake kernel32 (runs on any OS)
# ---------------------------------------------------------------------------


class _FakeFn:
    """Callable that also accepts ctypes-style .restype/.argtypes attribute writes."""

    def __init__(self, fn: object) -> None:
        self._fn = fn

    def __call__(self, *args: object) -> object:
        return self._fn(*args)  # type: ignore[operator]


class _FakeKernel32:
    """Minimal kernel32 stand-in for the Windows liveness probe."""

    def __init__(self, *, open_result: int, exit_code: int = 259, get_exit_ok: bool = True) -> None:
        self._exit_code = exit_code
        self._get_exit_ok = get_exit_ok
        self.OpenProcess = _FakeFn(lambda *a: open_result)
        self.GetExitCodeProcess = _FakeFn(self._get_exit)
        self.CloseHandle = _FakeFn(lambda *a: 1)

    def _get_exit(self, handle: object, ptr: object) -> int:
        # ptr is ctypes.byref(c_ulong); byref(x)._obj is x.
        ptr._obj.value = self._exit_code  # type: ignore[attr-defined]
        return 1 if self._get_exit_ok else 0


def _run_windows_probe(
    monkeypatch: pytest.MonkeyPatch, pid: int, fake: _FakeKernel32, *, last_error: int = 0
) -> bool:
    import ctypes

    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: fake, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)
    with _FORCE_WINDOWS:
        return OsProcessProbe().is_pid_alive(pid)


def test_windows_probe_negative_pid_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run_windows_probe(monkeypatch, -1, _FakeKernel32(open_result=0)) is False


def test_windows_probe_invalid_parameter_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    # OpenProcess fails (null) with ERROR_INVALID_PARAMETER (87) -> no such PID -> dead.
    assert (
        _run_windows_probe(monkeypatch, 999, _FakeKernel32(open_result=0), last_error=87) is False
    )


def test_windows_probe_access_denied_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    # OpenProcess fails (null) with ERROR_ACCESS_DENIED (5) -> exists but unprobable -> alive.
    assert _run_windows_probe(monkeypatch, 4, _FakeKernel32(open_result=0), last_error=5) is True


def test_windows_probe_still_active_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    # OpenProcess succeeds; exit code STILL_ACTIVE (259) -> alive.
    assert (
        _run_windows_probe(monkeypatch, 1234, _FakeKernel32(open_result=4242, exit_code=259))
        is True
    )


def test_windows_probe_concrete_exit_code_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    # OpenProcess succeeds but the process has exited with a concrete code -> dead.
    assert (
        _run_windows_probe(monkeypatch, 1234, _FakeKernel32(open_result=4242, exit_code=0)) is False
    )


def test_windows_probe_get_exit_query_fails_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    # GetExitCodeProcess fails -> cannot determine -> conservative alive.
    fake = _FakeKernel32(open_result=4242, get_exit_ok=False)
    assert _run_windows_probe(monkeypatch, 1234, fake) is True


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


def test_pid_zero_returns_a_bool_without_raising() -> None:
    """PID 0 behaviour is platform-defined, so we do not pin True vs False — but the
    probe MUST normalise it to a ``bool`` and never let a platform-specific exception
    (e.g. ``os.kill(0, 0)`` signalling the whole process group) escape its handlers.

    This replaces a non-strict xfail that always XPASSed (it had no assertion, so it
    could never fail and only added XPASS noise to the summary). As a plain contract
    test it now fails on a real regression: an unhandled exception or a non-bool return.
    """
    probe = OsProcessProbe()
    result = probe.is_pid_alive(0)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# New test 8: probe returns False for ProcessLookupError (explicit coverage)
# ---------------------------------------------------------------------------


def test_probe_returns_false_for_process_lookup_error() -> None:
    """ProcessLookupError from os.kill must produce False, not True."""
    probe = OsProcessProbe()
    with _FORCE_POSIX, patch("os.kill", side_effect=ProcessLookupError()):
        assert probe.is_pid_alive(42) is False
