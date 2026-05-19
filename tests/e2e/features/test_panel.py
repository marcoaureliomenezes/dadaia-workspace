"""E2E acceptance tests — Dadaia Workspace Panel (T-5.1 .. T-5.5).

All tests:
  - Spawn ``dadaia panel --no-open --port <ephemeral>`` as a subprocess.
  - Wait for the verbatim ready-line on stdout (no time.sleep()).
  - Run HTTP assertions via urllib (no browser required for the E2E layer).
  - Tear down via SIGINT in a try/finally block (no orphan processes).

Coverage map:
  T-5.1  → AC-1, AC-2 (sections render; JSON APIs respond)
  T-5.2  → AC-3 (loopback-only bind)
  T-5.3  → AC-10, NFR-2 (byte-identical memory serving end-to-end)
  T-5.4  → AC-6 (dashboard deprecation warning on stderr)
  T-5.5  → AC-9, NFR-4 (clean shutdown within 2 s; port freed)
"""

from __future__ import annotations

import json
import select
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]  # repos/dadaia-workspace/
# The dadaia workspace root is the parent that contains the real .dadaia/states/ directory.
# _REPO_ROOT has a .dadaia/ dir too, but only with agentic/reports/scripts — no states/.
# Walking: repos/dadaia-workspace/ → repos/ → dadaia/  (which has .dadaia/states/)
_DADAIA_WORKSPACE_ROOT = _REPO_ROOT.parents[1]  # /home/marco/workspace/dadaia/
# The real memory file is served from repos/<slug>/specs/memory/ relative to the workspace.
_REAL_MEMORY_HTML = (
    _DADAIA_WORKSPACE_ROOT / "repos" / "dadaia-workspace" / "specs" / "memory" / "architecture.html"
)


