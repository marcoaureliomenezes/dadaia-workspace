"""Intent: CONTRACT — review H5 (0.5.0 c3): a printed fix line RUNS, verbatim, in every
shell the host offers — POSIX ``sh``; on Windows Git Bash, cmd and PowerShell. The
Windows contract job runs this file, so a fix-line form one of them cannot execute
turns CI red instead of stalling an operator.

The CLI under test is a stand-in binary planted at the workspace path ``fix_line``
spells: a Poetry dev venv carries no ``dadaia.exe`` (its editable install writes a
``.cmd`` shim), so the running venv cannot be the ground truth — the path form is.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import cli_path, fix_line


def _shells() -> list[list[str]]:
    if sys.platform != "win32":
        return [["sh", "-c"]]
    shells = [["cmd", "/d", "/c"], ["powershell", "-NoProfile", "-Command"]]
    git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Git", "bin", "bash.exe")
    return [*shells, [str(git_bash), "-c"]] if git_bash.is_file() else shells


def _plant_cli(root: Path) -> None:
    """A real executable that exits 0 with no argument, where the workspace CLI lives."""
    stand_in = shutil.which("whoami" if sys.platform == "win32" else "true")
    assert stand_in, "the host has no stand-in executable"
    cli = cli_path(root)
    cli.parent.mkdir(parents=True)
    shutil.copy(stand_in, cli)


@pytest.mark.parametrize("shell", _shells(), ids=lambda argv: Path(argv[0]).stem)
def test_a_fix_line_runs_verbatim_in_the_host_shell(shell: list[str], tmp_path: Path) -> None:
    _plant_cli(tmp_path)
    line = fix_line(tmp_path)
    ran = subprocess.run([*shell, line], capture_output=True, text=True, timeout=25)
    assert ran.returncode == 0, f"{line}\n{ran.stdout}{ran.stderr}"
