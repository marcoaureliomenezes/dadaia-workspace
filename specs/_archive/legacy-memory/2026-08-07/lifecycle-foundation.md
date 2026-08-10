---
slug: lifecycle-foundation
title: lifecycle-foundation
category: product
tldr: Deterministic Python workflow engine with fragment-scoped workers, semantic gates, bounded retries, and immutable handoff evidence.
summary: >-
  The runtime foundation beneath the four dadaia-workflows. Python owns sequencing,
  context selection, policy resolution, task-marker and artifact gates, advisory Git
  preflight warnings, run state, retries, diagnostics, and retention. Codex and PI
  workers run behind AgentRuntimePort with content-delta changed-path attribution.
tags:
- sdd
- lifecycle
- multi-harness
- hygiene
- gates
token_estimate: 655
last_updated: '2026-07-14'
release_origin: v0.2.7
---

## Purpose

The lifecycle engine turns SDD activities into repeatable, inspectable executions.
The CLI is a thin adapter over Python workflow bodies in
`features/lifecycle/workflows/`; model workers do bounded role work but never control
the lifecycle state machine.

## Core Services

- `LifecycleService` owns run creation, blocked/completed state, and persistence.
- The four workflow bodies own their exact step sequence and terminal gates.
- `WorkflowExecutionPolicyResolver` resolves harness/profile precedence once and
  freezes a per-run snapshot.
- `PromptBuilder` composes the step fragment, persona, injected context, exact task,
  allowed paths, dependencies, and output schema.
- `AgentRunner` invokes `AgentRuntimePort`, redacts diagnostics, validates the worker
  result, and persists evidence even when the worker is noncompliant.
- `WorkflowHandoffResolver` enforces exact producer-to-consumer payload edges.
- Lifecycle preflight blocks invalid context/release state but reports Git dirtiness,
  missing upstream, and unpushed commits as deterministic warnings.
- Hygiene and retention operate only in `.dadaia/` safe zones and preserve active or
  referenced evidence.

## Runtime Boundary

`codex` and `pi` are real Layer-2 harnesses. `fake` is test-only. Claude Code remains
an entry/Layer-1 runtime and is rejected as a Layer-2 workflow worker.

Each step resolves a governed profile to a concrete `(harness, model, reasoning)`
triple. Precedence is explicit per-step override, run-level override, context overlay,
then catalog default. Invalid profiles, harness/profile mismatches, and unavailable
provider-qualified models fail before a worker executes.

PI receives the exact model id and `--thinking` value. GPT models intended for the
Codex subscription use `openai-codex/...`; optional OpenRouter models use their explicit
provider ids. Codex receives its governed GPT model and reasoning effort directly.

## Prompt And Artifact Contract

Every model step is assembled from:

1. the step-specific lifecycle fragment;
2. the operative role persona;
3. current context, release, and relevant memory references;
4. exact upstream payload references;
5. allowed paths and the required output schema.

Accepted workers return `agent-run-result-v1` with artifact references. Lifecycle
payloads conform to the current handoff contract and capture `self_pull` evidence when
the role has memory references. Worker `changed_paths` are derived from before/after Git
content and existence deltas around the attempt: untouched pre-existing dirty paths are
excluded, while new, removed, or content-changed paths are included. A successful process
without required artifacts is a blocked attempt, not success. Non-zero exits, parse
failures, missing verdicts, and schema failures retain redacted diagnostics.

## Review And Retry

Implementation plus reviews runs implement, ONE combined tri-angle review (QA +
security + code angles in a single worker session), then close. A rejected review
returns to implementation through a bounded correction loop with the rejection digest
injected into the retry prompt. In the definition workflows, a REJECTED review or a
failed deterministic lint auto-revises its consumed create step once in-run before
blocking. Each retry gets a new attempt number and immutable payload. Review prompts
receive executed evidence: the write-set-scoped git diff and the captured pytest run
of the release's declared test paths. The terminal close step is unreachable while any
canonical task marker remains `[ ]` or `[-]`, or while the review is not approved.

## Context And Concurrency

Preflight resolves mode only from the caller's environment or caller-owned session
record. A foreign bind can never impose READ mode or a context on the current run.
Git dirtiness, missing upstream, and unpushed commits are visible warnings rather than
workflow blockers; the commit, CI, and exact-security-verdict push chokepoints remain
the authoritative Git quality boundaries. Concurrent sessions are permitted and surfaced
through advisory presence; lifecycle does not acquire or wait on a concurrency lock.

## Hygiene

Transient runtime data stays under `.dadaia/` (worker output staging, diagnostics).
Durable step payloads are REGISTERED IN THE SPEC CONTEXT: a run with a release writes
`specs/releases/<release_id>/handoffs/<run_id>/steps/`; a no-release run (backlog
definition) writes `specs/backlog/handoffs/<run_id>/steps/`. Cleanup is
dry-run by default, path-confined, and reference-aware. No lifecycle execution creates
repo-local cache, state, report, or temporary directories.

## Dependencies

[[dadaia-workflows]], [[agent-comms]], [[sdd-gate-v3]], [[harness-codex]],
[[harness-pi]].
