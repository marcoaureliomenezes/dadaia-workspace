"""Integration tests for panel server binding and clean shutdown.

Merged (plan-integration.md): build (type+binding) -> serve -> shutdown-from-thread
within 2s -> port rebindable, as one fn. The host-parameterized duplicate and the
handler-factory attribute check (unit-ownable) are dropped; the port-rebind assertion
folds in as the tail of the same scenario.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from dadaia_workspace.features.panel.server import build_panel_http_server


class _NoopHandler(BaseHTTPRequestHandler):
    """Handler that silently ignores all requests."""

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def _serve_in_thread(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()
    return thread


def test_build_serve_shutdown_and_rebind_lifecycle() -> None:
    """build_panel_http_server -> serve -> shutdown within 2s from another thread -> rebindable.

    Signal discipline: we do NOT call serve_blocking() because it installs signal
    handlers, which requires the main thread and would interfere with pytest's own
    handlers. Calling server.shutdown() from a helper thread exercises the same
    shutdown path serve_blocking's daemon thread uses.
    """
    server = build_panel_http_server("127.0.0.1", 0, _NoopHandler)
    assert isinstance(server, ThreadingHTTPServer)
    host, port = server.server_address  # type: ignore[misc]
    assert host == "127.0.0.1"
    assert port > 0

    serve_thread = _serve_in_thread(server)
    with urlopen(f"http://{host}:{port}/", timeout=2) as response:  # noqa: S310
        assert response.status in {200, 204}

    shutdown_thread = threading.Thread(target=server.shutdown, daemon=True)
    shutdown_thread.start()
    serve_thread.join(timeout=2.0)
    assert not serve_thread.is_alive(), (
        "Server did not shut down within 2 s after server.shutdown() was called "
        "from a separate thread."
    )
    server.server_close()

    # Port should be reclaimable now.
    server2 = build_panel_http_server("127.0.0.1", port, _NoopHandler)
    try:
        assert isinstance(server2, ThreadingHTTPServer)
    finally:
        server2.server_close()
