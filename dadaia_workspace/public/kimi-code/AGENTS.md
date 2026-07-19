# .kimi-code/AGENTS.md — Kimi Code harness notes (dadaia-workspace)

> Generated projection from `dadaia_workspace/public/kimi-code/AGENTS.md` by
> `dadaia public install`. Do not edit in place — edit the source and re-install.

You are in a dadaia-workspace SDD workspace, running under the Kimi Code CLI — a
first-class Layer-1 entry harness. The workspace-root `AGENTS.md` is the global
contract; scoped `AGENTS.md` files deeper in the tree take precedence. This file
covers only the kimi-specific surface.

## Hook wiring (deterministic)

Kimi Code has no project-level config file, so the workspace hooks register once in
the user-level `$KIMI_CODE_HOME/config.toml` (default `~/.kimi-code/config.toml`)
inside a marker-delimited managed block written by
`dadaia public install --target kimi-code`. Four shims under
`$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` walk up from the hook cwd to this
workspace's `.dadaia/.venv/bin/python` and delegate to the same Python hook modules
the other harnesses use:

| Event | Shim | Deterministic action |
|---|---|---|
| `PreToolUse` (`Edit\|Write\|Bash`) | `dadaia-kimi-pre-gate.sh` | merged gate: root-whitelist → venv-guard → SDD gate (blocks via exit 2) |
| `PostToolUse` | `dadaia-kimi-post-gate.sh` | session/presence heartbeat |
| `UserPromptSubmit` | `dadaia-kimi-ctx-inject.sh` | context injection after `dadaia context bind` |
| `PostCompact` | `dadaia-kimi-post-compact.sh` | marks compaction and re-emits the bootstrap on stdout (observable; Kimi discards it) — the next prompt re-injects context |

The shims fail open (exit 0) outside dadaia workspaces and never store
workspace-absolute paths. Re-install or verify the wiring with
`dadaia public install --target kimi-code` / `dadaia public doctor`.

## Operating notes

- Use `.dadaia/.venv/bin/dadaia` (or `.dadaia/.venv/bin/python`) for every dadaia
  CLI call — the venv-guard hook enforces it.
- Bind the session before SDD work: `.dadaia/.venv/bin/dadaia context bind <ctx>`.
- Universal skills live in `.agents/skills/` — invoke with `/skill:<name>`.
- Sub-agents: Kimi built-ins (`coder`, `explore`, `plan`) only — dadaia projects no
  custom sub-agents for kimi-code. Layer-2 workflow workers stay codex/pi.
