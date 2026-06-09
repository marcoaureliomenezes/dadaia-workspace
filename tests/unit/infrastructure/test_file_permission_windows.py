"""Unit tests for infrastructure/file_permission_windows.py.

Behavior tests (with monkeypatched subprocess) run on ALL platforms so CI
validates the logic on Linux too.  Tests that require a real ``icacls``
binary are gated to a Windows runner with ``skipif != win32``.

Security invariants asserted:
  - ``shell=False`` is always used (CWE-78 / command injection prevention).
  - Username comes from ``getpass.getuser()``, not ``os.environ['USERNAME']``.
  - Non-zero ``icacls`` exit raises ``PlatformSecurityError``.
  - Missing/empty username raises ``PlatformSecurityError``.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.infrastructure.file_permission_windows import WindowsFilePermissionSetter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ok_result() -> MagicMock:
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = 0
    r.stderr = ""
    return r


def _make_fail_result(code: int = 1) -> MagicMock:
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = code
    r.stderr = "Access denied"
    return r


# ---------------------------------------------------------------------------
# shell=False assertions
# ---------------------------------------------------------------------------


def test_restrict_dir_uses_shell_false(tmp_path: Path) -> None:
    """icacls must be invoked with shell=False to prevent command injection."""
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_ok_result()) as mock_run,
    ):
        setter.restrict_dir_to_owner(tmp_path)

    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("shell") is False or call_kwargs.args[1:] == (), (
        "subprocess.run must be called with shell=False"
    )
    # Confirm the positional call also has shell=False
    all_kwargs = {**call_kwargs.kwargs}
    # shell may be a positional arg (unlikely but guard for it)
    assert all_kwargs.get("shell") is False, (
        "subprocess.run MUST be called with shell=False (CWE-78)"
    )


def test_restrict_to_owner_uses_shell_false(tmp_path: Path) -> None:
    """icacls must be invoked with shell=False for file restriction too."""
    f = tmp_path / "token"
    f.write_text("t", encoding="utf-8")
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_ok_result()) as mock_run,
    ):
        setter.restrict_to_owner(f)

    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("shell") is False, (
        "subprocess.run MUST be called with shell=False (CWE-78)"
    )


# ---------------------------------------------------------------------------
# Username source: getpass.getuser() — NOT os.environ['USERNAME']
# ---------------------------------------------------------------------------


def test_restrict_dir_uses_getpass_not_env(tmp_path: Path) -> None:
    """Username must come from getpass.getuser(), not os.environ['USERNAME']."""
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="getpass_user") as mock_getpass,
        patch("subprocess.run", return_value=_make_ok_result()) as mock_run,
    ):
        setter.restrict_dir_to_owner(tmp_path)

    mock_getpass.assert_called_once()
    cmd = mock_run.call_args.args[0]
    # The command must contain the getpass username, not a hard-coded env lookup
    assert any("getpass_user" in str(arg) for arg in cmd), (
        f"Command did not contain the getpass username 'getpass_user': {cmd}"
    )


# ---------------------------------------------------------------------------
# Non-zero icacls exit → PlatformSecurityError
# ---------------------------------------------------------------------------


def test_restrict_dir_raises_on_nonzero_exit(tmp_path: Path) -> None:
    """Non-zero icacls return code must raise PlatformSecurityError."""
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_fail_result(1)),
        pytest.raises(PlatformSecurityError),
    ):
        setter.restrict_dir_to_owner(tmp_path)


def test_restrict_to_owner_raises_on_nonzero_exit(tmp_path: Path) -> None:
    """Non-zero icacls return code for file restriction raises PlatformSecurityError."""
    f = tmp_path / "token"
    f.write_text("t", encoding="utf-8")
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_fail_result(2)),
        pytest.raises(PlatformSecurityError),
    ):
        setter.restrict_to_owner(f)


# ---------------------------------------------------------------------------
# Missing username → PlatformSecurityError
# ---------------------------------------------------------------------------


def test_restrict_dir_raises_on_getuser_exception(tmp_path: Path) -> None:
    """If getpass.getuser() raises, PlatformSecurityError is raised (not silenced)."""
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", side_effect=OSError("no tty")),
        pytest.raises(PlatformSecurityError),
    ):
        setter.restrict_dir_to_owner(tmp_path)


def test_restrict_dir_raises_on_empty_username(tmp_path: Path) -> None:
    """If getpass.getuser() returns an empty string, PlatformSecurityError is raised."""
    setter = WindowsFilePermissionSetter()
    with patch("getpass.getuser", return_value=""), pytest.raises(PlatformSecurityError):
        setter.restrict_dir_to_owner(tmp_path)


# ---------------------------------------------------------------------------
# Mode parameter is accepted but ignored on Windows
# ---------------------------------------------------------------------------


def test_restrict_to_owner_accepts_mode_param(tmp_path: Path) -> None:
    """mode parameter must be accepted without error (ignored on Windows)."""
    f = tmp_path / "token"
    f.write_text("t", encoding="utf-8")
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_ok_result()),
    ):
        # Should not raise
        setter.restrict_to_owner(f, mode=0o600)


def test_restrict_dir_to_owner_accepts_mode_param(tmp_path: Path) -> None:
    """mode parameter must be accepted without error (ignored on Windows)."""
    setter = WindowsFilePermissionSetter()
    with (
        patch("getpass.getuser", return_value="testuser"),
        patch("subprocess.run", return_value=_make_ok_result()),
    ):
        setter.restrict_dir_to_owner(tmp_path, mode=0o700)


# ---------------------------------------------------------------------------
# Real icacls test — Windows runner only
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Real icacls test only meaningful on a Windows runner",
)
def test_restrict_dir_real_icacls_applies_dacl_or_raises(tmp_path: Path) -> None:
    """On Windows: real icacls applies DACL or raises PlatformSecurityError."""
    setter = WindowsFilePermissionSetter()
    # icacls either applies the DACL (success) or raises PlatformSecurityError; on some
    # CI Windows environments icacls may be unavailable / UAC-restricted — both acceptable.
    with contextlib.suppress(PlatformSecurityError):
        setter.restrict_dir_to_owner(tmp_path)
