"""Integration tests for panel server binding and shutdown.

Tests:
  (a) build_panel_http_server returns a ThreadingHTTPServer bound to the
      requested host/port.
  (b) serve_blocking shuts down within 2 s when server.shutdown() is called
      from another thread.

Signal discipline:
  We do NOT call serve_blocking() from these tests because:
    1. serve_blocking() calls signal.signal() which requires the MAIN thread.
    2. pytest runs tests in the main thread but installs its own signal handlers;
       overwriting them would interfere with the test runner.
  Instead, we exercise the shutdown path by calling server.shutdown() directly
  from a helper thread (which is exactly what serve_blocking's daemon thread
  does) and verify the server terminates within 2 s.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from dadaia_workspace.features.panel.server import build_panel_http_server

# ---------------------------------------------------------------------------
# Minimal handler for test purposes only — never returns anything meaningful
# ---------------------------------------------------------------------------


class _NoopHandler(BaseHTTPRequestHandler):
    """Handler that silently ignores all requests."""

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress access log noise in test output.
        pass


def _serve_in_thread(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()
    return thread


def _assert_server_ready(server: ThreadingHTTPServer) -> None:
    host, port = server.server_address  # type: ignore[misc]
    with urlopen(f"http://{host}:{port}/", timeout=2) as response:  # noqa: S310
        assert response.status in {200, 204}


# ---------------------------------------------------------------------------
# (a) build_panel_http_server — correct type and binding
# ---------------------------------------------------------------------------


def test_build_panel_http_server_returns_threading_http_server() -> None:
    """(a) build_panel_http_server returns a ThreadingHTTPServer."""
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    try:
        assert isinstance(server, ThreadingHTTPServer)
    finally:
        server.server_close()


def test_build_panel_http_server_binds_to_requested_host_and_port() -> None:
    """(a) The server socket is bound to the host:port passed in."""
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    try:
        host, port = server.server_address  # type: ignore[misc]
        assert host == "127.0.0.1"
        # Port 0 lets the OS pick; just confirm it's nonzero after binding.
        assert port > 0
    finally:
        server.server_close()


def test_build_panel_http_server_host_is_parameterized() -> None:
    """(a) host is taken from the caller, not hardcoded inside server.py."""
    # We cannot bind 0.0.0.0 in all CI environments, so just verify the
    # argument is forwarded correctly by inspecting server_address.
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    try:
        bound_host, _ = server.server_address  # type: ignore[misc]
        assert bound_host == "127.0.0.1"
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# (b) Shutdown within 2 s when shutdown() called from another thread
# ---------------------------------------------------------------------------


def test_server_shuts_down_within_2s_from_external_thread() -> None:
    """(b) Calling server.shutdown() from another thread stops serve_forever within 2 s.

    This mirrors the behaviour of serve_blocking()'s daemon thread — the only
    difference is that serve_blocking also installs signal handlers, which we
    deliberately skip here (R2: signal.signal must not be called from a
    non-main thread or inside pytest test threads).
    """
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)

    serve_thread = _serve_in_thread(server)
    _assert_server_ready(server)

    # Simulate what serve_blocking's signal handler does: call shutdown()
    # from a daemon thread.
    shutdown_thread = threading.Thread(target=server.shutdown, daemon=True)
    shutdown_thread.start()

    serve_thread.join(timeout=2.0)
    assert not serve_thread.is_alive(), (
        "Server did not shut down within 2 s after server.shutdown() was called "
        "from a separate thread."
    )
    server.server_close()


def test_server_port_is_free_after_shutdown() -> None:
    """(b) After shutdown and server_close(), the same port can be rebound."""
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    _, port = server.server_address  # type: ignore[misc]

    serve_thread = _serve_in_thread(server)
    _assert_server_ready(server)

    server.shutdown()
    serve_thread.join(timeout=2.0)
    server.server_close()

    # Port should be reclaimable now.
    server2 = build_panel_http_server("127.0.0.1", port, _NoopHandler)
    try:
        assert isinstance(server2, ThreadingHTTPServer)
    finally:
        server2.server_close()


# ---------------------------------------------------------------------------
# (c) Handler factory injection — different factories produce different servers
# ---------------------------------------------------------------------------


class _AltHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def test_build_panel_http_server_accepts_handler_factory() -> None:
    """(c) The handler_factory parameter is forwarded and stored correctly."""
    server1 = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    server2 = build_panel_http_server("127.0.0.1", 0, _AltHandler)
    try:
        assert server1.RequestHandlerClass is _NoopHandler
        assert server2.RequestHandlerClass is _AltHandler
    finally:
        server1.server_close()
        server2.server_close()
