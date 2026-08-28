---
slug: harness-claude-code
title: Harness — Claude Code
category: product
tldr: Entry harness with native sub-agent dispatch; its scaffold is the CLAUDE.md bridge plus the .claude/ projection.
summary: Claude Code is the only harness with native sub-agent dispatch; it loads the law through the `CLAUDE.md` → `AGENTS.md` → `DADAIA.md` import chain and runs the nine-agent roster as sub-agents under the Python hooks.
tags:
- harness
- claude-code
- projection
- dispatch
---

## Load path and gates

Claude Code is the operator's interactive coding agent and the only harness with native sub-agent
dispatch (the Agent tool); the nine-agent roster runs inside it as sub-agents, with ordered work
carried by the SDD documents rather than any runtime. It has the strongest enforcement posture of
any harness: deterministic hooks plus chokepoints, native sub-agents, first-message injection.

`CLAUDE.md` imports `AGENTS.md`, which imports `DADAIA.md` — Claude Code does not read `AGENTS.md`
natively. That chain is the single load path, so the law is in context exactly once per session and
this harness receives no rules-directory mirror ([[public-asset-distribution]]).
`dadaia context bind <ctx>` arms ctx-inject (`UserPromptSubmit`), which injects the bound context's
tech-stack digest and feature catalog once per session; Claude Code exposes a native session id, so
the bind record is this session's own (rung 2) and a concurrent session's bind never reaches it.
`.claude/settings.json` also registers `SessionStart` matchers `compact` and `clear`, so the
bootstrap re-emits after a compact or `/clear`.

Writes pass the deterministic gate: PreToolUse `pre_gate` (matcher
`Edit|Write|MultiEdit|NotebookEdit|Bash`), PostToolUse heartbeat/reconciler (match-all), plus the
git chokepoints. The pre-gate emits a merged envelope — `hookSpecificOutput.permissionDecision`
`deny`/`defer` is the operative contract, with the top-level `decision`/`reason` pair riding along
for the Codex hooks and the Kimi shim — and never answers `permissionDecision: allow`, which would
bypass the permission prompts.

Projected by `dadaia public install --target claude`, manifest-tracked and never hand-edited:
`.claude/agents/` (the nine core personas, rendered with the resolved model/effort),
`.claude/skills/` (22 skill folders) and `.claude/settings.json`; the root `CLAUDE.md` + `AGENTS.md`
pair comes from the guardrail installer ([[workspace-init]]).

## Dependencies

[[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]], [[agent-orchestration]].
