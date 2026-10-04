"""One interpreter rule for every hook: the workspace's own self-locating wrapper (Kimi's
user-level shim: the nearest `.dadaia/states/spec_contexts.json` sentinel), and one
missing-venv posture — a loud stderr warning and exit 0 (DEC-10 (a)), told to the agent by
every ctx-inject firing (missing-venv-hook-disarms-the-gate-invisibly, AC2.7).
Size: MEDIUM — executes the rendered hook commands as the harness would.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_config import claude_hooks
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    envelope,
    hook_wrapper_contents,
    wrapper_name,
)
from tests.fixtures.harness_env import child_keys

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.name == "nt", reason="hook commands are POSIX sh"),
]

_WRITE = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.md"}})


def _workspace(root: Path, *, venv: bool) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    hooks = root / ".dadaia" / "hooks"
    hooks.mkdir()
    for name in ("claude", "codex", "cursor", "devin", "copilot", "kimi-code"):
        for wrapper, body in hook_wrapper_contents(HARNESS_RECORDS[name]).items():
            (hooks / wrapper).write_text(body, encoding="utf-8")
            (hooks / wrapper).chmod(0o755)
    if venv:
        (root / ".dadaia" / ".venv" / "bin").mkdir(parents=True)
        (root / ".dadaia" / ".venv" / "bin" / "python").symlink_to(sys.executable)
    return root


def _claude_pre_gate() -> str:
    return str(claude_hooks()["hooks"]["PreToolUse"][0]["hooks"][0]["command"])  # type: ignore[index]


def _kimi_shim(where: Path) -> Path:
    shim = where / "dadaia-kimi-pre-gate.sh"
    shim.write_text(hook_wrapper_contents(HARNESS_RECORDS["kimi-code"])[shim.name])
    return shim


def _run(command: str, cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    base = {
        **child_keys(),
        "PATH": os.environ["PATH"],
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
    }
    return subprocess.run(
        ["sh", "-c", command], input=_WRITE, capture_output=True, text=True, cwd=cwd,
        env={**base, **env}, timeout=60,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("harness", "output"),  # output: the ctx-inject lane's DADAIA_HOOK_OUTPUT ("": plain)
    [("claude", ""), ("codex", "codex-json"), ("cursor", "cursor-json"), ("devin", ""),
     ("copilot", "copilot-json"), ("kimi-code", "")],
)  # fmt: skip
def test_missing_venv_is_loud_and_fails_open_on_every_harness(
    tmp_path: Path, harness: str, output: str
) -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B3: no `.dadaia/.venv` —
    every lane exits 0 (never 127) naming the missing venv on stderr; and (AC2.7) each
    ctx-inject firing tells the agent, in that lane's envelope, with no file written."""
    ws = _workspace(tmp_path / 'w"s', venv=False)
    before = sorted((ws / ".dadaia").rglob("*"))
    hooks, record = ws / ".dadaia" / "hooks", HARNESS_RECORDS[harness]
    lanes = [wrapper_name(record, lane) for lane in ("pre-gate", "ctx-inject", "ctx-inject")]
    done = [_run(f"sh {shlex.quote(str(hooks / lane))}", ws) for lane in lanes]
    assert all(d.returncode == 0 and ".dadaia/.venv" in d.stderr for d in done), done
    told = (
        f"dadaia: no workspace venv at {ws}/.dadaia/.venv — the gate is off.\n"
        f"fix: uvx dadaia-workspace init {ws}\n"
    )
    assert [d.stdout for d in done[1:]] == [envelope({"DADAIA_HOOK_OUTPUT": output}, told)] * 2
    assert sorted((ws / ".dadaia").rglob("*")) == before


def test_kimi_shim_judges_the_nearest_sentinel_workspace(tmp_path: Path) -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B4: the shim run inside a
    venv-less inner workspace nested in an outer one warns about INNER and exits 0 —
    it never runs the outer workspace's interpreter."""
    outer = _workspace(tmp_path / "ws-outer", venv=True)
    (outer / "sandbox").mkdir()
    inner = _workspace(outer / "sandbox" / "inner", venv=False)
    done = _run(f"sh {_kimi_shim(tmp_path)}", inner)
    assert done.returncode == 0
    assert f"{inner}/.dadaia/.venv" in done.stderr
    assert str(outer / ".dadaia" / ".venv") + "/" not in done.stderr.replace(str(inner), "")


def test_the_claude_hook_survives_a_moved_workspace(tmp_path: Path) -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B5: the registered command
    resolves through $CLAUDE_PROJECT_DIR, so a workspace moved after install still gates:
    a new root entry is refused."""
    _workspace(tmp_path / "before", venv=True)
    moved = tmp_path / "after"
    shutil.move(str(tmp_path / "before"), moved)
    (moved / ".dadaia" / ".venv" / "bin" / "python").unlink()
    (moved / ".dadaia" / ".venv" / "bin" / "python").symlink_to(sys.executable)
    payload_dir = moved / "stray.md"
    done = subprocess.run(
        ["sh", "-c", _claude_pre_gate()],
        input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(payload_dir)},
                          "cwd": str(moved)}),
        capture_output=True, text=True, cwd=moved, timeout=60,
        env={**child_keys(), "PATH": os.environ["PATH"], "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
             "CLAUDE_PROJECT_DIR": str(moved)},
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
