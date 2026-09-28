"""v0.2.8 T2 — Kimi Code runtime-config generators (managed hook block + shims).

Pins the managed ``[[hooks]]`` TOML block shape (events, matchers, markers, absolute
commands), the replace-or-append upsert semantics, and the five workspace-agnostic shim
bodies — including a live ``sh`` replay of the pre-gate block/allow/fail-open contract
against a fake workspace venv.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.infrastructure.runtime_config import (
    KIMI_BLOCK_BEGIN,
    KIMI_BLOCK_END,
    kimi_code_home,
    kimi_hook_shims,
    kimi_hooks_block,
    upsert_kimi_hooks_block,
)

pytestmark = pytest.mark.unit

_HOME = Path("/tmp/kimi-home-test")


# ---------------------------------------------------------------------------
# kimi_code_home
# ---------------------------------------------------------------------------


def test_kimi_code_home_defaults_to_user_dot_dir() -> None:
    assert kimi_code_home({}) == Path.home() / ".kimi-code"


def test_kimi_code_home_honours_env_override() -> None:
    assert kimi_code_home({"KIMI_CODE_HOME": "/srv/kimi"}) == Path("/srv/kimi")


# ---------------------------------------------------------------------------
# kimi_hooks_block — exact managed TOML shape
# ---------------------------------------------------------------------------


def test_kimi_hooks_block_parses_as_toml_and_pins_rules() -> None:
    block = kimi_hooks_block(_HOME)
    assert block.startswith(KIMI_BLOCK_BEGIN + "\n")
    assert block.endswith(KIMI_BLOCK_END + "\n")

    parsed = tomllib.loads(block)
    hooks = parsed["hooks"]
    assert [h["event"] for h in hooks] == [
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "PostCompact",
        "SessionStart",
    ]
    by_event = {h["event"]: h for h in hooks}
    assert "matcher" not in by_event["SessionStart"]
    assert by_event["PreToolUse"]["matcher"] == "^(Edit|Write|Bash)$"
    assert by_event["PostCompact"]["matcher"] == "manual|auto"
    assert "matcher" not in by_event["PostToolUse"]
    assert "matcher" not in by_event["UserPromptSubmit"]
    assert by_event["PreToolUse"]["command"] == "/tmp/kimi-home-test/hooks/dadaia-kimi-pre-gate.sh"
    assert by_event["PostCompact"]["command"] == (
        "/tmp/kimi-home-test/hooks/dadaia-kimi-post-compact.sh"
    )
    assert all(h["timeout"] == 10 for h in hooks)


# ---------------------------------------------------------------------------
# upsert_kimi_hooks_block — replace-or-append, foreign content preserved
# ---------------------------------------------------------------------------


def test_upsert_appends_to_empty_file() -> None:
    block = kimi_hooks_block(_HOME)
    assert upsert_kimi_hooks_block("", block) == block


def test_upsert_appends_after_foreign_config_untouched() -> None:
    foreign = 'default_model = "kimi-code/k3"\n\n[thinking]\nenabled = true\n'
    block = kimi_hooks_block(_HOME)
    out = upsert_kimi_hooks_block(foreign, block)
    assert out.startswith(foreign)
    assert out.endswith(block)


def test_upsert_replaces_between_markers_and_preserves_surroundings() -> None:
    stale = (
        'default_model = "k3"\n'
        + KIMI_BLOCK_BEGIN
        + '\n[[hooks]]\nevent = "Stale"\n'
        + KIMI_BLOCK_END
        + "\n\n[thinking]\nenabled = true\n"
    )
    block = kimi_hooks_block(_HOME)
    out = upsert_kimi_hooks_block(stale, block)
    assert 'event = "Stale"' not in out
    assert out.count(KIMI_BLOCK_BEGIN) == 1
    assert out.endswith("\n\n[thinking]\nenabled = true\n")
    assert out.startswith('default_model = "k3"\n')


def test_upsert_is_idempotent() -> None:
    block = kimi_hooks_block(_HOME)
    once = upsert_kimi_hooks_block('default_model = "k3"\n', block)
    assert upsert_kimi_hooks_block(once, block) == once


def test_upsert_full_result_stays_valid_toml() -> None:
    foreign = 'default_model = "kimi-code/k3"\n'
    out = upsert_kimi_hooks_block(foreign, kimi_hooks_block(_HOME))
    parsed = tomllib.loads(out)
    assert parsed["default_model"] == "kimi-code/k3"
    assert len(parsed["hooks"]) == 5


# ---------------------------------------------------------------------------
# kimi_hook_shims — bodies and live sh contract
# ---------------------------------------------------------------------------


def test_kimi_hook_shims_keys_and_prologue() -> None:
    """Which workspace a shim judges, and its missing-venv posture, are executed in
    tests/integration/gate/test_hook_interpreter.py (#B3, #B4)."""
    shims = kimi_hook_shims()
    assert set(shims) == {
        "dadaia-kimi-pre-gate.sh",
        "dadaia-kimi-post-gate.sh",
        "dadaia-kimi-ctx-inject.sh",
        "dadaia-kimi-post-compact.sh",
        "dadaia-kimi-doctor-expired.sh",
    }
    assert all(body.startswith("#!/usr/bin/env sh\n") for body in shims.values())


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
@pytest.mark.parametrize("body", kimi_hook_shims().values())
def test_kimi_hook_shims_are_valid_sh_syntax(body: str, tmp_path: Path) -> None:
    shim = tmp_path / "shim.sh"
    shim.write_text(body, encoding="utf-8")
    subprocess.run(["sh", "-n", str(shim)], check=True)


def _fake_workspace(tmp_path: Path, python_body: str) -> Path:
    """Create a fake dadaia workspace whose venv python is a stub script."""
    workspace = tmp_path / "ws"
    bin_dir = workspace / ".dadaia" / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    fake_python = bin_dir / "python"
    fake_python.write_text(python_body, encoding="utf-8")
    fake_python.chmod(0o755)
    return workspace


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_blocks_with_reason_on_stderr(tmp_path: Path) -> None:
    """sa-gate-blind-on-cursor-copilot-devin#B5: the real pre_gate's multi-line reason reaches stderr with real
    newlines and its `fix:` at a line start; exit 2."""
    workspace = tmp_path / "ws"
    # An interpreter at the platform's own venv layout (bin/python, Scripts/python.exe):
    # a regular sh wrapper, never a symlink (MSYS sh does not see a native link as -x).
    scripts = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    scripts.mkdir(parents=True)
    python = scripts / f"python{PLATFORM.venv_exe_suffix}"
    python.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n', "utf-8")
    python.chmod(0o755)
    (workspace / ".dadaia" / "states").mkdir()
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(workspace / ".dadaia/states/install_ledger.json")},
    }
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": os.environ.get("PYTHONPATH", "")}
    env.update({k: os.environ[k] for k in ("SYSTEMROOT",) if k in os.environ})  # Windows

    def run(*sh_flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", *sh_flags, str(shim)],
            input=json.dumps(payload),
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
        )

    proc = run()
    if proc.returncode != 2:  # one CI round must say why: re-run traced
        traced = run("-x")
        pytest.fail(f"rc {proc.returncode}; traced shim stderr:\n{traced.stderr}")
    assert any(line.startswith("fix: ") for line in proc.stderr.splitlines()), proc.stderr


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_allows_on_allow_envelope(tmp_path: Path) -> None:
    workspace = _fake_workspace(
        tmp_path,
        '#!/usr/bin/env sh\ncat >/dev/null\nprintf \'{"decision": "allow"}\\n\'\n',
    )
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    proc = subprocess.run(
        ["sh", str(shim)],
        input='{"tool_name": "Write", "session_id": "s1"}',
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_fails_open_outside_dadaia_workspaces(tmp_path: Path) -> None:
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    proc = subprocess.run(
        ["sh", str(shim)],
        input='{"tool_name": "Write"}',
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stderr == ""
