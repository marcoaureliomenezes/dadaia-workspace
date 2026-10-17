"""One interpreter rule for every hook: the workspace's own self-locating wrapper (Kimi's
user-level shim: the nearest `.dadaia/states/spec_contexts.json` sentinel), and one
missing-venv posture — a loud stderr warning and exit 0, told to the agent by
every ctx-inject firing.
Size: MEDIUM — executes the rendered hook commands as the harness would.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.infrastructure.runtime_config import claude_hooks, kimi_hooks_block
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    envelope,
    hook_wrapper_contents,
    wrapper_name,
)
from tests.fixtures.harness_env import fire_kimi, git_bash, suite_env
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import detect, make_executable, run, write_text

#: A directory name the shell must not take apart. Windows has no double quote in a name, and Git
#: Bash's argv parser drops a `'` from a space-free argument, so there a space stands in.
_ODD = "w s" if detect().windows else 'w"s'
_SH = git_bash() if detect().windows else "sh"
_WRITE = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.md"}})


def _workspace(root: Path, *, venv: bool) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    write_text(
        root / ".dadaia" / "states" / "spec_contexts.json",
        '{"schema_version": "2", "contexts": []}',
    )
    hooks = root / ".dadaia" / "hooks"
    hooks.mkdir()
    for name in ("claude", "codex", "cursor", "devin", "copilot"):
        for wrapper, body in hook_wrapper_contents(HARNESS_RECORDS[name]).items():
            write_text(hooks / wrapper, body)
            make_executable(hooks / wrapper)
    if venv:
        fake_venv(root)
    return root


def _seen(path: Path) -> str:
    """*path* as the wrapper's shell names it (`pwd`): Git Bash spells `C:\\x` as `/c/x`."""
    return run([_SH, "-c", 'cd "$1" && pwd', "sh", str(path)]).stdout.strip()


def _claude_pre_gate() -> str:
    return str(claude_hooks()["hooks"]["PreToolUse"][0]["hooks"][0]["command"])  # type: ignore[index]


