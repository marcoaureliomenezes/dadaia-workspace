# TASKS — Release: multiharness-engine-v0116

**Status:** Aprovado
**Release ID:** multiharness-engine-v0116
**Owner:** product-engineer
**Created:** 2026-06-24

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
TDD-first: each task lands its failing test before the fix. Maximum one `[-]` per owner unless tasks
have disjoint write sets as declared. Hard spine: T-016-00 → 01 → {02,03} → 04 → 05 → 06 → 07.

---

## Pre-work

### [x] T-016-00 — Release start: ACTIVE.md → multiharness-engine-v0116 IMPLEMENTATION
- **Owner:** product-engineer
- **Write set:** `specs/releases/ACTIVE.md`
- **Acceptance:** `ACTIVE.md` reads `release: multiharness-engine-v0116` / `phase: IMPLEMENTATION`
  with SPEC/PLAN/TASKS `**Status:** Aprovado`.
- **Parallelism:** first, before all waves.

---

## W1 — Runtime kinds

### [x] T-016-01 — Add CLAUDE_SDK + OPENCODE_RUN to AgentRuntimeKind
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/lifecycle.py`, `tests/unit/core/test_agent_runtime_kind.py`
- **Acceptance:** enum has FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN; `AgentRunRequest` to_dict /
  from_dict round-trips all four; test asserts `AgentRuntimeKind(v.value) == v` for every member.

---

## W3 — OpenCode adapter stub (disjoint from W4)

### [x] T-016-02 — OpenCodeAdapter stub behind the port
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/opencode_runtime.py`,
  `tests/unit/infrastructure/test_opencode_runtime.py`
- **Acceptance:** implements `AgentRuntimePort` (`@runtime_checkable` passes);
  `runtime_kind() == OPENCODE_RUN`; `run(request)` raises `NotImplementedError` whose message names
  the deferred workstream and the unverified `opencode run` API. Test asserts isinstance-of-port and
  the raise + message substring.

---

## W4 — Claude SDK adapter stub (disjoint from W3)

