"""Unit tests for the panel launch-token mechanism (T-011-13 / ADR-10).

The launch token is a single-use, short-TTL credential carried in the launch
URL **instead of** the long-lived Bearer.  On first GET of the panel shell the
server consumes the launch token and mints the session cookie; the launch token
is invalidated immediately.  Replay or use after expiry returns False (the
handler maps that to 401).

These tests pin the store semantics in isolation (no HTTP).  The handler-level
cookie-exchange + 401-on-replay behaviour is covered in test_handler.py and the
binding e2e contract in tests/e2e/features/test_panel.py.
"""

from __future__ import annotations

import re

import pytest


def _import_auth():
    from dadaia_workspace.features.panel import auth  # type: ignore[import]

    return auth


class TestLaunchTokenStore:
    def test_mint_returns_url_safe_token(self) -> None:
        """A minted launch token is a non-empty URL-safe string (safe in a URL)."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)

        tok = store.mint()

        assert tok
        assert re.fullmatch(r"[A-Za-z0-9_\-]+", tok), f"launch token not url-safe: {tok!r}"

    def test_ttl_capped_at_60_seconds(self) -> None:
        """ADR-10 pins TTL <= 60s; a larger request is clamped, not honoured."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=3600)

        assert store.ttl_seconds <= 60

    def test_consume_valid_token_returns_true_once(self) -> None:
        """First consume of a fresh token succeeds (single-use begins green)."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)
        tok = store.mint()

        assert store.consume(tok) is True

    def test_consume_is_single_use_replay_is_false(self) -> None:
        """Replay of a consumed token returns False (handler maps to 401)."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)
        tok = store.mint()

        assert store.consume(tok) is True
        assert store.consume(tok) is False, "consumed launch token must not validate twice"

    def test_consume_unknown_token_is_false(self) -> None:
        """A token never minted by this store is rejected."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)

        assert store.consume("never-minted") is False

    def test_consume_none_or_empty_is_false(self) -> None:
        """None / empty launch token is rejected (no truthy bypass)."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)

        assert store.consume(None) is False
        assert store.consume("") is False

    def test_expired_token_is_false(self) -> None:
        """A token older than its TTL is rejected (uses injectable clock)."""
        auth = _import_auth()
        now = [1000.0]
        store = auth.LaunchTokenStore(ttl_seconds=60, clock=lambda: now[0])
        tok = store.mint()

        now[0] = 1061.0  # 61s later — past the 60s TTL
        assert store.consume(tok) is False, "expired launch token must not validate"

    def test_token_valid_within_ttl_window(self) -> None:
        """A token consumed just before expiry still validates (boundary)."""
        auth = _import_auth()
        now = [1000.0]
        store = auth.LaunchTokenStore(ttl_seconds=60, clock=lambda: now[0])
        tok = store.mint()

        now[0] = 1059.0  # 59s later — inside the window
        assert store.consume(tok) is True

    def test_minted_token_is_unique_per_call(self) -> None:
        """Each mint() returns a distinct token (no fixed/guessable value)."""
        auth = _import_auth()
        store = auth.LaunchTokenStore(ttl_seconds=60)

        assert store.mint() != store.mint()

    def test_default_ttl_is_within_cap(self) -> None:
        """Default construction yields a TTL within the ADR-10 cap."""
        auth = _import_auth()
        store = auth.LaunchTokenStore()

        assert 0 < store.ttl_seconds <= 60


class TestSessionCookieHelper:
    def test_build_session_cookie_has_required_flags(self) -> None:
        """The minted Set-Cookie carries SameSite=Strict; HttpOnly; Path=/ (ADR-10)."""
        auth = _import_auth()

        cookie = auth.build_session_cookie("sekret-bearer")

        assert cookie.startswith(f"{auth.SESSION_COOKIE_NAME}=sekret-bearer")
        # Case-insensitive attribute checks (RFC 6265 attributes are case-insensitive).
        low = cookie.lower()
        assert "httponly" in low, "session cookie must be HttpOnly"
        assert "samesite=strict" in low, "session cookie must be SameSite=Strict"
        assert "path=/" in low, "session cookie must scope Path=/"

    def test_session_cookie_value_is_the_bearer(self) -> None:
        """The cookie value is the session credential (the Bearer), set server-side.

        The Bearer is carried in a header, never a URL — see the no-URL grep
        contract test_no_bearer_in_url.py and the e2e.
        """
        auth = _import_auth()

        cookie = auth.build_session_cookie("the-bearer-value")

        assert "the-bearer-value" in cookie

    def test_session_cookie_rejects_unsafe_value(self) -> None:
        """A cookie value with CR/LF/; is rejected (header-injection guard, A03)."""
        auth = _import_auth()

        with pytest.raises(ValueError):
            auth.build_session_cookie("bad\r\nSet-Cookie: evil=1")
        with pytest.raises(ValueError):
            auth.build_session_cookie("has;semicolon")
