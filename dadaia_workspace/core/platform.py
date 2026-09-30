"""Platform capability seam — the sole authorized ``sys.platform`` read.

Every platform decision flows through the ``PLATFORM`` singleton; tests swap it:
``monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    """``venv_scripts_dir`` (``bin``/``Scripts``), ``venv_exe_suffix`` (``""``/``.exe``)
    and ``windows`` (the host path flavor is ``ntpath``)."""

    venv_scripts_dir: str
    venv_exe_suffix: str
    windows: bool

    @classmethod
    def detect(cls, platform: str | None = None) -> Capabilities:
        """Capabilities for *platform* (default ``sys.platform``)."""
        is_win = (platform if platform is not None else sys.platform) == "win32"
        return cls("Scripts" if is_win else "bin", ".exe" if is_win else "", is_win)


PLATFORM: Capabilities = Capabilities.detect()
