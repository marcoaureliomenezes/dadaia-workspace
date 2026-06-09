"""Unit tests for features/panel/auth.py bearer token auth."""

from __future__ import annotations

import inspect
import os
import pathlib
import sys
import unittest.mock

import pytest

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
    @pytest.mark.skipif(sys.platform == "win32", reason="os.chmod mode bits are no-op on Windows")
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

    def test_ensure_token_atomic_create_mode_0o600_no_widen_window(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Token file must be created with mode 0o600 atomically via O_EXCL.

        This test verifies two invariants of the TOCTOU fix:
        1. The file is created with O_EXCL (atomic) — no intermediate state
           where the file exists with a wider mode before being restricted.
        2. At the instant the file first appears on disk its mode is already
           0o600 (never wider).

        Strategy: intercept os.open to capture the flags and mode passed on
        the first call, then assert O_CREAT|O_WRONLY|O_EXCL and mode 0o600
        are used.  We do NOT call the real os.open (we call it via the spy)
        so the file still gets created, but we record the arguments.
        """
        auth = _import_auth()
        token_path = tmp_path / "state" / "panel.token"

        recorded_calls: list[dict[str, object]] = []
        _real_os_open = os.open

        def _spy_open(path: str, flags: int, mode: int = 0o777, **kw: object) -> int:
            recorded_calls.append({"path": path, "flags": flags, "mode": mode})
            return _real_os_open(path, flags, mode, **kw)

        with unittest.mock.patch("os.open", side_effect=_spy_open):
            auth.ensure_token(token_path)

        # At least one os.open call must have been made
        assert recorded_calls, "ensure_token did not call os.open"

        # The first call (file creation) must use O_EXCL | O_CREAT | O_WRONLY
        creation_call = recorded_calls[0]
        flags = int(creation_call["flags"])  # type: ignore[arg-type]
        assert flags & os.O_CREAT, "O_CREAT flag must be set"
        assert flags & os.O_WRONLY, "O_WRONLY flag must be set"
        assert flags & os.O_EXCL, "O_EXCL flag must be set (prevents widen-then-narrow window)"

        # Mode on creation must be 0o600
        assert creation_call["mode"] == 0o600, (
            f"Creation mode must be 0o600, got {oct(int(creation_call['mode']))}"  # type: ignore[arg-type]
        )

        # Resulting file on disk must also be 0o600
        result_stat = os.stat(token_path)
        assert result_stat.st_mode & 0o777 == 0o600, (
            f"On-disk file mode must be 0o600, got {oct(result_stat.st_mode)}"
        )

    def test_ensure_token_already_exists_graceful(self, tmp_path: pathlib.Path) -> None:
        """When the token file already exists, ensure_token returns its content gracefully.

        This verifies the already-exists case does not raise EEXIST.
        """
        auth = _import_auth()
        token_path = tmp_path / "panel.token"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text("existing-token")
        os.chmod(token_path, 0o600)

        result = auth.ensure_token(token_path)

        assert result == "existing-token"


# ---------------------------------------------------------------------------
# Permission setter injection tests
# ---------------------------------------------------------------------------


class TestEnsureTokenPermissionSetter:
    def test_ensure_token_calls_restrict_dir_before_creation(self, tmp_path: pathlib.Path) -> None:
        """When permission_setter is provided, restrict_dir_to_owner is called before token creation."""
        from tests.fakes import FakeFilePermissionSetter

        auth = _import_auth()
        setter = FakeFilePermissionSetter()
        token_path = tmp_path / "state" / "panel.token"

        auth.ensure_token(token_path, permission_setter=setter)

        assert token_path.exists(), "Token file should be created"
        assert len(setter.restricted_dirs) == 1, (
            "restrict_dir_to_owner must be called exactly once on the parent dir"
        )
        assert setter.restricted_dirs[0][0] == token_path.parent

    def test_ensure_token_permission_error_propagates(self, tmp_path: pathlib.Path) -> None:
        """PlatformSecurityError from permission_setter propagates without suppression (Tier-1)."""
        from dadaia_workspace.core.exceptions import PlatformSecurityError
        from tests.fakes import FakeFilePermissionSetter

        auth = _import_auth()
        setter = FakeFilePermissionSetter(raise_on_next=True)
        token_path = tmp_path / "state" / "panel.token"

        with pytest.raises(PlatformSecurityError):
            auth.ensure_token(token_path, permission_setter=setter)

        # Token must NOT have been created after the security error
        assert not token_path.exists(), (
            "Token file MUST NOT be created after PlatformSecurityError "
            "(panel must not start with unprotected token)"
        )

    def test_ensure_token_existing_file_skips_setter(self, tmp_path: pathlib.Path) -> None:
        """If token already exists, permission_setter is not called."""
        from tests.fakes import FakeFilePermissionSetter

        auth = _import_auth()
        token_path = tmp_path / "panel.token"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text("abc123")
        if sys.platform != "win32":
            os.chmod(token_path, 0o600)

        setter = FakeFilePermissionSetter()
        result = auth.ensure_token(token_path, permission_setter=setter)

        assert result == "abc123"
        assert len(setter.restricted_dirs) == 0, (
            "restrict_dir_to_owner must not be called when token file already exists"
        )

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Panel startup with unprotected token test requires POSIX mode bits",
    )
    def test_panel_does_not_start_with_unprotected_token_on_mocked_windows(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Panel startup with a mocked Windows environment raises PlatformSecurityError.

        Simulates the Windows path by using a FakeFilePermissionSetter that raises
        PlatformSecurityError on restrict_dir_to_owner — ensure_token propagates it.
        """
        from dadaia_workspace.core.exceptions import PlatformSecurityError
        from tests.fakes import FakeFilePermissionSetter

        auth = _import_auth()
        token_path = tmp_path / "state" / "panel.token"
        failing_setter = FakeFilePermissionSetter(raise_on_next=True)

        with pytest.raises(PlatformSecurityError):
            auth.ensure_token(token_path, permission_setter=failing_setter)

    def test_no_setter_fallback_fails_loud_when_chmod_is_noop(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No setter + chmod no-op platform (Windows) must raise, not silently no-op (CWE-732).

        Guards the fallback branch: the production panel always injects a setter, but a
        misuse calling ensure_token() without one on a non-chmod platform must refuse
        rather than create an unprotected token.
        """
        import dataclasses

        from dadaia_workspace.core.exceptions import PlatformSecurityError

        auth = _import_auth()
        # Simulate a no-effective-chmod platform (Windows) via the PLATFORM seam.
        fake_platform = dataclasses.replace(auth.PLATFORM, has_posix_chmod=False)
        monkeypatch.setattr(auth, "PLATFORM", fake_platform)
        token_path = tmp_path / "state" / "panel.token"

        with pytest.raises(PlatformSecurityError):
            auth.ensure_token(token_path)  # no permission_setter

        assert not token_path.exists(), (
            "Token MUST NOT be created when chmod is a no-op and no setter is provided"
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
