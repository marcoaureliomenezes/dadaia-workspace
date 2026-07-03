---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: "9-core + 3-plugin agent topology; two dispatchers; coordinator+sub-agent architecture; phase ownership; SDD step-0 read order; Layer-2 personas."
summary: Defines the public default 9-core agent topology with coordinator+sub-agent
  architecture (constitution §9), dispatcher-purity (only PM and project-auditor dispatch),
  per-agent phase ownership and lease relationships (constitution §14 + §7), the SDD
  step-0 read order and memory-format law, ADDITIVE vs MUTATING activity classes, and
  the Layer-2 persona surface.
tags:
- orchestration
- agents
- workflows
- dispatch
token_estimate: 1700
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

`dadaia-workspace` orchestrates specialist agents through SDD-aware workflows and
project-manager coordinator logic. The public default topology is generic and safe for
all consumers; project-specific, game-specific, data-vendor-specific, or private
agents belong in optional packs or local overlays.

## Usage flow

The public default has **9 core agents** in the coordinator + sub-agent architecture
defined by constitution §9:

```mermaid
graph TD
  OP["Operator"] --> PM["project-manager<br/>(dispatcher · holds the 1 MUTATING lease)"]
  OP --> PA["project-auditor<br/>(dispatcher · audit fan-out · ADDITIVE)"]
  PM --> PE["product-engineer<br/>(curator: SPEC/PLAN/TASKS/CLOSURE + memory)"]
  PM --> SE["software-engineer<br/>(code + tests)"]
  PM -. "review checkpoints" .-> QA["qa-engineer → commit gate"]
  PM -. .-> SEC["security-reviewer → push gate"]
  PM -. .-> CR["code-reviewer → PR gate"]
  PA --> QA
  PA --> SEC
  PA --> CR
  PA --> SA["software-architect<br/>(anti-slop review · ADDITIVE)"]
  PA --> AI["ai-engineer<br/>(public AI-entity surface)"]
  subgraph Plugins["plugin stubs (not in core roster — no behavior until pack installed)"]
    FE["frontend-engineer"]
    DS["design-specialist"]
    DV["devops-engineer"]
  end
  classDef disp fill:#1f6feb,color:#fff,stroke:#1f6feb;
  classDef plug fill:#30363d,color:#8b949e,stroke:#30363d,stroke-dasharray:3 3;
  class PM,PA disp;
  class FE,DS,DV plug;
```

Only the two dispatchers (solid `-->`) invoke the Agent tool; review specialists are
ADDITIVE workers reachable by either dispatcher (dashed `-.->`). Workers never dispatch
workers.

