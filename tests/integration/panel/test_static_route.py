"""Integration tests for GET /static/<name> — static asset serving.

Coverage areas:
  - Known assets served with correct MIME type, no-cache, no credential required
  - Path-traversal / unknown-name defence (400/404 table)

Panel auth removed by operator decision 2026-06-11 — the panel serves every
route without a credential; the no-auth + Host-guard contract is pinned in
tests/unit/features/panel/test_no_auth_contract.py.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views.static import render_static
from tests.integration.panel.conftest import get


@pytest.fixture(scope="module")
def static_server(panel_server_factory) -> str:
    return panel_server_factory({"static": render_static()})


class TestStaticKnownAssets:
    def test_tokens_css_served(self, static_server: str) -> None:
        status, headers, body = get(f"{static_server}/static/tokens.css")
        assert status == 200
        assert "text/css" in headers.get("content-type", "")
        assert len(body) > 0
        assert "no-cache" in headers.get("cache-control", "")

    def test_core_js_served(self, static_server: str) -> None:
        status, headers, body = get(f"{static_server}/static/core.js")
        assert status == 200
        assert "javascript" in headers.get("content-type", "")
        assert len(body) > 0

    def test_logo_svg_served(self, static_server: str) -> None:
        status, headers, body = get(f"{static_server}/static/logo-rhino-24.svg")
        assert status == 200
        assert "svg" in headers.get("content-type", "")
        assert len(body) > 0

    def test_static_route_no_credential_required(self, static_server: str) -> None:
        status, _, _ = get(f"{static_server}/static/tokens.css")
        assert status == 200


class TestStaticTraversalAndUnknownTable:
    @pytest.mark.parametrize(
        ("name", "expected_status"),
        [
            ("..%2Fetc%2Fpasswd", 400),  # dot-dot-slash traversal blocked
            ("..tokens.css", 400),  # dots-in-name triggers traversal check
            ("foo%5Cbar", 404),  # URL-encoded backslash — dict-only lookup, no fs reached
            ("nonexistent.css", 404),  # unknown asset name
            ("core.php", 404),  # unknown extension not in MIME map
        ],
    )
    def test_traversal_and_unknown_names(
        self, static_server: str, name: str, expected_status: int
    ) -> None:
        status, _, _ = get(f"{static_server}/static/{name}")
        assert status == expected_status
