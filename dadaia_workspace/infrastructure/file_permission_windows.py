"""Windows file-permission setter — ``icacls`` TOCTOU-safe adapter.

Implements ``FilePermissionSetter`` for Windows via ``icacls``.

TOCTOU mitigation option (a):
  ``restrict_dir_to_owner()`` restricts the **parent directory** ACL *before*
  the token file is created inside it.  The token file then inherits the
  restrictive ACL from the parent, so there is no window where the file exists
  with a wider ACL.

Security invariants:
  - ``icacls`` is called with ``shell=False`` (CWE-78 / command injection prevention).
  - The username is obtained via ``getpass.getuser()`` — never ``os.environ['USERNAME']``
    (which can be spoofed).
  - A non-zero ``icacls`` exit code raises ``PlatformSecurityError`` immediately;
    there is no warn-and-continue path (SPEC §5 Tier-1).
  - The mode parameter is accepted for interface compatibility but is ignored on
    Windows (ACL-based rather than POSIX mode-bit based).

Import note: this module imports ``subprocess`` and ``getpass`` (stdlib only).
It is safe to import on all platforms; the class only calls ``icacls`` on
``restrict_dir_to_owner``/``restrict_to_owner`` invocations.
"""

from __future__ import annotations

import getpass
import logging
import subprocess
from pathlib import Path

from dadaia_workspace.core.exceptions import PlatformSecurityError

logger = logging.getLogger(__name__)


def _icacls_restrict_dir(dir_path: Path) -> None:
    """Apply owner-only ACL to *dir_path* using ``icacls``.

    Grants the current user full control with inheritance (OI)(CI)F,
    removes all inherited permissions, and denies everyone else.

    The token file created inside this directory subsequently inherits
    the restrictive ACL — this is TOCTOU mitigation option (a) from SPEC §5.

    Args:
        dir_path: Directory path to restrict.

    Raises:
        PlatformSecurityError: If ``getpass.getuser()`` fails or ``icacls``
                               returns a non-zero exit code.
    """
    try:
        username = getpass.getuser()
    except Exception as exc:  # noqa: BLE001
        raise PlatformSecurityError(
            "Cannot determine username for icacls dir restriction",
            feature_name="file-permission-windows",
            platform="win32",
        ) from exc

    if not username:
        raise PlatformSecurityError(
            "getpass.getuser() returned empty string; cannot restrict directory ACL",
            feature_name="file-permission-windows",
            platform="win32",
        )

    # Remove inherited permissions and grant owner full control with inheritance.
    # (OI) = object inherit (files), (CI) = container inherit (subdirs), F = full control.
    cmd = [
        "icacls",
        str(dir_path),
        "/inheritance:r",
        "/grant:r",
        f"{username}:(OI)(CI)F",
    ]
    result = subprocess.run(  # noqa: S603
        cmd,
        shell=False,  # SECURITY: never shell=True (CWE-78)
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(
            "WindowsFilePermissionSetter: icacls failed (exit %d) for %s: %s",
            result.returncode,
            dir_path,
            result.stderr.strip(),
        )
        raise PlatformSecurityError(
            f"icacls failed (exit {result.returncode}) restricting directory {dir_path}",
            feature_name="file-permission-windows",
            platform="win32",
        )


def _icacls_restrict_file(file_path: Path) -> None:
    """Apply owner-only ACL to a file using ``icacls``.

    Used when restricting a file that already exists (e.g. Tier-2 paths).
    For Tier-1 token creation, the parent directory should be restricted
    via ``_icacls_restrict_dir`` BEFORE the file is created, so the file
    inherits the ACL automatically (TOCTOU option a).

    Args:
        file_path: File path to restrict.

    Raises:
        PlatformSecurityError: If ``getpass.getuser()`` fails or ``icacls``
                               returns a non-zero exit code.
    """
    try:
        username = getpass.getuser()
    except Exception as exc:  # noqa: BLE001
        raise PlatformSecurityError(
            "Cannot determine username for icacls file restriction",
            feature_name="file-permission-windows",
            platform="win32",
        ) from exc

    if not username:
        raise PlatformSecurityError(
            "getpass.getuser() returned empty string; cannot restrict file ACL",
            feature_name="file-permission-windows",
            platform="win32",
        )

    cmd = [
        "icacls",
        str(file_path),
        "/inheritance:r",
        "/grant:r",
        f"{username}:F",
    ]
    result = subprocess.run(  # noqa: S603
        cmd,
        shell=False,  # SECURITY: never shell=True (CWE-78)
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(
            "WindowsFilePermissionSetter: icacls failed (exit %d) for %s: %s",
            result.returncode,
            file_path,
            result.stderr.strip(),
        )
        raise PlatformSecurityError(
            f"icacls failed (exit {result.returncode}) restricting file {file_path}",
            feature_name="file-permission-windows",
            platform="win32",
        )


class WindowsFilePermissionSetter:
    """Restrict file/directory permissions via ``icacls`` on Windows.

    Security contract (SPEC §5 Tier-1):
      - ``restrict_dir_to_owner()`` must be called on the PARENT directory
        before the token file is created, so the token inherits a restrictive
        ACL.  This is TOCTOU mitigation option (a).
      - ``restrict_to_owner()`` applies an ACL to the file itself (used for
        Tier-2 / post-creation restriction, or where the parent-dir approach
        is not applicable).
      - Both methods raise ``PlatformSecurityError`` on any failure — there is
        no warn-and-continue path for Tier-1 callers.

    The ``mode`` parameter is accepted for interface compatibility with
    ``PosixFilePermissionSetter`` but is ignored on Windows.
    """

    def restrict_to_owner(self, path: Path, mode: int = 0o600) -> None:
        """Restrict *path* to owner-only access via ``icacls``.

        The ``mode`` argument is ignored (Windows uses ACLs, not POSIX modes).

        Args:
            path: ``pathlib.Path`` or ``str`` — the file to restrict.
            mode: Ignored on Windows.

        Raises:
            PlatformSecurityError: If the ``icacls`` call fails or the current
                                   username cannot be determined.
        """
        _icacls_restrict_file(Path(path))

    def restrict_dir_to_owner(self, path: Path, mode: int = 0o700) -> None:
        """Restrict directory *path* to owner-only access via ``icacls``.

        TOCTOU option (a): call this on the PARENT directory BEFORE creating
        the token file inside it.  The newly created token file inherits the
        restrictive ACL from the directory.

        The ``mode`` argument is ignored (Windows uses ACLs, not POSIX modes).

        Args:
            path: ``pathlib.Path`` or ``str`` — the directory to restrict.
            mode: Ignored on Windows.

        Raises:
            PlatformSecurityError: If the ``icacls`` call fails or the current
                                   username cannot be determined.
        """
        _icacls_restrict_dir(Path(path))
