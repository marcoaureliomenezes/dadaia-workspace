---
slug: agent-orchestration
title: agent-orchestration
tldr: Nine core Layer-1 roles, two dispatchers, document-governed ordered work, and advisory-only concurrency.
summary: Role ownership, dispatch purity, task discipline and review checkpoints; the ordered lifecycle is carried by SDD documents and agent dispatch, never by a runtime.
tags: [orchestration, agents, dispatch, sdd]
---

## Roster

The public core roster is nine Layer-1 agents (`public/agents/*.md`). Only `project-manager` and `project-auditor` dispatch; every other agent is a leaf worker.

| Role | Responsibility |
|---|---|
| `project-manager` | Operator-facing coordinator, backlog curator, dispatcher. |
| `project-auditor` | Audit dispatcher and disposition coordinator. |
| `product-engineer` | SPEC/PLAN/TASKS, closure, and `specs/memory/**`; holds `Bash` for read-side checks (doctor, catalog, memory tests) — the governance verbs and commits stay with the PM and `software-engineer`. |
| `software-engineer` | Production implementation and tests. |
| `qa-engineer` | Acceptance and executable-quality review. |
| `security-reviewer` | Security review and the committed PR-gate verdict. |
| `code-reviewer` | Diff/API/maintainability review. |
| `ai-engineer` | Agent, skill, rule, hook and harness surface. |
| `software-architect` | Architecture analysis and release-definition review; runs `dd-architecture-survey` before a candidate's review closes. |

## Behavior

- The entry harness reads `DADAIA.md`, classifies the demand and dispatches the owning agent per artifact class; no runtime drives agents through steps.
- Sequencing evidence is the artifacts themselves — `_RELEASE.json`, `**Status:** Aprovado` markers, task markers, handoffs.
- Each stage has exactly one owning skill: `dd-backlog-definition`, `dd-release-definition`, `dd-release-implementation` (whose RC-FLOW ends at the candidate PR; gate, ship and branch cut live in `dd-gitflow-default`), `dd-audit-project`, `dd-bug-registration` (ask-first), `dd-bug-resolution` (which carries the seven-phase diagnosing method); task reservation and recovery are RC-FLOW step 1, and `dadaia doctor` is one `dd-cli-library` idiom — neither has a skill of its own.
- An agent resolves or binds its context, reads the constitution, [[ARCHITECTURE]], [[TECHSTACK]], the catalog, the relevant atoms and the release artifacts, reserves tasks `[ ] -> [-]`, validates, marks `[x]`, and emits a handoff ([[agentic-entities]]); a record change goes through its governance verb, never a file tool ([[sdd-bug-backlog-governance]]).
- Concurrent sessions are allowed and presence is advisory: no agent acquires, holds, hands off, releases or steals a lock.
- Release definition requires architectural, QA and implementability review before approval; implementation requires QA, security and code review before a task is done, a rejection returning it to implementation.
- A merge requires an approved security handoff covering the PR head sha ([[sdd-gate-v3]]), and every verdict states the bug-surface delta from the bug ledger ([[QUALITY]]).
- Layer-1 agent sources are model-agnostic, receiving model and effort at `public install`.

## Dependencies

[[sdd-gate-v3]], [[agent-comms]], [[harness-claude-code]], [[harness-codex]], [[harness-kimi-code]], [[sdd-bug-backlog-governance]].
