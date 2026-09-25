"""Platform capability seam — sole authorized sys.platform call site.

No other module in dadaia_workspace may read ``sys.platform``, ``os.name``,
or ``platform.system()`` directly.  All platform decisions must flow through
the ``PLATFORM`` singleton exported by this module.

Consumers import the singleton::

    from dadaia_workspace.core.platform import PLATFORM

Tests call ``detect()`` and monkeypatch the result::

    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("win32"))

``detect()`` is the sole authorized call site for ``sys.platform`` in the
entire codebase.  Module-level ``sys.platform`` reads anywhere else are
forbidden.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    """Snapshot of platform capabilities detected at import time.

    All flag-reading code should access the ``PLATFORM`` module singleton
    rather than calling ``detect()`` directly.

    Attributes:
        venv_scripts_dir: Subdirectory name inside a venv that holds Python
                         executables.  ``"bin"`` on POSIX; ``"Scripts"`` on
                         Windows.
        venv_exe_suffix: File extension for the Python executable inside the
                         venv.  ``""`` on POSIX; ``".exe"`` on Windows.
    """

    venv_scripts_dir: str
    venv_exe_suffix: str

    @classmethod
    def detect(cls, platform: str | None = None) -> Capabilities:
        """Detect capabilities for *platform* — the **sole authorized** ``sys.platform``
        call site; *platform* overrides it (tests)."""
        is_win = (platform if platform is not None else sys.platform) == "win32"
        return cls(
            venv_scripts_dir="Scripts" if is_win else "bin",
            venv_exe_suffix=".exe" if is_win else "",
        )


def detect(platform: str | None = None) -> Capabilities:
    """Convenience wrapper — see ``Capabilities.detect``."""
    return Capabilities.detect(platform)


# ---------------------------------------------------------------------------
# Module-level singleton — import this in all consumer modules.
# ---------------------------------------------------------------------------

PLATFORM: Capabilities = Capabilities.detect()
