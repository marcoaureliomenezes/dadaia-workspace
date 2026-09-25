"""Intent: CONTRACT — AC2.1 (T-050-07): one CLI spelling, both platform forms pinned."""

from __future__ import annotations

import subprocess
from pathlib import Path, PureWindowsPath

import pytest

from dadaia_workspace.core import cli_line
from dadaia_workspace.core.platform import detect


def test_posix_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("linux"))
    root = Path("/ws/my ws")
    assert cli_line.cli_path(root) == Path("/ws/my ws/.dadaia/.venv/bin/dadaia")
    assert (
        cli_line.fix_line(root, "context", "bind", "a b")
        == "'/ws/my ws/.dadaia/.venv/bin/dadaia' context bind 'a b'"
    )


def test_windows_cli_path_and_fix_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("win32"))
    root = PureWindowsPath(r"C:\ws\my ws")
    assert cli_line.cli_path(root) == PureWindowsPath(
        r"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe"
    )
    assert (
        cli_line.fix_line(root, "doctor", "--fix")
        == r'"C:\ws\my ws\.dadaia\.venv\Scripts\dadaia.exe" doctor --fix'
    )


def test_windows_quotes_like_list2cmdline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("win32"))
    argv = ("context", "create", "", "a b", 'say "hi"')
    root = PureWindowsPath(r"C:\ws")
    expected = subprocess.list2cmdline([str(cli_line.cli_path(root)), *argv])
    assert cli_line.fix_line(root, *argv) == expected
