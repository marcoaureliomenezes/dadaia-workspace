"""Runtime configuration generators for Claude, Codex and Kimi Code projections.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  Each function takes explicit arguments instead of
``self``, so there are no circular imports.

Claude's hook commands cite the workspace's own self-locating wrappers through
``$CLAUDE_PROJECT_DIR`` — no interpreter is baked at render time.

v0.2.8 (kimi-code): Kimi Code has no project-level config file — hooks register only in
the user-level ``$KIMI_CODE_HOME/config.toml``. The kimi generators therefore emit a
managed, marker-delimited ``[[hooks]]`` TOML block plus workspace-agnostic POSIX shims
that resolve the nearest workspace (its ``spec_contexts.json`` sentinel) from the hook cwd
at runtime and delegate to the same shared Python hook modules the other harnesses use.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_agents_config_file_blocks,
)
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    REAPER_ARGS,
    VENV_PYTHON,
    hook_wrapper_command,
)


def _claude_cmd(lane: str) -> str:
    """The Claude hook command: the workspace's own wrapper, wherever the project now is."""
    return f'"$CLAUDE_PROJECT_DIR"/{hook_wrapper_command(f"claude-{lane}")}'


# T-010-18 (R6c, AC-R6-05, ai C-12): Claude Code PreToolUse gate matcher.
# The SDD gate and root-whitelist gate police filesystem writes (the write tools); the
# W3 venv guard (T-014-12) additionally polices Bash invocations of `dadaia`/`pip`/
# `python -m dadaia_workspace`. The merged pre_gate entrypoint therefore fires on the
# write tools AND Bash — still a scoped explicit matcher, never the forbidden empty
# (match-all) form the ai audit flagged.
_CLAUDE_WRITE_TOOLS = "Edit|Write|MultiEdit|NotebookEdit|Bash"
# Claude Code's canonical explicit match-all for tool-matching events. Used on
# PostToolUse so session heartbeat fires after every tool, including Bash.
_CLAUDE_MATCH_ALL = "*"


#: The markers that identify a hook entry as dadaia-owned: every command this module
#: generates cites a ``.dadaia/hooks/claude-*`` wrapper; an install predating the wrappers
#: ran ``-m dadaia_workspace`` directly and is replaced on upgrade. Ownership is decidable
#: from the emitted content alone — an operator's entry in the SAME event is never ours.
_DADAIA_HOOK_MARKERS = (".dadaia/hooks/claude-", "-m dadaia_workspace")


def _is_dadaia_hook_entry(entry: object) -> bool:
    """True iff *entry* is a hook entry this module generated."""
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(h, dict) and any(m in str(h.get("command", "")) for m in _DADAIA_HOOK_MARKERS)
        for h in hooks
    )


def merge_claude_settings(existing: dict[str, object] | None, root: Path) -> dict[str, object]:
    """Fold dadaia's hook wiring into an operator's ``.claude/settings.json``.

    ``settings.json`` is the file Claude Code documents for the operator's own
    ``permissions``, ``model``, ``env``, ``statusLine`` and custom hooks — it is NOT a
    dadaia-owned artifact. Writing it wholesale erased all of that silently, printing
    ``[ok]`` (bug ``claude-install-destroys-operator-settings``). dadaia owns exactly the
    hook entries whose command is one of its own (:data:`_DADAIA_HOOK_MARKERS`):

    * top-level keys other than ``hooks`` are preserved untouched;
    * hook EVENTS dadaia does not wire are preserved untouched;
    * inside an event dadaia does wire, the operator's own entries are preserved and only
      dadaia-owned entries are replaced by the canonical wiring.

    This is the same ownership discipline :func:`upsert_kimi_hooks_block` applies to the
    kimi config; the claude path had a naive whole-file writer instead.
    """
    canonical = claude_settings()
    canonical_hooks = canonical["hooks"]
    assert isinstance(canonical_hooks, dict)
    env = workspace_layout.tool_cache_env(root)  # absolute caches (ADR 0080)
    if not existing:
        return {**canonical, "env": env}

    merged: dict[str, object] = dict(existing)
    existing_hooks_raw = existing.get("hooks")
    existing_hooks: dict[str, object] = (
        dict(existing_hooks_raw) if isinstance(existing_hooks_raw, dict) else {}
    )
    for event, entries in canonical_hooks.items():
        prior = existing_hooks.get(event)
        foreign = (
            [e for e in prior if not _is_dadaia_hook_entry(e)] if isinstance(prior, list) else []
        )
        assert isinstance(entries, list)
        existing_hooks[event] = [*entries, *foreign]
    merged["hooks"] = existing_hooks
    prior_env = existing.get("env")  # dadaia owns only its cache keys
    merged["env"] = {**(prior_env if isinstance(prior_env, dict) else {}), **env}
    return merged


