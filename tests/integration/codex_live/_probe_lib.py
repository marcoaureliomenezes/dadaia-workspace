"""Reusable live-Codex contract probe primitives (WS-CDX-VERIFY, T-013-08).

This module ports the coordinator's pty-driven interactive probes into a
reusable, import-safe form. It carries NO import-time dependency on the throwaway
``.dadaia/tmp`` pylibs dir: ``pyte`` is optional and only used for human-readable
screen-rendering debug output. The load-bearing assertions (marker files exist,
file hash unchanged/changed) read the real filesystem and never need pyte.

Safety invariants (see FACTS.md):
  * ``~/.codex`` is NEVER modified. An isolated ``CODEX_HOME`` is built under a
    caller-supplied tmp dir; only ``auth.json`` is copied in (chmod 600).
  * All fixtures are git-init'd throwaway workspaces under the tmp dir — never
    inside the repo tree.

These primitives DRIVE the real ``codex`` binary and spend operator model
credits. The pytest wrapper gates every call behind an explicit opt-in
(``DADAIA_CODEX_LIVE=1``) plus binary/auth presence — see
``test_codex_live_contract.py``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import select
import shutil
import signal
import struct
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

# Terminal geometry the codex TUI is driven at (matches the coordinator probes).
_PTY_ROWS = 24
_PTY_COLS = 80

# Marker event names wired into the events fixture.
MARKER_EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse")

# The documented anchored PreToolUse matcher form (FACTS.md P1). T-014-12 added Bash so
# the merged pre_gate entrypoint also runs the W3 venv guard on shell invocations.
PRETOOLUSE_MATCHER = r"^(apply_patch|Edit|Write|Bash)$"


def codex_binary() -> str | None:
    """Return the resolved ``codex`` binary path, or None when absent.

    Honors the ``CODEX_BIN`` override used by the shell harness.
    """
    override = os.environ.get("CODEX_BIN")
    if override:
        return override if shutil.which(override) else None
    return shutil.which("codex")


def codex_auth_path() -> Path:
    """Path to the user's real codex auth file (read-only source for the copy)."""
    return Path.home() / ".codex" / "auth.json"


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class CodexSandbox:
    """An isolated CODEX_HOME + fixture root under a caller-supplied tmp dir.

    Never touches ``~/.codex``; copies only ``auth.json`` (chmod 600).
    """

    root: Path
    codex_home: Path = field(init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.codex_home = self.root / "codex_home"
        self.codex_home.mkdir(parents=True, exist_ok=True)
        auth = codex_auth_path()
        # The pytest wrapper asserts presence before constructing a sandbox; guard
        # anyway so a misuse fails loudly rather than driving codex unauthenticated.
        if not auth.is_file():
            raise FileNotFoundError(f"codex auth.json absent at {auth}")
        dest = self.codex_home / "auth.json"
        shutil.copyfile(auth, dest)
        os.chmod(dest, 0o600)

    def write_config(self, body: str) -> None:
        """Overwrite the isolated ``config.toml``."""
        (self.codex_home / "config.toml").write_text(body, encoding="utf-8")

    def env(self) -> dict[str, str]:
        """Process env with the isolated CODEX_HOME pinned."""
        return {**os.environ, "CODEX_HOME": str(self.codex_home), "TERM": "xterm-256color"}

    def git_init(self, fixture: Path) -> None:
        """git-init a throwaway fixture with a throwaway identity."""
        fixture.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q"], cwd=fixture, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=fixture, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=fixture, check=True)


def build_events_fixture(sandbox: CodexSandbox) -> Path:
    """Create the marker-event fixture: a trusted git workspace whose
    ``.codex/hooks.json`` appends to a per-event marker log on each event.

    Returns the fixture path. The marker dir is regenerated empty each call.
    """
    fixture = sandbox.root / "fixture_events"
    if fixture.exists():
        shutil.rmtree(fixture)
    sandbox.git_init(fixture)
    markers = fixture / "markers"
    markers.mkdir(parents=True, exist_ok=True)
    hooks_dir = fixture / ".codex"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    def cmd(event: str) -> str:
        log = markers / f"{event}.log"
        return f"date >> '{log}'"

    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [{"type": "command", "command": cmd("SessionStart")}],
                }
            ],
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": cmd("UserPromptSubmit")}]}
            ],
            "PreToolUse": [
                {
                    "matcher": PRETOOLUSE_MATCHER,
                    "hooks": [{"type": "command", "command": cmd("PreToolUse")}],
                }
            ],
            "PostToolUse": [{"hooks": [{"type": "command", "command": cmd("PostToolUse")}]}],
        }
    }
    (hooks_dir / "hooks.json").write_text(json.dumps(hooks, indent=2), encoding="utf-8")
    sandbox.write_config(f'[projects."{fixture}"]\ntrust_level = "trusted"\n')
    return fixture


