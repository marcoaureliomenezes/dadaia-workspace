---
slug: harness-claude-code
title: Harness — Claude Code
category: product
tldr: Entry harness with native sub-agent dispatch; its scaffold is the CLAUDE.md bridge plus the .claude/ projection.
summary: Claude Code is the only harness with native sub-agent dispatch, loading the law through the CLAUDE.md import chain and running the nine-agent roster under the Python hooks.
tags: [harness, claude-code, projection, dispatch]
---

## Load path and gates

- Claude Code is the only harness with native sub-agent dispatch (the Agent tool), and the nine-agent roster runs inside it as sub-agents.
- `CLAUDE.md` imports `AGENTS.md`, which imports `DADAIA.md`; that chain is the single load path, so the law is in context exactly once per session and this harness receives no rules-directory mirror.
- `dadaia context bind <ctx>` arms ctx-inject (`UserPromptSubmit`), which injects the bound context's tech-stack digest and feature catalog once per session.
- Claude Code exposes a native session id, so the bind record is this session's own at rung 2 and a concurrent session's bind never reaches it ([[context-management]]).
- `.claude/settings.json` registers `SessionStart` matchers `compact`, `clear`, `startup` and `resume` — the bootstrap re-emits after a compact or `/clear`, and a NEW session receives it at the event itself instead of waiting for its first prompt.
- Writes pass PreToolUse `pre_gate` (matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`), a match-all PostToolUse heartbeat/reconciler, and the git chokepoints ([[sdd-gate-v3]]).
- The pre-gate emits a merged envelope — `hookSpecificOutput.permissionDecision` `deny`/`defer` is the operative contract, the top-level `decision`/`reason` pair riding along for the Codex hooks and the Kimi shim.
- It never answers `permissionDecision: allow`, which would bypass the permission prompts.
- `dadaia public install --target claude` projects `.claude/agents/` (the nine personas rendered with resolved model/effort), `.claude/skills/` and `.claude/settings.json`, manifest-tracked and never hand-edited ([[public-asset-distribution]]).

## Dependencies

[[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]], [[agent-orchestration]].
