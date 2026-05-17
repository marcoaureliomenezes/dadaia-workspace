"""Unit tests for the _security_headers helper in handler.py (T-AM-14).

Uses a minimal harness that calls _security_headers() and inspects
what headers would be sent, avoiding the need to spin up a real HTTP server
for this unit test.
"""
from __future__ import annotations

from unittest.mock import MagicMock


def _make_handler_with_spy():
    """Return a PanelHandler-like instance with a tracked send_header."""
    from dadaia_workspace.features.panel.handler import make_handler_class

    # Minimal stub views — only "index" key required for make_handler_class.
    stub_views: dict = {
        "index": lambda **kw: (200, "text/html; charset=utf-8", b"<html></html>"),
        "api_servers": lambda **kw: (200, "application/json", b"{}"),
        "api_contexts": lambda **kw: (200, "application/json", b"{}"),
        "memory": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "memory_view": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "static": lambda **kw: (200, "text/plain", b"ok"),
    }
    HandlerClass = make_handler_class(stub_views)
    handler = HandlerClass.__new__(HandlerClass)
    headers_sent: list[tuple[str, str]] = []
    handler.send_header = lambda k, v: headers_sent.append((k, v))  # type: ignore[assignment]
    return handler, headers_sent


class TestSecurityHeaders:
    def test_html_response_sends_csp_header(self) -> None:
        """HTML content type causes Content-Security-Policy to be sent."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("text/html; charset=utf-8")  # type: ignore[attr-defined]

        header_names = [k for k, v in headers_sent]
        assert "Content-Security-Policy" in header_names, (
            "CSP header must be sent for HTML responses"
        )

    def test_html_csp_value(self) -> None:
        """CSP value matches SPEC § Threat matrix T8."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("text/html")  # type: ignore[attr-defined]

        csp_headers = [v for k, v in headers_sent if k == "Content-Security-Policy"]
        assert csp_headers, "No CSP header found"
        csp = csp_headers[0]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'unsafe-inline'" in csp

    def test_json_response_sends_nosniff_header(self) -> None:
        """application/json content type causes X-Content-Type-Options: nosniff to be sent."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("application/json")  # type: ignore[attr-defined]

        nosniff = [(k, v) for k, v in headers_sent if k == "X-Content-Type-Options"]
        assert nosniff, "X-Content-Type-Options header must be sent for JSON responses"
        assert nosniff[0][1] == "nosniff"

    def test_html_does_not_send_nosniff(self) -> None:
        """HTML responses should not have X-Content-Type-Options (only nosniff for JSON)."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("text/html")  # type: ignore[attr-defined]

        nosniff = [k for k, v in headers_sent if k == "X-Content-Type-Options"]
        assert not nosniff, "HTML responses should not include X-Content-Type-Options"

    def test_json_does_not_send_csp(self) -> None:
        """JSON responses should not emit CSP (CSP only for HTML)."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("application/json")  # type: ignore[attr-defined]

        csp = [k for k, v in headers_sent if k == "Content-Security-Policy"]
        assert not csp, "JSON responses should not include Content-Security-Policy"

    def test_other_content_type_sends_no_security_headers(self) -> None:
        """Other content types (e.g. text/plain) send neither CSP nor nosniff."""
        handler, headers_sent = _make_handler_with_spy()
        handler._security_headers("text/plain")  # type: ignore[attr-defined]

        security_headers = [k for k, v in headers_sent
                            if k in ("Content-Security-Policy", "X-Content-Type-Options")]
        assert not security_headers
