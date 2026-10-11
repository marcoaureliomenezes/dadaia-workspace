---
slug: agent-orchestration
title: agent-orchestration
tldr: Five dd- personas are leaf workers dispatched by the main thread; SDD documents, worktrees and handoffs carry the work, never an orchestration runtime.
summary: The role boundary, task-level dispatch by the job file's who column, evidence flow and install-time model and privilege resolution for the product, senior and junior engineering, research and review personas.
tags: [orchestration, agents, dispatch, sdd]
sources:
  - dadaia_workspace/public/agents/**
  - dadaia_workspace/core/model_registry.py
  - dadaia_workspace/public/skills/dd-manager-orchestration/**
---

## Roster and authority

The main thread is the operator's session and the only dispatcher. It owns intake, the grill, routing, gates and operator decisions. The five projected personas are leaf workers:

| Persona | Owns |
|---|---|
| `dd-product-engineer` | backlog, candidate SPEC, closure product memory and release summary |
| `dd-sw-engineer-sr` | as-is review, PLAN, job files (fills `who`), new behaviour, design choices, root causes and the RED test of a new contract |
| `dd-sw-engineer-jr` | a task whose AC and `W:` fully state the outcome; escalates any open design choice to the main thread |
| `dd-researcher` | read-only research; every finding a `path:line` or a URL; writes no file |
| `dd-code-reviewer` | independent three-axis review and the architecture, security, QA, product, audit and AI-surface lenses |

- A persona reports out-of-scope work with `[SCOPE ERROR]`; the main thread re-routes it.
- Only the operator accepts an ADR. Role agents never write `accepted` or `ruling`.
- The reviewer is verdict-only and writes its own sha-bound handoff through `verdict.py`.

## Dispatch and evidence

- The main thread dispatches by the job file's `who` column: `sr` to `dd-sw-engineer-sr`, `jr` to `dd-sw-engineer-jr`, `pe` and `cr` to the owning persona; research goes to `dd-researcher`. The `define` tree's reviewer judges each `who` against the shape rule.
- A REJECTED verdict whose finding names a `jr` task re-dispatches that task to `dd-sw-engineer-sr`.
- The task is the implementation dispatch unit. A behavior begins with a RED-test dispatch and continues in a fresh implementation dispatch that cannot touch test paths ([[worktrees]]).
- Jobs and tasks may run concurrently only where the approved PLAN and exact write sets permit it. Git exposes races; no agent acquires a lock.
- No runtime advances the lifecycle. `_RELEASE.json`, approved definition documents, job files, worktrees, commits and handoffs are the evidence ([[release-lifecycle]]).
- Only the main thread opens and merges canonical worktrees. A leaf works inside the path it receives and returns a validated handoff.
- A job, plain change, `define` or backlog tree lands only after the reviewer's `APPROVED` verdict binds to its exact diff; task merges are unreviewed and enforce git hygiene plus RED/implementation separation.

## Models and privilege

- Persona sources contain no model id and a dispatch passes none. `public install` renders each persona's tier alias (`fable`, `opus`, `sonnet`, `haiku`) and effort from one template of the `dadaia_workspace/core/model_registry.py` table — `balanced` by default, else the one `.dadaia/states/agent_model_policy.json` applies; Claude resolves the alias itself and `TIER_CODEX` maps it to the Codex id.
- `public install --template <id>` and `init --template <id>` select the template; an unknown id is refused ([[public-asset-distribution]], [[workspace-init]]).
- Install derives harness permissions from each persona's activity class. Harness serialization changes, but the role boundary does not ([[agentic-entities]], [[public-asset-distribution]]).

## Dependencies

[[agentic-entities]], [[agent-comms]], [[release-lifecycle]], [[worktrees]], [[audits-canon]], [[public-asset-distribution]], [[workspace-init]].