def _run(argv: list[str], cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return run(argv, input=_WRITE, cwd=cwd, env=suite_env(os.environ, Path.home(), overrides=env), timeout=60)  # fmt: skip


@pytest.mark.parametrize(
    ("harness", "output"),  # output: the ctx-inject lane's DADAIA_HOOK_OUTPUT ("": plain)
    [("claude", ""), ("codex", "codex-json"), ("cursor", "cursor-json"), ("devin", ""),
     ("copilot", "copilot-json")],
)  # fmt: skip
def test_missing_venv_is_loud_and_fails_open_on_every_harness(
    tmp_path: Path, harness: str, output: str
) -> None:
    """No `.dadaia/.venv` —
    every lane exits 0 (never 127) naming the missing venv on stderr; and each
    ctx-inject firing tells the agent, in that lane's envelope, with no file written."""
    ws = _workspace(tmp_path / _ODD, venv=False)
    before = sorted((ws / ".dadaia").rglob("*"))
    hooks, record = ws / ".dadaia" / "hooks", HARNESS_RECORDS[harness]
    lanes = [wrapper_name(record, lane) for lane in ("pre-gate", "ctx-inject", "ctx-inject")]
    done = [_run([_SH, str(hooks / lane)], ws) for lane in lanes]
    assert all(d.returncode == 0 and ".dadaia/.venv" in d.stderr for d in done), done
    told = (
        f"dadaia: no workspace venv at {_seen(ws)}/.dadaia/.venv — the gate is off.\n"
        "fix: Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument\n"
    )
    assert [d.stdout for d in done[1:]] == [envelope({"DADAIA_HOOK_OUTPUT": output}, told)] * 2
    assert sorted((ws / ".dadaia").rglob("*")) == before


def _kimi_seen(path: Path) -> str:
    """*path* as Kimi's host shell names it: `pwd` under sh, the path itself under cmd."""
    return str(path) if detect().windows else _seen(path)


_KIMI_VENV = str(Path(".dadaia") / ".venv")  # in the host's own separator
#: The dash the host's shell tells with: batch folds the em dash to ASCII.
_DASH = "-" if detect().windows else "\u2014"


def test_kimi_missing_venv_is_loud_and_fails_open(tmp_path: Path) -> None:
    """The registered command, run by the host's shell as Kimi runs it: every lane exits 0 naming
    the missing venv on stderr, and each ctx-inject firing tells the agent, writing no file."""
    ws = _workspace(tmp_path / _ODD, venv=False)
    before = sorted((ws / ".dadaia").rglob("*"))
    done = [fire_kimi(tmp_path / "k", lane, ws, _WRITE) for lane in ("pre-gate", "ctx-inject", "post-compact")]  # fmt: skip
    assert all(d.returncode == 0 and _KIMI_VENV in d.stderr for d in done), done
    assert done[0].stdout == ""
    for told in done[1:]:
        first, fix = told.stdout.splitlines()  # cmd's echo ends a line in CRLF
        assert first == f"dadaia: no workspace venv at {_kimi_seen(ws)}{os.sep}{_KIMI_VENV} {_DASH} the gate is off."  # fmt: skip
        assert fix == (
            "fix: Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
        )
    assert sorted((ws / ".dadaia").rglob("*")) == before


def test_kimi_command_judges_the_nearest_sentinel_workspace(tmp_path: Path) -> None:
    """Fired inside a venv-less inner workspace nested in an outer one, the command warns about
    INNER and exits 0 - it never runs the outer workspace's interpreter."""
    outer = _workspace(tmp_path / "ws-outer", venv=True)
    (outer / "sandbox").mkdir()
    inner = _workspace(outer / "sandbox" / "inner", venv=False)
    done = fire_kimi(tmp_path / "k", "pre-gate", inner, _WRITE)
    assert done.returncode == 0
    assert f"{_kimi_seen(inner)}{os.sep}{_KIMI_VENV}" in done.stderr
    assert f"{_kimi_seen(outer)}{os.sep}{_KIMI_VENV}" not in done.stderr


@pytest.mark.parametrize("blank", [False, True], ids=["plain-home", "home-with-a-blank"])
@pytest.mark.parametrize("below", [".", "sub/deeper"], ids=["at-the-root", "from-a-subdirectory"])
def test_kimi_command_gates_through_the_hosts_own_shell(tmp_path: Path, blank: bool, below: str) -> None:  # fmt: skip
    """The nearest sentinel is found from any cwd below it; a new root entry is denied with exit 2
    and the reason on stderr, a write in the ephemeral zone is allowed in silence."""
    ws = _workspace(tmp_path / "ws", venv=True)
    cwd = ws / below
    cwd.mkdir(parents=True, exist_ok=True)
    home = tmp_path / ("Jo Doe" if blank else "jo") / ".kimi-code"

    def fire(target: Path) -> subprocess.CompletedProcess[str]:
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target)}, "cwd": str(cwd)})  # fmt: skip
        return fire_kimi(home, "pre-gate", cwd, payload)

    denied, allowed = fire(ws / "stray.md"), fire(ws / ".dadaia" / "tmp" / "x.md")
    assert (denied.returncode, "stray.md" in denied.stderr) == (2, True), denied
    assert (allowed.returncode, allowed.stderr) == (0, ""), allowed


def test_kimi_command_runs_the_four_other_lanes(tmp_path: Path) -> None:
    """post-gate is silent on a plain write; ctx-inject and post-compact tell an unbound session;
    the reaper reports what it repaired in the bare workspace."""
    ws = _workspace(tmp_path / "ws", venv=False)
    fake_venv(ws, pth=True)
    done = {lane: fire_kimi(tmp_path / "k", lane, ws, _WRITE) for lane in ("post-gate", "ctx-inject", "post-compact", "doctor-expired")}  # fmt: skip
    assert {lane: d.returncode for lane, d in done.items()} == dict.fromkeys(done, 0), done
    assert done["post-gate"].stdout == ""
    assert done["doctor-expired"].stdout.startswith("WS-root-missing: created '.dadaiaignore'")
    assert all(done[lane].stdout.startswith("[no bound context]") for lane in ("ctx-inject", "post-compact"))  # fmt: skip


@pytest.mark.skipif(
    not detect().windows, reason="platform partition: delayed expansion is cmd.exe's"
)
def test_kimi_cmd_command_keeps_a_bang_in_the_workspace_path(tmp_path: Path) -> None:
    """A host with delayed expansion on (`/v:on`, as a registry setting makes it) must not eat the `!`."""
    ws = _workspace(tmp_path / "w!s", venv=False)
    done = fire_kimi(tmp_path / "k", "pre-gate", ws, _WRITE, cmd_switches="/v:on")
    assert done.returncode == 0 and "w!s" in done.stderr, done


