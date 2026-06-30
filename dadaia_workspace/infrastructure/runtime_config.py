"""Runtime configuration generators for Claude and Codex projections.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  Each function takes explicit arguments instead of
``self``, so there are no circular imports.

T-018-17: hook commands are emitted as ``<python> -m dadaia_workspace.hooks.<name>``
using the venv-aware ``_python_bin()`` helper (Windows-safe fallbacks: Scripts/python.exe
→ sys.executable → bare python). The ``.sh`` scripts are superseded, not appended.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_agents_config_file_blocks,
)


def _python_bin(workspace_root: Path) -> str:
    """Resolve the workspace venv Python binary, Windows-safe.

    Priority: ``.dadaia/.venv/bin/python`` (POSIX) or
    ``.dadaia/.venv/Scripts/python.exe`` (Windows) → ``sys.executable`` → bare ``python``.
    """
    from dadaia_workspace.core.platform import PLATFORM

    venv_python = (
        workspace_root
        / ".dadaia"
        / ".venv"
        / PLATFORM.venv_scripts_dir
        / f"python{PLATFORM.venv_exe_suffix}"
    )
    if venv_python.is_file():
        return str(venv_python)
    if sys.executable:
        return sys.executable
    return "python"


def _hook_cmd(workspace_root: Path, module: str) -> str:
    """Return ``<python_bin> -m <module>`` for *workspace_root*."""
    return f"{_python_bin(workspace_root)} -m {module}"


_CODEX_HOOK_WRAPPERS: dict[str, tuple[str, dict[str, str]]] = {
    "codex-pre-gate": ("dadaia_workspace.hooks.pre_gate", {}),
    "codex-post-gate": ("dadaia_workspace.hooks.sdd_post_gate", {}),
    "codex-ctx-inject": (
        "dadaia_workspace.hooks.ctx_inject",
        {"DADAIA_HOOK_OUTPUT": "codex-json"},
    ),
    "codex-ctx-inject-session-start": (
        "dadaia_workspace.hooks.ctx_inject",
        {"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "SessionStart"},
    ),
}


def codex_hook_wrapper_contents() -> dict[str, str]:
    """Return generated executable wrapper contents for Codex command hooks.

    Codex command execution differs across surfaces: some paths shell-parse command
    strings, while others direct-exec the string as an executable. The wrappers make the
    hook contract one executable path with no arguments or env-prefix syntax in
    ``hooks.json``. Each wrapper resolves the workspace venv Python relative to its own
    location, so moving/importing a workspace does not leave stale absolute Python paths.
    """
    wrappers: dict[str, str] = {}
    for name, (module, env) in _CODEX_HOOK_WRAPPERS.items():
        exports = "".join(f'{key}="{value}"\nexport {key}\n' for key, value in env.items())
        wrappers[name] = (
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
            'WORKSPACE_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)\n'
            'PYTHON_BIN="$WORKSPACE_ROOT/.dadaia/.venv/bin/python"\n'
            'if [ ! -x "$PYTHON_BIN" ]; then\n'
            '  echo "dadaia Codex hook wrapper: missing executable $PYTHON_BIN" >&2\n'
            "  exit 127\n"
            "fi\n"
            f"{exports}"
            f'exec "$PYTHON_BIN" -B -m {module} "$@"\n'
        )
    return wrappers


def _codex_hook_wrapper_command(name: str) -> str:
    """Return a direct-exec-safe hook command path for a generated wrapper."""
    return f".dadaia/hooks/{name}"


# T-010-18 (R6c, AC-R6-05, ai C-12): Claude Code PreToolUse gate matcher.
# The SDD gate and root-whitelist gate police filesystem writes (the write tools); the
# W3 venv guard (T-014-12) additionally polices Bash invocations of `dadaia`/`pip`/
# `python -m dadaia_workspace`. The merged pre_gate entrypoint therefore fires on the
# write tools AND Bash — still a scoped explicit matcher, never the forbidden empty
# (match-all) form the ai audit flagged.
_CLAUDE_WRITE_TOOLS = "Edit|Write|MultiEdit|NotebookEdit|Bash"
# Claude Code's canonical explicit match-all for tool-matching events. Used on
# PostToolUse so the lease heartbeat (T-010-04) fires after *every* tool, including
# Bash, not just write tools. Deliberately the explicit "*" form, NOT the empty
# string the ai audit forbids.
_CLAUDE_MATCH_ALL = "*"


def claude_settings(workspace_root: Path) -> dict[str, object]:
    """Return the Claude Code settings.json dict for *workspace_root*."""
    return {
        "hooks": {
            # FR-W4-01 (T-014-05): a SINGLE merged PreToolUse entrypoint (pre_gate) reads
            # stdin once and runs root-whitelist → venv-guard → SDD gate in order. The old
            # dual sdd_gate + root_whitelist wiring is gone (one interpreter spawn per write).
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "command": _hook_cmd(workspace_root, "dadaia_workspace.hooks.pre_gate"),
                            "type": "command",
                        }
                    ],
                    "matcher": _CLAUDE_WRITE_TOOLS,
                },
            ],
            "PostToolUse": [
                {
                    "hooks": [
                        {
                            "command": _hook_cmd(
                                workspace_root, "dadaia_workspace.hooks.sdd_post_gate"
                            ),
                            "type": "command",
                        }
                    ],
                    # Heartbeat must fire on ALL tools (T-010-04) — explicit match-all.
                    "matcher": _CLAUDE_MATCH_ALL,
                }
            ],
            # UserPromptSubmit has no tool to match; matcher unchanged (empty).
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "command": _hook_cmd(
                                workspace_root, "dadaia_workspace.hooks.ctx_inject"
                            ),
                            "type": "command",
                        }
                    ],
                    "matcher": "",
                }
            ],
        }
    }


def codex_config(agentic_dir: Path) -> str:
    """Return the .codex/config.toml content for *agentic_dir*."""
    lines = ['# Generated by "dadaia public install --target codex".\n', "\n"]
    # FR7: emit [agents.<name>] config_file blocks — one per canonical agent.
    agents_blocks = _render_agents_config_file_blocks(agentic_dir / "agents")
    if agents_blocks:
        lines.append("\n")
        lines.append(agents_blocks)
    # T-PB-4: emit [skills] table after all [agents.*] blocks
    lines.append("\n")
    lines.append("[skills]\n")
    lines.append('paths = [".agents/skills", ".codex/skills"]\n')
    return "".join(lines)


def codex_hooks(workspace_root: Path) -> dict[str, object]:
    """Return the .codex/hooks.json dict for *workspace_root*."""
    # PreToolUse gate fires on the write tools (filesystem writes) AND Bash — the W3 venv
    # guard (T-014-12) polices `dadaia`/`pip`/`python -m dadaia_workspace` Bash invocations.
    # Read-only tools are still excluded.
    write_matcher = "^(apply_patch|Edit|Write|Bash)$"
    return {
        "hooks": {
            # FR-W4-01 (T-014-05): single merged PreToolUse entrypoint (pre_gate) — one
            # interpreter spawn runs root-whitelist → venv-guard → SDD gate. The old dual
            # sdd_gate + root_whitelist wiring is removed.
            "PreToolUse": [
                {
                    "matcher": write_matcher,
                    "hooks": [
                        {
                            "type": "command",
                            "command": _codex_hook_wrapper_command("codex-pre-gate"),
                            "statusMessage": "Checking dadaia PreToolUse gate",
                        }
                    ],
                },
            ],
            # N-2 (v0.1.10 rc-2): the lease heartbeat MUST fire after *every* tool,
            # including Bash and read-only tools — otherwise a long non-write Codex
            # call (e.g. a multi-minute pytest run) starves the heartbeat and the
            # lease goes TTL-stale, the original lease-starvation incident's Codex
            # flavor. Codex's canonical match-all is an *omitted* matcher (same form
            # used by UserPromptSubmit), so the heartbeat block carries no matcher and
            # thus runs on all tools, mirroring Claude's explicit "*".
            "PostToolUse": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": _codex_hook_wrapper_command("codex-post-gate"),
                            "statusMessage": "Refreshing SDD session heartbeat",
                        }
                    ],
                }
            ],
            # SessionStart carries the full workspace context ONCE per logical
            # session (matcher startup|resume). ctx-inject keys idempotence on the
            # session_id Codex passes on stdin, so the per-prompt UserPromptSubmit
            # path below stays silent after the first injection (T-016-C01).
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _codex_hook_wrapper_command(
                                "codex-ctx-inject-session-start"
                            ),
                            "statusMessage": "Loading dadaia context",
                        }
                    ],
                }
            ],
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": _codex_hook_wrapper_command("codex-ctx-inject"),
                            "statusMessage": "Loading dadaia context",
                        }
                    ],
                }
            ],
        }
    }
