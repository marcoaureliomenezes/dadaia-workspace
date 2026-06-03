---
slug: agent-sdd-alignment
title: agent-sdd-alignment
category: product
tldr: Public agents, skills, workflows, hooks, and templates follow release-lifecycle SDD and Markdown memory.
summary: Defines how agentic assets resolve active specs, load Markdown memory, respect task gates, and avoid legacy feature-folder or HTML-memory assumptions.
tags:
- sdd
- agents
- memory
- release-lifecycle
agent_tier: self-pull
token_estimate: 285
last_updated: '2026-06-03'
release_origin: public-agentic-hygiene-codex-readiness
---

## Propósito

Public agentic assets are SDD-aware. Agents resolve the active Spec Context,
load constitution and Markdown memory, read the active release artifacts, and
only write within approved task scope.

## Fluxo de uso

For any implementation, review, or report that depends on product context:

1. Resolve the active Spec Context via `DADAIA_CONTEXT`, state, or
   `dadaia context show --json`.
2. Read `specs/constitution.md`.
3. Read `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, and
   `specs/memory/product/index.md` or `catalog.json`.
4. Pull the 1-3 relevant `specs/memory/product/<slug>.md` atoms.
5. Read `specs/releases/ACTIVE.md`.
6. Read the active release `SPEC.md`, `PLAN.md`, and `TASKS.md` according to
   phase.

Markdown is the memory source. `specs/memory/**/*.html`, `.yaml`, and `.yml`
are legacy/generated formats and must not be written as product memory.

Implementation requires approved `SPEC.md`, `PLAN.md`, `TASKS.md`, and one
reserved `[-]` task in `TASKS.md`. The SDD gate enforces memory phase rules,
archive read-only rules, write allowlists, active context, and task ownership.

Agents may draft missing SDD artifacts or report diagnostics without production
edits. They must not edit SPEC/PLAN/TASKS to justify code already written.

## Estado runtime tocado

The same SDD rules apply to `dadaia_workspace/public/**`: public agents, skills,
rules, workflows, hooks, and AGENTS.md sources are product behavior. Changes to
that surface require release context and must remain generic, public-safe, and
runtime-accurate for Claude Code, Codex, and OpenCode.
