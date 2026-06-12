"""Integration tests for GET /static/<name> — static asset serving.

Coverage areas:
  - Known assets served with correct MIME type
  - Path traversal defence-in-depth (names with / \\ .. rejected with 400)
  - Unknown file names → 404
  - Cache-Control: no-cache header is present on /static/ responses
  - Static route is accessible without any credential

Panel auth removed by operator decision 2026-06-11 — the panel serves every
route without a credential; the no-auth + Host-guard contract is pinned in
tests/unit/features/panel/test_no_auth_contract.py.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.static import render_static

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, headers, exc.read()


def _build_static_server() -> ThreadingHTTPServer:
    def _stub_html(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json; charset=utf-8", b"{}")

    views: dict[str, Any] = {
        "index": _stub_html,
        "api_servers": _stub_json,
        "api_contexts": _stub_json,
        "memory": _stub_html,
        "memory_view": _stub_html,
        "static": render_static(),
    }
    # The panel serves every route without a credential (no-auth decision).
    HandlerClass = make_handler_class(views, telemetry=None)
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


@pytest.fixture(scope="module")
def static_server():
    """Starts static-serving panel; yields base_url."""
    server = _build_static_server()
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()
    yield base_url
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests: Known assets served correctly
# ---------------------------------------------------------------------------


class TestStaticKnownAssets:
    def test_tokens_css_served(self, static_server: str) -> None:
        """GET /static/tokens.css → 200, Content-Type: text/css."""
        status, headers, body = _get(f"{static_server}/static/tokens.css")
        assert status == 200
        assert "text/css" in headers.get("content-type", "")
        assert len(body) > 0

    def test_core_js_served(self, static_server: str) -> None:
        """GET /static/core.js → 200, Content-Type: application/javascript."""
        status, headers, body = _get(f"{static_server}/static/core.js")
        assert status == 200
        assert "javascript" in headers.get("content-type", "")
        assert len(body) > 0

    def test_logo_svg_served(self, static_server: str) -> None:
        """GET /static/logo-rhino-24.svg → 200, Content-Type: image/svg+xml."""
        status, headers, body = _get(f"{static_server}/static/logo-rhino-24.svg")
        assert status == 200
        assert "svg" in headers.get("content-type", "")
        assert len(body) > 0

    def test_static_route_no_credential_required(self, static_server: str) -> None:
        """GET /static/tokens.css succeeds without any credential header."""
        status, _, _ = _get(f"{static_server}/static/tokens.css")
        assert status == 200

    def test_cache_control_no_cache_header(self, static_server: str) -> None:
        """GET /static/tokens.css response includes Cache-Control: no-cache."""
        status, headers, _ = _get(f"{static_server}/static/tokens.css")
        assert status == 200
        assert "no-cache" in headers.get("cache-control", "")


# ---------------------------------------------------------------------------
# Tests: Path traversal defence
# ---------------------------------------------------------------------------


class TestStaticTraversalDefence:
    def test_traversal_dot_dot_slash_rejected(self, static_server: str) -> None:
        """GET /static/..%2Fetc%2Fpasswd → 400 (traversal blocked by _is_traversal)."""
        # The route captures [^/]+ so slashes in the path are not forwarded.
        # URL-encoded slashes (%2F) pass through to the view as part of the name.
        status, _, _ = _get(f"{static_server}/static/..%2Fetc%2Fpasswd")
        assert status == 400

    def test_traversal_backslash_url_encoded_not_found(self, static_server: str) -> None:
        """GET /static/<name-with-url-encoded-backslash> → 404.

        The URL-encoded form %5C is not decoded before the dict lookup, so the
        asset name 'foo%5Cbar' is not in _ASSETS → 404.  This is safe because
        the real filesystem is never reached (dict-only lookup).
        """
        status, _, _ = _get(f"{static_server}/static/foo%5Cbar")
        assert status == 404

    def test_traversal_dotdot_in_name_rejected(self, static_server: str) -> None:
        """GET /static/..tokens.css → 400 (.. in name triggers traversal check)."""
        status, _, _ = _get(f"{static_server}/static/..tokens.css")
        assert status == 400


# ---------------------------------------------------------------------------
# Tests: Unknown assets
# ---------------------------------------------------------------------------


class TestStaticUnknownAssets:
    def test_unknown_name_returns_404(self, static_server: str) -> None:
        """GET /static/nonexistent.css → 404."""
        status, _, _ = _get(f"{static_server}/static/nonexistent.css")
        assert status == 404

    def test_unknown_extension_returns_404(self, static_server: str) -> None:
        """GET /static/core.php → 404 (extension not in MIME map)."""
        status, _, _ = _get(f"{static_server}/static/core.php")
        assert status == 404
