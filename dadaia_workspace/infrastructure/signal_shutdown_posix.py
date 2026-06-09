"""POSIX signal shutdown adapter — SIGTERM + SIGINT.

Registers both SIGTERM and SIGINT handlers on POSIX platforms (Linux, macOS).
Each handler spawns a daemon thread that calls ``server.shutdown()`` so that
the signal frame returns immediately and avoids deadlocking the serving loop.

This adapter MUST NOT be imported or instantiated on Windows.
On Windows, use ``signal_shutdown_windows.py`` (SIGINT only).
"""

from __future__ import annotations

import logging
import signal
import threading
from http.server import ThreadingHTTPServer

logger = logging.getLogger(__name__)


class PosixSignalShutdownHandler:
    """Install SIGTERM + SIGINT handlers that shut *server* down cleanly.

    Signal handling discipline (R2 — locked):
    - Handlers spawn a *daemon* thread calling ``server.shutdown()``.
    - The handler frame returns immediately; it never calls ``shutdown()``
      directly (that would deadlock the serving loop running in the calling
      thread).
    - ``signal.signal()`` requires the calling thread to be the process main
      thread.  Calling ``install()`` from a background thread raises
      ``ValueError``.
    """

    def install(self, server: ThreadingHTTPServer) -> None:
        """Register SIGTERM + SIGINT shutdown handlers for *server*.

        Parameters
        ----------
        server:
            The ``ThreadingHTTPServer`` instance to shut down on signal.

        Raises
        ------
        ValueError
            If called from a non-main thread (``signal.signal()`` constraint).
        """

        def _shutdown_in_thread() -> None:
            t = threading.Thread(target=server.shutdown, daemon=True)
            t.start()

        def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
            _shutdown_in_thread()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
        logger.debug("PosixSignalShutdownHandler: SIGINT + SIGTERM handlers installed.")
