"""FilePermissionSetter protocol — platform-agnostic file permission interface.

Implementations live in ``infrastructure/``:
  - ``file_permission_posix.py`` — POSIX ``os.chmod`` adapter.
  - ``file_permission_windows.py`` — Windows ``icacls`` TOCTOU-safe adapter.

The protocol is zero I/O (no import of OS-specific modules here).

Security tiers (SPEC §5):
  TIER 1 — panel auth token: ``WindowsFilePermissionSetter.restrict_to_owner()``
    MUST apply TOCTOU mitigation option (a) — restrict the parent directory ACL
    BEFORE the file is created.  On failure it raises ``PlatformSecurityError``
    immediately (never a warn-and-continue path).
  TIER 2 — telemetry state dir / ctx_locks dir: catch ``PlatformSecurityError``
    from the setter, degrade to None/503, emit an INFO log.
"""

from pathlib import Path
from typing import Protocol


class FilePermissionSetter(Protocol):
    """Restrict file or directory permissions to the owning user.

    All implementations must raise ``PlatformSecurityError`` if they cannot
    apply the requested restriction on a Tier-1 (security) path.  Tier-2
    callers should catch ``PlatformSecurityError`` and degrade gracefully.
    """

    def restrict_to_owner(self, path: Path, mode: int = 0o600) -> None:
        """Restrict *path* to owner read/write only (equivalent to chmod 600).

        On POSIX, calls ``os.chmod(path, mode)``.
        On Windows, applies an ``icacls`` ACL to the file that grants
        owner-only access.  The TOCTOU-safe approach restricts the *parent
        directory* before file creation so the file inherits a restrictive ACL.

        Args:
            path: ``pathlib.Path`` or ``str`` — the file to restrict.
            mode: Octal mode for POSIX chmod.  Ignored on Windows (ACL used
                  instead).

        Raises:
            PlatformSecurityError: When the restriction cannot be applied and
                                   the caller is on a Tier-1 security path.
        """
        ...

    def restrict_dir_to_owner(self, path: Path, mode: int = 0o700) -> None:
        """Restrict *path* (a directory) to owner-only access (chmod 700).

        On POSIX, calls ``os.chmod(path, mode)``.
        On Windows, applies an ``icacls`` ACL granting owner full control with
        inheritance so child files created inside inherit the restrictive ACL.

        Args:
            path: ``pathlib.Path`` or ``str`` — the directory to restrict.
            mode: Octal mode for POSIX chmod.  Ignored on Windows (ACL used
                  instead).

        Raises:
            PlatformSecurityError: When the restriction cannot be applied and
                                   the caller is on a Tier-1 security path.
        """
        ...
