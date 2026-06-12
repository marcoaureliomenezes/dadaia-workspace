# 04. Hooks, Rules, and Config

Hooks, Rules, and config are the strongest Codex customization surfaces because
they affect execution, not just prose. They are also the easiest place to create a
security or trust bug.

## Hooks

Hooks run commands at Codex lifecycle events. Current events include session start,
prompt submission, tool use, compaction, subagent start/stop, and stop.

Useful events for dadaia:

| Event | dadaia Use |
|---|---|
| `SessionStart` | Inject workspace memory/context once per session |
| `PreToolUse` | Block unauthorized file writes through SDD/root hooks |
| `PostToolUse` | Refresh lease heartbeat |
| `SubagentStart` / `SubagentStop` | Future bookkeeping for explicit delegation |
| `Stop` | Final validation or handoff checks |

Multiple matching hooks can run. They may run concurrently, so each hook must be
idempotent and must not assume it is the only guardian of an event. Project-local
hooks load only in trusted projects and non-managed hooks require review/trust.

### The verified hook contract (codex-cli 0.139.0)

These facts were verified against a live binary, not just the docs:

- The PreToolUse `matcher` is a regex string. Anchored forms like
  `^(apply_patch|Edit|Write)$` are valid — the official examples include
  `^apply_patch$`. `Edit` and `Write` are matcher aliases for `apply_patch`;
  the hook input still reports `tool_name: "apply_patch"`.
- Three deny mechanisms work: the preferred
  `hookSpecificOutput.permissionDecision = "deny"` shape; the older
  `{"decision": "block", "reason": ...}` envelope with exit 0, which is
  explicitly accepted (live-verified blocking a write interactively); and exit
  code 2 with the reason on stderr.
- Hook `command` strings run through a shell, so env-prefixed commands
  (`VAR=value python -m ...`), `$(...)` substitution, and `~` expansion all work.
- The real apply_patch payload carries no `file_path` key. The patch text lives
  in `tool_input.command`, so any path-based policy must parse the
  `*** Add/Update/Delete File:` headers — and must handle all of them, not just
  the first one in a multi-file patch.

### Hooks fire only in interactive sessions (the critical limitation)

On codex-cli 0.139.0, command hooks fire in the interactive `codex` TUI: all four
wired events (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse) run, and a
blocking PreToolUse hook really does stop the write. Under headless `codex exec`
the hooks never run. Every documented configuration form was tried — project
`.codex/hooks.json`, inline `[hooks]` in trusted project config, user-layer
`hooks.json`, match-all matchers — with a trusted project, the hooks feature flag
enabled, and `--dangerously-bypass-hook-trust`. Zero hook executions.

The consequence is blunt: deterministic gate enforcement on Codex exists only in
interactive sessions today. On the `codex exec` automation path the SDD gate,
root whitelist, context injection, and heartbeat do not execute — that path runs
on agent discipline plus after-the-fact doctor checks until the upstream defect
changes (tracked as the bug `codex-exec-hooks-do-not-fire-headless`).

## Codex Rules

Codex Rules are Starlark command policy files under a `rules/` directory next to an
active config layer. They control commands, especially commands outside the sandbox.

The documented unit is `prefix_rule(...)`:

```python
prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Publishing requires an explicit operator decision.",
)
```

Decision order is restrictive: `forbidden` beats `prompt`, and `prompt` beats
`allow`. Shell wrappers are split only when the script is simple enough to parse
safely; advanced shell features are treated conservatively.

Use Rules for command policy only. Do not put workspace workflow prose in
`.codex/rules/`. Markdown "rules" in dadaia public assets are guidance; `.rules`
files are executable Codex policy.

## Config Layers and Trust

Codex config lives in layers. User config is normally `~/.codex/config.toml`.
Project config can live in `.codex/config.toml`, but it loads only when the
project is trusted.

Project-local config must not own host-sensitive settings:

- provider credentials;
- base URLs;
- telemetry exporters;
- personal model preferences;
- notification commands.

Those belong to user/admin config. Project-local config can define project custom
agents, hooks, rules, and other repo-scoped behavior when the project is trusted.

Three config-key facts are worth knowing precisely (verified on 0.139.0):

- `approved_commands` is not a config key. `--strict-config` rejects it as an
  unknown field; otherwise it is silently ignored. Command approval belongs to
  Rules and the `approval_policy` / `[tools]` keys, never a flat allow-list.
- `[skills] paths` is also invalid. Repo skill discovery of `.agents/skills` is
  native and automatic; the real config surface is `skills.config`, an array of
  per-skill `{path, enabled}` override objects for enabling and disabling.
- `agents.<name>.config_file` is a real, documented key. Registering
  `.codex/agents/*.toml` role files through it is valid and supported.

## dadaia Projection Rules

The generated `.codex/` projection should satisfy these invariants:

- `.codex/hooks.json` points to workspace Python hooks, not stale shell scripts.
- `.codex/rules/*.rules` uses documented Codex Rules syntax.
- `.codex/config.toml` registers custom-agent TOML files via
  `agents.<name>.config_file` and emits no invalid keys (`approved_commands`,
  `[skills] paths`).
- `.codex/agents/*.toml` contains role-specific instructions and conservative
  sandbox defaults.
- No provider/auth/telemetry settings are emitted from public project assets.

When a behavior must be mechanically enforced, prefer a hook or Rule — and
remember that on Codex a hook enforces only in interactive sessions today. When
it is a role contract, put it in the custom agent and support it with sandbox
defaults.
