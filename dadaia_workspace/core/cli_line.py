"""The ONE spelling of the workspace CLI (ADR 0045): its absolute path and the fix lines
that invoke it. Every ``fix:`` naming the CLI is built here, so it runs from any cwd and
quotes correctly on the host's shell — ``shlex`` on POSIX, MSVCRT argv rules on Windows
(``subprocess.list2cmdline``'s rules; core may not import ``subprocess`` — setup.cfg).
"""

from __future__ import annotations

import shlex
from pathlib import PurePath

from dadaia_workspace.core import platform


def cli_path[P: PurePath](root: P) -> P:
    """The workspace CLI's real executable (``Scripts\\dadaia.exe`` on Windows)."""
    caps = platform.PLATFORM
    return root / ".dadaia" / ".venv" / caps.venv_scripts_dir / f"dadaia{caps.venv_exe_suffix}"


def fix_line(root: PurePath, *argv: str) -> str:
    """``<absolute CLI> argv…`` quoted for the host shell."""
    return shell_line(str(cli_path(root)), *argv)


def shell_line(*parts: str) -> str:
    """*parts* joined into one command line quoted for the host shell."""
    if platform.PLATFORM.venv_exe_suffix:  # Windows
        return " ".join(_win_quote(part) for part in parts)
    return shlex.join(parts)


def _win_quote(arg: str) -> str:
    if arg and not any(c in arg for c in ' \t"'):
        return arg
    return '"' + arg.replace('"', '\\"') + '"'
