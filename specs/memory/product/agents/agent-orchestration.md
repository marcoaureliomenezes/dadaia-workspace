---
slug: agent-orchestration
title: agent-orchestration
tldr: Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency.
summary: Role ownership, dispatch purity, task discipline and review checkpoints; the ordered lifecycle is carried by SDD documents and agent dispatch, never by a runtime.
tags: [orchestration, agents, dispatch, sdd]
sources:
  - dadaia_workspace/public/agents/**
  - dadaia_workspace/core/agent_model_templates.py
  - dadaia_workspace/core/model_registry.py
  - dadaia_workspace/public/skills/dd-manager-orchestration/**
---

## Roster

The public core roster is three Layer-1 agents (`public/agents/*.md`, ADR 0016). Only `project-manager` dispatches; the other two are leaf workers.

| Role | Responsibility |
|---|---|
| `project-manager` | Operator-facing coordinator: intake, grill-me, backlog curation, SPEC, the memory pass at closure, dispatch. |
| `software-engineer` | PLAN and TASKS as technical planning; production implementation and tests. |
| `code-reviewer` | The three-axis review plus six lenses — architecture, security, QA, product, audit, AI surface — read-only, verdict-only. |

## Behavior

- The entry harness reads `DADAIA.md`, classifies the demand and dispatches the owning agent per artifact class; no runtime drives agents through steps.
- Sequencing evidence is the artifacts themselves — `_RELEASE.json`, `**Status:** Aprovado` markers, task markers, handoffs.
- Each stage has exactly one owning skill: `dd-backlog-definition`, `dd-release-definition`, `dd-release-implementation` (whose RC-FLOW ends at the candidate PR; gate, ship and branch cut live in `dd-gitflow-default`), `dd-audit-project`, `dd-bug-registration` (ask-first), `dd-bug-resolution` (which carries the seven-phase diagnosing method); task reservation and recovery are RC-FLOW step 1, and `dadaia doctor` is one `dd-cli-library` idiom — neither has a skill of its own.
- An agent resolves or binds its context, reads the constitution, [[ARCHITECTURE]], the catalog, the relevant atoms and the release artifacts, reserves tasks `[ ] -> [-]`, validates, marks `[x]`, and emits a handoff ([[agentic-entities]]); a record change goes through its governance verb, never a file tool ([[sdd-bug-backlog-governance]]).
- Concurrent sessions are allowed and never locked: no agent acquires, holds, hands off, releases or steals a lock; races surface through git.
- Release definition passes the reviewer's architecture, QA and product lenses before approval; implementation passes the reviewer's `APPROVED` before a candidate closes, a rejection returning it to implementation.
- A merge requires the `security-review` check green on the PR head ([[sdd-gate-v3]]), and every verdict states the bug-surface delta from the bug record store (`bugs.py stats`, [[QUALITY]]).
- Layer-1 agent sources are model-agnostic, receiving model and effort at `public install`.

## Dependencies

[[sdd-gate-v3]], [[agent-comms]], [[harness-claude-code]], [[harness-codex]], [[harness-kimi-code]], [[sdd-bug-backlog-governance]].
