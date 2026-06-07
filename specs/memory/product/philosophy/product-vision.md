---
slug: product-vision
title: product-vision
category: product
tldr: Identity, pillars, lifecycle, concurrency model, agent roster, and anti-slop stance — the normative shape of dadaia-workspace from docs/01_medium_codex.md.
summary: >-
  Current-truth distillation of the normative Product Vision (docs/01_medium_codex.md).
  Covers the workspace identity (what it is and is not), the five design pillars,
  the canonical scaffold and operational layout, the development lifecycle phases,
  the concurrency model, the nine-core agent model, and the anti-slop operating stance.
  Constitution §0 operationalizes this vision into binding law; this atom cites,
  does not duplicate, constitution sections.
tags:
  - vision
  - philosophy
  - identity
  - lifecycle
  - anti-slop
agent_tier: self-pull
token_estimate: 950
last_updated: '2026-06-07'
release_origin: v0.2.1
---

## Propósito

`dadaia-workspace` is a Python library that creates an **AI-native development workspace
for multi-project, multi-agent, Spec-Driven Development**. Its product is not one repo and
not one assistant. Its product is the workspace-level context engineering that turns generic
AI coding agents into a disciplined software team able to work safely, repeatedly, and in
parallel across many projects.

The normative human-readable vision lives at `docs/01_medium_codex.md`. The constitution
(`specs/constitution.md`) operationalizes that vision into binding law. This atom distills
the vision's current-truth shape so agents can ground themselves without parsing the full
prose document.

The workspace combines seven elements:

1. A canonical scaffold.
2. Spec-Driven Development (SDD).
3. Spec Context Projects (the keystone concept — see [[spec-context-project]]).
4. Multi-agent roles, skills, hooks, rules, and scoped `AGENTS.md`.
5. Multi-harness support: Claude Code, Codex, and OpenCode.
6. Reports, handoffs, audits, memory, and a panel.
7. A strict anti-slop operating model.

## Fluxo de uso

1. Operator creates or activates a Spec Context Project via `dadaia context create` or
   `dadaia context bind`.
2. Workspace scaffolds the specs pattern under `repos/<ctx>/specs/` if absent.
3. Binding a session injects `constitution.md` + memory index into the AI harness context
   (lazy feature-atom pull on demand).
4. SDD gate enforces that no production write proceeds without an approved release and a
   reserved task marker.
5. Agents work within their lifecycle phase (constitution §7), coordinated by
   `project-manager`, without colliding across Spec Context Projects.
6. Review gates (qa → security → code-review) produce handoff JSON in `.dadaia/handoff/`
   and optionally HTML reports in `.dadaia/reports/`.
7. Closure: `product-engineer` updates memory atoms to reflect the current product state,
   archives the release, and the cycle restarts.

## Trigger típico

When an operator starts working on a new project or resumes an existing one: bind a context,
the workspace orients the agents, and work begins under SDD discipline. Also read by any
agent grounding itself in workspace philosophy before a cross-cutting decision.

## Diferencial

Without this workspace, a generic agent fleet has no persistent product memory, no
lifecycle enforcement, no collision protection across projects, and no scoped context
injection. Each session starts blind. dadaia-workspace closes all four gaps simultaneously:
memory atoms persist truth, the SDD gate enforces sequence, the single-TTL-lease model
prevents MUTATING collisions, and scoped `AGENTS.md` files orient agents near the files
they govern. The result is a professional AI-native development environment that stays
simple at the surface and strict where correctness matters.

### Five design pillars

1. **Multi-harness development**: one canonical source (`dadaia_workspace/public/`)
   projects agents, skills, rules, hooks, workflows, and instructions into Claude Code,
   Codex, OpenCode, and generic agent surfaces.
2. **SDD as the operating model**: releases are defined before implementation through
   `SPEC.md`, `PLAN.md`, `TASKS.md`, and closed through `CLOSURE.md`. No bypass language
   overrides the gate.
3. **Spec Context Project as the keystone**: each session works inside one bound project
   context with the right specs and memory — see [[spec-context-project]].
4. **Context engineering by scope**: rules live where they matter; root instructions stay
   short; detailed behavior is discovered near the files it governs (scoped `AGENTS.md`).
5. **Anti-slop by design**: the workspace protects roots, repos, specs, memory, tests,
   reports, and agentic assets from uncontrolled generated output through mechanical gates,
   naming conventions, and the no-slop constitution law (§12).

### Concurrency model (summary)

ADDITIVE phases (backlog, bugs, research, audit, review) run in parallel — no lease
required. MUTATING phases (release definition, implementation, closure) serialize under
exactly one TTL-lease per Spec Context Project, coordinated by `project-manager`.
Constitution §8 is the normative contract; this is a summary only.

### Agent model (summary)

Nine core agents cover the full lifecycle. Each is a generic AI implementation specialized
only in its dadaia-workspace SDD role — no project-domain knowledge in public defaults.
Three plugin agents (frontend-engineer, design-specialist, devops-engineer) are available
via `dadaia plugin install`. Constitution §14 is the normative roster; this is a summary
only.

### What dadaia-workspace must not become

1. A loose folder full of generated files.
2. A repo-root dumping ground.
3. A set of verbose global prompts.
4. A collection of private, domain-specific agents.
5. A system where agents bypass specs because a request sounds urgent.
6. A system where backlog, bugs, releases, and memory duplicate each other.
7. A system where parallel agent sessions can corrupt the same project.

## Estado runtime tocado

- `docs/01_medium_codex.md` — normative source; read-only (operator-authored).
- `specs/constitution.md` — operationalizes this vision into binding law.
- `specs/memory/architecture.md` — layer rules derived from the vision's layering pillar.
- `specs/memory/tech-stack.md` — approved toolchain consistent with the vision's public
  defaults law.
- `specs/memory/quality-assurance.md` — test architecture aligned with the anti-slop stance.

## Dependências

- [[spec-context-project]] — the keystone concept whose definition this vision originates.
- [[agent-sdd-alignment]] — the nine-core agent roster this vision specifies.
- [[sdd-gate-v3]] — the mechanical enforcement of the SDD pillar.
- [[public-asset-distribution]] — the multi-harness projection pipeline this vision requires.
- Constitution §0 names this vision (`docs/01_medium_codex.md`) as the document the
  constitution operationalizes — that citation is the canonical link between the two.
