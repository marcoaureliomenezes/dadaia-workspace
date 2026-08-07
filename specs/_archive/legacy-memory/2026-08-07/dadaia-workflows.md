---
slug: dadaia-workflows
title: dadaia-workflows
category: product
tldr: "Exactly four executable Layer-2 workflows: backlog definition, release definition, implementation plus reviews, and audit."
summary: >-
  The complete executable workflow surface. Each workflow has one CLI command, a
  Python-owned ordered body, fragment-plus-persona worker prompts, semantic gates,
  immutable per-attempt payloads, and an auditable handoff graph. Codex and PI are
  the supported real Layer-2 workers; fake is the deterministic test adapter.
tags:
- sdd
- workflows
- lifecycle
- layer-2
token_estimate: 649
last_updated: '2026-07-14'
release_origin: v0.2.3
---

## Purpose

`dadaia lifecycle` exposes exactly four workflows and no aliases:

| CLI command | Workflow id | Ordered responsibility |
|---|---|---|
| `backlog-definition` | `backlog_definition` | ONE author model call writes the item; the Python review gate validates what actually landed on disk (registry bind, duplicate/conflict classification). `--grill` opts into an evidence-first intake step whose digest feeds the author. |
| `release-definition` | `release_definition` | Author and review SPEC (one merged architecture+QA review), PLAN, and TASKS; a consumed backlog pick skips the scope model step; deterministic lints and reviews auto-revise their create step once in-run; the commit gate advances the approved release to implementation. |
| `implementation-reviews` | `implementation_reviews` | Reserve and implement approved tasks, judge with ONE combined tri-angle review (QA + security + code) over injected diff + executed-test evidence, bounded correction, close only when tasks and the review are complete. |
| `audit` | `audit` | ONE audit_report model pass (question, lenses, findings, dispositions routed bug/backlog/accepted-risk/resolved); the terminal Python gate checks referential integrity only — severity/lens are derived by finding id, never byte-copied. |

Research and bug intake are activities inside backlog definition or audit. Closure is
the terminal part of implementation plus reviews. Resume, hygiene, status, handoff
inspection, and model governance are services or diagnostics, not workflows.

## Execution Contract

- Python owns sequence, branching, retries, task-marker validation, state transitions,
  and terminal gates.
- Every model step receives its own fragment from
  `public/lifecycle_fragments/<workflow>/<step>.md` plus the role persona from
  `public/personas/<role>.md`.
- Supported real worker harnesses are `codex` and `pi`. `--harness auto` prefers the
  entry harness when it is Layer-2-capable; an explicit harness or per-step override wins.
- Model selection resolves through governed profiles. PI GPT profiles use explicit
  `openai-codex/...` ids; optional OpenRouter profiles remain explicit and never satisfy
  a Codex-subscription profile by fuzzy matching.
- A run freezes its effective policy before step one. Later policy edits cannot alter
  an in-flight run.

## Handoffs

Each model attempt produces one immutable run-scoped step payload. The payload records
the attempt, role, runtime, model profile, artifact references, verdict, metrics, and
the exact upstream payload ids consumed by that step. A consumer may advance only when
all declared producer payloads exist, validate, and match the current run/attempt graph.

Worker files are first written in a run-scoped temporary worker directory, validated,
then materialized into the lifecycle run ledger. Rejected or malformed attempts remain
available as evidence; a retry creates a new payload instead of overwriting the old one.
Terminal cleanup may purge expendable worker output, but never the accepted step ledger
or the evidence needed by closure and audit.

The human/agent communication boundary remains handoff-first:
`.dadaia/handoff/<context>/...handoff.json`. HTML is optional and only exists for a
human target or an explicit operator request.

## Validation Status

All four workflows are certified end-to-end on BOTH real harnesses with zero errors
(2026-07-14): the codex chain in 4m43 and the pi chain in 14m06 on
`gpt-5.3-codex-spark`, each running backlog → release → implementation → audit with no
resume and no operator intervention. Two production releases (panel Pong and Breakout)
were additionally shipped through the full chains. Failures found during the journeys
were root-caused and fixed in evidence path framing, unique-suffix anchor binding,
Python-side payload materialization, disk-truth deliverable checks, and lint/marker
grammar tolerance.

## Runtime State

- `.dadaia/runs/lifecycle/<run-id>/` - run state records.
- `specs/releases/<release-id>/handoffs/<run-id>/steps/` - immutable step payloads,
  REGISTERED IN THE RELEASE FOLDER (backlog runs: `specs/backlog/handoffs/<run-id>/`).
- `.dadaia/tmp/lifecycle-worker/<context>/` - bounded worker staging area.
- `.dadaia/handoff/<context>/` - validated cross-agent handoffs.
- `.dadaia/states/workflow_model_policy.json` - operator workflow policy overlay.
- `.dadaia/states/model_profiles.json` - optional operator model profiles.

## Dependencies

[[lifecycle-foundation]], [[agent-comms]], [[sdd-gate-v3]], [[harness-codex]],
[[harness-pi]], [[agent-orchestration]].
