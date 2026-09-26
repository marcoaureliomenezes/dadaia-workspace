"""The ONE spelling of the workspace CLI (ADR 0045): its absolute path and the fix lines
that invoke it. Every ``fix:`` naming the CLI is built here, so it runs from any cwd:
``shlex`` on POSIX; on Windows forward slashes and double quotes only around a blank —
the one form Git Bash (Claude Code's Windows shell), cmd and PowerShell all run — proven
by executing it in each (``tests/contract/test_fix_line_runs_in_every_shell.py``). A
quoted executable, i.e. a workspace path holding a blank, needs PowerShell's ``& ``
prefix: the documented limitation.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path, PurePath

from dadaia_workspace.core import platform


def cli_path[P: PurePath](root: P) -> P:
    """The workspace CLI's real executable (``Scripts\\dadaia.exe`` on Windows)."""
    return _venv_cli(root / ".dadaia" / ".venv")


def fix_line(root: PurePath | None, *argv: str) -> str:
    """``<absolute CLI> argv…`` quoted for the host shell. No workspace around the run
    (*root* ``None``: CI over a bare checkout) names the CLI of the venv running now."""
    return shell_line(
        str(cli_path(root) if root is not None else _venv_cli(Path(sys.prefix))), *argv
    )


def _venv_cli[P: PurePath](venv: P) -> P:
    caps = platform.PLATFORM
    return venv / caps.venv_scripts_dir / f"dadaia{caps.venv_exe_suffix}"


def shell_line(*parts: str) -> str:
    """*parts* joined into one command line quoted for the host shell."""
    if platform.PLATFORM.venv_exe_suffix:  # Windows
        return " ".join(_win_quote(part.replace("\\", "/")) for part in parts)
    return shlex.join(parts)


def _win_quote(arg: str) -> str:
    return arg if arg and not any(c in arg for c in ' \t"') else f'"{arg}"'