def foreign_claude_hook_commands(
    settings: dict[str, object], canonical: dict[str, object]
) -> list[str]:
    """Every hook command in the file that dadaia did not generate.

    Preserving the operator's own hooks is correct; going blind to them is not. A foreign
    command inside ``PreToolUse`` runs on every gated write, so it is exactly where a local
    injection would sit. This lists them so the doctor can surface them — the file belongs
    to the operator, so the finding is advisory, never drift.

    The sweep covers EVERY event present in the file, not only the four dadaia wires.
    Seeding from the canonical events alone left ``Stop``, ``PreCompact``, ``SessionEnd``,
    ``SubagentStop`` and ``Notification`` unsurfaced — events Claude Code executes just the
    same, so a foothold there was equally invisible and equally live.
    """
    canonical_hooks = canonical.get("hooks")
    wired = set(canonical_hooks) if isinstance(canonical_hooks, dict) else set()
    hooks_raw = settings.get("hooks")
    hooks = hooks_raw if isinstance(hooks_raw, dict) else {}
    found: list[str] = []
    for event in sorted(wired | set(hooks)):
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if _is_dadaia_hook_entry(entry) or not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []) if isinstance(entry.get("hooks"), list) else []:
                if isinstance(hook, dict) and hook.get("command"):
                    # BOTH tokens are attacker-controlled and land in a printed doctor line
                    # (CWE-117). Raw ESC/newline bytes let a crafted command forge a second
                    # physical line reading "[ok] claude:settings.json" — the very mechanism
                    # that exists to REVEAL a foothold, used to hide it. repr() escapes
                    # ESC, CR and LF, so the line can only ever be one line.
                    found.append(f"{event!r}:{hook['command']!r}")
    return found


def claude_settings() -> dict[str, object]:
    """Return the Claude Code settings.json hook wiring (workspace-relative)."""
    return {
        "hooks": {
            # FR-W4-01 (T-014-05): a SINGLE merged PreToolUse entrypoint (pre_gate) reads
            # stdin once and runs root-whitelist → venv-guard → SDD gate in order. The old
            # dual sdd_gate + root_whitelist wiring is gone (one interpreter spawn per write).
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "command": _claude_cmd("pre-gate"),
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
                            "command": _claude_cmd("post-gate"),
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
                            "command": _claude_cmd("ctx-inject"),
                            "type": "command",
                        }
                    ],
                    "matcher": "",
                }
            ],
            # Bug claude-compact-reinjection-missing: a compact erases the injected
            # bootstrap and /clear wipes the context; ctx_inject re-emits it at the event
            # (Claude Code adds SessionStart stdout back to context) and restamps the
            # sentinel. Matchers are the exact documented source names; fork stays on
            # the bind-driven UserPromptSubmit path (FR-W2). Parity with the
            # kimi-code PostCompact shim (v0.2.8) and the codex SessionStart wrapper.
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "command": _claude_cmd("ctx-inject"),
                            "type": "command",
                        }
                    ],
                    "matcher": "compact",
                },
                {
                    "hooks": [
                        {
                            "command": _claude_cmd("ctx-inject"),
                            "type": "command",
                        }
                    ],
                    "matcher": "clear",
                },
                # Backlog cli-help-architecture: a NEW session received zero context
                # until its first prompt — startup/resume now inject at the event
                # itself (parity with the codex SessionStart wrapper). They flow the
                # normal prompt path in the policy: fresh session -> bootstrap or
                # preflight + sentinel stamp; the next prompt stays silent.
                {
                    "hooks": [
                        {
                            "command": _claude_cmd("ctx-inject"),
                            "type": "command",
                        }
                    ],
                    "matcher": "startup",
                },
                {
                    "hooks": [
                        {
                            "command": _claude_cmd("ctx-inject"),
                            "type": "command",
                        }
                    ],
                    "matcher": "resume",
                },
                {
                    "hooks": [{"command": _claude_cmd("doctor-expired"), "type": "command"}],
                    "matcher": "startup|resume",
                },
            ],
        },
    }


