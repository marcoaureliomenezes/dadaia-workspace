---
slug: lifecycle-foundation
title: lifecycle-foundation
category: product
tldr: "Multi-harness procedural lifecycle engine: Python-owned state/gates/hygiene plus per-step harness-selectable agent workers behind AgentRuntimePort."
summary: >-
  `dadaia lifecycle` is the deterministic, multi-harness lifecycle engine. The CLI
  stays thin and calls procedural Python services in `features/lifecycle`; Python
  owns lifecycle state transitions, canonical runtime files, hygiene status/cleanup,
  semantic handoff gates, blocked/resume states, and scoped worker prompts. Each
  lifecycle step drives a bounded agent worker behind `AgentRuntimePort`, with the
  harness selectable per step via `build_agent_runtime(kind)` (FAKE, CODEX_EXEC,
  CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS). Single-step verbs run `LifecyclePhaseWorkflow`; the
  multi-step `LifecyclePipeline` threads one run through the IMPLEMENTATION→QA→
  SECURITY→CODE→CLOSURE ladder with per-step harness mixing. The Claude SDK adapter
  enforces a real Ring-1 write boundary via the shared `core/scope_match` classifier;
  a cacheable hashed `PromptPrefix` is reused across steps, which carry model tiers.
  Anti-slop self-governance is built in: a directory-aware slop metric and a
  boundary-safe retention sweep.
tags:
- sdd
- lifecycle
- multi-harness
- hygiene
- gates
agent_tier: self-pull
token_estimate: 1500
last_updated: '2026-06-25'
release_origin: pi-fourth-harness-v1
---

CLI surface: `dadaia lifecycle status`, `preflight`, `hygiene status`, `hygiene clean`, `report`, `resume`, `slop`, `clean`, `backlog define`, `release define`, `implement`, `review qa`, `review security`, `review code`, `close`, `pipeline`.

## Purpose

The lifecycle foundation moves workflow authority out of broad agent instructions and into deterministic Python services. Agents can still reason and produce evidence, but Python decides whether state advances. Every transition consumes structured inputs: release identity, context, task group, handoff JSON, verdicts, commit SHA, hygiene counters, and bounded runtime outputs.

## Core services

