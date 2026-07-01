---
slug: agent-sdd-alignment
title: agent-sdd-alignment
category: product
tldr: 9-core agents aligned to constitution §7 lifecycle phases; sub-agent model; dispatcher purity; Markdown memory protocol.
summary: Defines how the 9-core agent roster maps to lifecycle phases (constitution §7
  and §14), the sub-agent model (PE + software-engineer under PM lease), dispatcher
  purity (only PM and project-auditor dispatch), and SDD memory protocol.
tags:
- sdd
- agents
- memory
- release-lifecycle
agent_tier: self-pull
token_estimate: 690
last_updated: '2026-07-01'
release_origin: v0.1.47
---

## Propósito

Public agentic assets are SDD-aware. The 9-core agent roster (constitution §14) maps
to lifecycle phases (constitution §7). Agents resolve the active Spec Context, load
constitution and Markdown memory, read the active release artifacts, and only write
within approved task scope.

## Agent roster and phase ownership (constitution §14 + §7)

| Agent | Phase | Activity class | Lease relationship |
|-------|-------|----------------|--------------------|
| project-manager | 1–2, coordinates all MUTATING phases | ADDITIVE (backlog/bugs); MUTATING coordinator | holds + coordinates + releases the release lease |
| project-auditor | 4 (audit) | ADDITIVE | no lease |
| product-engineer | 5 + 8 (definition, closure) | MUTATING | PM sub-agent; no independent acquire |
| software-engineer | 6 (implementation) | MUTATING | PM sub-agent; no independent acquire |
| qa-engineer | 7 gate → commit | ADDITIVE evidence; votes | no lease |
| security-reviewer | 7 gate → push | ADDITIVE evidence; votes | no lease |
| code-reviewer | 7 gate → PR | ADDITIVE evidence; votes | no lease |
| ai-engineer | surface owner (`dadaia_workspace/public/**`) | MUTATING under PM lease during releases; own short lease for ad-hoc surface fixes | PM sub-agent when part of a release; own short MUTATING lease outside release spans (gate blocks overlap with PM lease) |
| software-architect | feeds findings into phases 4/5 | ADDITIVE | no lease |

Plugins (not in core roster): `frontend-engineer`, `design-specialist`, `devops-engineer`.

## Sub-agent model (constitution §9)

`product-engineer` and `software-engineer` run as PM sub-agents under the single
coordinator lease. They never independently bind a session or acquire a lease. The
"writer role" moves between sub-agents by PM dispatching the next one; the lease never
changes hands. This makes deadlocks between sessions in different lifecycle phases
structurally impossible.

## Dispatcher purity (constitution §9)

Only `project-manager` (lifecycle coordination) and `project-auditor` (audit fan-out)
may dispatch sub-agents through the active harness's real delegation primitive. All other
personas are workers — they reply only to their dispatcher and never invoke another agent.
Worker→worker dispatch is a structural impossibility.

## Fluxo de uso

For any implementation, review, or report that depends on product context:

1. Resolve the active Spec Context via `DADAIA_CONTEXT`, state, or
   `dadaia context show --json`.
2. Read `specs/constitution.md`.
3. Read `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, and
   `specs/memory/product/index.md` or `catalog.json`.
4. Pull the 1-3 relevant `specs/memory/product/<slug>.md` atoms.
5. Read `specs/releases/ACTIVE.md`.
6. Read the active release `SPEC.md`, `PLAN.md`, and `TASKS.md` according to phase.

Markdown is the memory source. `specs/memory/**/*.html`, `.yaml`, and `.yml`
are legacy/generated formats and must not be written as product memory.

Implementation requires approved `SPEC.md`, `PLAN.md`, `TASKS.md`, and one reserved
`[-]` task in `TASKS.md`. The SDD gate mechanically enforces only path-class × lease ×
phase × mode (memory writable in DEFINITION/CLOSURE; `_archive` read-only). Write
allowlists, `[-]` markers, and `Aprovado` status are agent/PM discipline — no hook can
verify persona identity ([[sdd-gate-v3]]).

## Estado runtime tocado

The same SDD rules apply to `dadaia_workspace/public/**`: public agents, skills,
rules, workflows, personas, lifecycle fragments, and AGENTS.md sources are product
behavior. Changes to that surface require release context and must remain generic,
public-safe, and runtime-accurate for Claude Code, Codex, and PI.

`product-engineer` may write `specs/memory/**` only in DEFINITION and CLOSURE phases
(constitution §13). No other agent may write memory atoms.