def codex_config(agentic_dir: Path, workspace_root: Path) -> str:
    """The .codex/config.toml: the absolute tool-cache env every shell command inherits
    (ADR 0080) and one ``[agents."<name>"]`` block per canonical agent (command policy
    lives in ``.codex/rules``; skills are discovered natively)."""
    env = workspace_layout.tool_cache_env(workspace_root).items()
    lines = ['# Generated by "dadaia harness add codex".\n', "\n[shell_environment_policy.set]\n"]
    lines += [*(f"{var} = '{path}'\n" for var, path in env), "\n"]
    # FR7: emit [agents.<name>] config_file blocks — one per canonical agent.
    agents_blocks = _render_agents_config_file_blocks(agentic_dir / "agents")
    if agents_blocks:
        lines.append(agents_blocks)
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
                            "command": hook_wrapper_command("codex-pre-gate"),
                            "statusMessage": "Checking dadaia PreToolUse gate",
                        }
                    ],
                },
            ],
            # Session heartbeat fires after every tool. Codex's canonical
            # match-all is an omitted matcher, mirroring Claude's explicit "*".
            "PostToolUse": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_wrapper_command("codex-post-gate"),
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
                            "command": hook_wrapper_command("codex-ctx-inject-session-start"),
                            "statusMessage": "Loading dadaia context",
                        },
                        {
                            "type": "command",
                            "command": hook_wrapper_command("codex-doctor-expired"),
                            "statusMessage": "Reaping expired workspace files",
                        },
                    ],
                }
            ],
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_wrapper_command("codex-ctx-inject"),
                            "statusMessage": "Loading dadaia context",
                        }
                    ],
                }
            ],
        }
    }


# ---------------------------------------------------------------------------
# Kimi Code (v0.2.8) — managed user-level hook block + workspace-agnostic shims.
#
# Kimi Code has no project-level config file: ``[[hooks]]`` rules live only in
# ``$KIMI_CODE_HOME/config.toml`` (default ``~/.kimi-code/config.toml``). The installer
# therefore upserts a marker-delimited block there and writes four shims under
# ``$KIMI_CODE_HOME/hooks/``. The shims carry no workspace-absolute paths — they resolve
# the nearest ``.dadaia/.venv/bin/python`` by walking up from the hook cwd (Kimi runs
# hooks with the session project dir as cwd), so one global block serves every dadaia
# workspace and stays inert (fail-open, exit 0) outside them.
# ---------------------------------------------------------------------------

#: Managed-block markers in ``config.toml``. Content outside them is never touched.
KIMI_BLOCK_BEGIN = (
    "# >>> dadaia-workspace kimi-code hooks (managed by dadaia public install — do not edit) >>>"
)
KIMI_BLOCK_END = "# <<< dadaia-workspace kimi-code hooks (managed) <<<"

