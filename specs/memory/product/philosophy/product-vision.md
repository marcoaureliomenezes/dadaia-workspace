---
slug: product-vision
title: product-vision
category: product
tldr: Identity, pillars, users, capability map, known limits, and anti-slop stance — the normative §13 shape of dadaia-workspace (docs/01_medium_codex.md).
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
token_estimate: 1700
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

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
5. Multi-harness support at two layers: three entry harnesses and the Layer-2 worker
   runtimes driven inside the lifecycle engine — the concrete roster is single-sourced
   in [[tech-stack]] §Agent runtimes.
6. Reports, handoffs, audits, memory, and a panel.
7. A strict anti-slop operating model.

## Usage flow

1. Operator creates or activates a Spec Context Project via `dadaia context create` or
   `dadaia context bind`.
2. Workspace scaffolds the specs pattern under `repos/<ctx>/specs/` if absent.
3. Binding a session injects the context's tech-stack digest + feature-catalog digest
   into the AI harness context (lazy feature-atom pull on demand; the constitution is
   read from disk, not injected).
4. SDD gate enforces that no production write proceeds without an approved release and a
   reserved task marker.
5. Agents work within their lifecycle phase (constitution §7), coordinated by
   `project-manager`, without colliding across Spec Context Projects.
6. Review gates (qa → security → code-review) produce handoff JSON in `.dadaia/handoff/`
   and optionally HTML reports in `.dadaia/reports/`.
7. Closure: `product-engineer` updates memory atoms to reflect the current product state,
   archives the release, and the cycle restarts.

## Typical trigger

When an operator starts working on a new project or resumes an existing one: bind a context,
the workspace orients the agents, and work begins under SDD discipline. Also read by any
agent grounding itself in workspace philosophy before a cross-cutting decision.

## Differentiator

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
   Codex, PI, and generic agent surfaces.
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
Three plugin agents (frontend-engineer, design-specialist, devops-engineer) ship as
behavior-less stubs until their plugin packs are distributed (no install command exists
yet — backlog `plugin-packs-and-install-command`). Constitution §14 is the normative
roster; this is a summary only.

### Two-layer agentic model (summary)

The same agent fleet runs at two layers, and "harness" means a different thing at each.
**Layer 1** is the entry harness the operator launches in the terminal — `claude`,
`codex`, or `pi` — governed by `AGENTS.md` read up-tree plus the projected
`.X/` asset trees. **Layer 2** is the bounded agent workers that `dadaia lifecycle` drives
per step behind `AgentRuntimePort` — selectable workers are pi and codex (plus a FAKE
runtime for offline/test); Claude Code is Layer-1-only by law. PI is an officially
supported third harness at both layers. The concrete runtime roster is single-sourced in
[[tech-stack]] §Agent runtimes; [[architecture]] and [[lifecycle-foundation]] carry the
normative detail; constitution §0 names the two layers.

### What dadaia-workspace must not become

1. A loose folder full of generated files.
2. A repo-root dumping ground.
3. A set of verbose global prompts.
4. A collection of private, domain-specific agents.
5. A system where agents bypass specs because a request sounds urgent.
6. A system where backlog, bugs, releases, and memory duplicate each other.
7. A system where parallel agent sessions can corrupt the same project.

## Users

1. **The operator** — the human who launches an entry harness, binds contexts,
   approves specs, and decides ship/iterate. The only actor with trust authority
   (`.pi/`), push authority, and constitution-amendment authority.
2. **Layer-1 agents** — the 9-core agent roster running inside the entry harness
   (sub-agents in Claude Code; projected personas in Codex/PI).
3. **Layer-2 workers** — the bounded workers the dadaia-workflows drive per step
   ([[dadaia-workflows]]).
4. **Consumers** — generated workspaces that install the public surface via
   `dadaia public install` and never edit projections in-place.

## Capability map

- **Context**: Spec Context Projects + bind→inject ([[spec-context-project]],
  [[context-management]]).
- **Enforcement**: PreToolUse gate + git chokepoints + doctors ([[sdd-gate-v3]],
  [[specs-doctor]], [[workspace-doctor]]).
- **Work governance**: JSONL bugs + consistent backlog + releases
  ([[sdd-bug-backlog-governance]]); Layer-2 workflows ([[dadaia-workflows]],
  [[lifecycle-foundation]]).
- **Distribution**: multi-harness public asset chain ([[public-asset-distribution]],
  [[multi-platform-parity]]).
- **Observability**: panel + telemetry + reports/handoffs ([[panel]],
  [[agent-monitoring]], [[agent-comms]]).
- **Platform**: init, portability, cross-OS, dev servers ([[workspace-init]],
  [[workspace-portability]], [[cross-platform-portability]], [[server-registry]]).

The **ordered feature catalog** is generated: `specs/memory/product/index.md` +
`catalog.json` (regenerated by `dadaia memory catalog generate` from the atoms'
frontmatter — `index.md` is a generated TOC and any manual edit to it is
overwritten; the §13 vision/users/capabilities/limits content lives HERE).

## Known limits

- Only 4 workflow verbs are operator-invocable today; `audit`/`research`/
  `bug_report` have real bodies with no verb ([[dadaia-workflows]]).
- Deterministic enforcement covers file-write tools + git chokepoints; arbitrary
  Bash writes between chokepoints are discipline + the advisory reconciler
  ([[sdd-gate-v3]]).
- The import-linter contracts exist but do not run in CI (backlog
  `import-boundary-enforcement`).
- The panel is a loopback-only dev tool with no authentication; never expose it
  beyond the machine ([[panel]]).
- Plugin packs (frontend-design, devops) are not yet distributed.

## Runtime state touched

- `docs/01_medium_codex.md` — normative source; read-only (operator-authored).
- `specs/constitution.md` — operationalizes this vision into binding law.
- `specs/memory/architecture.md` — layer rules derived from the vision's layering pillar.
- `specs/memory/tech-stack.md` — approved toolchain consistent with the vision's public
  defaults law.
- `specs/memory/quality-assurance.md` — test architecture aligned with the anti-slop stance.

## Dependencies

- [[spec-context-project]] — the keystone concept whose definition this vision originates.
- [[agent-orchestration]] — the nine-core agent roster this vision specifies.
- [[sdd-gate-v3]] — the mechanical enforcement of the SDD pillar.
- [[public-asset-distribution]] — the multi-harness projection pipeline this vision requires.
- Constitution §0 names this vision (`docs/01_medium_codex.md`) as the document the
  constitution operationalizes — that citation is the canonical link between the two.