def build_frozen_fixture(sandbox: CodexSandbox) -> tuple[Path, Path]:
    """Create the FROZEN-write fixture: a trusted git workspace with a committed
    ``specs/_archive/some.md`` and a gate-shaped PreToolUse hook that emits the
    legacy ``{"decision":"block"}`` envelope when the apply_patch payload touches
    ``specs/_archive``.

    Returns ``(fixture_path, frozen_target_path)``.
    """
    fixture = sandbox.root / "fixture_frozen"
    if fixture.exists():
        shutil.rmtree(fixture)
    archive = fixture / "specs" / "_archive"
    archive.mkdir(parents=True, exist_ok=True)
    hooks_dir = fixture / ".codex" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    sandbox.git_init(fixture)

    target = archive / "some.md"
    target.write_text("ORIGINAL FROZEN CONTENT\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fixture, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=fixture, check=True)

    gate = hooks_dir / "frozen_gate.py"
    gate.write_text(
        "import json, sys\n"
        "raw = sys.stdin.read()\n"
        'if "specs/_archive" in raw:\n'
        '    print(json.dumps({"decision": "block", '
        '"reason": "FROZEN: specs/_archive is read-only"}))\n'
        "    sys.exit(0)\n",
        encoding="utf-8",
    )
    hooks_json = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": PRETOOLUSE_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"/usr/bin/python3 '{gate}'",
                        }
                    ],
                }
            ]
        }
    }
    (fixture / ".codex" / "hooks.json").write_text(json.dumps(hooks_json), encoding="utf-8")
    sandbox.write_config(f'[projects."{fixture}"]\ntrust_level = "trusted"\n')
    return fixture, target


def _answer_terminal_queries(fd: int, chunk: bytes) -> None:
    """Reply to the terminal capability queries the codex TUI blocks on."""
    if b"\x1b[6n" in chunk:
        os.write(fd, b"\x1b[24;80R")  # cursor position report
    if b"\x1b[c" in chunk or b"\x1b[0c" in chunk:
        os.write(fd, b"\x1b[?62;22c")  # device attributes
    if b"\x1b]10;?" in chunk:
        os.write(fd, b"\x1b]10;rgb:ffff/ffff/ffff\x1b\\")
    if b"\x1b]11;?" in chunk:
        os.write(fd, b"\x1b]11;rgb:0000/0000/0000\x1b\\")


@dataclass
class PtySession:
    """A pty-driven interactive ``codex`` TUI session.

    The constructor forks codex under a pty sized 80x24 with terminal-query
    auto-responses. Callers drive it with ``drain`` / ``send`` and MUST call
    ``close`` (use as a context manager).
    """

    fixture: Path
    env: dict[str, str]
    binary: str
    pid: int = field(init=False, default=-1)
    fd: int = field(init=False, default=-1)
    _out: bytes = field(init=False, default=b"")

    def __post_init__(self) -> None:
        import pty  # POSIX-only; this harness is Linux/macOS live-test only.

        pid, fd = pty.fork()
        if pid == 0:  # child
            os.chdir(self.fixture)
            os.execvpe(
                self.binary,
                [
                    self.binary,
                    "--dangerously-bypass-hook-trust",
                    "--dangerously-bypass-approvals-and-sandbox",
                ],
                self.env,
            )
        # parent
        import fcntl
        import termios

        self.pid = pid
        self.fd = fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", _PTY_ROWS, _PTY_COLS, 0, 0))

    def drain(self, seconds: float) -> bytes:
        """Read pty output for ``seconds``, auto-answering terminal queries."""
        end = time.time() + seconds
        out = b""
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(self.fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
                _answer_terminal_queries(self.fd, chunk)
        self._out += out
        return out

    def send(self, text: str) -> None:
        """Write raw bytes (no implicit newline) to the pty."""
        os.write(self.fd, text.encode())

    def submit(self, text: str) -> None:
        """Type ``text`` then press Enter (with a short settle drain between)."""
        self.send(text)
        self.drain(3)
        self.send("\r")

    @property
    def output(self) -> bytes:
        """All pty output captured so far."""
        return self._out

    def render(self) -> list[str]:
        """Render captured output to screen lines via pyte (debug only).

        pyte is optional: when unavailable, returns a single sentinel line rather
        than raising. No assertion depends on this output.
        """
        try:
            import pyte
        except ImportError:
            return ["<pyte unavailable: screen rendering skipped>"]
        screen = pyte.Screen(_PTY_COLS, _PTY_ROWS)
        stream = pyte.ByteStream(screen)
        stream.feed(self._out)
        return [line.rstrip() for line in screen.display if line.strip()]

    def close(self) -> None:
        """Terminate the codex process (SIGTERM then SIGKILL)."""
        if self.pid <= 0:
            return
        try:
            os.kill(self.pid, signal.SIGTERM)
            time.sleep(1)
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        with contextlib.suppress(ChildProcessError, OSError):
            os.waitpid(self.pid, 0)
        if self.fd > 0:
            with contextlib.suppress(OSError):
                os.close(self.fd)
        self.pid = -1
        self.fd = -1

    def __enter__(self) -> PtySession:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def run_headless_exec(
    sandbox: CodexSandbox, fixture: Path, prompt: str, timeout: float = 150.0
) -> subprocess.CompletedProcess[str]:
    """Run a non-interactive ``codex exec`` turn against a fixture.

    Used by the headless hooks-don't-fire probe (FACTS.md: headless hooks never
    fire). Returns the completed process for diagnostic capture.
    """
    binary = codex_binary()
    assert binary is not None  # caller gates on presence
    return subprocess.run(
        [
            binary,
            "exec",
            "--dangerously-bypass-hook-trust",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            str(fixture),
            prompt,
        ],
        cwd=fixture,
        env=sandbox.env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def marker_fired(fixture: Path, event: str) -> bool:
    """True iff the per-event marker log exists and is non-empty."""
    log = fixture / "markers" / f"{event}.log"
    return log.is_file() and log.stat().st_size > 0
