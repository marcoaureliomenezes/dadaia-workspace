---
slug: lifecycle-foundation
title: lifecycle-foundation
category: product
tldr: "Deterministic Codex lifecycle foundation with Python-owned state, gates, hygiene, blocked/resume, and scoped Codex exec."
summary: >-
  `dadaia lifecycle` is the Codex-side deterministic lifecycle spine. The CLI stays
  thin and calls Python services in `features/lifecycle`; Python owns lifecycle
  state transitions, canonical runtime files, hygiene status/cleanup, semantic
  handoff gates, blocked/resume states, and scoped worker prompts. Codex is a
  bounded worker behind `AgentRuntimePort`, with a fake runtime for CI and an
  exec-backed adapter that uses explicit cwd/env/model/profile inputs and redacts
  credentials. The foundation exposes status, preflight, hygiene, report, resume,
  and guarded backlog/release/implementation/review/close skeletons; full
  autonomous workflow bodies remain future releases.
tags:
- sdd
- lifecycle
- codex
- hygiene
- gates
agent_tier: self-pull
token_estimate: 620
last_updated: '2026-06-20'
release_origin: v0.1.15
---

CLI surface: `dadaia lifecycle status`, `preflight`, `hygiene status`, `hygiene clean`, `report`, `resume`, `backlog define`, `release define`, `implement`, `review qa`, `review security`, `review code`, `close`.

## Purpose

The lifecycle foundation moves workflow authority out of broad agent instructions and into deterministic Python services. Agents can still reason and produce evidence, but Python decides whether state advances. Every transition consumes structured inputs: release identity, context, task group, handoff JSON, verdicts, commit SHA, hygiene counters, and bounded runtime outputs.

## Core services

- `core/models/lifecycle.py` and `core/models/hygiene.py` define pure run, gate, blocked-state, agent-request, and hygiene models.
- `core/protocols/agent_runtime.py` and `core/protocols/runtime_files.py` define the runtime and artifact ports.
- `features/lifecycle/state_machine.py` owns legal, illegal, blocked, and resume transitions.
- `features/lifecycle/gates.py` validates handoff evidence semantically: agent, context, release, verdict, artifact hash, commit SHA, task group, age, and severity thresholds.
- `features/lifecycle/hygiene.py` owns the canonical `SlopPolicy`: reports TTL 48h, handoffs TTL 24h, tmp TTL 24h, safe-zone cleanup, protected residuals, unknown `.dadaia/` top-level detection, malformed/orphan handoffs, and elapsed scan metrics.
- `features/lifecycle/report_workflow.py` writes human report HTML, matching handoff JSON, baseline/final hygiene snapshots, and optional explicit cleanup.
- `features/lifecycle/run_store.py` and `infrastructure/json_lifecycle_run_store.py` persist lifecycle run records under canonical workspace state/run zones and reject repo-tree stores.
- `features/lifecycle/prompt_builder.py` builds scoped worker prompts from role, context, release, task, allowed paths, forbidden paths, expected schema, and required evidence; whole-workspace or repo-wide scopes are rejected.

## Codex runtime boundary

Lifecycle code depends on `AgentRuntimePort`. CI uses a fake runtime to prove that Python advances only after structured output and write-scope evidence pass validation. The production Codex path is `infrastructure/codex_runtime.py` (`CodexExecAdapter`), not an SDK dependency. The adapter does not read project-local provider/auth/profile configuration, does not pass through `os.environ`, accepts only an explicit environment allowlist, redacts credential-looking values from outputs/errors, and records sandbox/profile widening only when operator-controlled input requests it.

## Blocking and resume

Preflight failures return typed `BlockedState` data instead of ambiguous prose. In no-approval Codex push scenarios, lifecycle preflight emits a valid blocked handoff with the exact operator command and resume token. The Codex command policy is not widened by this release; blocked/resume is the deterministic product behavior.

## Hygiene and anti-slop behavior

Lifecycle hygiene status measures reports, handoffs, and tmp zones without deleting. Cleanup defaults to dry-run; apply requires an explicit flag. Cleanup only deletes expired candidates in safe zones and preserves current-release evidence, important reports, valid handoff-linked artifacts, active runs, durable state, locks, sessions, operator-protected paths, and anything outside safe zones. The performance guard covers a synthetic baseline of 122 reports, 295 handoffs, and 437,724 tmp files with bounded time, RSS, and content reads.

## Current limits

The release intentionally ships foundation commands and guarded skeletons, not full autonomous backlog/release/implementation/review workflows. The next architecture step is to implement workflow bodies as reusable Python routines that call bounded agent runtimes and these lifecycle gates.
