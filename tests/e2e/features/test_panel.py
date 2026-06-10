"""E2E acceptance tests — Dadaia Workspace Panel (T-5.1 .. T-5.5).

All tests:
  - Spawn ``dadaia panel --no-open --port <ephemeral>`` as a subprocess.
  - Wait for the verbatim ready-line on stdout (no time.sleep()).
  - Run HTTP assertions via urllib (no browser required for the E2E layer).
  - Tear down via SIGINT in a try/finally block (no orphan processes).

Coverage map:
  T-5.1  → AC-1, AC-2 (sections render; JSON APIs respond)
  T-5.2  → AC-3 (loopback-only bind)
  T-5.3  → AC-10, NFR-2 (memory .md atom rendered + served end-to-end; D-4)
  T-5.4  → AC-6 (dashboard deprecation warning on stderr)
  T-5.5  → AC-9, NFR-4 (clean shutdown within 2 s; port freed)
"""

from __future__ import annotations

import fcntl
import http.client
import json
import os
import queue
import select
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
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


def _find_free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


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
    _wait_for_ready_and_token(proc, port, timeout)


def _drain_stderr_nonblocking(proc: subprocess.Popen[str], wait: float = 0.3) -> str:
    """Best-effort, NON-blocking read of whatever is currently on stderr.

    The panel runs ``serve_forever`` and never closes its pipes, so a plain
    ``proc.stderr.read()`` on a live process blocks forever.  We mark the fd
    non-blocking and read what is buffered so diagnostics never hang the suite.
    """
    if proc.stderr is None:
        return ""
    time.sleep(wait)
    fd = proc.stderr.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    try:
        return proc.stderr.read() or ""
    except (BlockingIOError, OSError):
        return ""


def _wait_for_ready_and_token(proc: subprocess.Popen[str], port: int, timeout: float = 10.0) -> str:
    """Block until the panel is ready and return the Bearer token.

    The panel prints two lines on startup (flushed before ``serve_forever``)::

        Panel running at http://127.0.0.1:<port>/
        First-load URL:  http://127.0.0.1:<port>/?token=<token>

    A reader thread drains stdout line-by-line; mixing ``select`` on the raw fd
    with a buffered ``TextIOWrapper.readline`` is unsound (the second line can be
    sitting in the wrapper's buffer while ``select`` reports the fd as empty,
    which is exactly the hang this replaces).  The token is required because
    there is no loopback auth bypass (sec F-3 / T-010-21): every sensitive API
    call must carry ``Authorization: Bearer <token>``.

    Fails fast with a bounded timeout — never an unbounded poll, and never a
    blocking ``stderr.read()`` on the still-running process.
    """
    expected = f"Panel running at http://127.0.0.1:{port}/"
    token_marker = "/?token="
    assert proc.stdout is not None

    lines: queue.Queue[str | None] = queue.Queue()

    def _reader() -> None:
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                lines.put(raw)
        finally:
            lines.put(None)  # EOF sentinel

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    deadline = time.monotonic() + timeout
    ready = False
    token: str | None = None
    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            line = lines.get(timeout=min(0.2, remaining) or 0.05)
        except queue.Empty:
            if proc.poll() is not None:
                stderr = _drain_stderr_nonblocking(proc)
                raise RuntimeError(
                    f"Panel process exited early (rc={proc.returncode}). stderr:\n{stderr}"
                ) from None
            continue
        if line is None:  # EOF — process closed stdout
            stderr = _drain_stderr_nonblocking(proc)
            raise RuntimeError(
                f"Panel closed stdout before becoming ready (rc={proc.poll()}). stderr:\n{stderr}"
            )
        if expected in line:
            ready = True
        if token_marker in line:
            token = line.split(token_marker, 1)[1].strip()
        if ready and token is not None:
            return token

    stderr = _drain_stderr_nonblocking(proc)
    raise TimeoutError(
        f"Panel did not print ready-line + token within {timeout}s. stderr:\n{stderr}"
    )


