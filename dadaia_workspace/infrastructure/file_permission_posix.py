"""POSIX file-permission setter — ``os.chmod`` adapter.

Implements ``FilePermissionSetter`` for Linux/macOS.  On these platforms
``os.chmod`` has a real effect; mode bits enforce kernel-level access control.

Import guard: this module imports ``os`` (stdlib only, always available).
It is safe to import on all platforms, but ``PosixFilePermissionSetter`` should
only be instantiated via ``container.py`` when ``PLATFORM.has_posix_chmod``
is ``True``.
"""

from __future__ import annotations

import os
from pathlib import Path


class PosixFilePermissionSetter:
    """Restrict file/directory permissions via ``os.chmod``.

    This is the Tier-1-safe implementation on POSIX: ``os.chmod`` has a real
    effect and the kernel enforces the mode bits.
    """

    def restrict_to_owner(self, path: Path, mode: int = 0o600) -> None:
        """Apply ``chmod <mode>`` to *path* (default 0o600 = owner r/w only).

        Args:
            path: ``pathlib.Path`` or ``str`` — the file to restrict.
            mode: Octal POSIX mode.  Defaults to ``0o600``.

        Raises:
            OSError: If ``os.chmod`` fails (e.g. permission denied, missing file).
        """
        os.chmod(Path(path), mode)

    def restrict_dir_to_owner(self, path: Path, mode: int = 0o700) -> None:
        """Apply ``chmod <mode>`` to directory *path* (default 0o700 = owner rwx only).

        Args:
            path: ``pathlib.Path`` or ``str`` — the directory to restrict.
            mode: Octal POSIX mode.  Defaults to ``0o700``.

        Raises:
            OSError: If ``os.chmod`` fails (e.g. permission denied, missing dir).
        """
        os.chmod(Path(path), mode)
