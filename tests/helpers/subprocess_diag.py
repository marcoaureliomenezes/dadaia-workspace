"""Shared non-blocking subprocess stderr diagnostic helper.

Extracted from ``tests/e2e/features/test_panel.py`` (T-043-25 / FR18b, Verdict 1) so it
has a single home reachable from both its production caller-in-tests (``test_panel.py``'s
``_wait_for_ready`` diagnostic path) and its own dedicated coverage
(``tests/integration/features/test_panel_stderr_drain.py``), instead of two independent
copies drifting apart.

Bug ``panel-e2e-readiness-flaky-under-xdist-load``: reading through the TEXT-mode wrapper
here is unsound — on an empty non-blocking pipe the raw layer returns ``None`` and the
codec crashes with ``TypeError: can't concat NoneType to bytes``, turning this diagnostic
path into the test failure itself whenever a panel was merely slow to start. Read the fd
directly and decode.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
import time


def drain_stderr_nonblocking(proc: subprocess.Popen[str], wait: float = 0.3) -> str:
    """Best-effort, NON-blocking read of whatever is currently on stderr.

    A long-running process (e.g. one running ``serve_forever``) never closes its pipes,
    so a plain ``proc.stderr.read()`` on a live process blocks forever. We mark the fd
    non-blocking and read what is buffered so diagnostics never hang the caller.
    """
    if proc.stderr is None:
        return ""
    time.sleep(wait)
    fd = proc.stderr.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    chunks: list[bytes] = []
    try:
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
    except (BlockingIOError, OSError):
        pass
    return b"".join(chunks).decode("utf-8", errors="replace")
