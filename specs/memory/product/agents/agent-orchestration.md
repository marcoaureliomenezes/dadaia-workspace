---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency.
summary: >-
  Defines role ownership, dispatch purity, memory bootstrap, task discipline, review
  checkpoints, and Layer-1 model governance. The ordered lifecycle is carried by SDD
  documents and agent dispatch, not by a runtime, and each stage's protocol has one owning
  dd- skill the law points at. No role acquires or coordinates a concurrency lock.
tags:
- orchestration
- agents
- dispatch
- sdd
last_updated: '2026-08-24'
release_origin: v0.3.0
---

## Purpose

The public core roster has nine Layer-1 agents. Only `project-manager` and
`project-auditor` dispatch. All other agents are leaf workers and never dispatch another
worker.

| Role | Responsibility |
|---|---|
| `project-manager` | Operator-facing coordinator, backlog curator, and dispatcher. |
| `project-auditor` | Audit dispatcher and disposition coordinator. |
| `product-engineer` | SPEC/PLAN/TASKS/CLOSURE and memory ownership. |
| `software-engineer` | Production implementation and tests. |
| `qa-engineer` | Acceptance and executable-quality review. |
| `security-reviewer` | Security review and the committed PR-gate approval evidence. |
| `code-reviewer` | Diff/API/maintainability review. |
| `ai-engineer` | Agent, skill, rule, hook, and harness surface. |
| `software-architect` | Architecture analysis and release-definition review. |


## How Ordered Work Happens

The ordered lifecycle — demand, backlog definition, release definition, implementation
plus reviews, audit — is governed by documents and executed by dispatch. The entry
harness reads `DADAIA.md`, classifies the demand, and dispatches the owning agent for
each artifact class. Sequencing evidence is the SDD artifacts themselves: `ACTIVE.md`
phase, `**Status:** Aprovado` markers on SPEC/PLAN/TASKS, task markers, handoffs, and
CLOSURE. No runtime drives agents through steps.

Each stage's protocol has exactly one owning skill, and the always-on law points at it
rather than restating it: `dd-backlog-definition` (backlog definition, run continuously by
`project-manager`), `dd-release-definition` (picking the set, the mandatory grill, SPEC),
`dd-release-implement` (implementation, its review-gate cadence **and** the closure —
memory update, CLOSURE, dispositions, artifact GC, archive — disclosed to its own sibling
files), `dd-audit-project` (audit and its remediation release), `dd-bug-registration` and
`dd-bug-fix` (the bug arm, end to end). A skill that needs another stage's rule names that
skill instead of repeating it, and which skill owns which law topic is declared once, in
the rules-skills map ([[agentic-entities]]).

The bug arm is ordered too, and its order is checkable. `dd-bug-fix` carries six
diagnosing phases — red loop before any hypothesis, minimise, falsifiable hypotheses,
instrument the executed path, regression test at the correct seam, cleanup — each ending
in a criterion a reader can verify, and it yields to `software-architect` when no correct
seam exists. Closing the bug is gated rather than narrated: the `resolved` event is refused
without its three checkable fields, and a net-positive diff on the touched feature is
ruled on by `software-architect` before the commit ([[sdd-bug-backlog-governance]]).

## Operating Rules

1. Resolve or bind the intended Spec Context.
2. Read constitution, architecture, tech stack, product catalog, relevant memory atoms,
   and the active release artifacts.
3. Dispatch the owning agent for the artifact class being produced.
4. Reserve production tasks `[ ] -> [-]`, stay inside the declared write set, validate,
   then mark `[x]`.
5. Emit a machine-readable handoff; add HTML only for an explicit human target.

Concurrent sessions are allowed. Presence is advisory, and no agent acquires, holds,
hands off, releases, or steals a workspace concurrency lock. Dispatch coordination and
task markers reduce conflicting intent; Git conflicts remain visible when races occur.

## Review Sequence

Release definition requires architectural, QA, and implementability review before the
definition is approved. Implementation requires QA, security, and code review before a
task is marked done; a rejection returns the task to implementation. A **merge** requires
an approved security handoff covering the pull request's head sha ([[sdd-gate-v3]]).

Every verdict states the **bug-surface delta** of each feature it touched, with evidence
read from the bug ledger rather than from the test result; "tests green" is not a verdict
([[quality-assurance]]).

## Model Governance

Layer-1 agent sources are model-agnostic and receive model/effort at public install from
the selected template plus operator overlay. The panel's Agents tab manages
this policy.

## Dependencies

[[sdd-gate-v3]], [[agent-comms]], [[harness-claude-code]], [[harness-codex]],
[[harness-kimi-code]].