#: PreToolUse matcher: the SDD gate and root-whitelist police filesystem writes (Edit,
#: Write); the venv-guard polices Bash `dadaia`/`pip`/`python -m dadaia_workspace` calls.
#: Kimi has no MultiEdit/NotebookEdit/apply_patch tools, so the matcher stays minimal.
_KIMI_WRITE_MATCHER = "^(Edit|Write|Bash)$"
#: PostCompact fires for both manual (``/compact``) and automatic compaction.
_KIMI_COMPACT_MATCHER = "manual|auto"

#: The five kimi hook rules: (shim filename, event, matcher-or-None, timeout seconds).
#: SessionStart carries no matcher: Kimi's ``source`` vocabulary is undocumented, and the
#: reaper is idempotent and silent on a compliant workspace.
_KIMI_HOOK_RULES: tuple[tuple[str, str, str | None, int], ...] = (
    ("dadaia-kimi-pre-gate.sh", "PreToolUse", _KIMI_WRITE_MATCHER, 10),
    ("dadaia-kimi-post-gate.sh", "PostToolUse", None, 10),
    ("dadaia-kimi-ctx-inject.sh", "UserPromptSubmit", None, 10),
    ("dadaia-kimi-post-compact.sh", "PostCompact", _KIMI_COMPACT_MATCHER, 10),
    ("dadaia-kimi-doctor-expired.sh", "SessionStart", None, 10),
)

#: Shared shim prologue: walk up from the hook cwd to the nearest workspace sentinel
#: (``.dadaia/states/spec_contexts.json``); none -> silent exit 0 (not a workspace); a
#: workspace without its venv -> the wrappers' one warning and exit 0.
_KIMI_SHIM_PROLOGUE = (
    """\
#!/usr/bin/env sh
# Generated by "dadaia harness add kimi-code" — do not edit in place.
# dadaia-workspace kimi-code hook shim: resolve the nearest dadaia workspace from the
# hook cwd and delegate to the shared Python hook module. Fail-open: any resolution or
# runtime error exits 0, a missing venv with one warning, so a hook never blocks.
set -u

ROOT=$PWD
while [ ! -f "$ROOT/.dadaia/states/spec_contexts.json" ]; do
  [ "$ROOT" = / ] && exit 0
  ROOT=$(dirname "$ROOT")
done
"""
    + VENV_PYTHON
    + """
payload=$(cat)
"""
)


