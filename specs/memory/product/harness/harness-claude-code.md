---
slug: harness-claude-code
title: harness-claude-code
tldr: Entry harness with native sub-agent dispatch; reads the root AGENTS.md map natively and reaches skills and personas through per-entry symlinks into .agents/.
summary: How Claude Code loads the workspace law, reaches the three dd- personas and the skills, binds a session, and which hook events carry the workspace's behaviours.
tags: [harness, claude-code, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/runtime_config.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Load path

- Claude Code is the harness with native sub-agent dispatch (the Agent tool): the main thread runs there and dispatches the three `dd-` personas as sub-agents ([[agent-orchestration]]).
- It reads the root `AGENTS.md` map natively at session start when no `CLAUDE.md` sits on or above the cwd; a scoped `AGENTS.md` attaches when a file in its directory is read ([[agentic-entities]]).
- The workspace ships no `CLAUDE.md` and `dadaia init` prints no settings advice — the root `AGENTS.md` is read natively; sessions launch at the workspace root.
- `.claude/skills/<name>` and `.claude/agents/<name>.md` are relative symlinks into `.agents/skills/` and `.agents/agents/`, with a hash-verified copy where `os.symlink` fails; `dadaia public doctor`'s `SYMLINK-TARGET-1` attests every entry ([[public-asset-distribution]]).
- Least privilege is rendered into each persona at install from its `activity_class`: `permissionMode` plus, for a read-only persona, `disallowedTools`.

## Hooks and binding

- `dadaia harness add claude` writes `.claude/settings.json` and the symlink set.
- The four hook behaviours ([[agentic-entities]]) are registered there: `PreToolUse` `dadaia_workspace.hooks.pre_gate` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`), a match-all `PostToolUse` `dadaia_workspace.hooks.sdd_post_gate` (the throttled reaper), `UserPromptSubmit` and `SessionStart` `dadaia_workspace.hooks.ctx_inject`, and the session-start reaper; the git chokepoints run beside them ([[sdd-gate-v3]]).
- `SessionStart` matchers `startup`, `resume`, `compact` and `clear` re-emit the bootstrap after a compact or `/clear` as well as at a new session.
- A block answers `hookSpecificOutput.permissionDecision: deny` with its reason, the top-level `decision: block`/`reason` pair riding along for other consumers; an allow carries no permission verdict, so the user's permission prompts are never bypassed.
- `dadaia context bind <ctx>` records the bind in this session's own record, keyed by Claude Code's native session id; ctx-inject then injects that context's tech-stack section and feature catalog once, and again after a re-bind — never the law, which the map already loads ([[context-management]]).

## Dependencies

[[agentic-entities]], [[agent-orchestration]], [[sdd-gate-v3]], [[context-management]], [[public-asset-distribution]].
