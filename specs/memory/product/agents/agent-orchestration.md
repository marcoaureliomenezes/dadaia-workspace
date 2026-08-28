---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency.
summary: Role ownership, dispatch purity, task discipline and review checkpoints; the ordered lifecycle is carried by SDD documents and agent dispatch, never by a runtime, and each stage has one owning `dd-` skill.
tags:
- orchestration
- agents
- dispatch
- sdd
---

## Purpose

The public core roster is nine Layer-1 agents (`public/agents/*.md`). Only
`project-manager` and `project-auditor` dispatch; every other agent is a leaf worker.

| Role | Responsibility |
|---|---|
| `project-manager` | Operator-facing coordinator, backlog curator, dispatcher. |
| `project-auditor` | Audit dispatcher and disposition coordinator. |
| `product-engineer` | SPEC/PLAN/TASKS, closure, and `specs/memory/**`. |
| `software-engineer` | Production implementation and tests. |
| `qa-engineer` | Acceptance and executable-quality review. |
| `security-reviewer` | Security review and the committed PR-gate verdict. |
| `code-reviewer` | Diff/API/maintainability review. |
| `ai-engineer` | Agent, skill, rule, hook and harness surface. |
| `software-architect` | Architecture analysis and release-definition review. |

## Current behavior

Ordered work — demand, backlog definition, release definition, implementation with its
reviews, audit — is governed by documents and executed by dispatch. The entry harness reads
`DADAIA.md`, classifies the demand, and dispatches the owning agent per artifact class.
Sequencing evidence is the artifacts themselves: the `RELEASE.jsonl` fold, `**Status:**
Aprovado` markers, task markers, and handoffs. No runtime drives agents through steps.

Each stage has exactly one owning skill, which the law points at rather than restating:
`dd-backlog-definition`, `dd-release-definition`, `dd-release-implement` (implementation,
its review cadence and closure, disclosed to sibling files), `dd-audit-project`,
`dd-bug-registration` and `dd-bug-resolution`. `dd-diagnose` carries the seven-phase
diagnosing method `dd-bug-resolution` calls, ending in a handback. Which skill owns which
law section is declared once in the behavior map ([[agentic-entities]]).

## Operating rules

1. Resolve or bind the intended Spec Context.
2. Read the constitution, [[architecture]], [[tech-stack]], the product catalog, the
   relevant atoms, and the active release artifacts.
3. Dispatch the owning agent for the artifact class being produced.
4. Reserve production tasks `[ ] -> [-]`, stay inside the declared write set, validate,
   then mark `[x]`.
5. Emit a machine-readable handoff; add HTML only for an explicit human target.

Concurrent sessions are allowed. Presence is advisory: no agent acquires, holds, hands off,
releases or steals a lock. Git conflicts remain visible when races occur.

## Review sequence

Release definition requires architectural, QA and implementability review before approval.
Implementation requires QA, security and code review before a task is marked done; a
rejection returns the task to implementation. A merge requires an approved security handoff
covering the pull request's head sha ([[sdd-gate-v3]]).

Every verdict states the bug-surface delta of each feature it touched, with evidence read
from the bug ledger rather than the test result ([[quality-assurance]]).

## Model governance

Layer-1 agent sources are model-agnostic and receive model/effort at `public install` from
the selected template plus the operator overlay. The panel's Agents tab manages that policy.

## Dependencies

[[sdd-gate-v3]], [[agent-comms]], [[harness-claude-code]], [[harness-codex]],
[[harness-kimi-code]].