def kimi_code_home(env: Mapping[str, str] | None = None) -> Path:
    """Resolve the Kimi Code data root: ``$KIMI_CODE_HOME`` or ``~/.kimi-code``."""
    source = os.environ if env is None else env
    override = (source.get("KIMI_CODE_HOME") or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".kimi-code"


def kimi_hook_shims() -> dict[str, str]:
    """Return the five kimi hook shim bodies as ``{filename: POSIX sh content}``.

    - pre-gate: forwards the payload to ``hooks.pre_gate`` and translates the dadaia
      envelope to the Kimi protocol — ``"decision": "block"`` ⇒ reason on stderr +
      exit 2; anything else ⇒ exit 0.
    - post-gate: session heartbeat via ``hooks.sdd_post_gate``; output discarded.
    - ctx-inject: ``hooks.ctx_inject``; stdout passes through (Kimi appends
      ``UserPromptSubmit`` stdout to the context).
    - post-compact: ``hooks.ctx_inject`` with ``DADAIA_HOOK_EVENT=PostCompact`` — writes
      the compact-epoch marker consumed by the next ``UserPromptSubmit`` AND re-emits
      the bootstrap on stdout (observable-contract posture; Kimi discards PostCompact
      stdout, so the deterministic re-injection still lands at the next prompt).
    - doctor-expired: the SessionStart reaper as a CLI process — the same
      ``REAPER_ARGS`` the Claude and Codex entries run.
    """
    pre_gate = (
        _KIMI_SHIM_PROLOGUE
        + """
export DADAIA_RUNTIME="kimi-code"
out=$(printf '%s' "$payload" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.pre_gate 2>/dev/null) || exit 0
printf '%s' "$out" | "$PYTHON_BIN" -B -c 'import json, sys  # JSON, never sed: real newlines
d = json.load(sys.stdin)
sys.exit(2 if d.get("decision") == "block" and sys.stderr.write(d["reason"] + "\\n") else 0)'
[ $? -eq 2 ] && exit 2
exit 0
"""
    )
    post_gate = (
        _KIMI_SHIM_PROLOGUE
        + """
export DADAIA_RUNTIME="kimi-code"
printf '%s' "$payload" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.sdd_post_gate >/dev/null 2>&1 || true
exit 0
"""
    )
    ctx_inject = (
        _KIMI_SHIM_PROLOGUE
        + """
export DADAIA_RUNTIME="kimi-code"
printf '%s' "$payload" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.ctx_inject 2>/dev/null || true
exit 0
"""
    )
    post_compact = (
        _KIMI_SHIM_PROLOGUE
        + """
export DADAIA_HOOK_EVENT="PostCompact"
export DADAIA_RUNTIME="kimi-code"
printf '%s' "$payload" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.ctx_inject 2>/dev/null || true
exit 0
"""
    )
    doctor_expired = (
        _KIMI_SHIM_PROLOGUE
        + f"""
"$PYTHON_BIN" -B -m dadaia_workspace {REAPER_ARGS} 2>/dev/null || true
exit 0
"""
    )
    return {
        "dadaia-kimi-pre-gate.sh": pre_gate,
        "dadaia-kimi-post-gate.sh": post_gate,
        "dadaia-kimi-ctx-inject.sh": ctx_inject,
        "dadaia-kimi-post-compact.sh": post_compact,
        "dadaia-kimi-doctor-expired.sh": doctor_expired,
    }


def kimi_hooks_block(home: Path) -> str:
    """Return the managed ``[[hooks]]`` TOML block for ``<home>/config.toml``.

    The block is self-contained between the :data:`KIMI_BLOCK_BEGIN` /
    :data:`KIMI_BLOCK_END` markers so the installer can replace-or-append it
    idempotently. Commands point at the shims under ``<home>/hooks/`` (POSIX paths).
    """
    hooks_dir = (home / "hooks").as_posix()
    rules: list[str] = []
    for shim, event, matcher, timeout in _KIMI_HOOK_RULES:
        lines = ["[[hooks]]", f'event = "{event}"']
        if matcher is not None:
            lines.append(f'matcher = "{matcher}"')
        lines.append(f'command = "{hooks_dir}/{shim}"')
        lines.append(f"timeout = {timeout}")
        rules.append("\n".join(lines))
    return f"{KIMI_BLOCK_BEGIN}\n" + "\n\n".join(rules) + f"\n{KIMI_BLOCK_END}\n"


def upsert_kimi_hooks_block(existing: str, block: str) -> str:
    """Return *existing* config.toml text with the managed kimi block replaced or appended.

    Pure text transform (the caller owns file IO): when both markers are present and
    ordered, the span between them (inclusive) is swapped for *block*; otherwise the
    block is appended at end of file — TOML allows extending the ``hooks`` array-of-tables from a later
    position. Content outside the markers is preserved byte-for-byte.
    """
    begin = existing.find(KIMI_BLOCK_BEGIN)
    end = existing.find(KIMI_BLOCK_END)
    if begin != -1 and end != -1 and begin < end:
        end += len(KIMI_BLOCK_END)
        # Swallow one trailing newline after the end marker so the splice is stable.
        if existing[end : end + 1] == "\n":
            end += 1
        return existing[:begin] + block + existing[end:]
    sep = "" if not existing or existing.endswith("\n") else "\n"
    glue = "" if not existing else "\n"
    return f"{existing}{sep}{glue}{block}"