def test_the_claude_hook_survives_a_moved_workspace(tmp_path: Path) -> None:
    """The registered command
    resolves through $CLAUDE_PROJECT_DIR, so a workspace moved after install still gates:
    a new root entry is refused."""
    _workspace(tmp_path / "before", venv=True)
    moved = tmp_path / "after"
    shutil.move(str(tmp_path / "before"), moved)
    payload_dir = moved / "stray.md"
    # the trailing space makes Windows quote the argument whole; unquoted, Git Bash loses an inner `"`
    done = run([_SH, "-c", _claude_pre_gate() + " "], input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(payload_dir)},
                          "cwd": str(moved)}), cwd=moved, timeout=60, env=suite_env(
            os.environ, Path.home(), overrides={"CLAUDE_PROJECT_DIR": str(moved)}
        ))  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


_WIN = Capabilities.detect("win32")
#: Kimi runs a hook `command` as `cmd /d /s /c "<command>"` on Windows (Node `spawn` with a shell).
_CMD_PRE_GATE = "\r\n".join([
    "@echo off",
    "setlocal EnableExtensions DisableDelayedExpansion",
    'set "ROOT=%CD%"',
    ":up",
    'if exist "%ROOT%\\.dadaia\\states\\spec_contexts.json" goto found',
    'for %%I in ("%ROOT%\\..") do set "UP=%%~fI"',
    'if "%UP%"=="%ROOT%" exit /b 0',
    'set "ROOT=%UP%"',
    "goto up",
    ":found",
    'set "PYTHON_BIN=%ROOT%\\.dadaia\\.venv\\Scripts\\python.exe"',
    'if exist "%PYTHON_BIN%" goto run',
    "echo dadaia hook: no workspace venv at %ROOT%\\.dadaia\\.venv - hook skipped>&2",
    "exit /b 0",
    ":run",
    'set "DADAIA_RUNTIME=kimi-code"',
    '"%PYTHON_BIN%" -B -m dadaia_workspace.hooks.pre_gate %* | "%PYTHON_BIN%" -B -m dadaia_workspace.hooks.translate 2',
    "exit /b %ERRORLEVEL%",
    "",
])  # fmt: skip


def test_kimi_on_windows_gets_a_cmd_wrapper_whose_literal_is_pinned() -> None:
    """Platform partition, not a skip: this row builds the Windows wrapper with faked win32 caps on
    every host; the real `cmd.exe` execution is the next row, Windows-only."""
    record = HARNESS_RECORDS["kimi-code"]
    wrappers = hook_wrapper_contents(record, _WIN)
    assert sorted(wrappers) == [f"dadaia-kimi-{lane}.cmd" for lane in
        ("ctx-inject", "doctor-expired", "post-compact", "post-gate", "pre-gate")]  # fmt: skip
    assert wrappers["dadaia-kimi-pre-gate.cmd"] == _CMD_PRE_GATE
    assert wrappers["dadaia-kimi-post-gate.cmd"].endswith(
        '"%PYTHON_BIN%" -B -m dadaia_workspace.hooks.sdd_post_gate %*\r\nexit /b %ERRORLEVEL%\r\n'
    )
    assert wrappers["dadaia-kimi-doctor-expired.cmd"].endswith(
        "-m dadaia_workspace doctor --fix --expired-only --quiet\r\nexit /b %ERRORLEVEL%\r\n"
    )
    told = wrappers["dadaia-kimi-ctx-inject.cmd"]
    assert "echo dadaia: no workspace venv at %ROOT%\\.dadaia\\.venv - the gate is off.\r\n" in told


@pytest.mark.parametrize(
    ("home", "command"),
    [
        ("C:/kimi", "C:/kimi/hooks/dadaia-kimi-pre-gate.cmd"),
        (r"D:\Kimi Home\.kimi-code", '"D:/Kimi Home/.kimi-code/hooks/dadaia-kimi-pre-gate.cmd"'),
    ],
)  # fmt: skip
def test_kimi_windows_command_is_what_cmd_runs_whole(
    home: str, command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`cmd /d /s /c` strips one outer quote pair, so a home with a blank is a quoted head."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", _WIN)
    hooks = tomllib.loads(kimi_hooks_block(Path(home)))["hooks"]
    assert hooks[0]["command"] == command
