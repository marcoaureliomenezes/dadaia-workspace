"""Runtime configuration generators for Claude, Codex and Kimi Code projections.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  Each function takes explicit arguments instead of
``self``, so there are no circular imports.

T-018-17: hook commands are emitted as ``<python> -B -m dadaia_workspace.hooks.<name>``
using the venv-aware ``_python_bin()`` helper (Windows-safe fallbacks: Scripts/python.exe
→ sys.executable → bare python). The ``.sh`` scripts are superseded, not appended.

v0.2.8 (kimi-code): Kimi Code has no project-level config file — hooks register only in
the user-level ``$KIMI_CODE_HOME/config.toml``. The kimi generators therefore emit a
managed, marker-delimited ``[[hooks]]`` TOML block plus workspace-agnostic POSIX shims
that resolve the nearest ``.dadaia/.venv/bin/python`` from the hook cwd at runtime and
delegate to the same shared Python hook modules the other harnesses use.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
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
    """Return a bytecode-suppressed Python module command for *workspace_root*."""
    return f"{_python_bin(workspace_root)} -B -m {module}"


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
# PostToolUse so session/presence heartbeat fires after every tool, including Bash.
_CLAUDE_MATCH_ALL = "*"


#: The marker that identifies a hook entry as dadaia-owned. Every command this module
#: generates invokes a ``dadaia_workspace.hooks.*`` module, so ownership is decidable from
#: the emitted content alone — no side-car state, and an operator's own entry in the SAME
#: event is never mistaken for ours.
_DADAIA_HOOK_MARKER = "dadaia_workspace.hooks."


def _is_dadaia_hook_entry(entry: object) -> bool:
    """True iff *entry* is a hook entry this module generated."""
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(h, dict) and _DADAIA_HOOK_MARKER in str(h.get("command", "")) for h in hooks
    )


def merge_claude_settings(
    existing: dict[str, object] | None, workspace_root: Path
) -> dict[str, object]:
    """Fold dadaia's hook wiring into an operator's ``.claude/settings.json``.

    ``settings.json`` is the file Claude Code documents for the operator's own
    ``permissions``, ``model``, ``env``, ``statusLine`` and custom hooks — it is NOT a
    dadaia-owned artifact. Writing it wholesale erased all of that silently, printing
    ``[ok]`` (bug ``claude-install-destroys-operator-settings``). dadaia owns exactly the
    hook entries whose command invokes ``dadaia_workspace.hooks.*``:

    * top-level keys other than ``hooks`` are preserved untouched;
    * hook EVENTS dadaia does not wire are preserved untouched;
    * inside an event dadaia does wire, the operator's own entries are preserved and only
      dadaia-owned entries are replaced by the canonical wiring.

    This is the same ownership discipline :func:`upsert_kimi_hooks_block` applies to the
    kimi config; the claude path had a naive whole-file writer instead.
    """
    canonical = claude_settings(workspace_root)
    canonical_hooks = canonical["hooks"]
    assert isinstance(canonical_hooks, dict)
    if not existing:
        return canonical

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
    return merged


def foreign_claude_hook_commands(
    settings: dict[str, object], canonical: dict[str, object]
) -> list[str]:
    """Commands in dadaia-WIRED hook events that dadaia did not generate.

    Preserving the operator's own hooks is correct; going blind to them is not. A foreign
    command inside ``PreToolUse`` runs on every gated write, so it is exactly where a local
    injection would sit. This lists them so the doctor can surface them — the file belongs
    to the operator, so the finding is advisory, never drift.
    """
    canonical_hooks = canonical.get("hooks")
    wired = set(canonical_hooks) if isinstance(canonical_hooks, dict) else set()
    hooks_raw = settings.get("hooks")
    hooks = hooks_raw if isinstance(hooks_raw, dict) else {}
    found: list[str] = []
    for event in sorted(wired):
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if _is_dadaia_hook_entry(entry) or not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []) if isinstance(entry.get("hooks"), list) else []:
                if isinstance(hook, dict) and hook.get("command"):
                    found.append(f"{event}:{hook['command']}")
    return found


def dadaia_owned_claude_settings(settings: dict[str, object]) -> dict[str, object]:
    """Project *settings* down to the dadaia-owned hook wiring, for drift comparison.

    The doctor must compare what dadaia owns, not the whole file — otherwise an operator
    who legitimately adds ``permissions`` reads ``[drift]`` forever, and the documented
    remedy for drift (re-run install) is exactly what used to destroy their config.
    """
    hooks_raw = settings.get("hooks")
    hooks = hooks_raw if isinstance(hooks_raw, dict) else {}
    owned: dict[str, object] = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        mine = [e for e in entries if _is_dadaia_hook_entry(e)]
        if mine:
            owned[event] = mine
    return {"hooks": owned}


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
            # Bug claude-compact-reinjection-missing: a compact erases the injected
            # bootstrap and /clear wipes the context; ctx_inject re-emits it at the event
            # (Claude Code adds SessionStart stdout back to context) and restamps the
            # sentinel. Matchers are the exact documented source names — startup/resume/
            # fork stay on the bind-driven UserPromptSubmit path (FR-W2). Parity with the
            # kimi-code PostCompact shim (v0.2.8) and the codex SessionStart wrapper.
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "command": _hook_cmd(
                                workspace_root, "dadaia_workspace.hooks.ctx_inject"
                            ),
                            "type": "command",
                        }
                    ],
                    "matcher": "compact",
                },
                {
                    "hooks": [
                        {
                            "command": _hook_cmd(
                                workspace_root, "dadaia_workspace.hooks.ctx_inject"
                            ),
                            "type": "command",
                        }
                    ],
                    "matcher": "clear",
                },
            ],
        }
    }


def codex_config(agentic_dir: Path) -> str:
    """Return the .codex/config.toml content for *agentic_dir*.

    W1-2: the former ``approved_commands = [...]`` array and ``[skills] paths`` table are no
    longer emitted — both were live-verified invalid/inert in codex-cli. Real command policy
    lives in the Starlark ``.codex/rules`` file (``_render_codex_command_policy_rules``); Codex
    discovers skills from ``.codex/skills``/``.agents/skills`` natively, not via a config key.
    The generated config now carries only the header plus one ``[agents."<name>"]``
    ``config_file`` block per canonical agent.
    """
    lines = ['# Generated by "dadaia public install --target codex".\n', "\n"]
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
                            "command": _codex_hook_wrapper_command("codex-pre-gate"),
                            "statusMessage": "Checking dadaia PreToolUse gate",
                        }
                    ],
                },
            ],
            # Session/presence heartbeat fires after every tool. Codex's canonical
            # match-all is an omitted matcher, mirroring Claude's explicit "*".
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

#: The four kimi hook rules: (shim filename, event, matcher-or-None, timeout seconds).
_KIMI_HOOK_RULES: tuple[tuple[str, str, str | None, int], ...] = (
    ("dadaia-kimi-pre-gate.sh", "PreToolUse", _KIMI_WRITE_MATCHER, 10),
    ("dadaia-kimi-post-gate.sh", "PostToolUse", None, 10),
    ("dadaia-kimi-ctx-inject.sh", "UserPromptSubmit", None, 10),
    ("dadaia-kimi-post-compact.sh", "PostCompact", _KIMI_COMPACT_MATCHER, 10),
)

#: Shared shim prologue: resolve the nearest dadaia workspace venv python by walking up
#: from the hook cwd; exit 0 (fail-open) when no dadaia workspace is found.
_KIMI_SHIM_PROLOGUE = """\
#!/usr/bin/env sh
# Generated by "dadaia public install --target kimi-code" — do not edit in place.
# dadaia-workspace kimi-code hook shim: resolve the nearest dadaia workspace from the
# hook cwd and delegate to the shared Python hook module. Fail-open everywhere: any
# resolution or runtime error exits 0 so a hook problem never blocks the operator.
set -u