def _auth_get(url: str, token: str, timeout: float = 5.0) -> http.client.HTTPResponse:
    """GET *url* with an Authorization: Bearer header. Returns the response."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    resp: http.client.HTTPResponse = urllib.request.urlopen(req, timeout=timeout)
    return resp


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
        token = _wait_for_ready_and_token(proc, port)

        # --- index page (PUBLIC — no token required) ---
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

        # --- /api/panel-status (sensitive — Bearer token required) ---
        # Response shape: {"groups": [...]}  (see views/api.py contract docstring)
        with _auth_get(f"http://127.0.0.1:{port}/api/panel-status", token) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, f"Unexpected content-type for /api/panel-status: {ct}"
            servers_data = json.loads(resp.read())
            assert isinstance(servers_data, dict), "/api/panel-status must return a JSON object"
            assert "groups" in servers_data, "/api/panel-status response missing 'groups' key"
            assert isinstance(servers_data["groups"], list), "'groups' must be a list"

        # --- /api/contexts (sensitive — Bearer token required) ---
        # Response shape: {"contexts": [...]}  (see views/api.py contract docstring)
        with _auth_get(f"http://127.0.0.1:{port}/api/contexts", token) as resp:
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
# T-010-21 R7c — panel loopback auth (sec F-3, AC-R7-03)
# ---------------------------------------------------------------------------


@pytest.mark.slow(reason="spawns the panel CLI subprocess end-to-end")
def test_tokenless_loopback_request_to_sensitive_api_is_401(tmp_path: Path) -> None:
    """AC-R7-03 contract pin: a tokenless 127.0.0.1 request to a sensitive panel
    API returns 401; the same request with the Bearer token returns 200.

    There is no loopback auth bypass — a co-located local process or a malicious
    local web page (DNS-rebinding / CSRF-style) cannot reach workspace state
    without the token.
    """
    _init_workspace(tmp_path)
    port = _find_free_port()
    proc = _spawn_panel(port, cwd=tmp_path)

    try:
        token = _wait_for_ready_and_token(proc, port)

        # Tokenless request to a sensitive API → 401.
        sensitive_url = f"http://127.0.0.1:{port}/api/panel-status"
        try:
            with urllib.request.urlopen(sensitive_url, timeout=5):
                raise AssertionError("Tokenless request to sensitive API must NOT return 2xx")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401, f"Expected 401 for tokenless sensitive API, got {exc.code}"

        # Same request WITH the Bearer token → 200.
        with _auth_get(sensitive_url, token) as resp:
            assert resp.status == 200

        # PUBLIC /health stays reachable without a token.
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            assert resp.status == 200

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


def test_memory_view_iframe_loads(tmp_path: Path) -> None:
    """Memory wrapper contains the correct iframe; /memory/ route renders the .md atom.

    Acceptance: AC-10, NFR-2 — the memory viewer chain works end-to-end for the
    markdown-memory reality (memory-markdown-source-v1, D-4): the ``.md`` source is
    the canonical artefact and the ``/memory/`` route renders it to HTML in-memory.
    The byte-identity SPEC-DOC-008 invariant on committed ``.html`` is retired; the
    behaviour asserted here is "the rendered HTML carries the source's semantics".

    Runs against a tmp workspace fixture (cwd=tmp_path) with a hand-built memory atom
    under ``repos/<slug>/specs/memory/architecture.md`` — never the real workspace
    root (the previous incarnation pointed at ``cwd=_DADAIA_WORKSPACE_ROOT`` and
    guarded on a retired ``architecture.html``, so it was dead-by-skip since the
    markdown migration). Memory routes are Bearer-gated (sec F-3), so every request
    carries the token.
    """
    _init_workspace(tmp_path)

    slug = "memory-fixture"
    atom_dir = tmp_path / "repos" / slug / "specs" / "memory"
    atom_dir.mkdir(parents=True)
    # A real .md atom whose rendered HTML semantics we assert on. The heading and the
    # body sentence are distinct, non-injected strings: if the renderer regresses
    # (stops emitting <h1>, drops body text, or serves raw Markdown), the asserts fail.
    (atom_dir / "architecture.md").write_text(
        "# Architecture Atom\n\nThe container wires every feature dependency.\n",
        encoding="utf-8",
    )

    port = _find_free_port()
    proc = _spawn_panel(port, cwd=tmp_path)

    try:
        token = _wait_for_ready_and_token(proc, port)

        # --- /memory-view/<slug>/architecture.md → wrapper with iframe ---
        wrapper_url = f"http://127.0.0.1:{port}/memory-view/{slug}/architecture.md"
        with _auth_get(wrapper_url, token) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "text/html" in ct, f"Unexpected content-type for memory-view: {ct}"
            wrapper_body = resp.read().decode("utf-8", errors="replace")

        expected_iframe_src = f'src="/memory/{slug}/architecture.md"'
        assert expected_iframe_src in wrapper_body, (
            f"Wrapper page missing expected iframe src.\n"
            f"Expected to find: {expected_iframe_src!r}\n"
            f"In: {wrapper_body[:400]!r}"
        )

        # --- /memory/<slug>/architecture.md → Markdown rendered to HTML (D-4) ---
        memory_url = f"http://127.0.0.1:{port}/memory/{slug}/architecture.md"
        with _auth_get(memory_url, token) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "text/html" in ct, f"Unexpected content-type for memory render: {ct}"
            served = resp.read().decode("utf-8", errors="replace")

        # The renderer must turn the .md heading into an <h1> and preserve the body
        # sentence — i.e. it served rendered HTML, not the raw Markdown source.
        assert "<h1" in served, (
            "Memory render did not emit an <h1> for the '# Architecture Atom' heading — "
            f"the .md atom was not rendered to HTML. Got: {served[:400]!r}"
        )
        assert "Architecture Atom" in served, "Rendered HTML dropped the heading text"
        assert "The container wires every feature dependency." in served, (
            "Rendered HTML dropped the body sentence"
        )
        assert "# Architecture Atom" not in served, (
            "Served body still contains the raw Markdown '# ' heading marker — "
            "the route served source bytes instead of rendered HTML (D-4 violated)."
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
