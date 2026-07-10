"""Unit tests for OsProcessProbe (infrastructure layer, T-018-11)."""

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


@pytest.mark.parametrize(
    ("pid", "fake_kwargs", "last_error", "expected"),
    [
        pytest.param(-1, {"open_result": 0}, 0, False, id="negative-pid-is-dead"),
        pytest.param(
            999, {"open_result": 0}, 87, False, id="invalid-parameter-no-such-pid-is-dead"
        ),
        pytest.param(4, {"open_result": 0}, 5, True, id="access-denied-exists-unprobable-is-alive"),
        pytest.param(
            1234,
            {"open_result": 4242, "exit_code": 259},
            0,
            True,
            id="still-active-exit-code-is-alive",
        ),
        pytest.param(
            1234,
            {"open_result": 4242, "exit_code": 0},
            0,
            False,
            id="concrete-exit-code-is-dead",
        ),
        pytest.param(
            1234,
            {"open_result": 4242, "get_exit_ok": False},
            0,
            True,
            id="get-exit-query-fails-conservative-alive",
        ),
    ],
)
def test_windows_probe_matrix(
    monkeypatch: pytest.MonkeyPatch,
    pid: int,
    fake_kwargs: dict[str, object],
    last_error: int,
    expected: bool,
) -> None:
    fake = _FakeKernel32(**fake_kwargs)  # type: ignore[arg-type]
    assert _run_windows_probe(monkeypatch, pid, fake, last_error=last_error) is expected


# ---------------------------------------------------------------------------
# POSIX os.kill(pid, 0) liveness semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    ["own-pid-alive", "missing-pid-dead", "process-lookup-error-dead", "pid-zero-returns-bool"],
)
def test_posix_liveness_matrix(case: str) -> None:
    probe = OsProcessProbe()
    if case == "own-pid-alive":
        assert probe.is_pid_alive(os.getpid()) is True
    elif case == "missing-pid-dead":
        # 99_999_999 is well above any realistic PID on Linux (default pid_max is
        # 4_194_304). ProcessLookupError → False.
        assert probe.is_pid_alive(99_999_999) is False
    elif case == "process-lookup-error-dead":
        with _FORCE_POSIX, patch("os.kill", side_effect=ProcessLookupError(3, "No such process")):
            assert probe.is_pid_alive(12345) is False
    else:  # pid-zero-returns-bool
        # PID 0 behaviour is platform-defined, so we do not pin True vs False — but
        # the probe MUST normalise it to a bool and never let a platform-specific
        # exception (e.g. os.kill(0, 0) signalling the whole process group) escape.
        result = probe.is_pid_alive(0)
        assert isinstance(result, bool)


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

    Bug C: false-stale vs false-active semantics — this is the ONLY coverage of
    the cross-user-pid conservative-alive fix. Keep verbatim.
    """
    probe = OsProcessProbe()
    with _FORCE_POSIX, patch("os.kill", side_effect=PermissionError(1, "Operation not permitted")):
        assert probe.is_pid_alive(12345) is True
    # No warning emitted for PermissionError — it's expected, not anomalous.
    assert not any("unexpected OSError" in rec.message for rec in caplog.records)


def test_unexpected_oserror_is_treated_as_alive_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Conservative default: any other OSError means we cannot determine —
    assume alive and warn. Better false-active than false-stale. Sole coverage of
    this conservative-default branch — keep verbatim.
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
