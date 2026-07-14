---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: Nine core Layer-1 roles, eight Layer-2 personas, two dispatchers, four workflows, and advisory-only concurrency.
summary: >-
  Defines role ownership, dispatch purity, memory bootstrap, task discipline, review
  checkpoints, model governance, and the relationship between Layer-1 agents and
  Layer-2 workflow personas. No role acquires or coordinates a concurrency lock.
tags:
- orchestration
- agents
- workflows
- dispatch
token_estimate: 526
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

The public core roster has nine Layer-1 agents. Only `project-manager` and
`project-auditor` dispatch. All other agents are leaf workers and never dispatch another
worker.

| Role | Responsibility |
|---|---|
| `project-manager` | Operator-facing lifecycle coordinator and workflow dispatcher. |
| `project-auditor` | Audit dispatcher and disposition coordinator. |
| `product-engineer` | Backlog, SPEC/PLAN/TASKS/CLOSURE, and memory ownership. |
| `software-engineer` | Production implementation and tests. |
| `qa-engineer` | Acceptance and executable-quality review. |
| `security-reviewer` | Security review and pre-push approval evidence. |
| `code-reviewer` | Diff/API/maintainability review. |
| `ai-engineer` | Agent, skill, rule, hook, persona, and harness surface. |
| `software-architect` | Architecture analysis and release-definition review. |

Optional plugin packs add domain workers without changing the core roster.

## Layer 1 And Layer 2

Layer 1 is the interactive entry harness. Layer 2 is a bounded worker invoked by one
of the four Python workflows. Layer-2 personas exist for the eight non-PM core roles;
`project-manager` remains the Python/Layer-1 orchestrator and has no persona atom.

A persona is behavioral context, not a model choice. Harness, model profile, and
reasoning effort are resolved per workflow step through the workflow policy.

## Operating Rules

1. Resolve or bind the intended Spec Context.
2. Read constitution, architecture, tech stack, product catalog, relevant memory, and
   the active release artifacts.
3. Use the appropriate one of four workflows for ordered lifecycle work.
4. Reserve production tasks `[ ] -> [-]`, stay inside the declared write set, validate,
   then mark `[x]`.
5. Emit a machine-readable handoff; add HTML only for an explicit human target.

Concurrent sessions are allowed. Presence is advisory, and no agent acquires, holds,
hands off, releases, or steals a workspace concurrency lock. Dispatch coordination and
task markers reduce conflicting intent; Git conflicts remain visible when races occur.

## Review Sequence

Release definition requires architectural, QA, and implementability review before the
terminal definition gate. Implementation plus reviews runs QA, security, and code
review; rejection returns to implementation through a bounded retry. Push requires an
approved security handoff for the exact commit SHA.

## Model Governance

Layer-1 agent sources are model-agnostic and receive model/effort at public install from
the selected template plus operator overlay. The panel's 1st Agentic Layer manages this
policy. Layer-2 profiles are managed independently in the 2nd Agentic Layer.

## Dependencies

[[dadaia-workflows]], [[lifecycle-foundation]], [[sdd-gate-v3]], [[agent-comms]],
[[harness-codex]], [[harness-pi]].
