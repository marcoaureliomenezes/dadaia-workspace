#!/usr/bin/env python3
"""The one reader of `sys.platform` for the skill scripts — does this host spell paths and venvs the Windows way —
and the shell words and git lines spelled by it."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import NamedTuple


class Caps(NamedTuple):
    scripts_dir: str
    exe_suffix: str
    windows: bool


def detect(platform: str | None = None) -> Caps:
    """Capabilities of *platform* (default ``sys.platform``)."""
    windows = (platform if platform is not None else sys.platform) == "win32"
    return Caps("Scripts" if windows else "bin", ".exe" if windows else "", windows)


def venv_dir(root: Path) -> Path:
    """The workspace venv under *root*."""
    return root / ".dadaia" / ".venv"


def cli_path(root: Path, caps: Caps | None = None) -> Path:
    """Where the workspace CLI lives under *root*; whether it exists is not asked."""
    return venv_tool(venv_dir(root), "dadaia", caps)


def venv_tool(venv: Path, tool: str, caps: Caps | None = None) -> Path:
    """Where *venv* keeps the executable *tool* on this host."""
    caps = caps or detect()
    return venv / caps.scripts_dir / f"{tool}{caps.exe_suffix}"


def quote(word: str) -> str:
    """One shell word as `core/cli_line.shell_line` spells it: ``shlex`` on POSIX; on
    Windows forward slashes, double quotes only around a blank."""
    if not detect().windows:
        return shlex.quote(word)
    word = word.replace("\\", "/")
    return word if word and not any(c in word for c in ' \t"') else f'"{word}"'


def head(word: str) -> str:
    """A command's first word as `core/cli_line.shell_line` spells it: on Windows a quote
    opens after the drive letter, so the line never opens with one PowerShell reads as an
    expression."""
    word = quote(word)
    return f'{word[1]}"{word[2:]}' if detect().windows and word.startswith('"') else word


def git_line(repo: Path | str, *argv: str) -> str:
    """``git -C <repo> argv…`` quoted, as `core/cli_line.git_line` spells it."""
    return " ".join(map(quote, ("git", "-C", str(repo), *argv)))
