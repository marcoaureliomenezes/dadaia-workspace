#!/usr/bin/env python3
"""The one reader of `sys.platform` for the skill scripts: does this host spell paths and venvs the Windows way?"""

from __future__ import annotations

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


def workspace_cli(root: Path) -> Path | None:
    """The workspace CLI under *root*, or None when no install put it there."""
    cli = venv_tool(root / ".dadaia/.venv", "dadaia")
    return cli if cli.exists() else None


def venv_tool(venv: Path, tool: str, caps: Caps | None = None) -> Path:
    """Where *venv* keeps the executable *tool* on this host."""
    caps = caps or detect()
    return venv / caps.scripts_dir / f"{tool}{caps.exe_suffix}"
