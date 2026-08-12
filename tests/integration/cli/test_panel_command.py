"""Integration tests for `dadaia panel` CLI command.

Tests:
  - test_panel_starts_serves_shuts_down_clean: spawn the panel as a subprocess,
    wait for the "Panel running at" line on stdout, fetch /, send SIGINT, assert
    exit 0, assert port is freed.
  - test_panel_bind_validation_rejects_non_loopback: ensure --bind 0.0.0.0
    exits with code 2 and the correct error message on stderr.
"""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


def _free_port() -> int:
    """Return an OS-assigned free TCP port (bind-then-release trick)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create and chdir into a minimal initialized dadaia workspace."""
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _wait_for_line(proc: subprocess.Popen[str], prefix: str, timeout: float = 5.0) -> bool:
    """Read stdout lines until a line starting with *prefix* is found or timeout."""
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        # Use a short readline with non-blocking check via select
        import select

        rlist, _, _ = select.select([proc.stdout], [], [], 0.1)
        if rlist:
            line = proc.stdout.readline()
            if line.startswith(prefix):
                return True
        if proc.poll() is not None:
            break
    return False


@pytest.mark.slow(reason="spawns the panel CLI subprocess and waits for HTTP readiness")
def test_panel_starts_serves_shuts_down_clean(workspace: Path) -> None:
    """Panel subprocess boots, serves /, shuts down on SIGINT, frees the port."""
    port = _free_port()

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dadaia_workspace",
            "panel",
            "--no-open",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(workspace),
    )

    try:
        # 30 s bound (bug panel-command-readiness-flaky-under-xdist-load): 10 s missed
        # under full-suite xdist load — the exact mode the pre-push preflight runs.
        # Returns on the ready line, so the green-path cost is unchanged.
        found = _wait_for_line(proc, "Panel running at", timeout=30.0)
        assert found, "Panel did not print 'Panel running at' within 10 s"

        # Fetch the index page and assert HTTP 200
        url = f"http://127.0.0.1:{port}/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read()
            assert len(body) > 0

        # Send SIGINT — should trigger clean shutdown
        proc.send_signal(signal.SIGINT)
        exit_code = proc.wait(timeout=5)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    # Assert port is free after shutdown
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))  # should not raise if port is free


@pytest.mark.slow(reason="spawns the panel CLI subprocess to validate bind handling")
def test_panel_bind_validation_rejects_non_loopback(workspace: Path) -> None:
    """--bind 0.0.0.0 exits with code 2 and prints the loopback error message."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dadaia_workspace",
            "panel",
            "--no-open",
            "--port",
            "4999",
            "--bind",
            "0.0.0.0",
        ],
        capture_output=True,
        text=True,
        cwd=str(workspace),
    )
    assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
    assert "Release-1 supports loopback bind only" in result.stderr, (
        f"Expected loopback error in stderr. Got: {result.stderr!r}"
    )
