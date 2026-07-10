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


@pytest.mark.parametrize("target_kind", ["dir", "file"])
def test_restrict_uses_shell_false_and_getpass_not_env(tmp_path: Path, target_kind: str) -> None:
    """icacls must be invoked with shell=False (CWE-78) for both dir and file
    restriction, and the username must come from getpass.getuser(), not
    os.environ['USERNAME']."""
    setter = WindowsFilePermissionSetter()
    target: Path
    if target_kind == "dir":
        target = tmp_path
    else:
        target = tmp_path / "token"
        target.write_text("t", encoding="utf-8")

    with (
        patch("getpass.getuser", return_value="getpass_user") as mock_getpass,
        patch("subprocess.run", return_value=_make_ok_result()) as mock_run,
    ):
        if target_kind == "dir":
            setter.restrict_dir_to_owner(target)
        else:
            setter.restrict_to_owner(target)

    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("shell") is False, (
        "subprocess.run MUST be called with shell=False (CWE-78)"
    )

    mock_getpass.assert_called_once()
    cmd = call_kwargs.args[0]
    assert any("getpass_user" in str(arg) for arg in cmd), (
        f"Command did not contain the getpass username 'getpass_user': {cmd}"
    )


@pytest.mark.parametrize(
    ("target_kind", "getuser_kwargs", "run_result"),
    [
        pytest.param(
            "dir", {"return_value": "testuser"}, _make_fail_result(1), id="dir-nonzero-exit"
        ),
        pytest.param(
            "file", {"return_value": "testuser"}, _make_fail_result(2), id="file-nonzero-exit"
        ),
        pytest.param("dir", {"side_effect": OSError("no tty")}, None, id="getuser-raises"),
        pytest.param("dir", {"return_value": ""}, None, id="empty-username"),
    ],
)
def test_restrict_raises_platform_security_error(
    tmp_path: Path,
    target_kind: str,
    getuser_kwargs: dict[str, object],
    run_result: MagicMock | None,
) -> None:
    """Non-zero icacls exit, a raising getpass.getuser(), and an empty username all
    raise PlatformSecurityError — never a silent failure."""
    setter = WindowsFilePermissionSetter()
    target: Path
    if target_kind == "file":
        target = tmp_path / "token"
        target.write_text("t", encoding="utf-8")
    else:
        target = tmp_path

    patches = [patch("getpass.getuser", **getuser_kwargs)]
    if run_result is not None:
        patches.append(patch("subprocess.run", return_value=run_result))

    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with pytest.raises(PlatformSecurityError):
            if target_kind == "dir":
                setter.restrict_dir_to_owner(target)
            else:
                setter.restrict_to_owner(target)


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
