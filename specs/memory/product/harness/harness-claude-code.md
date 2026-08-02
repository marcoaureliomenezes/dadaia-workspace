---
slug: harness-claude-code
title: Harness — Claude Code
category: product
tldr: Layer-1-only entry harness; richest deterministic enforcement; scaffold = CLAUDE.md bridge + .claude/ projection (agents, skills, rules, hooks).
summary: Capability and scaffold truth for the Claude Code harness — what it can do at
  each agentic layer, what dadaia projects for it, its enforcement posture, and what a
  Claude-only workspace installation contains.
tags:
- harness
- claude-code
- layer-1
- projection
token_estimate: 520
last_updated: '2026-07-22'
release_origin: v0.1.58
---

## Purpose

Claude Code is a **Layer-1-only** harness: the operator's interactive coding agent, and
the only harness with native sub-agent dispatch (the Agent tool). By law it is **never a
dispatch target for another harness** — each harness runs its own personas, so Claude
operator's subscription, so `claude` is rejected as a `--harness` value (the
`ClaudeSdkAdapter` remains importable and unit-tested for Layer-1 SDK use only). When
the operator works Claude-only, the 9-agent roster runs entirely inside Claude Code via
sub-agents, derived from the core persona definitions.

## Usage flow

1. Operator launches `claude` at the workspace root; `CLAUDE.md` (`@AGENTS.md` bridge)
   loads the workspace law — Claude Code does not read `AGENTS.md` natively.
2. `dadaia context bind <ctx>` → the ctx-inject hook (UserPromptSubmit) injects the
   bound context's tech-stack digest + feature catalog once per session; the bind-epoch
   marker is pid-attributed, so a concurrent session's bind never steals this session's
   injection.
3. Work proceeds under the deterministic gate: PreToolUse `pre_gate` (matcher
   `Edit|Write|MultiEdit|NotebookEdit|Bash`), PostToolUse heartbeat/reconciler
   (match-all), plus the git chokepoints. The pre-gate emits the MERGED envelope —
   `hookSpecificOutput.permissionDecision` `deny`/`defer` is the operative documented
   Claude Code contract; the top-level `decision`/`reason` pair rides along for codex
   hooks and the kimi shim (bug claude-pre-gate-envelope-contract; the gate never
   answers `permissionDecision: allow`, which would bypass the permission prompts).
4. Compaction survival: `.claude/settings.json` registers `SessionStart` matchers
   `compact` and `clear` on ctx-inject — after a compact (or /clear) the bootstrap
   re-emits at the event and the sentinel restamps, so the next prompt stays silent
   (bug claude-compact-reinjection-missing; parity with kimi's PostCompact shim and
   the codex SessionStart wrapper).
5. Coordinators (project-manager, project-auditor) dispatch role sub-agents from
   `.claude/agents/`; skills load on invocation.

## Typical trigger

Any interactive session: releases coordinated by PM sub-agents, audits, reviews,
ad-hoc engineering. Also the harness of choice when the operator wants multi-agent
fan-out without the lifecycle engine.

## Differentiator

Strongest Layer-1 posture: deterministic hooks + chokepoints, native sub-agents,
first-message context injection. The trade-off is that heavy
batch/workflow execution is delegated to pi/codex workers.

## Runtime state touched

Scaffold projected by `dadaia public install --target claude` (all lib-originated,
manifest-tracked, never hand-edited): `.claude/agents/` (12 = 9 core + 3 plugin stubs),
`.claude/skills/` (19), `.claude/rules/` (9), `.claude/workflows/` (2, reference),
`.claude/settings.json` (hook registration). Root `CLAUDE.md` + `AGENTS.md` written by
the guardrail pair. A Claude-only workspace = `--target claude` (+ the shared
`--target agents` tree); no `.codex/` or `.pi/` is required. This isolation is now
**enforced mechanically at init** — `dadaia init --harness claude` scaffolds only the
claude surface and persists the profile, so `public install`/`doctor` stay claude-scoped
([[workspace-init]]) — not merely documented.

## Dependencies

- [[tech-stack]] — the harness/runtime roster single source.
- [[sdd-gate-v3]] — the deterministic enforcement mechanism this harness participates in.
- [[public-asset-distribution]] — how the `.claude/` projection is staged and installed.
- [[agent-orchestration]] — the sub-agent topology that runs inside this harness.