def _find_free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _spawn_panel(
    port: int,
    extra: list[str] | None = None,
    cwd: Path | None = None,
) -> subprocess.Popen[str]:
    """Spawn ``dadaia panel --no-open --port <port>`` and return the Popen object."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dadaia_workspace",
            "panel",
            "--no-open",
            "--port",
            str(port),
            *(extra or []),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd or _REPO_ROOT),
    )


def _wait_for_ready(proc: subprocess.Popen[str], port: int, timeout: float = 10.0) -> None:
    """Block until the 'Panel running at' line appears on stdout or timeout."""
    expected = f"Panel running at http://127.0.0.1:{port}/"
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        rlist, _, _ = select.select([proc.stdout], [], [], 0.2)
        if rlist:
            line = proc.stdout.readline()
            if expected in line:
                return
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(
                f"Panel process exited early (rc={proc.returncode}). stderr:\n{stderr}"
            )
    stderr = proc.stderr.read() if proc.stderr else ""
    raise TimeoutError(f"Panel did not print ready-line within {timeout}s. stderr:\n{stderr}")


def _kill_proc(proc: subprocess.Popen[str]) -> None:
    """Force-kill if still running (emergency teardown)."""
    if proc.poll() is None:
        proc.kill()
        proc.wait()


def _init_workspace(path: Path) -> Path:
    """Bootstrap a minimal .dadaia/ workspace in *path*."""
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


# ---------------------------------------------------------------------------
# T-5.1 — test_panel_renders_all_sections  (AC-1, AC-2)
# ---------------------------------------------------------------------------


def test_panel_renders_all_sections(tmp_path: Path) -> None:
    """Panel serves HTML with 3 section markers and valid JSON on /api endpoints.

    Acceptance: AC-1 (specs doctor gate satisfied by green test run),
    AC-2 (3 sections render in the index page).
    """
    _init_workspace(tmp_path)
    port = _find_free_port()
    proc = _spawn_panel(port, cwd=tmp_path)

    try:
        _wait_for_ready(proc, port)

        # --- index page ---
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8", errors="replace")

        # The 3 section identifiers that must appear in the rendered HTML.
        # The index view renders sections for Servers, Memories, and Agents.
        # The exact text tokens are drawn from the frontend mockup / T-3.1 acceptance.
        assert "Servers" in body, "Index page missing 'Servers' section"
        assert any(marker in body for marker in ("Memórias", "Memories", "memories", "memory")), (
            "Index page missing Memories section marker"
        )
        assert any(marker in body for marker in ("Agents", "Agentes", "Em breve", "Release-2")), (
            "Index page missing Agents/Workflows section marker"
        )

        # --- /api/servers ---
        # Response shape: {"groups": [...]}  (see views/api.py contract docstring)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/servers", timeout=5) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, f"Unexpected content-type for /api/servers: {ct}"
            servers_data = json.loads(resp.read())
            assert isinstance(servers_data, dict), "/api/servers must return a JSON object"
            assert "groups" in servers_data, "/api/servers response missing 'groups' key"
            assert isinstance(servers_data["groups"], list), "'groups' must be a list"

        # --- /api/contexts ---
        # Response shape: {"contexts": [...]}  (see views/api.py contract docstring)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/contexts", timeout=5) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, f"Unexpected content-type for /api/contexts: {ct}"
            contexts_data = json.loads(resp.read())
            assert isinstance(contexts_data, dict), "/api/contexts must return a JSON object"
            assert "contexts" in contexts_data, "/api/contexts response missing 'contexts' key"
            assert isinstance(contexts_data["contexts"], list), "'contexts' must be a list"

        # --- SIGINT teardown ---
        proc.send_signal(signal.SIGINT)
        rc = proc.wait(timeout=5)
        assert rc == 0, f"Expected exit 0 after SIGINT, got {rc}"
    finally:
        _kill_proc(proc)


# ---------------------------------------------------------------------------
# T-5.2 — test_panel_bind_loopback_only  (AC-3)
# ---------------------------------------------------------------------------


def test_panel_bind_loopback_only(tmp_path: Path) -> None:
    """Panel binds only to 127.0.0.1; a non-loopback connection must be refused.

    Acceptance: AC-3 (nc -z 127.0.0.1 <port> succeeds; nc -z <LAN-ip> <port> fails).
    """
    _init_workspace(tmp_path)
    port = _find_free_port()
    proc = _spawn_panel(port, cwd=tmp_path)

    try:
        _wait_for_ready(proc, port)

        # Loopback connection MUST succeed.
        try:
            conn = socket.create_connection(("127.0.0.1", port), timeout=2)
            conn.close()
        except OSError as exc:
            pytest.fail(f"Loopback connection to 127.0.0.1:{port} failed: {exc}")

        # Non-loopback connection MUST fail (ConnectionRefusedError or similar).
        # Detect non-loopback IPv4 addresses on this host.
        try:
            _, _, addrs = socket.gethostbyname_ex(socket.gethostname())
        except OSError:
            addrs = []

        non_loopback = [a for a in addrs if not a.startswith("127.")]

        if not non_loopback:
            pytest.skip("No non-loopback IPv4 address available — skipping LAN-side check")

        for lan_ip in non_loopback:
            try:
                conn = socket.create_connection((lan_ip, port), timeout=1)
                conn.close()
                pytest.fail(
                    f"Panel accepted a non-loopback connection from {lan_ip}:{port} — "
                    "FR-7 loopback-only bind is broken"
                )
            except OSError:
                # Expected: connection refused or network unreachable.
                pass

        proc.send_signal(signal.SIGINT)
        rc = proc.wait(timeout=5)
        assert rc == 0, f"Expected exit 0 after SIGINT, got {rc}"
    finally:
        _kill_proc(proc)


# ---------------------------------------------------------------------------
# T-5.3 — test_memory_view_iframe_loads  (AC-10, NFR-2)
# ---------------------------------------------------------------------------


def test_memory_view_iframe_loads() -> None:
    """Memory wrapper contains the correct iframe; /memory/ route serves bytes identical to disk.

    Acceptance: AC-10 (raw bytes unchanged), NFR-2 (memory atomicity preserved end-to-end).

    This test uses the REAL workspace root (cwd=_WORKSPACE_ROOT) so that the panel can
    resolve repos/dadaia-workspace/specs/memory/architecture.html from disk.
    The active context slug is 'dadaia-workspace' (primary_context.json).
    """
    if not _REAL_MEMORY_HTML.exists():
        pytest.skip(
            f"Memory fixture not found at {_REAL_MEMORY_HTML} — skipping byte-identity canary"
        )

    slug = "dadaia-workspace"
    port = _find_free_port()
    # Spawn from the dadaia workspace root (which has .dadaia/states/) so the panel
    # can resolve the workspace and serve memory files from repos/dadaia-workspace/.
    proc = _spawn_panel(port, cwd=_DADAIA_WORKSPACE_ROOT)

    try:
        _wait_for_ready(proc, port)

        # --- /memory-view/<slug>/architecture.html → wrapper with iframe ---
        wrapper_url = f"http://127.0.0.1:{port}/memory-view/{slug}/architecture.html"
        with urllib.request.urlopen(wrapper_url, timeout=5) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "text/html" in ct, f"Unexpected content-type for memory-view: {ct}"
            wrapper_body = resp.read().decode("utf-8", errors="replace")

        expected_iframe_src = f'src="/memory/{slug}/architecture.html"'
        assert expected_iframe_src in wrapper_body, (
            f"Wrapper page missing expected iframe src.\n"
            f"Expected to find: {expected_iframe_src!r}\n"
            f"In: {wrapper_body[:400]!r}"
        )

        # --- /memory/<slug>/architecture.html → byte-identical to disk (NFR-2 / AC-10) ---
        memory_url = f"http://127.0.0.1:{port}/memory/{slug}/architecture.html"
        with urllib.request.urlopen(memory_url, timeout=5) as resp:
            assert resp.status == 200
            served_bytes = resp.read()

        disk_bytes = _REAL_MEMORY_HTML.read_bytes()

        assert served_bytes == disk_bytes, (
            f"NFR-2 VIOLATED: served bytes differ from disk bytes for "
            f"repos/{slug}/specs/memory/architecture.html. "
            f"Served {len(served_bytes)} bytes, disk has {len(disk_bytes)} bytes. "
            "The panel must serve memory HTML verbatim (SPEC-DOC-008)."
        )

        proc.send_signal(signal.SIGINT)
        rc = proc.wait(timeout=5)
        assert rc == 0, f"Expected exit 0 after SIGINT, got {rc}"
    finally:
        _kill_proc(proc)


# ---------------------------------------------------------------------------
# T-5.4 — test_dashboard_deprecation_warning_visible  (AC-6)
# ---------------------------------------------------------------------------


def test_dashboard_deprecation_warning_visible(tmp_path: Path) -> None:
    """'dadaia server dashboard' emits the verbatim deprecation line to stderr.

    Acceptance: AC-6 (FR-6 deprecation warning visible to shell users).
    """
    _init_workspace(tmp_path)
    port = _find_free_port()

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dadaia_workspace",
            "server",
            "dashboard",
            "--no-open",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(tmp_path),
    )

    expected_deprecation = (
        "[deprecation] 'dadaia server dashboard' will be removed in a future release."
        " Use 'dadaia panel' instead."
    )

    try:
        # Wait up to 10s for the deprecation line to appear on stderr.
        deadline = time.monotonic() + 10.0
        found = False
        assert proc.stderr is not None
        while time.monotonic() < deadline:
            rlist, _, _ = select.select([proc.stderr], [], [], 0.2)
            if rlist:
                line = proc.stderr.readline()
                if expected_deprecation in line:
                    found = True
                    break
            if proc.poll() is not None:
                break

        if not found:
            # Read remaining stderr for diagnostics.
            remaining = proc.stderr.read() if proc.stderr else ""
            pytest.fail(
                f"Deprecation line not found in stderr within 10s.\n"
                f"Expected: {expected_deprecation!r}\n"
                f"Remaining stderr: {remaining!r}"
            )

        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    finally:
        _kill_proc(proc)


# ---------------------------------------------------------------------------
# T-5.5 — test_panel_clean_shutdown_within_2s  (AC-9, NFR-4)
# ---------------------------------------------------------------------------


def test_panel_clean_shutdown_within_2s(tmp_path: Path) -> None:
    """Panel exits 0 within 2 s of SIGINT and immediately frees the port.

    Acceptance: AC-9 (Ctrl+C exits 0 within 2s), NFR-4 (foreground + clean shutdown).
    """
    _init_workspace(tmp_path)
    port = _find_free_port()
    proc = _spawn_panel(port, cwd=tmp_path)

    try:
        _wait_for_ready(proc, port)

        t0 = time.monotonic()
        proc.send_signal(signal.SIGINT)
        rc = proc.wait(timeout=2)
        elapsed = time.monotonic() - t0

        assert rc == 0, f"Panel did not exit 0 on SIGINT (got {rc})"
        assert elapsed < 2.5, (
            f"Panel shutdown took {elapsed:.2f}s — exceeds 2s NFR-4 budget (+0.5s slack)"
        )
    finally:
        _kill_proc(proc)

    # Port must be free immediately after shutdown.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError as exc:
            pytest.fail(
                f"Port {port} still bound after panel shutdown: {exc}. "
                "NFR-4 requires port to be freed within 2s."
            )
