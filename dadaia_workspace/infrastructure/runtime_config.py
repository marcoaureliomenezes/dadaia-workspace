"""Claude settings merge, Codex config and the Kimi user-level hook block.

The hook wiring itself is ``hook_wrappers.HOOK_DIALECTS``; these serialize and merge it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_agents_config_file_blocks,
)
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    HOOK_DIALECTS,
    hook_documents,
    wrapper_name,
)

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


def claude_hooks() -> dict[str, object]:
    """Claude's ``settings.json`` hook slice, rendered from ``HOOK_DIALECTS``."""
    return hook_documents(HARNESS_RECORDS["claude"])["settings.json"]


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
    canonical = claude_hooks()
    canonical_hooks = canonical["hooks"]
    assert isinstance(canonical_hooks, dict)
    env = {  # absolute caches (ADR 0080); the Playwright MCP output in its zone (ADR 0156)
        **workspace_layout.tool_cache_env(root),
        "PLAYWRIGHT_MCP_OUTPUT_DIR": str(root / ".dadaia" / "mcps" / "playwright"),
    }
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
    prior_env = existing.get("env")  # dadaia owns only its own keys
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


#: Kimi Code has no project-level config: its hooks are a managed block in the user-level
#: ``$KIMI_CODE_HOME/config.toml``; content outside these markers is never touched.
KIMI_BLOCK_BEGIN = (
    "# >>> dadaia-workspace kimi-code hooks (managed by dadaia public install — do not edit) >>>"
)
KIMI_BLOCK_END = "# <<< dadaia-workspace kimi-code hooks (managed) <<<"


def kimi_code_home(env: Mapping[str, str] | None = None) -> Path:
    """Resolve the Kimi Code data root: ``$KIMI_CODE_HOME`` or ``~/.kimi-code``."""
    source = os.environ if env is None else env
    override = (source.get("KIMI_CODE_HOME") or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".kimi-code"


def kimi_hooks_block(home: Path) -> str:
    """Return the managed ``[[hooks]]`` TOML block for ``<home>/config.toml``.

    The block is self-contained between the :data:`KIMI_BLOCK_BEGIN` /
    :data:`KIMI_BLOCK_END` markers so the installer can replace-or-append it
    idempotently. Commands point at the shims under ``<home>/hooks/`` (POSIX paths).
    """
    record = HARNESS_RECORDS["kimi-code"]
    rules: list[str] = []
    for event, lane, matcher in HOOK_DIALECTS[record.hooks].files[0].events:
        lines = ["[[hooks]]", f'event = "{event}"']
        if matcher is not None:
            lines.append(f'matcher = "{matcher}"')
        lines.append(f'command = "{(home / "hooks").as_posix()}/{wrapper_name(record, lane)}"')
        lines.append(f"timeout = {HOOK_DIALECTS[record.hooks].timeout(lane)}")
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