**Dispatchers (only 2 may dispatch through the active harness's delegation primitive — constitution §9):**
- `project-manager` — lease coordinator; holds the single MUTATING lease through
  phases 5→6→8; dispatches product-engineer and software-engineer as sub-agents.
- `project-auditor` — audit fan-out dispatcher; dispatches audit workers (ADDITIVE).

**Curator (1):**
- `product-engineer` — owns SPEC/PLAN/TASKS/CLOSURE and memory updates; runs as
  PM sub-agent; no independent lease acquire.

**Leaf specialists (6 core):**
- `software-engineer` — implementation (production code + tests); PM sub-agent.
- `qa-engineer` — review → commit gate (ADDITIVE evidence; votes).
- `security-reviewer` — review → push gate (ADDITIVE evidence; votes).
- `code-reviewer` — review → PR gate (ADDITIVE evidence; votes).
- `ai-engineer` — owns `dadaia_workspace/public/**` AI-entity surface.
- `software-architect` — architectural review; feeds findings into phases 4/5 (ADDITIVE).

**Plugins (not in core roster):** `frontend-engineer`, `design-specialist` (plugin
`frontend-design`); `devops-engineer` (plugin `devops`).

### Dispatcher purity (constitution §9)

Only `project-manager` and `project-auditor` may dispatch sub-agents via the Agent tool.
All other personas are workers — they reply only to their dispatcher and never invoke
another agent. A worker that perceives a need for another agent's work surfaces it to its
dispatcher; it never spawns the agent itself. Worker→worker dispatch is a structural
impossibility and keeps the dispatch topology auditable.

### Coordinator + sub-agent architecture

`project-manager` is the lease coordinator for a release. When a release enters its
MUTATING span (phase 5), PM acquires ONE lease and holds it through definition →
implementation → review-closure. `product-engineer` and `software-engineer` run as
PM sub-agents under that single lease. They never independently bind a session, so
there is no session handoff and no second lock.

### Phase ownership (constitution §14 + §7)

| Agent | Phase | Activity class | Lease relationship |
|-------|-------|----------------|--------------------|
| project-manager | 1–2, coordinates all MUTATING phases | ADDITIVE (backlog/bugs); MUTATING coordinator | holds + coordinates + releases the release lease |
| project-auditor | 4 (audit) | ADDITIVE | no lease |
| product-engineer | 5 + 8 (definition, closure) | MUTATING | PM sub-agent; no independent acquire |
| software-engineer | 6 (implementation) | MUTATING | PM sub-agent; no independent acquire |
| qa-engineer | 7 gate → commit | ADDITIVE evidence; votes | no lease |
| security-reviewer | 7 gate → push | ADDITIVE evidence; votes | no lease |
| code-reviewer | 7 gate → PR | ADDITIVE evidence; votes | no lease |
| ai-engineer | surface owner (`dadaia_workspace/public/**`) | MUTATING under PM lease during releases; own short lease for ad-hoc surface fixes | PM sub-agent when part of a release; own short MUTATING lease outside release spans (gate still enforces at-most-one-holder) |
| software-architect | feeds findings into phases 4/5 | ADDITIVE | no lease |

### SDD step-0 read order

For any implementation, review, or report that depends on product context:

1. Resolve the active Spec Context via `DADAIA_CONTEXT`, state, or
   `dadaia context show --json`.
2. Read `specs/constitution.md`.
3. Read `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, and
   `specs/memory/product/index.md` or `catalog.json`.
4. Pull the 1-3 relevant `specs/memory/product/<slug>.md` atoms.
5. Read `specs/releases/ACTIVE.md`.
6. Read the active release `SPEC.md`, `PLAN.md`, and `TASKS.md` according to phase.

**Memory-format law:** Markdown is the memory source. `specs/memory/**/*.html`,
`.yaml`, and `.yml` are legacy/generated formats and must not be written as product
memory.

### Layer-2 personas — the codex/pi equivalent of a Claude sub-agent

The 9-core roster above is the **Claude Layer-1** sub-agent surface. The **persona** is its
**Layer-2 counterpart**: a harness-universal role mandate that governs a codex/pi worker
inside the `dadaia lifecycle` workflow engine, the way a Claude sub-agent persona governs a
Layer-1 dispatch. Personas ship as `dadaia_workspace/public/personas/<role>.md` — **8 files,
one per non-PM role** (`software-engineer`, `product-engineer`, `qa-engineer`,
`security-reviewer`, `code-reviewer`, `software-architect`, `ai-engineer`,
`project-auditor`) — each a Markdown body with YAML frontmatter carrying the 5 required keys
`{id, role, summary, source_agent, harness_universal}`. `PersonaLoader`
(`features/lifecycle/personas/loader.py`) loads + validates them. Load-bearing: a persona
has **no `model` and no `tier`** — a Layer-2 worker's model is a per-workflow-**step**
binding (`--step-model` / the governed `dadaia_catalog` step), not a persona attribute. The
persona body is **injected into a workflow step's prompt as the operative role directive**.
See [[architecture]] "Two-layer agentic model" for the loader/dataclass detail.

### ADDITIVE vs MUTATING activity classes

| Class | Phases | Lease |
|-------|--------|-------|
| ADDITIVE | Backlog def, bug filing, research, audit, review gates | None — concurrent |
| MUTATING | Release definition (5), implementation (6), closure (8) | Single PM-held lease |

### Workflow surfaces (two distinct things)

- **Layer-1 reference workflow docs (2):** `release-ship` and `audit-fanout` ship in
  `public/workflows/` and project to `.claude/workflows/` / `.codex/workflows/`. They
  are documentation — they never auto-execute.
- **dadaia-workflows (7):** the executable Layer-2 lifecycle workflows live in the
  engine's governed catalog — see [[dadaia-workflows]] for the roster and which verbs
  are operator-invocable today.

Domain workflows such as game development, dashboard publication, or vendor-specific
data pipelines are not part of the default public install.

### Review checkpoint sequence (constitution §11)

During release definition (phase 5): qa-engineer first → software-architect optional
(parallel) → software-engineer last.

During implementation checkpoints (rc-N ship): qa → commit; security → push;
code-review → PR; product-engineer memory update → after code-review checkpoint.

Before TASKS approval: owning implementer, `qa-engineer`, `code-reviewer`, and
`security-reviewer` must agree tasks are implementable, testable, reviewable. Task `[x]`,
push, PR, merge, deploy, and memory updates are blocked until all required reviewers APPROVE.

### Runtime dispatch honesty

Claude Code dispatches via the native Agent tool; Codex custom agents are real
configured delegates under `.codex/agents/*.toml`, while workflow Markdown remains
documentation that never auto-executes. Per-harness capability truth (enforcement
surfaces, Ring-1/Ring-2 boundaries, worker transports) lives in [[harness-codex]] and
[[harness-pi]]. The dispatcher layer must report unsupported runtime capabilities
honestly instead of simulating success.

## Runtime state touched

`ai-engineer` owns public AI entities under
`dadaia_workspace/public/{agents,skills,rules,workflows,personas,lifecycle_fragments}/**`.
`software-engineer` owns implementation code and tests, not public agentic assets.
`product-engineer` owns specs and memory according to SDD phase.

The SDD gate enforces **path-class × lease × memory-phase × mode** only. It does
**not** validate write-allowlists, task markers, or `Aprovado` status — the RULE-D
allowlist check was removed in 0.1.7 rc-3 (no harness can assert persona identity to a
hook). Write-allowlists, `[-]` task reservation, and `Aprovado` status are agent/PM
**discipline**, not gate mechanism (workspace-protocol §6). Reports are emitted under
`.dadaia/reports/<context>/<agent>/`
with machine-readable handoff sidecars. Agent↔agent handoffs go to
`.dadaia/handoff/<context>/`. Audit results go to `specs/audits/<ts>-<session_id_8chars>/`
(committed Markdown — constitution §11).

`ai-engineer` model assignment: `claude-opus-4-8` (synthesis-heavy harness-mastery workload).

`ai-engineer` exclusive skills (restricted by `harness-skill-scope` rule):
`ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering`.

Shared literacy skill (all agents): `harness-primitives`.

Public rules inventory (8): `workspace-protocol`, `tmp-file-guardrail`,
`plugin-scope`, `dadaia-workspace-dev-guardrail`, `harness-skill-scope`,
`backlog-ownership`, `bug-registration-guardrail`, `release-governance`.
