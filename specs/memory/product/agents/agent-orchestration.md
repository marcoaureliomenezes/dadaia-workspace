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

## Roster

The public core roster is nine Layer-1 agents (`public/agents/*.md`). Only `project-manager` and
`project-auditor` dispatch; every other agent is a leaf worker.

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

## Behavior

Ordered work is governed by documents and executed by dispatch: the entry harness reads `DADAIA.md`,
classifies the demand, and dispatches the owning agent per artifact class. Sequencing evidence is
the artifacts themselves — `RELEASE.json`, `**Status:** Aprovado` markers, task markers, handoffs.
No runtime drives agents through steps. Each stage has exactly one owning skill the law points at
rather than restating: `dd-backlog-definition`, `dd-release-definition`, `dd-release-implement`,
`dd-audit-project`, `dd-bug-registration`, `dd-bug-resolution`, with `dd-diagnose` carrying the
seven-phase method. Which skill owns which law section is declared once in the behavior map
([[agentic-entities]]).

An agent resolves or binds its Spec Context; reads the constitution, [[architecture]],
[[tech-stack]], the product catalog, the relevant atoms and the active release artifacts; reserves
production tasks `[ ] -> [-]`, stays inside the declared write set, validates, then marks `[x]`; and
emits a machine-readable handoff. Concurrent sessions are allowed and presence is advisory — no
agent acquires, holds, hands off, releases or steals a lock.

Release definition requires architectural, QA and implementability review before approval;
implementation requires QA, security and code review before a task is marked done, a rejection
returning the task to implementation; a merge requires an approved security handoff covering the
pull request's head sha ([[sdd-gate-v3]]). Every verdict states the bug-surface delta of each
feature it touched, evidenced from the bug ledger rather than the test result
([[quality-assurance]]). Layer-1 agent sources are model-agnostic, receiving model/effort at
`public install`.

## Dependencies

[[sdd-gate-v3]], [[agent-comms]], [[harness-claude-code]], [[harness-codex]],
[[harness-kimi-code]].