### [x] T-016-03 — ClaudeSdkAdapter stub behind the port
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/claude_sdk_runtime.py`,
  `tests/unit/infrastructure/test_claude_sdk_runtime.py`
- **Acceptance:** implements `AgentRuntimePort`; `runtime_kind() == CLAUDE_SDK`; `run(request)`
  raises `NotImplementedError` whose message names `claude-agent-sdk` + the deferred live
  integration. No import of `claude_agent_sdk` / `anthropic` at module load. Test asserts the raise +
  no-import.

---

## W2 — Runtime factory (depends on W1, W3, W4)

### [x] T-016-04 — build_agent_runtime factory in container.py
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `tests/unit/test_build_agent_runtime.py`
- **Acceptance:** `build_agent_runtime(kind, *, cwd=None) -> AgentRuntimePort` returns
  `FakeAgentRuntime` for FAKE, `CodexExecAdapter` for CODEX_EXEC, `OpenCodeAdapter` for OPENCODE_RUN,
  `ClaudeSdkAdapter` for CLAUDE_SDK; the returned port's `runtime_kind()` equals the requested kind
  (FAKE may map to a fake whose kind is FAKE); unknown / unhandled kind raises a clear `ValueError`.
  Test parametrizes all four kinds + the error path.

---

## W5 — Integration proof

### [x] T-016-05 — Factory-built FAKE runtime drives LifecycleAgentRunner green
- **Owner:** software-engineer
- **Write set:** `tests/unit/features/lifecycle/test_runner_with_factory_runtime.py`
- **Acceptance:** `LifecycleAgentRunner(runtime=build_agent_runtime(FAKE, …))` produces an accepted
  `TransitionDecision` for a well-formed request — proving the factory output satisfies the runner's
  injection contract end-to-end.

---

## Verification + closure

### [x] T-016-06 — Full local gate green
- **Owner:** software-engineer / qa-engineer
- **Acceptance:** `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` all green;
  `_repo_root_write_guard` clean; no new venvs. QA review handoff recorded.

### [ ] T-016-07 — CLOSURE (deferred to rc / operator ship decision)
- **Owner:** product-engineer
- **Write set:** `specs/releases/multiharness-engine-v0116/CLOSURE.md`, `specs/memory/**`,
  `specs/releases/ACTIVE.md`
- **Acceptance:** CLOSURE.md with evidence triples; memory atoms updated (DEFINITION/CLOSURE phase
  only); release archived. **Held** until the operator chooses to ship alpha-1 or iterate to alpha-2
  (WS-1 per-phase workflows).

---

## W6 — Alpha-2: first real engine-driven verb (WS-1 slice)

### [x] T-016-08 — LifecyclePhaseWorkflow + wire review verbs to the engine
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/phase_workflow.py`,
  `dadaia_workspace/container.py` (`build_lifecycle_phase_workflow`),
  `dadaia_workspace/cli/commands/lifecycle.py` (`review qa|security|code`),
  `tests/unit/features/lifecycle/test_phase_workflow.py`,
  `tests/integration/test_lifecycle_review_cli.py`,
  `tests/integration/cli/test_lifecycle_command_skeletons.py` (drop the 3 review skeletons).
- **Acceptance:** `LifecyclePhaseWorkflow.run(...)` threads scoped prompt → factory-selected
  `AgentRuntimePort` → `LifecycleAgentRunner` gate → legal transition → persisted `LifecycleRun`.
  `dadaia lifecycle review {qa,security,code} --harness fake|codex|claude|opencode --release-id <id>`
  runs the engine (no longer `unavailable_workflow`): FAKE worker (no APPROVED verdict) BLOCKS with
  the real gate reason and persists the run; an injected APPROVED result advances the phase. Gate
  green (ruff/mypy --strict/pytest 3325). **NOTE:** `decision.accepted` is True even for a legal
  transition INTO BLOCKED — pass/fail is `run.blocked is None`.
- **Done:** alpha-2; QA review gate recorded.

---

## W7 — Alpha-3: every single-step lifecycle verb runs the engine

### [x] T-016-09 — Wire backlog/release/implement/close to the engine; retire the stub layer
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py` (generalize `_run_review` →
  `_run_phase_step`; wire `backlog define`, `release define`, `implement`, `close`),
  `dadaia_workspace/features/lifecycle/service.py` (remove dead `unavailable_workflow`),
  `tests/integration/cli/test_lifecycle_command_skeletons.py` (assert all 7 verbs drive the engine),
  remove redundant `tests/integration/test_lifecycle_review_cli.py`.
- **Acceptance:** all seven single-step verbs (`backlog define`, `release define`, `implement`,
  `review {qa,security,code}`, `close`) run `LifecyclePhaseWorkflow` on a `--harness`-selectable
  runtime over a legal transition; the `unavailable_workflow` service method + CLI helper are deleted
  (no dead stub layer). Integration test proves every verb blocks on the real gate with FAKE.
  Gate green (ruff/mypy --strict/pytest 3322). QA review gate recorded.
- **Done:** alpha-3.
- **Known simplification (tracked):** the runner applies a uniform APPROVED-verdict gate to every
  step, so non-review phases (implement/define) also require the worker to emit an APPROVED handoff.
  Phase-specific gating (e.g. implement needs evidence, not self-approval) is a follow-up runner
  refinement, not this release.

---

## W8 — WS-4: live Claude Agent SDK adapter (optional extra)

### [x] T-016-10 — ClaudeSdkAdapter with real Ring-1 write boundary + injectable transport
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/claude_sdk_runtime.py`,
  `dadaia_workspace/features/lifecycle/scope_match.py` (NEW, shared Ring-1/Ring-2 matcher),
  `dadaia_workspace/features/lifecycle/agent_runner.py` (use the shared matcher),
  `tests/unit/infrastructure/test_claude_sdk_runtime.py`,
  `tests/unit/features/lifecycle/test_scope_match.py`.
- **Acceptance:** `ClaudeSdkAdapter` implements `AgentRuntimePort`; derives a Ring-1
  `write_permission` decider from the request's allowed/forbidden paths via the SAME
  `scope_match` the runner's Ring-2 uses (one classifier, two boundaries); maps a Claude run
  to `AgentRunResult` (verdict/changed_paths/artifacts); transport is injectable (`query_fn`) so
  permission + mapping are tested hermetically. `claude-agent-sdk` is an **optional,
  operator-installed runtime extra** — NOT a locked dependency (offline-first build); the default
  transport lazily imports it and returns a FAILED result with an actionable
  `pip install claude-agent-sdk` message when absent. Gate green (ruff/mypy --strict/pytest).
- **Done:** WS-4 core.
- **LIVE-VERIFICATION CAVEAT (tracked):** the exact `claude-agent-sdk` `query()`/`can_use_tool`
  binding is isolated in `_default_query_fn` and must be confirmed the first time the package is
  installed in a networked env. Offline here (no network, lock-pinned), so the SDK call line is the
  one unverified piece; all engine-depended logic (Ring-1 decider + result mapping) is real + tested.
- **CLOSURE follow-up:** record `claude-agent-sdk` as an optional runtime extra in tech-stack memory.

---

## W9 — WS-3: collapse the reference-only markdown-orchestrate layer

### [x] T-016-11 — Retire the dead dispatch path; .workflow.md become docs-only
- **Owner:** software-engineer
- **Write set:** delete `core/protocols/agent_dispatcher.py`, `infrastructure/{claude,cli,codex}_agent_dispatcher.py`,
  `features/orchestration/{runner,resolver}.py`; rewire `features/orchestration/service.py`
  (dispatcher-free, read-only), `container.py` (drop `_select_dispatcher` + `build_orchestration_service`
  dispatcher), `cli/commands/orchestrate.py` (`run`/`resume` → honest "moved to lifecycle" no-op),
  `infrastructure/workflow_launcher_adapter.py`, `public/workflows/*.workflow.md` (docs-only banner);
  migrate/delete ~60 dispatcher/execution tests.
- **Acceptance:** the four reference-only `AgentDispatcher`s (which spawned nothing) and the
  `orchestrate` execution path are gone; `OrchestrationService` no longer takes a dispatcher and keeps
  only read-only listing; `dadaia orchestrate run <wf>` exits 0 with a message steering to
  `dadaia lifecycle`; `.workflow.md` are reference docs only. **Panel remains intact** (loads, lists,
  launcher target exits 0 — verified). Gate green (ruff/mypy --strict/pytest).
- **Done:** WS-3.
- **CLOSURE follow-up:** re-stage/install the edited `public/workflows/*.workflow.md` projection
  (`dadaia public stage && install`) so the live instance reflects the docs-only banner.

---

## W10 — WS-1 multi-step: the release pipeline with per-step harness mixing

### [x] T-016-12 — LifecyclePipeline (implement→qa→security→code), harness-mixable per step
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/pipeline.py` (NEW),
  `dadaia_workspace/container.py` (`build_lifecycle_pipeline`),
  `dadaia_workspace/cli/commands/lifecycle.py` (`pipeline` verb + `--step-harness`),
  `tests/unit/features/lifecycle/test_pipeline.py`,
  `tests/integration/cli/test_lifecycle_pipeline_cli.py`.
- **Acceptance:** `LifecyclePipeline.run(run_id, steps)` threads ONE `LifecycleRun` through an
  ordered phase ladder (IMPLEMENTATION→QA→SECURITY→CODE→CLOSURE), each step on its declared
  `AgentRuntimeKind` via an injected runtime factory (so claude-implements / codex-reviews mixing is
  a per-step adapter swap), persisting at every step and stopping at the first blocked gate.
  `dadaia lifecycle pipeline --release-id <id> --harness <default> --step-harness label=kind`
  drives the canonical `implementation_ladder`; with FAKE it blocks at `implement` (no verdict).
  Gate green (ruff/mypy --strict/pytest). This is the headline multi-harness workflow.
- **Done:** WS-1 multi-step (single-step verbs were T-016-08/09).

---

## W11 — WS-6 anti-slop self-governance: directory-aware slop metric + CLI visibility

### [x] T-016-13 — Directory-aware slop metric (`slop_scan`) + `dadaia lifecycle slop`

Close the directory-BLIND gap (D3/D4): the existing `LifecycleHygieneService._cleanup_candidates`
only matches `path.is_file()`, so multi-GB dir trees (venvs/caches) hide from the metric. Add a
read-only, directory-aware slop metric whose canonical manifest derives from
`hooks/root_whitelist._WHITELIST` (never a hand-maintained copy), plus a `dadaia lifecycle slop`
CLI command that emits counts + total bytes + top offenders.

- NEW `features/lifecycle/antislop/slop_scan.py`: `SlopEntry`, `SlopReport`, `slop_scan(...)` — pure,
  injected clock, NO FS mutation, directory tree counts as ONE entry with recursive size.
- `cli/commands/lifecycle.py`: `dadaia lifecycle slop [--json]` (read-only).
- `container.py`: wiring helper.
- Tests: hermetic `tmp_path` + injected clock (no real venvs); dir-tree counted once with recursive
  size; non-swept stray not counted; past-TTL vs fresh straddle; drift-guard test
  (manifest derives from `root_whitelist._WHITELIST`); CLI smoke.
- Scope = metric + visibility only; full retention-sweep consolidation (D5) stays deferred.
- **Done.** Also bundles the fix for bug `infrastructure-claude-sdk-imports-features-scope-match`
  (a WS-4/T-016-10 layering break surfaced by `lint-imports`): `scope_match` moved
  `features/lifecycle/ → core/`; `lint-imports` now 6 kept / 0 broken.

## W11b — D5: directory-aware retention SWEEP (the deleter)

### [x] T-016-15 — RetentionSweep (`retention.py`) + `dadaia lifecycle clean`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/antislop/retention.py`,
  `dadaia_workspace/features/lifecycle/hygiene.py` (`protected_refs` accessor),
  `dadaia_workspace/cli/commands/lifecycle.py` (`clean` command),
  `dadaia_workspace/container.py` (`build_retention_sweep` + live-claims provider),
  `tests/unit/features/lifecycle/test_retention_sweep.py`,
  `tests/integration/cli/test_lifecycle_clean_cli.py`.
- **Acceptance:** `RetentionSweep.sweep(*, apply=False)` is dry-run by default and deletes
  only with `apply=True`; reclaims past-TTL/non-canonical swept-zone entries (dir trees via
  rmtree, files via unlink); HARD liveness gate (never reclaims a live lifecycle run's tmp,
  D6); important-protected; refuses canonical/outside-.dadaia/symlink-escape paths;
  idempotent with injected clock; returns a typed `RetentionResult`. `dadaia lifecycle clean
  [--apply] [--json]` (default dry-run) delegates to it. Gate green (ruff/mypy --strict/
  pytest) + lint-imports 6 kept / 0 broken.
- **Follow-up (out of scope this pass):** rewire legacy `dadaia clean` / `reports cleanup`
  onto `RetentionSweep`; persist explicit per-run tmp working-dir claims in `LifecycleRun`
  so the liveness provider keys on a registered workdir rather than `expected_artifacts`.
- **Done:** D5 deferred line item, now implemented.

## W12 — WS-7: cacheable prompt prefix + step model-tiering

### [x] T-016-14 — PromptPrefix (deterministic, hashed) reused per step + per-step tiers
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/prompt_builder.py` (`PromptPrefix`,
  `build(..., prefix=)`), `dadaia_workspace/features/lifecycle/pipeline.py`
  (`PipelineStep.model_profile`, prefix reuse, tiered `implementation_ladder`),
  `dadaia_workspace/container.py` (`build_lifecycle_pipeline(..., prefix=)`),
  `tests/unit/features/lifecycle/test_prompt_prefix.py`, `test_pipeline.py` (reuse+tier test).
- **Acceptance:** `PromptPrefix.from_sections` assembles a byte-identical, sha256-hashed stable
  context block (sorted → order-independent); `build(scope, prefix=p)` prepends it verbatim and
  records `prefix_hash`; the pipeline builds the prefix ONCE and every step reuses the same bytes
  (provider-cache-friendly, EPIC D11); steps carry model tiers (implement=sonnet, reviews=opus).
  Gate green (ruff/mypy --strict/pytest + lint-imports 6/0).
- **Done:** WS-7 core. Follow-up: assemble the prefix from real release context + wire provider
  cache-control markers in the live Claude adapter (pending SDK live-binding verification).

---

## W13 — D12: bounded AI-surface collapse (the 3 full-collapse skills)

### [x] T-016-16 — Trim engine-owned ordered mechanics out of 3 skills (keep identity/judgment)
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/skills/{dadaia-task-manager,dadaia-step0-memory-bootstrap,project-orchestration}/SKILL.md` (source; projected via `public stage`/`install`).
- **Acceptance:** the ordered pass/fail mechanics these skills duplicated — now owned by the engine
  (`state_machine.py` TRANSITIONS, `gates.py`, `pipeline.py`/`phase_workflow.py`, `prompt_builder.py`
  PromptPrefix) — are trimmed to concise engine pointers; ALL identity/scope/refusal/rubric/contract
  vocabulary is KEPT (the orchestration contract terms were restored after an over-trim caught by the
  contract test). −92 lines total. `dadaia public doctor` `[ok] public-privacy` exit 0; projection
  consistent across `.claude/.codex/.opencode`; `ci preflight` green + `lint-imports` 6/0.
- **Done:** D12 bounded full-collapse subset.
- **CAVEAT (tracked):** full shadow-validation (engine verdict matching human discipline over a live
  release) is not yet possible — engine doesn't drive live releases. This is the design-complete,
  REVERSIBLE trim. PARTIAL skills + rules + AGENTS.md collapse remain a follow-up after shadow-validation.

---

## Status of the engine workstreams (multiharness-engine-v0116)

**DONE on feature/v0.1.16:** runtime kinds + factory (W1–W5) · single-step verbs (WS-1 slice,
T-016-08/09) · WS-4 Claude adapter Ring-1 · WS-3 orchestrate collapse · WS-1 multi-step pipeline ·
WS-6 slop metric · WS-7 prompt prefix + tiers.

**REMAINING (deferred):**
- **D5** — directory-aware **retention SWEEP** consolidation (the deleter; WS-6 shipped the metric).
- **D12** — AI-surface reduction execution (designed, shadow-validated fast-follow).
- **Live Claude SDK binding** verification (first networked install) + provider cache-control wiring.
- **Phase-specific gate** refinement (drop the uniform APPROVED-verdict requirement for non-review
  phases) — tracked simplification from T-016-09.
