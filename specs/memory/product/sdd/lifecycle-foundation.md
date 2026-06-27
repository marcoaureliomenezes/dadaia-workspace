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
  harness selectable per step via `build_agent_runtime(kind, *, cwd, model)` (FAKE,
  CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS — OPENCODE_RUN removed in v0.1.24). LAW 1: the
  selectable Layer-2 workflow harnesses are {pi, codex, fake} (claude rejected as a
  workflow harness; CLAUDE_SDK kept/tested for Layer-1). LAW 2: a discrete per-harness
  GPT model catalog selected on the CLI (--model/--step-model; pi-3 / codex-2). The verbs
  are dadaia-workflows: Python bodies that import prompt fragments, select dynamic
  context, call workers, and advance Python-validated gates; the release-definition
  workflow is the first fully fragment-driven workflow. Single-step verbs run
  `LifecyclePhaseWorkflow`; the multi-step `LifecyclePipeline` threads one run through the
  IMPLEMENTATION→QA→SECURITY→CODE→CLOSURE ladder with per-step harness mixing. The Claude
  SDK adapter enforces a real Ring-1 write boundary via the shared `core/scope_match`
  classifier; a cacheable hashed `PromptPrefix` is reused across steps. v0.1.28 adds the
  workflow model governance control plane: a built-in WorkflowModelProfile registry over
  harness_models, an atomic operator overlay (missing != invalid), one shared
  WorkflowExecutionPolicyResolver, a per-run policy snapshot resolved once before step 1,
  and WMP-* governance doctor checks. v0.1.29 makes harness a first-class governed dimension:
  an effective-harness precedence chain (CLI step > CLI default > overlay step > overlay
  default_harness > catalog default), profile validated against the effective harness,
  auto-profile-on-harness-override, apply_resolved_policy as the single runtime_kind author
  (FAKE preserved), overlay default_harness/harnesses fields, and a completed governed
  catalog of all 7 workflows (3 runnable + closure resolvable + 3 deferred zero-step) — so
  PI is fully selectable as a Layer-2 worker. Anti-slop self-governance is built in: a
  directory-aware slop metric and a boundary-safe retention sweep.
tags:
- sdd
- lifecycle
- multi-harness
- hygiene
- gates
agent_tier: self-pull
token_estimate: 3050
last_updated: '2026-06-27'
release_origin: v0.1.29
---

CLI surface: `dadaia lifecycle status`, `preflight`, `hygiene status`, `hygiene clean`, `report`, `resume`, `slop`, `clean`, `backlog define`, `release define`, `implement`, `review qa`, `review security`, `review code`, `close`, `pipeline`, `workflow policy show`, `workflow profiles list`, `workflow doctor`. Run verbs accept `--step-model <step>=<profile-id>` (profile ids only) + `--show-policy`/`--json`.

The engine is the **Layer-2** half of the two-layer model (see [[architecture]] for the
full two-layer picture): a Layer-1 entry harness invokes `dadaia lifecycle`, which threads
one `LifecycleRun` through the phase ladder, running each step on a per-step selectable
worker harness behind `AgentRuntimePort` and advancing only when the gate passes.

```mermaid
flowchart TB
    OP["dadaia lifecycle pipeline --release &lt;id&gt;<br/>(ou implement · review qa|security|code · close)"]
    OP --> PB["prompt_builder · PromptPrefix<br/>(sha256, cacheable, reusado byte-a-byte por step)"]
    PB --> LAD
    subgraph LAD["LifecyclePipeline — phase ladder (1 LifecycleRun · persiste a cada step · para no 1º bloqueio)"]
        direction LR
        I["implement"] --> Q["review_qa"] --> S["review_security"] --> C["review_code<br/>(→ fase CLOSURE)"]
        C -.->|"close é step separado"| CLp["CLOSURE<br/>(dadaia lifecycle close)"]
    end
    LAD -.->|"build_agent_runtime(kind) — --step-harness"| RT
    subgraph RT["AgentRuntimePort — worker harness selecionável por step (LAW 1: pi/codex/fake)"]
        direction LR
        FK["FAKE"]:::w
        CXk["CODEX_EXEC"]:::w
        PIk["PI_HEADLESS"]:::w
        CLk["CLAUDE_SDK · Ring-1<br/>(kept, NOT workflow harness)"]:::x
    end
    RT --> GATE{"LifecycleAgentRunner gate:<br/>verdict APPROVED?<br/>Ring-2 changed_paths in-scope?"}
    GATE -->|sim| NEXT(["transição legal → próximo step"])
    GATE -->|não| BLK(["BlockedState + resume token"])
    classDef w fill:#238636,color:#fff,stroke:#238636;
    classDef x fill:#6e7681,color:#fff,stroke:#6e7681;
```

