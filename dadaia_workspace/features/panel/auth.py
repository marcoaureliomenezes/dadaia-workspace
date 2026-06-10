"""Bearer token auth for the panel.

Token is generated once at startup, persisted to ~/.dadaia/state/panel.token
with owner-only permissions. Validated on every request via constant-time compare.

Per SPEC § Auth model (D-AM-06) and SPEC §5 Tier-1 (fail-loud security).

Platform security (FR-05 / CWE-732):
  On POSIX, ``os.open(..., 0o600)`` creates the file at the correct mode atomically
  (TOCTOU fix — no widen window).  The parent directory is restricted to 0o700.
  On Windows, ``FilePermissionSetter.restrict_dir_to_owner()`` MUST be called on the
  parent directory BEFORE the token file is created so the file inherits the
  restrictive ACL (TOCTOU option a).  Any failure raises ``PlatformSecurityError`` —
  the panel MUST NOT start with an unprotected token.
"""

from __future__ import annotations

import hmac
import os
import pathlib
import secrets
import stat as _stat
import sys

from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter

DEFAULT_TOKEN_PATH = pathlib.Path("~/.dadaia/state/panel.token").expanduser()
_BEARER_PREFIX = "Bearer "

# Mode bits that make the token readable by group or other. A token carrying
# these bits is effectively world-readable and must be tightened to 0o600.
_GROUP_OTHER_READABLE = _stat.S_IRWXG | _stat.S_IRWXO


def _tighten_existing_token(
    path: pathlib.Path,
    permission_setter: FilePermissionSetter | None,
) -> None:
    """Re-check the mode of a pre-existing token file and tighten to 0o600.

    F-7 (CWE-732): the atomic ``O_EXCL | 0o600`` create only protects newly
    minted tokens.  A token left behind by an older (pre-fix) panel may sit at a
    group/other-readable mode (e.g. ``0o644``) and stays world-readable forever.
    On every read we verify the mode and, if it is too wide, restrict it back to
    owner-only — preferring the injected ``FilePermissionSetter`` (icacls on
    Windows / chmod on POSIX) and falling back to ``os.chmod`` on POSIX.

    On platforms with no effective ``os.chmod`` (Windows) and no setter injected,
    the mode cannot be read/changed meaningfully via POSIX bits; the ACL-based
    setter is the only honest tightening path, so this is a no-op without one.
    """
    if permission_setter is not None:
        # The seam owns the platform-correct tightening (icacls/chmod). Always
        # route through it so Windows ACLs get re-applied too.
        permission_setter.restrict_to_owner(path, 0o600)
        return

    if not PLATFORM.has_posix_chmod:
        # No setter and chmod is a no-op (Windows): cannot tighten via POSIX bits.
        # The production panel always injects a setter; this guards a misuse only.
        return

    current_mode = _stat.S_IMODE(os.stat(path).st_mode)
    if current_mode & _GROUP_OTHER_READABLE:
        os.chmod(path, 0o600)


def ensure_token(
    path: pathlib.Path = DEFAULT_TOKEN_PATH,
    permission_setter: FilePermissionSetter | None = None,
) -> str:
    """Read token from path; generate + persist if missing.

    Creates parent dir with restricted permissions. Token file is created
    with owner-only access.  A pre-existing token file has its mode re-checked
    on every read and tightened to 0o600 if an older panel left it
    group/other-readable (F-7 / CWE-732, platform-seam aware).

    Platform security (Tier-1 / SPEC §5):
      If *permission_setter* is provided it is used to restrict the parent
      directory BEFORE the token file is created (TOCTOU option a on Windows).
      On POSIX the atomic ``O_EXCL | 0o600`` open provides the same guarantee.
      If the permission setter raises ``PlatformSecurityError``, the token is
      NOT created and the error propagates — the panel MUST NOT start with an
      unprotected token.

    Parameters
    ----------
    path:
        Filesystem path for the token file.  Defaults to
        ``~/.dadaia/state/panel.token``.
    permission_setter:
        Optional ``FilePermissionSetter`` implementation.  When provided it
        is used to restrict the parent directory before token creation.

    Returns
    -------
    str
        The token value (read from file or freshly generated).

    Raises
    ------
    PlatformSecurityError
        If *permission_setter* is provided and cannot restrict the parent
        directory.  Propagated without suppression (Tier-1 fail-loud).
    """
    if path.exists():
        # F-7: re-check the mode of a pre-existing token and tighten it if an
        # older panel left it group/other-readable (CWE-732, platform-seam aware).
        _tighten_existing_token(path, permission_setter)
        return path.read_text(encoding="utf-8").strip()

    # Create parent directory.
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Apply permission restriction to parent directory BEFORE token creation.
    # On Windows this is the TOCTOU mitigation option (a): the token file
    # inherits the restrictive ACL from the parent.
    # On POSIX the O_EXCL|0o600 open below is the canonical TOCTOU fix, but
    # restricting the parent directory too is defense-in-depth.
    # PlatformSecurityError is intentionally NOT caught here (Tier-1 fail-loud).
    if permission_setter is not None:
        permission_setter.restrict_dir_to_owner(parent)
    elif PLATFORM.has_posix_chmod:
        os.chmod(parent, 0o700)
    else:
        # No setter injected AND chmod is a no-op on this platform (Windows):
        # refuse rather than silently leave the token dir unprotected (CWE-732,
        # Tier-1 fail-loud). The production panel path always injects a setter
        # (container._build_permission_setter), so this guards a misuse/fallback only.
        raise PlatformSecurityError(
            "cannot restrict panel token directory on this platform without a "
            "FilePermissionSetter (refusing to create an unprotected token)",
            feature_name="panel-auth",
            platform=sys.platform,
        )

    token = secrets.token_urlsafe(32)

    # Atomic restricted-mode create: O_CREAT|O_WRONLY|O_EXCL|0o600 so the
    # file is born at 0o600 — there is no window where it exists at a wider
    # mode (OWASP A02, TOCTOU fix).  O_EXCL also prevents a race where two
    # processes both try to create the token simultaneously.
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    except FileExistsError:
        # Another process beat us to creation; read their token.
        return path.read_text(encoding="utf-8").strip()

    try:
        os.write(fd, token.encode())
    finally:
        os.close(fd)

    return token


def validate(header_value: str | None, expected_token: str) -> bool:
    """Constant-time comparison via hmac.compare_digest.

    Returns True only if header is exactly 'Bearer <expected_token>'.
    None header, empty string, missing prefix, wrong token → False.

    Parameters
    ----------
    header_value:
        The raw ``Authorization`` header string (or None when absent).
    expected_token:
        The token loaded via ``ensure_token()`` at startup.
    """
    if not header_value:
        return False
    if not header_value.startswith(_BEARER_PREFIX):
        return False
    candidate = header_value[len(_BEARER_PREFIX) :]
    if not candidate:
        return False
    return hmac.compare_digest(candidate, expected_token)
