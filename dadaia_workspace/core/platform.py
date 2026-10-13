"""Platform capability seam: every platform decision flows through the ``PLATFORM`` singleton,
whose facts are the kernel's ``_platform`` (the one host reader); tests swap it:
``monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from dadaia_workspace.core.skill_owner import load_owner

_owner = load_owner("dd-bug-resolution", "_platform")


@dataclass(frozen=True)
class Capabilities:
    """``venv_scripts_dir`` (``bin``/``Scripts``), ``venv_exe_suffix`` (``""``/``.exe``)
    and ``windows`` (the host path flavor is ``ntpath``)."""

    venv_scripts_dir: str
    venv_exe_suffix: str
    windows: bool

    @classmethod
    def detect(cls, platform: str | None = None) -> Capabilities:
        """Capabilities for *platform* (default: this host)."""
        caps = _owner.detect(platform)
        return cls(caps.scripts_dir, caps.exe_suffix, caps.windows)


PLATFORM: Capabilities = Capabilities.detect()


def _caps() -> _owner.Caps:
    return _owner.Caps(PLATFORM.venv_scripts_dir, PLATFORM.venv_exe_suffix, PLATFORM.windows)


def venv_dir[P: PurePath](root: P) -> P:
    """The workspace venv under *root*, by the kernel's rule."""
    path: P = _owner.venv_dir(root)
    return path


def venv_tool[P: PurePath](venv: P, tool: str) -> P:
    """Where *venv* keeps the executable *tool*, by the kernel's rule fed the current ``PLATFORM``."""
    path: P = _owner.venv_tool(venv, tool, _caps())
    return path


def workspace_cli_path[P: PurePath](root: P) -> P:
    """Where the workspace CLI lives under *root*, by the kernel's rule fed the current ``PLATFORM``."""
    path: P = _owner.cli_path(root, _caps())
    return path
