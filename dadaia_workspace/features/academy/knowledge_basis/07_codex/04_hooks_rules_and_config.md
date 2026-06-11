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
agents, project skills paths, hooks, rules, and other repo-scoped behavior when the
project is trusted.

## dadaia Projection Rules

The generated `.codex/` projection should satisfy these invariants:

- `.codex/hooks.json` points to workspace Python hooks, not stale shell scripts.
- `.codex/rules/*.rules` uses documented Codex Rules syntax.
- `.codex/config.toml` references custom-agent TOML files and skill paths.
- `.codex/agents/*.toml` contains role-specific instructions and conservative
  sandbox defaults.
- No provider/auth/telemetry settings are emitted from public project assets.

When a behavior must be mechanically enforced, prefer a hook or Rule. When it is a
role contract, put it in the custom agent and support it with sandbox defaults.
