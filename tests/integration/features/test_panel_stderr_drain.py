"""Regression locks for the shared non-blocking subprocess stderr drain.

Intent: CONTRACT — bug panel-e2e-readiness-flaky-under-xdist-load
Owner: software-engineer

v0.4.3 T-043-25 (FR18b, Verdict 1 — DEMOTE): moved verbatim out of
``tests/e2e/features/test_panel.py`` where this pair called
``_drain_stderr_nonblocking`` directly against a bare subprocess — no panel
started, no HTTP call made, no CLI invoked, so the ``e2e`` tier's 120 s budget and
panel-subprocess fixture machinery were unneeded. The helper itself is now shared
via ``tests.helpers.subprocess_diag`` (used by ``test_panel.py``'s own readiness
diagnostics), and this pair keeps its regression coverage — unchanged behavior,
cheaper tier.

Under full-suite xdist load a slow panel start routed every failure through the
drain, which crashed with ``TypeError: can't concat NoneType to bytes``
(non-blocking read through the text-mode wrapper) and replaced the real
diagnostic with a codec traceback.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from tests.helpers.subprocess_diag import drain_stderr_nonblocking

pytestmark = pytest.mark.integration


def _kill_proc(proc: subprocess.Popen[str]) -> None:
    """Force-kill if still running (emergency teardown)."""
    if proc.poll() is None:
        proc.kill()
        proc.wait()


def test_drain_stderr_nonblocking_returns_empty_on_quiet_live_process() -> None:
    """The drain must never raise on a live process whose stderr has nothing buffered."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert drain_stderr_nonblocking(proc, wait=0.0) == ""
    finally:
        _kill_proc(proc)


def test_drain_stderr_nonblocking_returns_buffered_content() -> None:
    """Whatever the child already wrote to stderr must come back as text."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, time; print('boom-diagnostic', file=sys.stderr, flush=True); time.sleep(30)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert "boom-diagnostic" in drain_stderr_nonblocking(proc, wait=0.5)
    finally:
        _kill_proc(proc)