_dir=$PWD
PYTHON_BIN=""
while [ "$_dir" != "/" ]; do
  if [ -x "$_dir/.dadaia/.venv/bin/python" ]; then
    PYTHON_BIN="$_dir/.dadaia/.venv/bin/python"
    break
  fi
  _dir=$(dirname "$_dir")
done
# Root itself may hold the venv (workspace mounted at /).
if [ -z "$PYTHON_BIN" ] && [ -x "/.dadaia/.venv/bin/python" ]; then
  PYTHON_BIN="/.dadaia/.venv/bin/python"
fi
if [ -z "$PYTHON_BIN" ]; then
  exit 0
fi

payload=$(cat)
"""


def kimi_code_home(env: Mapping[str, str] | None = None) -> Path:
    """Resolve the Kimi Code data root: ``$KIMI_CODE_HOME`` or ``~/.kimi-code``."""
    source = os.environ if env is None else env
    override = (source.get("KIMI_CODE_HOME") or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".kimi-code"


def kimi_hook_shims() -> dict[str, str]:
    """Return the four kimi hook shim bodies as ``{filename: POSIX sh content}``.

    - pre-gate: forwards the payload to ``hooks.pre_gate`` and translates the dadaia
      envelope to the Kimi protocol — ``"decision": "block"`` ⇒ reason on stderr +
      exit 2; anything else ⇒ exit 0.
    - post-gate: presence heartbeat via ``hooks.sdd_post_gate``; output discarded.
    - ctx-inject: ``hooks.ctx_inject``; stdout passes through (Kimi appends
      ``UserPromptSubmit`` stdout to the context).
    - post-compact: ``hooks.ctx_inject`` with ``DADAIA_HOOK_EVENT=PostCompact`` — writes
      the compact-epoch marker consumed by the next ``UserPromptSubmit`` AND re-emits
      the bootstrap on stdout (observable-contract posture; Kimi discards PostCompact
      stdout, so the deterministic re-injection still lands at the next prompt).
    """
    pre_gate = (
        _KIMI_SHIM_PROLOGUE
        + """
