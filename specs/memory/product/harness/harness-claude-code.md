---
slug: harness-claude-code
title: Harness — Claude Code
category: product
tldr: Entry harness with native sub-agent dispatch; scaffold = CLAUDE.md bridge + .claude/ projection.
summary: Capability and scaffold truth for the Claude Code harness — what it can do,
  what dadaia projects for it, its enforcement posture, and what a Claude-only workspace
  installation contains.
tags:
- harness
- claude-code
- projection
- dispatch
last_updated: '2026-08-24'
release_origin: v0.3.0
---

## Purpose

Claude Code is the operator's interactive coding agent and the only harness with native
sub-agent dispatch (the Agent tool). The 9-agent roster runs entirely inside Claude Code
via sub-agents: coordinators dispatch role agents, and the ordered SDD flow is carried by
the specs documents rather than by any runtime. The `ClaudeSdkAdapter` remains importable
and unit-tested for programmatic SDK use.

## Usage flow

1. Operator launches `claude` at the workspace root; `CLAUDE.md` (`@AGENTS.md` bridge)
   loads the workspace law — Claude Code does not read `AGENTS.md` natively. That import
   chain is the **single** load path: because the root chain already resolves to the law,
   this harness receives no rules-directory mirror of it, so the whole law is in context
   exactly once per session rather than twice ([[public-asset-distribution]]).
2. `dadaia context bind <ctx>` → the ctx-inject hook (UserPromptSubmit) injects the
   bound context's tech-stack digest + feature catalog once per session. Claude Code
   exposes a native session id, so the bind record is this session's own (rung 2 of the
   resolution law) and the trigger is that record's `bound_at` against this session's
   sentinel — a concurrent session's bind never reaches this session's injection.
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
ad-hoc engineering. The harness of choice when the operator wants multi-agent fan-out.

## Differentiator

Strongest enforcement posture of any harness: deterministic hooks + chokepoints, native
sub-agents, first-message context injection.

## Runtime state touched

Scaffold projected by `dadaia public install --target claude` (all lib-originated,
manifest-tracked, never hand-edited): `.claude/agents/` (the 9 core personas),
`.claude/skills/` (21 skill **folders** — each a `SKILL.md` plus every sibling it discloses
its depth to), `.claude/settings.json` (hook registration). Root `CLAUDE.md` + `AGENTS.md` written by
the guardrail pair. A Claude-only workspace = `--target claude` (+ the shared
`--target agents` tree); no `.codex/` or `.kimi-code/` is required. This isolation is now
**enforced mechanically at init** — `dadaia init --harness claude` scaffolds only the
claude surface and persists the profile, so `public install`/`doctor` stay claude-scoped
([[workspace-init]]) — not merely documented.

## Dependencies

- [[tech-stack]] — the harness/runtime roster single source.
- [[sdd-gate-v3]] — the deterministic enforcement mechanism this harness participates in.
- [[public-asset-distribution]] — how the `.claude/` projection is staged and installed.
- [[agent-orchestration]] — the sub-agent topology that runs inside this harness.