- `core/models/lifecycle.py` and `core/models/hygiene.py` define pure run, gate, blocked-state, agent-request, and hygiene models. `AgentRuntimeKind` enumerates `FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, `OPENCODE_RUN`, `PI_HEADLESS`.
- `core/scope_match.py` is the shared, pure path classifier used by BOTH the runner's Ring-2 out-of-scope detection and the Claude adapter's Ring-1 write-permission decider — one classifier, two boundaries.
- `core/protocols/agent_runtime.py` and `core/protocols/runtime_files.py` define the runtime and artifact ports.
- `features/lifecycle/state_machine.py` owns legal, illegal, blocked, and resume transitions.
- `features/lifecycle/gates.py` validates handoff evidence semantically: agent, context, release, verdict, artifact hash, commit SHA, task group, age, and severity thresholds.
- `features/lifecycle/phase_workflow.py` (`LifecyclePhaseWorkflow`) threads a scoped prompt → factory-selected `AgentRuntimePort` → `LifecycleAgentRunner` gate → legal transition → persisted run, for any single lifecycle step.
- `features/lifecycle/pipeline.py` (`LifecyclePipeline`) threads ONE `LifecycleRun` through an ordered phase ladder (IMPLEMENTATION→QA→SECURITY→CODE→CLOSURE), each step running on its declared `AgentRuntimeKind` via an injected runtime factory, persisting at every step and stopping at the first blocked gate. Each `PipelineStep` carries a model tier (implement=sonnet, reviews=opus).
- `features/lifecycle/prompt_builder.py` builds scoped worker prompts; `PromptPrefix.from_sections` assembles a byte-identical, sha256-hashed, order-independent context block, and `build(scope, prefix=)` prepends it verbatim and records `prefix_hash`. The pipeline builds the prefix once and every step reuses the same bytes (provider-cache-friendly). Whole-workspace or repo-wide scopes are rejected.
- `features/lifecycle/hygiene.py` owns the canonical `SlopPolicy`: reports TTL 48h, handoffs TTL 24h, tmp TTL 24h, safe-zone cleanup, protected residuals, unknown `.dadaia/` top-level detection, malformed/orphan handoffs, and elapsed scan metrics.
- `features/lifecycle/antislop/slop_scan.py` is the directory-aware slop metric: a directory tree counts as ONE entry with recursive size (closing the directory-blind gap where multi-GB caches/venvs hid from the file-only metric); the canonical manifest derives from `hooks/root_whitelist._WHITELIST`, never hand-copied. Surfaced via `dadaia lifecycle slop`.
- `features/lifecycle/antislop/retention.py` (`RetentionSweep.sweep`) is the deleter: dry-run by default, deletes only with `apply=True`; reclaims past-TTL non-canonical swept-zone entries; has a HARD liveness gate (never reclaims a live run's tmp); refuses canonical/outside-`.dadaia`/symlink-escape paths (resolve + relative_to, TOCTOU re-confine). Surfaced via `dadaia lifecycle clean [--apply]`.
- `features/lifecycle/report_workflow.py` writes human report HTML, matching handoff JSON, baseline/final hygiene snapshots, and optional explicit cleanup.
- `features/lifecycle/run_store.py` and `infrastructure/json_lifecycle_run_store.py` persist lifecycle run records under canonical workspace state/run zones and reject repo-tree stores.

## Harness runtime boundary

Lifecycle code depends on `AgentRuntimePort`; `build_agent_runtime(kind, *, cwd=None)` in `container.py` is the factory that maps a kind to its adapter: `FAKE→FakeAgentRuntime`, `CODEX_EXEC→CodexExecAdapter` (`infrastructure/codex_runtime.py`), `OPENCODE_RUN→OpenCodeAdapter` (`infrastructure/opencode_runtime.py`, stub), `CLAUDE_SDK→ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`), `PI_HEADLESS→PiHeadlessAdapter` (`infrastructure/pi_runtime.py`). The factory stays total over the enum. `--harness pi` / `--step-harness x=pi` resolve across every `dadaia lifecycle` verb with zero change to `phase_workflow.py` / `pipeline.py` — a clean adapter addition. CI uses the fake runtime to prove that Python advances only after structured output and write-scope evidence pass validation.

The Codex adapter does not read project-local provider/auth/profile configuration, does not pass through `os.environ`, accepts only an explicit environment allowlist, redacts credential-looking values, and records sandbox/profile widening only when operator-controlled input requests it. The Claude SDK adapter derives a real Ring-1 `write_permission` decider from the request's allowed/forbidden paths via the same `core/scope_match` classifier the runner's Ring-2 uses; its transport is injectable (`query_fn`) so permission + result mapping are tested hermetically. `claude-agent-sdk` is an OPTIONAL, operator-installed runtime extra (not a locked dependency, offline-first build); the default transport lazily imports it and returns an actionable `pip install claude-agent-sdk` message when absent.

The PI adapter (`PiHeadlessAdapter` + frozen `PiHeadlessConfig`) is a structural twin of `CodexExecAdapter`: it drives `pi --mode json --tools <csv> -p -` (prompt on stdin) over an injectable subprocess runner, imports no PI client at module load (offline-first preserved), and accepts only an explicit env allowlist (incl. `ANTHROPIC_API_KEY`, redacted from output). Result mapping parses the line-delimited JSON stream and takes the **last** `message_end` event's assistant text from `message.content`, handling both string and content-block shapes; an absent or unparseable `message_end` degrades to raw stdout as the summary (SUCCEEDED, never crashes), and a fenced JSON block matching the request's `expected_schema` populates `structured_output`. A valid terminal `message_end` maps to SUCCEEDED **even when `pi` exits non-zero** — the terminal assistant message is trusted over the raw exit code (deliberate precedence); the downstream verdict gate and the Ring-2 write boundary still apply. PI's Ring-2 write boundary is real: `changed_paths` is computed from the injected git client's `diff_name_only(cwd)` (working-tree + staged + untracked, non-ignored) at result time and written into `structured_output["changed_paths"]`, **unconditionally overwriting any model self-report** — so the runner's Ring-2 out-of-scope block fires for PI exactly as for Codex/OpenCode. PI has no CLI-level pre-disk (Ring-1) gate yet: its enforcement posture is Ring-2 + git chokepoints, identical to Codex/OpenCode. The first-layer `.pi/` projection (WS-PI-3) and the Ring-1 `.pi/` `tool_call` extension (WS-PI-4) are deferred. The live `pi --mode json` event schema — specifically the `AgentMessage.content` shape — is the one upstream-owned unverified seam, verified via the opt-in `DADAIA_PI_LIVE=1` integration test (`tests/integration/pi_live/`), not CI-gated.

## Gating note (current behavior)

The runner applies a uniform APPROVED-verdict gate to every phase: non-review phases (implement/define) also require the worker to emit an APPROVED handoff. Phase-specific gating (implement needs evidence, not self-approval) is a deferred runner refinement.

## Blocking and resume

Preflight failures return typed `BlockedState` data instead of ambiguous prose. In no-approval Codex push scenarios, lifecycle preflight emits a valid blocked handoff with the exact operator command and resume token. The Codex command policy is not widened by this release; blocked/resume is the deterministic product behavior.

## Hygiene and anti-slop behavior

Lifecycle hygiene status measures reports, handoffs, and tmp zones without deleting. Cleanup defaults to dry-run; apply requires an explicit flag. Cleanup only deletes expired candidates in safe zones and preserves current-release evidence, important reports, valid handoff-linked artifacts, active runs, durable state, locks, sessions, operator-protected paths, and anything outside safe zones. The performance guard covers a synthetic baseline of 122 reports, 295 handoffs, and 437,724 tmp files with bounded time, RSS, and content reads.

## Current limits

Every single-step verb and the multi-step pipeline run the engine over a real
`AgentRuntimePort`, but the engine does not yet autonomously drive a live end-to-end
release. Deferred: live Claude SDK binding verification (the `_default_query_fn`
`query()`/`can_use_tool` call is the one unverified piece — offline build) plus provider
cache-control marker wiring; phase-specific gate refinement (dropping the uniform
APPROVED-verdict requirement for non-review phases); the live OpenCode `opencode run`
adapter (currently a documented stub); and persisting explicit per-run tmp working-dir
claims in `LifecycleRun` so the retention liveness provider keys on a registered workdir.
