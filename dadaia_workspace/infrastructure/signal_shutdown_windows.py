"""Windows signal shutdown adapter — SIGINT only.

On Windows, ``signal.signal(signal.SIGTERM, ...)`` raises ``OSError`` because
SIGTERM is not a real signal in the Win32 process model.  This adapter
registers SIGINT only and logs an INFO message noting that SIGTERM is skipped.

This adapter is safe to import on all platforms; the SIGTERM registration is
intentionally absent (not guarded by a conditional).

Usage::

    handler = WindowsSignalShutdownHandler()
    handler.install(server)
"""

from __future__ import annotations

import logging
import signal
import threading
from http.server import ThreadingHTTPServer

logger = logging.getLogger(__name__)


class WindowsSignalShutdownHandler:
    """Install SIGINT-only shutdown handler for *server* (Windows-safe).

    SIGTERM is intentionally not registered.  On Windows,
    ``signal.signal(signal.SIGTERM, ...)`` raises ``OSError`` because SIGTERM
    is not a real Win32 signal.  An INFO log message is emitted to document
    the omission so that operators are aware of the platform limitation.

    Signal handling discipline:
    - The SIGINT handler spawns a daemon thread that calls
      ``server.shutdown()``.  The handler frame itself MUST NOT call
      ``shutdown()`` directly (deadlock risk with the serving loop).
    - ``signal.signal()`` requires the calling thread to be the process main
      thread.  Calling ``install()`` from a background thread raises
      ``ValueError``.
    """

    def install(self, server: ThreadingHTTPServer) -> None:
        """Register SIGINT shutdown handler for *server*.

        SIGTERM is not registered on Windows; see class docstring.

        Parameters
        ----------
        server:
            The ``ThreadingHTTPServer`` instance to shut down on SIGINT.

        Raises
        ------
        ValueError
            If called from a non-main thread (``signal.signal()`` constraint).
        """
        logger.info(
            "WindowsSignalShutdownHandler: SIGTERM registration skipped on Windows "
            "(signal.signal(SIGTERM, ...) raises OSError on this platform). "
            "Only SIGINT (Ctrl+C) is handled."
        )

        def _shutdown_in_thread() -> None:
            t = threading.Thread(target=server.shutdown, daemon=True)
            t.start()

        def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
            _shutdown_in_thread()

        signal.signal(signal.SIGINT, _handler)
        logger.debug("WindowsSignalShutdownHandler: SIGINT handler installed.")
