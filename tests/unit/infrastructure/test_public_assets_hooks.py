"""Hooks/config generators extracted from ``public_assets`` (T-2, v0.1.75 split of
``test_public_assets.py`` by concern — 4/4: hooks).

Covers: the codex hooks contract (structure + SessionStart + the N-2
PostToolUse-heartbeat-fires-on-ALL-tools omitted-matcher assert, kept verbatim), the
claude settings contract (structure + matcher-scoping + PostToolUse ``*``), the
seed-5 single-PreToolUse-command-per-runtime proof, and the wrapper-contents +
force-rm-stale + omits-inert-config-keys checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
)


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    return agentic_dir, workspace_root


def test_codex_hooks_contract(tmp_path: Path) -> None:
    """Structure (PreToolUse/PostToolUse/UserPromptSubmit/SessionStart, all Python
    module invocations via wrapper scripts) + the N-2 lease-starvation fix: the
    PostToolUse heartbeat block must fire on ALL tools (omitted matcher = Codex's
    canonical match-all), NOT only the write tools — kept verbatim, never edit."""
    manager = FileSystemPublicAssetManager()
    config = manager._codex_hooks(tmp_path)
    assert "hooks" in config
    hooks = config["hooks"]

    assert "PreToolUse" in hooks
    matchers = hooks["PreToolUse"]
    assert isinstance(matchers, list)
    assert len(matchers) > 0
    assert matchers[0]["matcher"] == "^(apply_patch|Edit|Write|Bash)$"
    assert "Bash" in matchers[0]["matcher"]  # T-014-12: W3 venv guard fires on Bash.
    assert matchers[0]["hooks"][0]["type"] == "command"
    pre_gate_cmd = str(matchers[0]["hooks"][0]["command"])
    assert pre_gate_cmd == ".dadaia/hooks/codex-pre-gate"
    assert " " not in pre_gate_cmd
    assert "sdd-spec-gate.sh" not in pre_gate_cmd

    assert "PostToolUse" in hooks
    post_matchers = hooks["PostToolUse"]
    assert isinstance(post_matchers, list)
    assert len(post_matchers) > 0
    assert "matcher" not in post_matchers[0]
    assert post_matchers[0]["hooks"][0]["type"] == "command"
    post_cmd = str(post_matchers[0]["hooks"][0]["command"])
    assert post_cmd == ".dadaia/hooks/codex-post-gate"
    assert " " not in post_cmd
    assert "sdd-post-gate.sh" not in post_cmd

    assert "UserPromptSubmit" in hooks
    prompt_matchers = hooks["UserPromptSubmit"]
    assert isinstance(prompt_matchers, list)
    assert "matcher" not in prompt_matchers[0]
    assert prompt_matchers[0]["hooks"][0]["type"] == "command"
    prompt_command = str(prompt_matchers[0]["hooks"][0]["command"])
    assert prompt_command == ".dadaia/hooks/codex-ctx-inject"
    assert " " not in prompt_command
    assert "DADAIA_HOOK_OUTPUT=" not in prompt_command
    assert "ctx-inject.sh" not in prompt_command

    # T-016-C01: SessionStart carries context once per session (matcher startup|resume).
    assert "SessionStart" in hooks
    ss = hooks["SessionStart"]
    assert isinstance(ss, list) and ss
    assert ss[0]["matcher"] == "startup|resume"
    ss_cmd = str(ss[0]["hooks"][0]["command"])
    assert ss_cmd == ".dadaia/hooks/codex-ctx-inject-session-start"
    assert " " not in ss_cmd
    assert "DADAIA_HOOK_EVENT=" not in ss_cmd
    assert "DADAIA_HOOK_OUTPUT=" not in ss_cmd
    assert "ctx-inject.sh" not in ss_cmd

    # N-2 (v0.1.10 rc-2 re-audit HIGH) — PERMANENT, byte-verbatim regression guard.
    post = hooks["PostToolUse"]
    assert isinstance(post, list) and len(post) == 1
    assert "matcher" not in post[0], (
        "Codex heartbeat must NOT be pinned to the write tools — an omitted "
        "matcher is Codex's canonical match-all (N-2)."
    )
    post_cmds = [str(h["command"]) for h in post[0]["hooks"]]
    assert ".dadaia/hooks/codex-post-gate" in post_cmds
    assert all(" " not in c for c in post_cmds)

    pre = hooks["PreToolUse"]
    assert isinstance(pre, list) and len(pre) == 1
    for entry in pre:
        assert entry["matcher"] == "^(apply_patch|Edit|Write|Bash)$"
        assert "Bash" in entry["matcher"]
    pre_cmds = [str(h["command"]) for e in pre for h in e["hooks"]]
    assert ".dadaia/hooks/codex-pre-gate" in pre_cmds
    assert all(" " not in c for c in pre_cmds)
    assert not any("dadaia_workspace.hooks.sdd_gate" in c for c in pre_cmds)
    assert not any("dadaia_workspace.hooks.root_whitelist" in c for c in pre_cmds)

    # root-whitelist policy is registered via the merged pre_gate entrypoint.
    all_pre_commands = [str(hook["command"]) for entry in pre for hook in entry.get("hooks", [])]
    assert ".dadaia/hooks/codex-pre-gate" in all_pre_commands
    assert not any("root-whitelist-gate.sh" in cmd for cmd in all_pre_commands)


def test_claude_settings_contract(tmp_path: Path) -> None:
    """Structure (PreToolUse/PostToolUse/UserPromptSubmit, sdd_post_gate module),
    matcher scoping (write-gate hooks scoped to the write tools + Bash, never an
    empty match-all), and PostToolUse heartbeat firing on ALL tools via the
    explicit ``*`` matcher."""
    manager = FileSystemPublicAssetManager()
    settings = manager._claude_settings(tmp_path)
    assert "hooks" in settings
    hooks = settings["hooks"]
    assert "PreToolUse" in hooks
    assert "UserPromptSubmit" in hooks
    assert "PostToolUse" in hooks

    post_hooks = hooks["PostToolUse"]
    assert isinstance(post_hooks, list)
    assert len(post_hooks) > 0
    commands = [h["command"] for h in post_hooks[0]["hooks"]]
    assert any("dadaia_workspace.hooks.sdd_post_gate" in str(c) for c in commands)
    assert not any("sdd-post-gate.sh" in str(c) for c in commands)

    # T-014-12: the merged gate now also fires on Bash for the W3 venv guard.
    write_matcher = "Edit|Write|MultiEdit|NotebookEdit|Bash"
    pre = hooks["PreToolUse"]
    assert isinstance(pre, list) and len(pre) == 1
    for entry in pre:
        assert entry["matcher"] == write_matcher
        assert "Bash" in entry["matcher"]
        assert entry["matcher"] != "", "write gate must not use the empty match-all"
    pre_cmds = [str(h["command"]) for e in pre for h in e["hooks"]]
    assert any("dadaia_workspace.hooks.pre_gate" in c for c in pre_cmds)
    assert all(" -B -m " in c for c in pre_cmds)
    assert not any("dadaia_workspace.hooks.sdd_gate" in c for c in pre_cmds)
    assert not any("dadaia_workspace.hooks.root_whitelist" in c for c in pre_cmds)

    post = hooks["PostToolUse"]
    assert isinstance(post, list) and len(post) == 1
    assert post[0]["matcher"] == "*"
    post_cmds = [str(h["command"]) for h in post[0]["hooks"]]
    assert any("dadaia_workspace.hooks.sdd_post_gate" in c for c in post_cmds)
    assert all(" -B -m " in c for c in post_cmds)

    ups = hooks["UserPromptSubmit"]
    assert isinstance(ups, list) and len(ups) == 1
    assert ups[0]["matcher"] == ""
    ups_cmds = [str(h["command"]) for h in ups[0]["hooks"]]
    assert any("dadaia_workspace.hooks.ctx_inject" in c for c in ups_cmds)
    assert all(" -B -m " in c for c in ups_cmds)

    # T-SANI-01 + T-014-05: root-whitelist policy registered via merged pre_gate.
    all_pre_commands = [str(hook["command"]) for entry in pre for hook in entry.get("hooks", [])]
    assert any("dadaia_workspace.hooks.pre_gate" in cmd for cmd in all_pre_commands)
    assert not any("root-whitelist-gate.sh" in cmd for cmd in all_pre_commands)


def test_seed5_single_pretooluse_command_per_runtime(tmp_path: Path) -> None:
    """Seed-5 static proof (T-014-05): exactly ONE registered PreToolUse hook command
    per runtime config (the merged pre_gate), down from the old dual sdd_gate +
    root_whitelist wiring — one interpreter spawn per write tool call."""
    manager = FileSystemPublicAssetManager()
    for hooks in (
        manager._claude_settings(tmp_path)["hooks"],
        manager._codex_hooks(tmp_path)["hooks"],
    ):
        pre = hooks["PreToolUse"]
        commands = [str(h["command"]) for entry in pre for h in entry.get("hooks", [])]
        assert len(commands) == 1, f"expected one PreToolUse command, got {commands}"
        assert (
            "dadaia_workspace.hooks.pre_gate" in commands[0]
            or commands[0] == ".dadaia/hooks/codex-pre-gate"
        )


def test_wrapper_contents_and_inert_config_keys_omitted(tmp_path: Path) -> None:
    """T-018-17 wrapper-contents: the 4 codex hook wrapper scripts carry the exact
    module invocations and env-var forms; W1-2: the inert ``approved_commands``
    array and ``[skills] paths`` table are no longer emitted (invalid/not-a-real
    codex config key)."""
    from dadaia_workspace.infrastructure.runtime_config import codex_hook_wrapper_contents

    wrappers = codex_hook_wrapper_contents()
    assert set(wrappers) == {
        "codex-pre-gate",
        "codex-post-gate",
        "codex-ctx-inject",
        "codex-ctx-inject-session-start",
    }
    assert "dadaia_workspace.hooks.pre_gate" in wrappers["codex-pre-gate"]
    assert "dadaia_workspace.hooks.sdd_post_gate" in wrappers["codex-post-gate"]
    assert 'DADAIA_HOOK_OUTPUT="codex-json"' in wrappers["codex-ctx-inject"]
    assert 'DADAIA_HOOK_EVENT="SessionStart"' in wrappers["codex-ctx-inject-session-start"]
    assert all('exec "$PYTHON_BIN" -B -m ' in body for body in wrappers.values())

    agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
    manager = FileSystemPublicAssetManager()
    config_text = manager._codex_config(agentic_dir)
    assert "approved_commands" not in config_text
    assert "[skills]" not in config_text


@pytest.mark.skipif(os.name == "nt", reason="generated Codex hook wrappers are POSIX shell")
def test_codex_pre_gate_wrapper_never_creates_repo_bytecode(tmp_path: Path) -> None:
    """The projected wrapper is repository-clean even when cwd shadows the package."""
    from dadaia_workspace.infrastructure.runtime_config import codex_hook_wrapper_contents

    workspace = tmp_path / "workspace"
    repo = workspace / "repos" / "sample"
    package = repo / "dadaia_workspace" / "hooks"
    package.mkdir(parents=True)
    (package.parent / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "pre_gate.py").write_text(
        "import json, sys\njson.load(sys.stdin)\n",
        encoding="utf-8",
    )

    python_bin = workspace / ".dadaia" / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.symlink_to(Path(sys.executable))
    hook = workspace / ".dadaia" / "hooks" / "codex-pre-gate"
    hook.parent.mkdir(parents=True)
    hook.write_text(codex_hook_wrapper_contents()["codex-pre-gate"], encoding="utf-8")
    hook.chmod(0o755)

    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    subprocess.run(
        [str(hook)],
        cwd=repo,
        input="{}",
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    assert list(repo.rglob("__pycache__")) == []
    assert list(repo.rglob("*.pyc")) == []
