"""Panel HTTP server factory and blocking runner.

Provides two public functions:

    build_panel_http_server(host, port, handler_factory) -> ThreadingHTTPServer
        Creates a ThreadingHTTPServer bound to (host, port) using the supplied
        handler factory.  Does NOT start serving; caller controls the lifecycle.

    serve_blocking(server)
        Blocks until SIGINT or SIGTERM.  Per R2 (signal handler deadlock
        pattern — locked):
          - Signal handlers spawn a daemon thread that calls server.shutdown();
            the handler frame itself MUST NOT call shutdown() directly (doing so
            would deadlock the serving loop against the signal frame).
          - signal.signal() is installed ONLY when this function runs on the
            main thread (the Typer CLI command path).  Integration tests that
            start serve_forever() in a background thread MUST NOT call
            serve_blocking() and MUST NOT install signal handlers.
          - Clean shutdown completes within 2 s (NFR-4 / AC-9).
"""

from __future__ import annotations

import signal
import threading
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


def serve_blocking(server: ThreadingHTTPServer) -> None:
    """Block until SIGINT or SIGTERM, then shut down *server* cleanly.

    Signal handling discipline (R2 — locked):
    - Handlers spawn a *daemon* thread calling ``server.shutdown()``.
    - The handler frame returns immediately; it never calls ``shutdown()``
      directly (that would deadlock the serving loop running in the calling
      thread).
    - ``signal.signal()`` is installed here, which requires the calling thread
      to be the process main thread.  Tests that call ``serve_forever()``
      directly in a background thread must not call this function.

    Raises
    ------
    ValueError
        If called from a non-main thread (Python raises this when
        ``signal.signal()`` is used outside the main thread).
    """

    def _shutdown_in_thread() -> None:
        t = threading.Thread(target=server.shutdown, daemon=True)
        t.start()

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        _shutdown_in_thread()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    server.serve_forever()
