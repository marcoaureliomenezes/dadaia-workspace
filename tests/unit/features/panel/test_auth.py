"""Unit tests for features/panel/auth.py — Bearer token auth (T-AM-13).

Per TDD: tests written first. They will fail until auth.py is created.
"""

from __future__ import annotations

import inspect
import os
import pathlib

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_auth():
    from dadaia_workspace.features.panel import auth  # type: ignore[import]

    return auth


# ---------------------------------------------------------------------------
# ensure_token tests
# ---------------------------------------------------------------------------


class TestEnsureToken:
    def test_ensure_token_creates_file_with_0o600(self, tmp_path: pathlib.Path) -> None:
        """Token file created with mode 0o600; parent dir created with mode 0o700."""
        auth = _import_auth()
        token_path = tmp_path / "state" / "panel.token"

        auth.ensure_token(token_path)

        assert token_path.exists(), "Token file should be created"
        stat = os.stat(token_path)
        assert stat.st_mode & 0o777 == 0o600, f"File mode must be 0o600, got {oct(stat.st_mode)}"

        parent_stat = os.stat(token_path.parent)
        assert parent_stat.st_mode & 0o777 == 0o700, (
            f"Dir mode must be 0o700, got {oct(parent_stat.st_mode)}"
        )

    def test_ensure_token_existing_returned_as_is(self, tmp_path: pathlib.Path) -> None:
        """Pre-existing token file is returned as-is without regenerating."""
        auth = _import_auth()
        token_path = tmp_path / "panel.token"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text("abc123")
        os.chmod(token_path, 0o600)

        result = auth.ensure_token(token_path)

        assert result == "abc123"

    def test_ensure_token_generates_url_safe(self, tmp_path: pathlib.Path) -> None:
        """Fresh path generates a URL-safe token of length >= 32 with no whitespace."""
        auth = _import_auth()
        token_path = tmp_path / "subdir" / "panel.token"

        token = auth.ensure_token(token_path)

        assert len(token) >= 32, f"Token too short: {len(token)}"
        assert not any(c.isspace() for c in token), "Token must not contain whitespace"

        # URL-safe base64 charset: [A-Za-z0-9_-]
        import re

        assert re.fullmatch(r"[A-Za-z0-9_\-]+", token), (
            f"Token contains non-urlsafe chars: {token!r}"
        )


# ---------------------------------------------------------------------------
# validate tests
# ---------------------------------------------------------------------------


class TestValidate:
    def test_validate_valid_header(self) -> None:
        """'Bearer xyz' with expected 'xyz' returns True."""
        auth = _import_auth()
        assert auth.validate("Bearer xyz", "xyz") is True

    def test_validate_missing_header(self) -> None:
        """None header returns False."""
        auth = _import_auth()
        assert auth.validate(None, "xyz") is False

    def test_validate_no_bearer_prefix(self) -> None:
        """Header without 'Bearer ' prefix returns False."""
        auth = _import_auth()
        assert auth.validate("xyz", "xyz") is False

    def test_validate_wrong_token(self) -> None:
        """Wrong token with correct prefix returns False."""
        auth = _import_auth()
        assert auth.validate("Bearer abc", "xyz") is False

    def test_validate_empty_string(self) -> None:
        """Empty string header returns False."""
        auth = _import_auth()
        assert auth.validate("", "any_token") is False

    def test_validate_just_prefix(self) -> None:
        """'Bearer ' with no token after it returns False."""
        auth = _import_auth()
        assert auth.validate("Bearer ", "anything") is False

    def test_validate_constant_time(self) -> None:
        """validate() uses hmac.compare_digest for constant-time comparison.

        Inspect the source to confirm the reference is used; this guards
        against accidental replacement with '==' which would be timing-attackable.
        """
        auth = _import_auth()
        source = inspect.getsource(auth.validate)
        assert "compare_digest" in source, (
            "validate() must use hmac.compare_digest for constant-time comparison"
        )
