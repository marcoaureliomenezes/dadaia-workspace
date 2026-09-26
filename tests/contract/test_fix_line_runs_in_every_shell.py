"""Intent: CONTRACT — review H5 (0.5.0 c3): a printed fix line RUNS, verbatim, in every
shell the host offers — POSIX ``sh``; on Windows Git Bash, cmd and PowerShell. The
Windows contract job runs this file, so a fix-line form one of them cannot execute
turns CI red instead of stalling an operator.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line


def _shells() -> list[list[str]]:
    if sys.platform != "win32":
        return [["sh", "-c"]]
    shells = [["cmd", "/d", "/c"], ["powershell", "-NoProfile", "-Command"]]
    git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Git", "bin", "bash.exe")
    return [*shells, [str(git_bash), "-c"]] if git_bash.is_file() else shells


@pytest.mark.parametrize("shell", _shells(), ids=lambda argv: Path(argv[0]).stem)
def test_a_fix_line_runs_verbatim_in_the_host_shell(shell: list[str]) -> None:
    line = fix_line(None, "--help")
    ran = subprocess.run([*shell, line], capture_output=True, text=True, timeout=25)
    assert ran.returncode == 0, f"{line}\n{ran.stdout}{ran.stderr}"
    assert "Usage" in ran.stdout
