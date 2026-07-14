"""Bounded synchronization helpers for multi-process end-to-end tests."""

from __future__ import annotations

import time
from pathlib import Path

POLL_INTERVAL = 0.02


def wait_for_file(flag: Path, *, deadline_s: float, what: str) -> None:
    """Wait for a signal file or fail at a bounded deadline."""
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        if flag.exists():
            return
        time.sleep(POLL_INTERVAL)
    raise AssertionError(
        f"rendezvous timed out after {deadline_s:.1f}s waiting for {what} (flag={flag})"
    )
