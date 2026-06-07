---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: "9-core + 3-plugin agent topology; two dispatchers (PM + project-auditor); coordinator+sub-agent architecture; 2 workflows; dispatcher purity."
summary: Defines the public default 9-core agent topology with coordinator+sub-agent
  architecture (constitution §9), dispatcher-purity (only PM and project-auditor dispatch),
  ADDITIVE vs MUTATING activity classes, and the minimal 2-workflow set.
tags:
- orchestration
- agents
- workflows
- dispatch
agent_tier: self-pull
token_estimate: 865
last_updated: '2026-06-07'
release_origin: v0.2.2
---

## Propósito

`dadaia-workspace` orchestrates specialist agents through SDD-aware workflows and
project-manager coordinator logic. The public default topology is generic and safe for
all consumers; project-specific, game-specific, data-vendor-specific, or private
agents belong in optional packs or local overlays.

## Fluxo de uso

The public default has **9 core agents** in the coordinator + sub-agent architecture
defined by constitution §9:

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

### ADDITIVE vs MUTATING activity classes

| Class | Phases | Lease |
|-------|--------|-------|
| ADDITIVE | Backlog def, bug filing, research, audit, review gates | None — concurrent |
| MUTATING | Release definition (5), implementation (6), closure (8) | Single PM-held lease |

### Workflows (2 default)

Two workflows ship by default (stale workflows deleted in v0.1.9):

- `release-ship` — the deploy gate sequence (deterministic, non-judgment steps).
- `audit-fanout` — fan-out pattern for project-auditor audit dispatches.

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

Claude Code uses Claude-native agent/tool semantics with real Agent tool dispatch.
Codex custom agents are real configured delegates projected under `.codex/agents/*.toml`;
they are not simulated with fake tool names or stale tool-discovery promises. Codex
workflow Markdown is still documentation: it does not auto-execute, schedule fan-out, or
turn a workflow file into a runtime primitive by itself. OpenCode uses its own agent and
plugin projection. The dispatcher layer must report unsupported runtime capabilities
honestly instead of simulating success.

## Estado runtime tocado

`ai-engineer` owns public AI entities under
`dadaia_workspace/public/{agents,skills,rules,workflows,commands,hooks}/**`.
`software-engineer` owns implementation code and tests, not public agentic assets.
`product-engineer` owns specs and memory according to SDD phase.

The SDD gate validates write allowlists, task ownership, active context, and
memory phase rules. Reports are emitted under `.dadaia/reports/<context>/<agent>/`
with machine-readable handoff sidecars. Agent↔agent handoffs go to
`.dadaia/handoff/<context>/`. Audit results go to `specs/audits/<ts>-<session_id_8chars>/`
(committed Markdown — constitution §11).

`ai-engineer` model assignment: `claude-opus-4-8` (synthesis-heavy harness-mastery workload).

`ai-engineer` exclusive skills (restricted by `harness-skill-scope` rule):
`ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering`.

Shared literacy skill (all agents): `harness-primitives`.

Public rules inventory (5): `workspace-protocol`, `tmp-file-guardrail`,
`plugin-scope`, `dadaia-workspace-dev-guardrail`, `harness-skill-scope`.
