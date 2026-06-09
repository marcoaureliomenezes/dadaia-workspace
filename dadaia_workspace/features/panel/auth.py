"""Bearer token auth for the panel.

Token is generated once at startup, persisted to ~/.dadaia/state/panel.token
with chmod 0o600. Validated on every request via constant-time compare.

Per SPEC § Auth model (D-AM-06).
"""

from __future__ import annotations

import hmac
import os
import pathlib
import secrets

DEFAULT_TOKEN_PATH = pathlib.Path("~/.dadaia/state/panel.token").expanduser()
_BEARER_PREFIX = "Bearer "


def ensure_token(path: pathlib.Path = DEFAULT_TOKEN_PATH) -> str:
    """Read token from path; generate + persist if missing.

    Creates parent dir with 0o700 if missing. File chmod 0o600.

    Parameters
    ----------
    path:
        Filesystem path for the token file.  Defaults to
        ``~/.dadaia/state/panel.token``.

    Returns
    -------
    str
        The token value (read from file or freshly generated).
    """
    if path.exists():
        return path.read_text().strip()

    # Create parent directory with restricted permissions.
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    os.chmod(parent, 0o700)

    token = secrets.token_urlsafe(32)

    # Atomic restricted-mode create: O_CREAT|O_WRONLY|O_EXCL|0o600 so the
    # file is born at 0o600 — there is no window where it exists at a wider
    # mode (OWASP A02, TOCTOU fix).  O_EXCL also prevents a race where two
    # processes both try to create the token simultaneously.
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    except FileExistsError:
        # Another process beat us to creation; read their token.
        return path.read_text().strip()

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
