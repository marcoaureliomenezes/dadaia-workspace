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
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

`dadaia lifecycle` exposes exactly four workflows and no aliases:

| CLI command | Workflow id | Ordered responsibility |
|---|---|---|
| `backlog-definition` | `backlog_definition` | Refine one demand, bind canonical subjects, reconcile duplicates/conflicts, author one consistent backlog item, validate it. |
| `release-definition` | `release_definition` | Scope selected intake, author and review SPEC, PLAN, and TASKS, then advance an approved release to implementation. |
| `implementation-reviews` | `implementation_reviews` | Reserve and implement approved tasks, run QA/security/code review with bounded correction, close only when tasks and reviews are complete. |
| `audit` | `audit` | Bound an audit, scan for drift, triage every finding, and validate complete dispositions. |

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

All four workflows have completed real phantom journeys through both Codex and PI.
The PI validation journeys were pinned to `openai-codex/gpt-5.5` and did not use
OpenRouter. Failures found during the journeys were fixed in the workflow gates,
provider qualification, release contract validation, task-marker closure validation,
and caller-owned context preflight.

## Runtime State

- `.dadaia/runs/lifecycle/<run-id>/` - run state and immutable step payloads.
- `.dadaia/tmp/lifecycle-worker/<run-id>/` - bounded worker staging area.
- `.dadaia/handoff/<context>/` - validated cross-agent handoffs.
- `.dadaia/states/workflow_model_policy.json` - operator workflow policy overlay.
- `.dadaia/states/model_profiles.json` - optional operator model profiles.

## Dependencies

[[lifecycle-foundation]], [[agent-comms]], [[sdd-gate-v3]], [[harness-codex]],
[[harness-pi]], [[agent-orchestration]].
