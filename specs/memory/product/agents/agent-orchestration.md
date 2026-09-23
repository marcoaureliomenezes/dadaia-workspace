---
slug: agent-orchestration
title: agent-orchestration
tldr: Three dd- personas dispatched by the main thread alone; ordered work carried by the SDD documents and handoffs, never a runtime; concurrent sessions, no locks.
summary: Who owns which artifact, who may dispatch, how a stage's sequencing is evidenced by the documents themselves, and how each persona receives its model, effort and least-privilege tool set at install.
tags: [orchestration, agents, dispatch, sdd]
sources:
  - dadaia_workspace/public/agents/**
  - dadaia_workspace/core/agent_model_templates.py
  - dadaia_workspace/core/model_registry.py
  - dadaia_workspace/public/skills/dd-manager-orchestration/**
---

## Roster

The main thread — the operator's own session — coordinates: intake, the grill, dispatch, gates. It is the only dispatcher; the three personas in `dadaia_workspace/public/agents/*.md` are leaf workers that return a handoff and never spawn agents ([[agentic-entities]]).

| Persona | Owns |
|---|---|
| `dd-product-engineer` | backlog curation, the SPEC of a candidate (from the main thread's grill handoff), product-memory reconciliation at closure |
| `dd-software-engineer` | PLAN and TASKS, production code and its tests, inside the task's declared write set |
| `dd-code-reviewer` | the three-axis review plus six lenses — architecture, security, QA, product, audit, AI surface — read-only and verdict-only |

- A request outside a persona's scope is answered with a `[SCOPE ERROR]` block naming the owner; the main thread re-dispatches.
- `dd-manager-orchestration` is the main thread's reference: the Input Contract block that opens every dispatch prompt, the decision-authority table, the escalation triggers and the forbidden actions.

## Behaviour

- No runtime drives agents through steps; the main thread classifies the demand (feature or bug) and dispatches the owning persona per artifact.
- Sequencing evidence is the artifacts themselves: `_RELEASE.json`'s `phase`, `**Status:** Approved` markers, the `[ ] [-] [x]` task markers and handoffs ([[agent-comms]]).
- An agent grounds itself with `dd-spec-navigator` (context, constitution, [[ARCHITECTURE]], the catalog, the relevant atoms, the live release), reserves a task `[ ] -> [-]`, validates, marks `[x]`, and emits a handoff; a record change goes through its governance script, never a hand edit ([[release-lifecycle]]).
- Concurrent sessions are allowed and never locked: no agent acquires, holds or releases a lock; races surface through git.
- The reviewer's `APPROVED` is required before a candidate's PR; a `REJECTED` keeps the task `[-]` and blocks the PR, and every verdict states the bug-surface delta from the bug ledger ([[QUALITY]]).
- A merge further requires CI green and a `dd-code-reviewer` APPROVED verdict, security lens included, on the PR head ([[sdd-gate-v3]]).

## Models and privilege

- Persona sources carry no model; `public install` resolves `(model, effort)` per persona from one of three templates — `balanced` (default), `max-quality`, `economy` — with a per-agent overlay taking precedence, all through the one resolver in `dadaia_workspace/core/agent_model_templates.py`.
- The resolver refuses a model unknown to `dadaia_workspace/core/model_registry.py` and a Fable-family model for `dd-code-reviewer`.
- Least privilege derives from each persona's `activity_class` at install: Claude `permissionMode`/`disallowedTools`, Codex `sandbox_mode` ([[harness-claude-code]], [[harness-codex]]).

## Dependencies

[[agentic-entities]], [[agent-comms]], [[sdd-gate-v3]], [[release-lifecycle]], [[harness-claude-code]], [[harness-codex]].
