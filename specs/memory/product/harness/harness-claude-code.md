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

## Purpose

Claude Code is the operator's interactive coding agent and the only harness with native
sub-agent dispatch (the Agent tool). The nine-agent roster runs inside it as sub-agents;
ordered work is carried by the SDD documents, not by any runtime.

## Usage flow

1. The operator launches `claude` at the workspace root. `CLAUDE.md` imports `AGENTS.md`,
   which imports `DADAIA.md` — Claude Code does not read `AGENTS.md` natively. That chain
   is the single load path, so the law is in context exactly once per session and this
   harness receives no rules-directory mirror of it ([[public-asset-distribution]]).
2. `dadaia context bind <ctx>` arms ctx-inject (`UserPromptSubmit`), which injects the
   bound context's tech-stack digest and feature catalog once per session. Claude Code
   exposes a native session id, so the bind record is this session's own (rung 2 of the
   resolution law) and the trigger is that record's `bound_at` against this session's
   sentinel; a concurrent session's bind never reaches it.
3. Writes pass the deterministic gate: PreToolUse `pre_gate` (matcher
   `Edit|Write|MultiEdit|NotebookEdit|Bash`), PostToolUse heartbeat/reconciler
   (match-all), plus the git chokepoints. The pre-gate emits a merged envelope —
   `hookSpecificOutput.permissionDecision` `deny`/`defer` is the operative contract, with
   the top-level `decision`/`reason` pair riding along for the Codex hooks and the Kimi
   shim. The gate never answers `permissionDecision: allow`, which would bypass the
   permission prompts.
4. `.claude/settings.json` registers `SessionStart` matchers `compact` and `clear` on
   ctx-inject, so the bootstrap re-emits after a compact or `/clear` and the sentinel
   restamps.
5. Coordinators dispatch role sub-agents from `.claude/agents/`; skills load on invocation.

## Differentiator

The strongest enforcement posture of any harness: deterministic hooks plus chokepoints,
native sub-agents, and first-message context injection.

## Runtime state touched

Projected by `dadaia public install --target claude`, all manifest-tracked and never
hand-edited: `.claude/agents/` (the nine core personas, rendered with the resolved
model/effort), `.claude/skills/` (22 skill folders, each a `SKILL.md` plus every disclosed
sibling), `.claude/settings.json` (hook registration). The root `CLAUDE.md` + `AGENTS.md`
pair is written by the guardrail installer.

A Claude-only workspace is `--target claude` plus the shared `--target agents` tree, with
no `.codex/` or `.kimi-code/`; `dadaia init --harness claude` scaffolds only that surface
and persists the profile ([[workspace-init]]).

## Dependencies

[[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]], [[agent-orchestration]].
