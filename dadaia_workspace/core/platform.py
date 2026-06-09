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
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Capabilities:
    """Snapshot of platform capabilities detected at import time.

    All flag-reading code should access the ``PLATFORM`` module singleton
    rather than calling ``detect()`` directly.

    Attributes:
        has_fcntl:       True on POSIX platforms that provide the ``fcntl``
                         module (Linux, macOS).  False on Windows.
        has_proc_fs:     True only on Linux (``/proc`` filesystem available).
        has_posix_chmod: True on POSIX platforms where ``os.chmod`` has effect
                         (Linux, macOS).  False on Windows (no-op — CWE-732).
        has_sigterm:     True on platforms where ``signal.SIGTERM`` can be
                         registered via ``signal.signal()`` (Linux, macOS).
                         False on Windows (SIGTERM raises OSError).
        venv_scripts_dir: Subdirectory name inside a venv that holds Python
                         executables.  ``"bin"`` on POSIX; ``"Scripts"`` on
                         Windows.
        venv_exe_suffix: File extension for the Python executable inside the
                         venv.  ``""`` on POSIX; ``".exe"`` on Windows.
        tmp_dir:         Platform-canonical temporary directory
                         (``tempfile.gettempdir()``).  Prefer this over
                         hardcoded ``/tmp`` paths for cross-platform safety.
    """

    has_fcntl: bool
    has_proc_fs: bool
    has_posix_chmod: bool
    has_sigterm: bool
    venv_scripts_dir: str
    venv_exe_suffix: str
    tmp_dir: Path

    @classmethod
    def detect(cls, platform: str | None = None) -> Capabilities:
        """Detect capabilities for *platform*.

        This is the **sole authorized** ``sys.platform`` call site in the
        entire codebase.  All other modules must read ``PLATFORM`` instead of
        calling this directly.

        Args:
            platform: Override value for ``sys.platform`` (used in tests).
                      When ``None``, reads ``sys.platform`` at call time.

        Returns:
            A frozen ``Capabilities`` snapshot for the given platform string.
        """
        plat = platform if platform is not None else sys.platform
        is_win = plat == "win32"
        is_linux = plat == "linux"
        is_posix = not is_win  # macOS, Linux, *BSD, ...

        return cls(
            has_fcntl=is_posix,
            has_proc_fs=is_linux,
            has_posix_chmod=is_posix,
            has_sigterm=is_posix,
            venv_scripts_dir="Scripts" if is_win else "bin",
            venv_exe_suffix=".exe" if is_win else "",
            tmp_dir=Path(tempfile.gettempdir()),
        )


def detect(platform: str | None = None) -> Capabilities:
    """Convenience wrapper — see ``Capabilities.detect``."""
    return Capabilities.detect(platform)


# ---------------------------------------------------------------------------
# Module-level singleton — import this in all consumer modules.
# ---------------------------------------------------------------------------

PLATFORM: Capabilities = Capabilities.detect()