## Purpose

The lifecycle foundation moves workflow authority out of broad agent instructions and into deterministic Python services. Agents can still reason and produce evidence, but Python decides whether state advances. Every transition consumes structured inputs: release identity, context, task group, handoff JSON, verdicts, commit SHA, hygiene counters, and bounded runtime outputs.

## Core services

- `core/models/lifecycle.py` and `core/models/hygiene.py` define pure run, gate, blocked-state, agent-request, and hygiene models. `AgentRuntimeKind` enumerates `FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, `PI_HEADLESS` (`OPENCODE_RUN` removed in v0.1.24).
- `core/scope_match.py` is the shared, pure path classifier used by BOTH the runner's Ring-2 out-of-scope detection and the Claude adapter's Ring-1 write-permission decider — one classifier, two boundaries.
- `core/protocols/agent_runtime.py` and `core/protocols/runtime_files.py` define the runtime and artifact ports.
- `features/lifecycle/state_machine.py` owns legal, illegal, blocked, and resume transitions.
- `features/lifecycle/gates.py` validates handoff evidence semantically: agent, context, release, verdict, artifact hash, commit SHA, task group, age, and severity thresholds.
- `features/lifecycle/phase_workflow.py` (`LifecyclePhaseWorkflow`) threads a scoped prompt → factory-selected `AgentRuntimePort` → `LifecycleAgentRunner` gate → legal transition → persisted run, for any single lifecycle step.
- `features/lifecycle/pipeline.py` (`LifecyclePipeline`) threads ONE `LifecycleRun` through an ordered phase ladder (IMPLEMENTATION→QA→SECURITY→CODE→CLOSURE), each step running on its declared `AgentRuntimeKind` via an injected runtime factory, persisting at every step and stopping at the first blocked gate. Each `PipelineStep` carries a **discrete model** chosen from the selected harness's catalog (the hardcoded `"sonnet"/"opus"` tiers were removed in v0.1.24; default model is derived from `core/harness_models.py`).
- `core/harness_models.py` (v0.1.24) is the discrete per-harness GPT model catalog (LAW 2): `harness → ordered model options` with a `validate(harness, model) → (model_id, effort?)` helper, consistent with — but not a tier-view of — `core/model_registry.py`. **pi → 3:** `(gpt-5.5,high)`, `(gpt-5.5,low)`, `(gpt-5.3-codex,medium)`; **codex → 2:** `(gpt-5.5,high)`, `(gpt-5.5,medium)`. Both catalogs are GPT-only (PI runs on the operator's Codex subscription); no `claude-*` id is ever a Layer-2 option. An invalid `(harness, model)` pair is rejected with the valid set.
- `features/lifecycle/fragments/loader.py` (v0.1.24) loads + validates the prompt-fragment library at `dadaia_workspace/public/lifecycle_fragments/` (Markdown + frontmatter `id/role/workflow/step/static_inputs/dynamic_inputs/output_schema/max_context_policy`; projected + manifest-tracked). `features/lifecycle/context_selector.py` selects dynamic context per step under explicit max-context policies (`exact-files-only`/`summary`/`catalog-only`/`diff-only`/`previous-handoff-only`). `features/lifecycle/workflows/release_definition.py` is the first fully fragment-driven dadaia-workflow: each step's prompt is `role + fragment bundle + selected context + output schema + discrete (harness, model)`, Python owns step order and blocks on missing/rejected handoffs. Backlog/audit/research/bug-report workflow bodies are scaffolded + fail-loud (`NotImplementedError("deferred to follow-up release")`).
- `features/lifecycle/prompt_builder.py` builds scoped worker prompts; `PromptPrefix.from_sections` assembles a byte-identical, sha256-hashed, order-independent context block, and `build(scope, prefix=)` prepends it verbatim and records `prefix_hash`. The pipeline builds the prefix once and every step reuses the same bytes (provider-cache-friendly). Whole-workspace or repo-wide scopes are rejected. v0.1.24 adds a fragment-suffix path: a workflow step's prompt is assembled from a fragment bundle (not the generic "Run the step" suffix). **Prompt observability (v0.1.24):** each lifecycle run record persists, per step, the fragment ids, dynamic context refs, `prefix_hash`, the discrete model, the runtime kind, the output schema, and the gate result — surfaced in a panel/report view; whole-memory injection is never the default (context selection is scoped).
- `features/lifecycle/hygiene.py` owns the canonical `SlopPolicy`: reports TTL 48h, handoffs TTL 24h, tmp TTL 24h, safe-zone cleanup, protected residuals, unknown `.dadaia/` top-level detection, malformed/orphan handoffs, and elapsed scan metrics.
- `features/lifecycle/antislop/slop_scan.py` is the directory-aware slop metric: a directory tree counts as ONE entry with recursive size (closing the directory-blind gap where multi-GB caches/venvs hid from the file-only metric); the canonical manifest derives from `hooks/root_whitelist._WHITELIST`, never hand-copied. Surfaced via `dadaia lifecycle slop`.
- `features/lifecycle/antislop/retention.py` (`RetentionSweep.sweep`) is the deleter: dry-run by default, deletes only with `apply=True`; reclaims past-TTL non-canonical swept-zone entries; has a HARD liveness gate (never reclaims a live run's tmp); refuses canonical/outside-`.dadaia`/symlink-escape paths (resolve + relative_to, TOCTOU re-confine). Surfaced via `dadaia lifecycle clean [--apply]`.
- `features/lifecycle/report_workflow.py` writes human report HTML, matching handoff JSON, baseline/final hygiene snapshots, and optional explicit cleanup.
- `features/lifecycle/run_store.py` and `infrastructure/json_lifecycle_run_store.py` persist lifecycle run records under canonical workspace state/run zones and reject repo-tree stores.

## Harness runtime boundary

Lifecycle code depends on `AgentRuntimePort`; `build_agent_runtime(kind, *, cwd=None, model=None)` in `container.py` is the factory that maps a kind to its adapter: `FAKE→FakeAgentRuntime`, `CODEX_EXEC→CodexExecAdapter` (`infrastructure/codex_runtime.py`), `CLAUDE_SDK→ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`), `PI_HEADLESS→PiHeadlessAdapter` (`infrastructure/pi_runtime.py`). (`OPENCODE_RUN`/`OpenCodeAdapter` were removed entirely in v0.1.24.) The factory stays total over the enum and threads the discrete `model` into `PiHeadlessConfig.model` (PI honors `pi --model <id>`) and `CodexExecConfig.model`+`reasoning_effort` (Codex takes the discrete `(id, effort)` verbatim; the tier fallback remains only when no discrete model is given). **LAW 1:** the workflow `--harness` choices are `{pi, codex, fake}`; `claude` is rejected with a Layer-1 pointer (the SDK adapter stays importable + unit-tested). `--harness pi` / `--step-harness x=pi` + `--model`/`--step-model` resolve across every `dadaia lifecycle` verb with zero change to `phase_workflow.py` / `pipeline.py`. CI uses the fake runtime to prove that Python advances only after structured output and write-scope evidence pass validation.

The Codex adapter does not read project-local provider/auth/profile configuration, does not pass through `os.environ`, accepts only an explicit environment allowlist, redacts credential-looking values, and records sandbox/profile widening only when operator-controlled input requests it. The Claude SDK adapter derives a real Ring-1 `write_permission` decider from the request's allowed/forbidden paths via the same `core/scope_match` classifier the runner's Ring-2 uses; its transport is injectable (`query_fn`) so permission + result mapping are tested hermetically. `claude-agent-sdk` is an OPTIONAL, operator-installed runtime extra (not a locked dependency, offline-first build); the default transport lazily imports it and returns an actionable `pip install claude-agent-sdk` message when absent.

The PI adapter (`PiHeadlessAdapter` + frozen `PiHeadlessConfig`) is a structural twin of `CodexExecAdapter`: it drives `pi --mode json --tools <csv> -p -` (prompt on stdin) over an injectable subprocess runner, imports no PI client at module load (offline-first preserved), and accepts only an explicit env allowlist (incl. `ANTHROPIC_API_KEY`, redacted from output). Result mapping parses the line-delimited JSON stream and takes the **last** `message_end` event's assistant text from `message.content`, handling both string and content-block shapes; an absent or unparseable `message_end` degrades to raw stdout as the summary (SUCCEEDED, never crashes), and a fenced JSON block matching the request's `expected_schema` populates `structured_output`. A valid terminal `message_end` maps to SUCCEEDED **even when `pi` exits non-zero** — the terminal assistant message is trusted over the raw exit code (deliberate precedence); the downstream verdict gate and the Ring-2 write boundary still apply. PI's Ring-2 write boundary is real: `changed_paths` is computed from the injected git client's `diff_name_only(cwd)` (working-tree + staged + untracked, non-ignored) at result time and written into `structured_output["changed_paths"]`, **unconditionally overwriting any model self-report** — so the runner's Ring-2 out-of-scope block fires for PI exactly as for Codex/OpenCode. The Layer-2 `PI_HEADLESS` worker (this adapter, `pi --mode json` headless) has no CLI-level pre-disk (Ring-1) gate: its enforcement posture is Ring-2 + git chokepoints, identical to Codex/OpenCode. (The **Layer-1** interactive `pi` entry harness is separate and DOES have a Ring-1 SDD-gate extension — `.pi/extensions/dadaia-sdd-gate.ts`, WS-PI-4, active post-trust — see [[architecture]] §"two-layer agentic model".) The first-layer `.pi/` projection (WS-PI-3) shipped in v0.1.18 and the Layer-1 Ring-1 extension (WS-PI-4) in v0.1.21; both are no longer deferred. The live `pi --mode json` event schema — specifically the `AgentMessage.content` shape — is the one upstream-owned unverified seam, verified via the opt-in `DADAIA_PI_LIVE=1` integration test (`tests/integration/pi_live/`), not CI-gated.

## Workflow model governance (control plane, v0.1.28)

Layer-2 model selection is **governed**, not ad hoc: a named profile registry layered over
the discrete `harness_models` catalog, a validated operator overlay, one shared resolver,
and a per-run policy snapshot. The resolver is the single policy seam consumed by both the
CLI and the panel (see [[panel]] for the panel control plane).

- `features/lifecycle/model_profiles.py` — the built-in `WorkflowModelProfile` registry
  (D-2: **built-in only**). Five profiles: Codex `codex-implementation-standard`
  (`gpt-5.5:medium`), `codex-review-deep` (`gpt-5.5:high`); PI `pi-implementation-standard`
  (`gpt-5.3-codex:medium`), `pi-reasoning-high` (`gpt-5.5:high`), `pi-reasoning-low`
  (`gpt-5.5:low`). Each profile resolves to a real `harness_models.HarnessModelOption`; an
  import-time `_assert_profiles_resolve` (mirrors `_assert_ids_known`) fails loudly on any
  ungoverned `(model_id, effort)` pair, a `claude-*` id (GPT-only Layer-2 invariant), a
  non-Layer-2 harness, a duplicate id, or a deprecated profile without a known replacement —
  so this is **never a second drifting model table**. Accessors: `list_profiles`,
  `profiles_for(harness)`, `resolve(profile_id) → WorkflowModelProfile`, `to_option`.
- `core/models/workflow_execution.py` — the pure DTOs threaded through every layer:
  `WorkflowModelProfile`, `ResolvedModelConfig` (`profile_id, harness, model, reasoning,
  source`), and `WorkflowPolicySnapshot` (`workflow_id, policy_id, resolved_at,
  source_precedence[], steps{step → {harness, model_profile, model, reasoning, fragments[],
  output_schema}}`). Zero I/O, core-clean.
- `infrastructure/json_workflow_model_policy_store.py` — the atomic overlay store over the
  FIXED path `.dadaia/states/workflow_model_policy.json` (schema `workflow-model-policy-v1`).
  Reuses the `JsonLifecycleRunStore` atomic temp+rename pattern (`mkstemp` 0600 in target dir
  → `os.replace`); `load()` returns `None` on missing (⇒ library defaults); raises a typed
  error on invalid JSON / unknown top-level field; `save()` writes `.last-good.json` from the
  prior valid file before overwriting. **Missing ≠ invalid:** absent file = defaults; a
  present-but-invalid overlay blocks execution before the first model call with the last-good
  intact. Only the `default` context is honored this release (D-2).
- `features/lifecycle/policy_resolver.py` — the single shared
  `WorkflowExecutionPolicyResolver` over the governed catalog + profile registry + overlay.
  `resolve(workflow_id, context, cli_overrides) → WorkflowPolicySnapshot` applies the
  precedence **CLI > context overlay > default overlay > library default**, validating every
  override against catalog step ids + profile ids + harness match (a deprecated profile
  without an explicit replacement path is a hard failure).
- `core/models/lifecycle.py` (extended) — `AgentRunRequest.resolved_model:
  ResolvedModelConfig | None` (additive; `model_profile` kept for observability) and
  `LifecycleRun.workflow_policy: WorkflowPolicySnapshot | None` (additive optional; old v1
  records load to `None` — the run-store schema literal is deliberately unchanged for
  back-compat read).
- **Resolve-once-before-step-1 (LAW 7).** The pipeline/phase workflow resolve the policy and
  freeze the snapshot onto `LifecycleRun.workflow_policy` **before** the first worker call;
  the snapshot is preserved across transitions via `dataclasses.replace`. An overlay mutated
  after a run starts does not change the in-flight run; the panel reads the persisted
  snapshot for run history (current policy only governs future runs).
- **Adapters consume the resolved model (AC-12).** `CodexExecAdapter` prefers
  `request.resolved_model` in `_model_and_effort` and passes `-m <id> -c
  model_reasoning_effort=<effort>`; `PiHeadlessAdapter._command()` adds `--model <id>` from
  the per-request resolved model; `FakeAgentRuntime` echoes the resolved config so tests
  assert policy resolution offline. The model string that reaches argv is the profile's
  registry-constant `model_id` (D-3: no free-text reaches a worker).
- **CLI (D-3).** `--step-model <step>=<profile-id>` resolves through the profile registry; a
  raw `<id>:<effort>` string / unknown / harness-mismatched / deprecated profile is rejected
  with an actionable message. `--show-policy` + `--json` print the resolved policy.
  Read-only `dadaia lifecycle workflow policy show <workflow> --context --json` and
  `workflow profiles list --harness --json` make the governance scriptable.
- **Governed catalog (Wave B).** `features/workflows/dadaia_catalog.py` carries each step's
  `default_harness` + `default_profile` per supported harness + fragment ids, and is the
  single governed source the resolver and panel both read (`_assert_catalog_defaults_resolve`
  ties every default profile to the registry at import). The old `*.workflow.md`
  (`WorkflowsService.get_detail`/`list_summaries`) is **reference/doc-only** — no longer the
  authority for executable workflow behavior.
- **Governance doctor (AC-10).** `dadaia lifecycle workflow doctor` runs the `WMP-*`
  invariants (`policy_doctor.py`): invalid policy JSON, unknown profile, harness/profile
  mismatch, stale workflow/step id in an override, missing default profile per supported
  harness, unresolved fragment/output schema, and any `claude`/`opencode` Layer-2 residue
  (`WMP-LAYER2-RESIDUE`). A `public doctor` workflow-policy residue scan
  (`policy_public_doctor.py`) keeps the public surface clean. Doctor never crashes the panel.

## Harness as a governed dimension (v0.1.29)

The harness is now a **first-class governed dimension** alongside the model, so PI is fully
usable as a Layer-2 worker through governance (not just as an execution adapter). The same
shared resolver moves a step onto PI from three paths — the CLI, a persisted overlay, and
the panel toggle — and the executed adapter and the recorded snapshot always agree.

- **Effective-harness precedence (D-1).** `resolve()` takes harness inputs (a per-workflow
  default-harness override and a `{step → harness}` map) and reads the overlay's harness
  fields, computing the effective harness per step with the precedence
  **CLI `--step-harness` > CLI `--harness` > overlay step harness > overlay `default_harness`
  > catalog step default** (`_resolve_harness`). The chain is total: every governed step has
  a catalog `default_harness` (`_DEFAULT_WORKER_HARNESS = codex`), so no step is left without
  an effective harness.
- **Profile validated against the effective harness.** `_validate_profile` compares
  `profile.harness` to the step's **resolved** harness, not the catalog default — fixing the
  v0.1.28 `policy_resolver.py:288` mismatch that rejected a PI profile on a codex-default
  step. A CLI mismatch (e.g. `--harness pi` + a codex `--step-model`) resolves to a clean
  rejection, not ambiguity.
- **Auto-profile-on-harness-override (D-1).** When a step's harness is overridden with **no**
  explicit profile override (neither CLI `--step-model` nor overlay step profile), the
  library default becomes `CatalogStep.default_profiles[effective_harness]` — the harness's
  default profile for the step's purpose (producing step → standard profile, review/gate step
  → deep/reasoning profile). The per-harness default profiles live on the catalog DTO; the
  resolver reads the effective harness's entry instead of only `default_profile`.
- **Single source of truth for `runtime_kind` (D-2).** `pipeline.apply_resolved_policy` is
  the **sole** author of each `PipelineStep.runtime_kind`, derived from the snapshot entry's
  resolved harness (codex → `CODEX_EXEC`, pi → `PI_HEADLESS`; an unmappable harness raises).
  The CLI's separate post-resolve `runtime_kind` swap was removed, so the executed adapter
  and the persisted snapshot provably agree — fixing the v0.1.28
  codex-recorded-while-pi-ran divergence. **FAKE is preserved:** a step built on
  `AgentRuntimeKind.FAKE` keeps FAKE (so `--harness fake` dry-runs still drive the fake
  adapter) while the snapshot records the governed harness.
- **Overlay carries harness (D-3).** The overlay schema + store carry an optional per-step
  `harnesses` map and a per-workflow `default_harness` (Layer-2 enum `codex|pi`, store +
  schema widened in lockstep, `additionalProperties:false` kept). Accessors `step_harness`
  and `workflow_default_harness` (default context only). **Back-compat:** an overlay with no
  harness field resolves byte-identically to v0.1.28 (catalog default codex). The panel
  codex/pi toggle persists a real harness change through `PUT /api/workflow-model-policy`;
  the resolver honors it (see [[panel]]).
- **Completed governed catalog — 7 workflows (D-4).** `closure` is cataloged as its real
  single `close` worker step (role product-engineer, generic/no-fragment) plus the Python
  `closure_removal_gate` modeled as a gate; `governed_workflow_catalog()` projects the
  `close` step so `policy show closure` resolves. `audit` / `research` / `bug_report` (the
  three `_deferred.DEFERRED_WORKFLOWS` names) are enumerated as `deferred` with zero governed
  steps — inspectable at the catalog/panel layer; `resolve(<deferred>)` raises the actionable
  "no governed steps" error (correct, not a gap). No invented model-step ladders, no second
  drifting source.
- **Doctor validates the harness dimension (D-doctor).** `dadaia lifecycle workflow doctor`
  resolves every overlay harness override through the shared resolver, so an overlay harness
  referencing a harness the step does not support is a hard ERROR; an overlay harness value
  of `claude`/`opencode` is `WMP-LAYER2-RESIDUE`. WMP-1..WMP-7 pass over the completed
  catalog (the generic `close` step is WMP-5-exempt — no false positive).

Carried-forward laws hold unchanged: Layer-2 = codex|pi only (`fake` test-only;
`claude`/`opencode` rejected); default-first (unconfigured → library defaults, codex);
auditability snapshot frozen before step 1 and read verbatim for history; panel governance
via validated overlay; resolve-once-before-step-1.

> Still deferred (v0.1.28 D-2): operator-added PI profiles
> (`.dadaia/states/workflow_model_profiles.local.json`, not loaded — built-in profiles only)
> and per-context overlays + `extends` inheritance (only the `default` context is honored; a
> non-`default` key is inert).

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
APPROVED-verdict requirement for non-review phases); the full runnable
backlog/audit/research/bug-report workflow bodies (scaffolded + fail-loud only in v0.1.24);
**live pi/codex worker runs of the fragment-driven release-definition workflow** (the FAKE
e2e proves the seam; live confirmation against real PI/Codex workers is deferred to real
use — the upstream CLI contracts cannot be proven by mocked tests); and persisting explicit
per-run tmp working-dir claims in `LifecycleRun` so the retention liveness provider keys on
a registered workdir.
