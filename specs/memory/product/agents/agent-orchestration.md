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

- The main thread dispatches by the job file's `who` column: `sr` to `dd-sw-engineer-sr`, `jr` to `dd-sw-engineer-jr`, `pe` and `cr` to the owning persona; research goes to `dd-researcher`. The definition's reviewer judges each `who` against the shape rule.
- A REJECTED verdict whose finding names a `jr` task re-dispatches that task to `dd-sw-engineer-sr`.
- An implementation dispatch needs the precondition `specs/AGENTS.md` states under Before implementing: the live release in `IMPLEMENTATION` and the task a row of its job file whose `W:` names every file it touches; a `wt-hotfix` lane, or a block-list fix on a closed `wt-rc` for code only that rc holds, needs only its open bug ([[bug-ledger]]).
- The task is the implementation dispatch unit. A behavior begins with a RED-test dispatch and continues in a fresh implementation dispatch that cannot touch test paths ([[worktrees]]).
- Before every hand-back an implementer runs one self-check, stated once in `dd-release-implementation`, a skill both engineer personas carry: the repo's `verify:` line, the test directories the change reaches, and a read of its own diff for removed assertions, newly skipped tests, hand-typed fix-line labels, platform literals in assertions and the job's sweep greps; it hands back with no process of its own still running. When a task's work merges or its hand-back is checked, the main thread stops every agent of that task still running.
- Jobs and tasks may run concurrently only where the approved PLAN and exact write sets permit it. Git exposes races; no agent acquires a lock.
- No runtime advances the lifecycle. `_RELEASE.json`, approved definition documents, job files, worktrees, commits and handoffs are the evidence ([[release-lifecycle]]).
- Only the main thread opens and merges canonical worktrees. A leaf works inside the path it receives and returns a validated handoff.
- A `wt-main`, `wt-rc`, backlog or hotfix tree lands only after the reviewer's `APPROVED` verdict binds to its exact diff; task merges are unreviewed and enforce git hygiene plus RED/implementation separation.
- A review is dispatched on the tree as it stands; no preflight runs before it, and the reviewer never runs `verify:`: its `## Verify` section reports the tests it ran itself (the revert-RED check) and, for a PR, the `verify:` result the merge gate requires of its head. The merge runs `verify:` once ([[worktrees]]). The first review of a fix sweeps the fixed pattern across the context's repos and states the grep with its hit count; a net-positive fix states its reason, else it is a finding; a verdict on work whose evidence lacks the implementer's run of the tests the change reaches is `REJECTED`, and so is a `fix(bugs)` label where the bugs law requires a REBUILD ([[bug-ledger]]).

## Questions and decisions

- Every open question goes to `dd-grill-me` before launch, one question at a time, with the stage reference that fits it: before a backlog entry, before a candidate SPEC, when a decision may be an ADR, and after the PLAN.
- After launch the main thread asks the operator nothing: it decides by law, ADRs and rulings, logs an unruled choice with the grill's agent-default label, and keeps independent tasks running.
- An act the law reserves to the operator, and every bug proposal, waits for the closure report to the operator as one batch; a block-list bug is put to the operator at once, since it stops every merge ([[release-lifecycle]], [[bug-ledger]]).

## Models and privilege

- Persona sources contain no model id and a dispatch passes none. `public install` renders each persona's tier alias (`fable`, `opus`, `sonnet`, `haiku`) and effort from one template of the `dadaia_workspace/core/model_registry.py` table — `balanced` by default, else the one `.dadaia/states/agent_model_policy.json` applies; Claude resolves the alias itself and `TIER_CODEX` maps it to the Codex id.
- `public install --template <id>` and `init --template <id>` select the template; an unknown id is refused ([[public-asset-distribution]], [[workspace-init]]).
- Install derives harness permissions from each persona's activity class. Harness serialization changes, but the role boundary does not ([[agentic-entities]], [[public-asset-distribution]]).

## Dependencies

[[agentic-entities]], [[agent-comms]], [[release-lifecycle]], [[worktrees]], [[audits-canon]], [[public-asset-distribution]], [[workspace-init]], [[bug-ledger]].
