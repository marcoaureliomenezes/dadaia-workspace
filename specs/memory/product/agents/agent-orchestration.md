---
slug: agent-orchestration
title: agent-orchestration
tldr: Three dd- personas are leaf workers dispatched by the main thread; SDD documents, worktrees and handoffs carry the work, never an orchestration runtime.
summary: The role boundary, task-level dispatch contract, evidence flow and install-time model and privilege resolution for the product, software and review personas.
tags: [orchestration, agents, dispatch, sdd]
sources:
  - dadaia_workspace/public/agents/**
  - dadaia_workspace/core/model_registry.py
  - dadaia_workspace/public/skills/dd-manager-orchestration/**
---

## Roster and authority

The main thread is the operator's session and the only dispatcher. It owns intake, the grill, routing, gates and operator decisions. The three projected personas are leaf workers:

| Persona | Owns |
|---|---|
| `dd-product-engineer` | backlog, candidate SPEC, closure product memory and release summary |
| `dd-software-engineer` | as-is review, PLAN, job files, production code and tests |
| `dd-code-reviewer` | independent three-axis review and the architecture, security, QA, product, audit and AI-surface lenses |

- A persona reports out-of-scope work with `[SCOPE ERROR]`; the main thread re-routes it.
- Only the operator accepts an ADR. Role agents never write `accepted` or `ruling`.
- The reviewer is verdict-only and writes its own sha-bound handoff through `verdict.py`.

## Dispatch and evidence

- The task is the implementation dispatch unit. A behavior begins with a RED-test dispatch and continues in a fresh implementation dispatch that cannot touch test paths ([[worktrees]]).
- Jobs and tasks may run concurrently only where the approved PLAN and exact write sets permit it. Git exposes races; no agent acquires a lock.
- No runtime advances the lifecycle. `_RELEASE.json`, approved definition documents, job files, worktrees, commits and handoffs are the evidence ([[release-lifecycle]]).
- Only the main thread opens and merges canonical worktrees. A leaf works inside the path it receives and returns a validated handoff.
- A job, plain change, `define` or backlog tree lands only after the reviewer's `APPROVED` verdict binds to its exact diff; task merges are unreviewed and enforce git hygiene plus RED/implementation separation.

## Models and privilege

- Persona sources contain no model id. `public install` resolves model and effort from the selected policy template and per-agent overlay through `dadaia_workspace/core/model_registry.py`.
- Unknown models are refused, and the reviewer cannot use a model family disallowed for review.
- Install derives harness permissions from each persona's activity class. Harness serialization changes, but the role boundary does not ([[agentic-entities]], [[public-asset-distribution]]).

## Dependencies

[[agentic-entities]], [[agent-comms]], [[release-lifecycle]], [[worktrees]], [[audits-canon]], [[public-asset-distribution]].
