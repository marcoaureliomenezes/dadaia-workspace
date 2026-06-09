"""Panel HTTP server factory.

Provides one public function:

    build_panel_http_server(host, port, handler_factory) -> ThreadingHTTPServer
        Creates a ThreadingHTTPServer bound to (host, port) using the supplied
        handler factory.  Does NOT start serving; caller controls the lifecycle.

Signal/shutdown handling is the responsibility of the injected
``ShutdownHandler`` adapter (see ``core/protocols/shutdown_handler.py``).
The CLI command (``cli/commands/panel.py``) obtains the handler from the
factory ``container.build_shutdown_handler()`` and calls
``handler.install(server)`` before announcing readiness.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def build_panel_http_server(
    host: str,
    port: int,
    handler_factory: type[BaseHTTPRequestHandler],
) -> ThreadingHTTPServer:
    """Create and return a ThreadingHTTPServer bound to *host*:*port*.

    Parameters
    ----------
    host:
        Bind address supplied by the caller.  Do not hardcode here; the CLI
        command (Phase 4) is responsible for restricting to ``127.0.0.1`` in
        Release-1 (FR-7 / bind-security constraint).
    port:
        TCP port to bind.  Caller should catch ``OSError`` (port in use).
    handler_factory:
        A ``BaseHTTPRequestHandler`` subclass (or a callable returning one).
        Passed directly to ``ThreadingHTTPServer``; supports both the plain
        class form and a factory-function form (for dependency injection in
        tests).
    """
    server = ThreadingHTTPServer((host, port), handler_factory)
    return server