export DADAIA_RUNTIME="kimi-code"
out=$(printf '%s' "$payload" | "$PYTHON_BIN" -B -m dadaia_workspace.hooks.pre_gate 2>/dev/null) || exit 0
case $out in
  *'"decision": "block"'*)
    reason=$(printf '%s' "$out" | sed -n 's/.*"reason": "\\(.*\\)".*/\\1/p' | head -n 1)
    [ -n "$reason" ] || reason="blocked by the dadaia SDD gate"
    printf '%s\\n' "$reason" >&2
    exit 2
    ;;
esac
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
    return {
        "dadaia-kimi-pre-gate.sh": pre_gate,
        "dadaia-kimi-post-gate.sh": post_gate,
        "dadaia-kimi-ctx-inject.sh": ctx_inject,
        "dadaia-kimi-post-compact.sh": post_compact,
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


def _strip_unmanaged_kimi_rules(existing: str) -> str:
    """Remove every ``[[hooks]]`` table referencing the dadaia-kimi shims OUTSIDE the markers.

    Bug kimi-install-duplicates-hooks-on-legacy-config: a pre-v0.2.8 install wrote the
    four dadaia rules WITHOUT the managed-block markers, and a naive append then
    double-registered every event (4 → 8 rules). Any un-marked table whose body names
    ``dadaia-kimi-`` is provably dadaia-managed (a legacy install or a botched
    duplicate — the reserved shim prefix is never operator content), so it is stripped
    before the managed block is appended/replaced. Tables INSIDE the marker span are
    owned by the block itself; non-dadaia tables are operator content, preserved
    byte-for-byte. Line-oriented by design (the upsert is a pure text transform); a
    ``[[hooks]]`` line inside a TOML string literal is a documented non-goal for the
    config shapes this file manages.
    """
    begin = existing.find(KIMI_BLOCK_BEGIN)
    end = existing.find(KIMI_BLOCK_END)
    span = (begin, end + len(KIMI_BLOCK_END)) if begin != -1 and end != -1 and begin < end else None
    lines = existing.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    pos = 0  # char offset of lines[i] in the original text
    while i < len(lines):
        if lines[i].strip() == "[[hooks]]":
            table_end = pos + len(lines[i])
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("[["):
                table_end += len(lines[j])
                j += 1
            table = "".join(lines[i:j])
            # A table is inside the managed span when it STARTS within it (the END
            # marker line is absorbed into the last table's extent, so an end-position
            # check would misclassify that table — and the marker with it).
            inside_span = span is not None and span[0] <= pos < span[1]
            if "dadaia-kimi-" not in table or inside_span:
                out.extend(lines[i:j])
            i = j
            pos = table_end
        else:
            out.append(lines[i])
            pos += len(lines[i])
            i += 1
    return "".join(out)


def upsert_kimi_hooks_block(existing: str, block: str) -> str:
    """Return *existing* config.toml text with the managed kimi block replaced or appended.

    Pure text transform (the caller owns file IO). Legacy un-marked dadaia rules are
    ADOPTED first (:func:`_strip_unmanaged_kimi_rules` — never duplicated). Then
    replace-or-append semantics: when both markers are present and ordered, the span
    between them (inclusive) is swapped for *block*; otherwise the block is appended
    at end of file — TOML allows extending the ``hooks`` array-of-tables from a later
    position. Content outside the markers is preserved byte-for-byte.
    """
    existing = _strip_unmanaged_kimi_rules(existing)
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
