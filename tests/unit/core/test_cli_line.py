"""Intent: CONTRACT — AC2.1 (T-050-07): one CLI spelling, both platform forms pinned."""

from __future__ import annotations

import shlex
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from dadaia_workspace.core import cli_line
from dadaia_workspace.core.platform import detect


def test_posix_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("linux"))
    root = PurePosixPath("/ws/my ws")
    assert cli_line.cli_path(root) == PurePosixPath("/ws/my ws/.dadaia/.venv/bin/dadaia")
    assert (
        cli_line.fix_line(root, "context", "bind", "a b")
        == "'/ws/my ws/.dadaia/.venv/bin/dadaia' context bind 'a b'"
    )


def test_windows_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review H5: forward slashes, quoted only when a part holds a blank — one line Git
    Bash, cmd and PowerShell all run (PowerShell needs `& ` before a quoted executable:
    a workspace path with a blank is the documented limitation)."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("win32"))
    root = PureWindowsPath(r"C:\ws\my ws")
    assert cli_line.cli_path(root) == PureWindowsPath(
        r"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe"
    )
    assert (
        cli_line.fix_line(root, "doctor", "--fix")
        == '"C:/ws/my ws/.dadaia/.venv/Scripts/dadaia.exe" doctor --fix'
    )
    assert (
        cli_line.shell_line("git", "-C", r"C:\ws\repos\app", "status")
        == "git -C C:/ws/repos/app status"
    )


def test_no_workspace_names_the_cli_of_the_running_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI over a bare checkout runs the CLI from a venv outside any workspace: the fix
    line names THAT executable, never a workspace-relative path that does not exist."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("linux"))
    monkeypatch.setattr("sys.prefix", "/cache/venvs/proj")
    cli = str(Path("/cache/venvs/proj", "bin", "dadaia"))
    assert cli_line.fix_line(None, "doctor", "--fix") == shlex.join([cli, "doctor", "--fix"])
