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
agent_tier: self-pull
token_estimate: 1560
last_updated: '2026-07-01'
release_origin: v0.1.47
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
5. Multi-harness support at two layers: three entry harnesses and the Layer-2 worker
   runtimes driven inside the lifecycle engine — the concrete roster is single-sourced
   in [[tech-stack]] §Agent runtimes.
6. Reports, handoffs, audits, memory, and a panel.
7. A strict anti-slop operating model.

## Fluxo de uso

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

## Usuários

1. **O operador** — o humano que lança um harness de entrada, binda contextos,
   aprova specs e decide ship/iterate. Único ator com autoridade de trust (`.pi/`),
   de push e de amendment da constitution.
2. **Agentes Layer-1** — o roster de 9 core agents rodando dentro do harness de
   entrada (sub-agents no Claude Code; personas projetadas em Codex/PI).
3. **Workers Layer-2** — os workers bounded que os dadaia-workflows dirigem por step
   ([[dadaia-workflows]]).
4. **Consumers** — workspaces gerados que instalam a superfície pública via
   `dadaia public install` e nunca editam projeções in-place.

## Mapa de capacidades

- **Contexto**: Spec Context Projects + bind→inject ([[spec-context-project]],
  [[context-management]]).
- **Enforcement**: gate PreToolUse + chokepoints git + doctors ([[sdd-gate-v3]],
  [[specs-doctor]], [[workspace-doctor]]).
- **Governança de trabalho**: bugs JSONL + backlog consistente + releases
  ([[sdd-bug-backlog-governance]]); workflows Layer-2 ([[dadaia-workflows]],
  [[lifecycle-foundation]]).
- **Distribuição**: asset chain público multi-harness ([[public-asset-distribution]],
  [[multi-platform-parity]]).
- **Observabilidade**: panel + telemetria + reports/handoffs ([[panel]],
  [[agent-monitoring]], [[agent-comms]]).
- **Plataforma**: init, portabilidade, cross-OS, dev servers ([[workspace-init]],
  [[workspace-portability]], [[cross-platform-portability]], [[server-registry]]).

O **catálogo ordenado de features** é gerado: `specs/memory/product/index.md` +
`catalog.json` (regenerados por `dadaia memory catalog generate` a partir do
frontmatter dos atoms — o `index.md` é um TOC gerado e qualquer edição manual nele é
sobrescrita; o conteúdo §13 de visão/usuários/capacidades/limites vive AQUI).

## Limites conhecidos

- Apenas 4 verbos de workflow são operator-invocáveis hoje; `audit`/`research`/
  `bug_report` têm corpos reais sem verbo ([[dadaia-workflows]]).
- Enforcement determinístico cobre file-write tools + chokepoints git; writes Bash
  arbitrários entre chokepoints são disciplina + reconciler advisory
  ([[sdd-gate-v3]]).
- Os contratos import-linter existem mas não rodam em CI (backlog
  `import-boundary-enforcement`).
- O panel é uma ferramenta dev loopback-only sem autenticação; não expor além da
  máquina ([[panel]]).
- Plugin packs (frontend-design, devops) ainda não são distribuídos.

## Estado runtime tocado

- `docs/01_medium_codex.md` — normative source; read-only (operator-authored).
- `specs/constitution.md` — operationalizes this vision into binding law.
- `specs/memory/architecture.md` — layer rules derived from the vision's layering pillar.
- `specs/memory/tech-stack.md` — approved toolchain consistent with the vision's public
  defaults law.
- `specs/memory/quality-assurance.md` — test architecture aligned with the anti-slop stance.

## Dependências

- [[spec-context-project]] — the keystone concept whose definition this vision originates.
- [[agent-orchestration]] — the nine-core agent roster this vision specifies.
- [[sdd-gate-v3]] — the mechanical enforcement of the SDD pillar.
- [[public-asset-distribution]] — the multi-harness projection pipeline this vision requires.
- Constitution §0 names this vision (`docs/01_medium_codex.md`) as the document the
  constitution operationalizes — that citation is the canonical link between the two.
