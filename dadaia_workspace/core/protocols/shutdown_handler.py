"""ShutdownHandler protocol — platform-agnostic signal/shutdown interface.

Consumers (CLI commands) inject a ShutdownHandler and call ``install(server)``
to register OS-level signals that will shut the HTTP server down cleanly.

Concrete adapters live in ``infrastructure/``:
  - ``signal_shutdown_posix.py``:  SIGTERM + SIGINT (Linux / macOS)
  - ``signal_shutdown_windows.py``: SIGINT only (Windows — SIGTERM raises OSError)

The factory ``container.build_shutdown_handler()`` selects the correct adapter.
"""

from __future__ import annotations

from http.server import ThreadingHTTPServer
from typing import Protocol


class ShutdownHandler(Protocol):
    """Install OS signal handlers that shut *server* down gracefully.

    Implementations must:
    - Spawn a daemon thread that calls ``server.shutdown()`` — the signal
      handler frame MUST NOT call ``shutdown()`` directly (deadlock risk with
      the serving loop).
    - Register signals only when called from the process main thread.
    - Windows adapters MUST NOT call ``signal.signal(SIGTERM, ...)``; SIGTERM
      registration raises ``OSError`` on Windows.

    Raises
    ------
    ValueError
        If called from a non-main thread.
    """

    def install(self, server: ThreadingHTTPServer) -> None:
        """Register shutdown signal handlers for *server*."""
        ...
