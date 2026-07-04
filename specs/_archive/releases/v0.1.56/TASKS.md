# TASKS — v0.1.56 — Lifecycle Verb Governance

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets:
`cli/commands/lifecycle.py` W1-W3, `pipeline.py` W1+W3, `container.py` W1-W2) are sequential — one
owner, no parallel `[-]`. Every implementation-wave task: **NO `specs/backlog/**` paths staged**
(both consumed anchors survive → archival is a CLOSURE step, T-56-60). Every move/rename/repoint
grep **includes `tests/` AND non-import textual references** (docstrings/comments). AC-7
mutation-sanity: each new test is sabotaged → shown to FAIL → reverted, captured on the task line.

## W0 — definition

- [x] T-56-01 SPEC/PLAN/TASKS authored from the 2026-07-03 **verb-by-verb code read** (not a dossier
  restatement): the verb→governance matrix derived by reading `cli/commands/lifecycle.py`,
  `pipeline.py`, `phase_workflow.py`, `release_definition.py`, `governed_catalog.py`, `agent_runner.py`,
  `state_machine.py`, `container.py` — confirmed ONLY `pipeline` is resolver-governed; `run_implement_review_loop`
  drops the digest (l.309) + bypasses the runner gate (`_run_loop_worker` l.375) + has zero prod
  callers; audit/research/bug_report are real bodies, AVAILABLE, with no builder/verb; the three
  review→implementation TRANSITIONS edges are unused. Mandatory release-definition grill on the
  picked set (1 backlog; open-bug debt 0). **Dual definition review (software-architect REJECT +
  qa-engineer REJECT — strongly convergent) — ALL amendments folded:** R-1 structural-only loop gate
  (architect A3 ≡ qa A3); R-2 `apply_entry_to_step` + structural `PolicyApplicableStep` Protocol
  (architect A2 × qa A2); R-3 FAKE-preservation seed (architect A5); R-4 FR2 workflow-body seam
  (architect A1); R-5 in-scope bug_report fake + structural ADDITIVE assertion (architect A4); R-6
  run-store AC-1 channel (architect A6 ≡ qa A7); + qa A1 (7 verbs), A4 (loop-test-fate ledger), A5 (3
  inverted CLI-test rewrites), A6 (frozenset pins), A8 (workflow-vs-verb count), A9 (public-asset note);
  + the `--model` **non-fatal deprecation-warning** ruling. **Decisions RATIFIED:** A = FR2 WIRE
  (conditioned on R-4+R-5); B = FR4 REMOVE. Archival-at-CLOSURE (both anchors survive). `Aprovado` after
  QA re-verify; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 policy resolver on every run-a-worker verb

- [x] T-56-10 Route all **7 verbs** — `release define`, `backlog define`, `implement`, `review qa`,
  `review security`, `review code`, `close` — through the shared resolver; retire the raw
  `<id>:<effort>` path. **AC-7 evidence:** (a) `policy_snapshot=None` in `release_define` ⇒
  `test_lifecycle_verb_governance.py::test_verb_persists_resolver_derived_snapshot[release-define]`
  FAILED (`workflow_policy is None`) → reverted; (e) disable the D-3 raw-string guard in
  `_parse_step_profile_overrides` ⇒ `::test_verb_rejects_raw_step_model[release-define,backlog-define]`
  FAILED → reverted. **AC-8 ledger** — SURVIVING (all gain governance): `release_define`,
  `backlog_define`, `implement`, `review_qa/security/code`, `close`, `pipeline`,
  `apply_resolved_policy` (now generic over the structural `PolicyApplicableStep` Protocol);
  NEW: `apply_entry_to_step`, `PolicyApplicableStep`, `_warn_model_deprecated`,
  `_resolve_workflow_snapshot`, `_parse_step_harness_overrides`, `ReleaseStep`/`BacklogStep`
  `resolved_model`+`model_profile` fields + `policy_snapshot` on both workflow `__init__`s;
  DEAD (removed): `_resolve_model`, `_HARNESS_CATALOG_KEY`, the CLI raw `<id>:<effort>` path,
  the builders' `models`-by-kind arg. No `specs/backlog/**` staged. Checklist:
  - **Extract `apply_entry_to_step(entry, *, base_kind, preserve_fake) -> (AgentRuntimeKind,
    ResolvedModelConfig)`** (`pipeline.py`, R-2): the single FAKE-preserving per-step author
    (`codex→CODEX_EXEC`, `pi→PI_HEADLESS`; returns FAKE when `preserve_fake`). `apply_resolved_policy(steps,
    snapshot)` **maps** it over a **structural** Protocol `PolicyApplicableStep`
    (`label`/`runtime_kind`/`resolved_model`/`model_profile`) satisfied by `PipelineStep`, `ReleaseStep`,
    `BacklogStep`, `AuditStep`, `ResearchStep`, `BugReportStep`. Keep the existing pipeline
    `apply_resolved_policy` tests green as the invariant.
  - **`ReleaseStep` + backlog step**: add `resolved_model: ResolvedModelConfig | None = None` and
    `model_profile: str | None = None` (additive-optional, mirror `PipelineStep`); thread
    `step.resolved_model` into `_scope` → `PromptScope.resolved_model` in `release_definition.py` +
    `backlog_definition.py`.
  - **`ReleaseDefinitionWorkflow` / backlog workflow `__init__`**: add optional `policy_snapshot`,
    frozen onto the `LifecycleRun` built in `run()` (set `workflow_policy=self._policy_snapshot`,
    mirror `LifecyclePipeline.run` / `LifecyclePhaseWorkflow.run`) — frozen **before step 1**.
  - **`release_define` / `backlog_define` CLI**: build resolver (`build_workflow_policy_resolver`),
    `resolve("release_definition"|"backlog_definition", context="default", cli_overrides=…,
    default_harness=(None if fake else harness), step_harness_overrides=…)` → snapshot; **seed each base
    step `runtime_kind = default_kind` (FAKE for a fake run) BEFORE applying (R-3), mirroring the
    pipeline l.1148-1151**; `apply_resolved_policy(_SEQUENCE, snapshot)`; pass `policy_snapshot` to the
    builder. **Remove** the CLI's own `_replace(step, runtime_kind=…)` swap (l.434/573). `--step-model`
    → profile-ids via `_parse_step_profile_overrides` (raw `<id>:<effort>` rejected, D-3). **`--model` →
    non-fatal deprecation warning** (ruling): accept the flag, emit a one-line **stderr** warning naming
    `--step-model <profile-id>` + `workflow profiles list`, proceed under the resolved policy — NOT a
    silent no-op, NOT a hard error. Delete the per-verb `_resolve_model` raw path usage.
  - **`_run_phase_step` (implement / review / close)**: add `workflow_id` + `catalog_step_label`
    params (map: `implement→(implementation, implement)`, `qa→(implementation, review_qa)`,
    `security→(implementation, review_security)`, `code→(implementation, review_code)`,
    `close→(closure, close)`); resolve the workflow snapshot, select the step entry, call
    `apply_entry_to_step(entry, base_kind=kind, preserve_fake=(default_harness is None))` **once** →
    local `kind` + `scope.resolved_model`; pass `policy_snapshot` to `LifecyclePhaseWorkflow.run`. Does
    NOT route through `apply_resolved_policy` (no step object). `--step-model` profile-ids-only; `--model`
    same deprecation warning.
  - **Container builders**: `build_release_definition_workflow` + `build_backlog_definition_workflow`
    accept + forward `policy_snapshot`; retire the `models`-by-kind arg (the snapshot's per-step
    `resolved_model` reaches the adapter). Driving-fake factory unchanged.
  - **(Optional, coherence):** the pipeline's own silent `_ = model` (l.1094) adopts the same `--model`
    deprecation warning.
  - **Tests — AC-1 per-verb RED-first over ALL 7 exact verb ids** (`release define`, `backlog define`,
    `implement`, `review qa`, `review security`, `review code`, `close`): parametrized; run under
    `--harness fake`; assert the persisted `LifecycleRun.workflow_policy` in the **run-store record**
    (`JsonLifecycleRunStore`; NOT `--show-policy`, pipeline-only) is `None` pre-wire and a resolver-derived
    snapshot post-wire. **AC-2 (FAKE-aware, R-2/A2):** a **non-fake** unit test of `apply_entry_to_step`
    asserts harness→kind (`codex→CODEX_EXEC`, `pi→PI_HEADLESS`) + FAKE preservation; under `--harness
    fake` each verb asserts (a) `runtime_kind` stayed **FAKE**, (b) snapshot entry
    harness/model_profile/model/reasoning resolver-derived, (c) `req.resolved_model.profile_id ==
    resolved` — **NOT** `FAKE == codex`; (v) the **FAKE adapter executed** (not codex/pi). A raw
    `--step-model label=<id>:<effort>` is rejected (D-3) on every run verb; `--model <x>` emits the
    deprecation warning and proceeds (test via `CliRunner(mix_stderr=False)`: warning in
    `result.stderr`; `--model X --json` stdout stays parseable — R-QA-1). **Rewrite the 3 inverted CLI tests (A5)** —
    `tests/integration/cli/test_lifecycle_cli.py::test_lifecycle_implement_rejects_invalid_model_with_valid_set`
    (l.128), `tests/integration/cli/test_cli_backlog_define.py::test_bad_model_rejected_law2` (l.101) +
    `::test_fake_harness_takes_no_model_law2` (l.118) — each → (a) raw `--step-model` D-3 rejection + (b)
    the `--model` deprecation warning. Confirm `test_pi_runtime.py --model` (pi subprocess arg) OUT of
    scope; audit `test_lifecycle_policy_cli.py` + `test_policy_resolver_harness_governance.py`. AC-7(a)
    break one verb's wiring ⇒ its AC-1 FAILS; AC-7(e) accept a raw `--step-model` ⇒ AC-2(iii) rejection
    FAILS. Both reverted.
  - **AC-8 ledger** (surviving: every verb function survives + gains governance; dead: the per-verb
    `_resolve_model` raw path). NO `specs/backlog`.

## W2 — FR2 wire audit / research / bug_report (born governed)

- [x] T-56-20 Make the three catalog-AVAILABLE workflows invocable, born on the W1 resolver seam.
  **AC-7 evidence:** in `audit` CLI verb, set `build_audit_workflow(..., policy_snapshot=None)` ⇒
  `test_lifecycle_fr2_wire_verbs.py::test_wire_verb_completes_and_persists_resolver_snapshot[audit]`
  FAILED (`workflow_policy is None — verb is not resolver-governed`) → reverted.
  **AC-8 ledger** — SURVIVING: the three workflow bodies (`AuditWorkflow`/`ResearchWorkflow`/
  `BugReportWorkflow`) + the governed catalog (audit/research/bug_report already AVAILABLE);
  NEW: the three-part FR1 seam on each body (`AuditStep`/`ResearchStep`/`BugReportStep`
  `resolved_model`+`model_profile` fields → `_scope` → `PromptScope.resolved_model`; optional
  `policy_snapshot` on each `__init__` frozen via `workflow_policy=` in `run()`) + three container
  builders (`build_audit_workflow`/`build_research_workflow`/`build_bug_report_workflow`, the
  bug_report one step-aware so ADDITIVE `bug_write` stays in-scope) + three `@app.command` verbs
  (`audit`/`research`/`bug_report`) + `_emit_wire_result` + `_WireWorkflowResult` Protocol. NO
  `pipeline.py` edit (structural `PolicyApplicableStep` decoupling). No `specs/backlog/**` staged.
  **Adjudication:** bug_report driving fake is STEP-AWARE (specs/bugs ref for `bug_write`, handoff
  ref elsewhere), not the uniform `.dadaia/handoff/` note in the checklist — a uniform handoff ref
  out-of-scope-BLOCKs `bug_write` (empirically confirmed) since the frozen bug_write scope is
  `specs/bugs/**`-only; step-aware is the only impl satisfying AC-3 COMPLETED + the frozen scope test.
  Checklist:
  - **Workflow-body seam edit (A1/R-4 — FR2 is NOT builder+verb only)**: `audit.py`, `research.py`,
    `bug_report.py` each get the **same three-part FR1 seam** W1 gave `ReleaseStep`/`ReleaseDefinitionWorkflow`:
    (a) `resolved_model: ResolvedModelConfig | None = None` + `model_profile: str | None = None` on
    `AuditStep`/`ResearchStep`/`BugReportStep`; (b) `step.resolved_model` threaded into `_scope` →
    `PromptScope.resolved_model`; (c) optional `policy_snapshot` on `__init__`, frozen in `run()` via
    `workflow_policy=self._policy_snapshot`. **Decoupling:** the structural `PolicyApplicableStep`
    Protocol (W1) makes these field additions auto-satisfy `apply_resolved_policy` — **NO `pipeline.py`
    edit in this wave**.
  - **Container builders** `build_audit_workflow` / `build_research_workflow` /
    `build_bug_report_workflow` in `container.py`, mirroring `build_release_definition_workflow`
    (`ContextSelector` + `build_lifecycle_run_store` + a driving-fake factory that returns an APPROVED
    handoff with an in-scope `artifact_ref`; each accepts an optional `policy_snapshot`). **The
    `bug_report` fake returns an IN-SCOPE `.dadaia/handoff/<ctx>/**` artifact_ref (A4/R-5)** — like the
    release/backlog fakes — so its `bug_write` step does not out-of-scope-BLOCK; a `specs/bugs/` fake
    ref would BLOCK.
  - **CLI verbs** `dadaia lifecycle audit|research|bug_report --context --release-id --run-id
    --harness --step-model --json`: shape like `release_define` minus the synthetic demand; call the
    body's `run(run_id, sequence=_SEQUENCE)`. Each **seeds base kinds** → resolves its snapshot
    (`resolve("audit"|"research"|"bug_report", …)`) → applies (W1 applier) → freezes it onto the run.
    Register on `app`.
  - **Tests — AC-3**: each verb runs to **COMPLETED** under `--harness fake` (exit 0), leaves a
    resolver snapshot in the run-store record (extends AC-1 to the three verbs); the governed catalog
    reports all 7 AVAILABLE + now invocable. The `bug_report` **ADDITIVE/no-lease** property is asserted
    **STRUCTURALLY** — the verb routes through no MUTATING/lease-acquiring path by construction (its real
    `bug_write` target is the ADDITIVE `specs/bugs/` class); under `--harness fake` "no lease" is vacuous
    (the fake writes nothing), so it is **not** a fake-run lease observation. AC-7: break one new verb's
    snapshot wiring ⇒ its AC-1/AC-3 FAILS; reverted.
  - **AC-8 ledger** (surviving: the three workflow bodies + governed catalog; new: the three-part seam
    on each body + three builders + three verbs). NO `specs/backlog`.

## W3 — FR3 loop fixes + CLI caller

- [x] T-56-30 Fix `run_implement_review_loop` and give it a CLI caller.
  **AC-7 mutation-sanity evidence (both captured then reverted):** (b) revert the digest line
  (`digest = WorkflowHandoffResolver.render_digest(resolved)` → `digest = None`) ⇒
  `pytest tests/unit/features/lifecycle/test_implement_review_loop.py::test_implement_prompt_contains_prior_review_digest`
  FAILED (`assert 'handoff qa#0' in impl1.prompt`) → re-applied. (c) revert the structural-gate
  wiring (`_run_loop_worker` → `return runtime.run(built.request), None` instead of
  `evaluate_gate_with_result(..., is_review=False)`) ⇒
  `pytest …::test_loop_blocks_on_evidence_less_worker_via_structural_gate` FAILED (loop COMPLETED
  on the ungated APPROVED verdict instead of blocking) → re-applied.
  **4-test fate ledger (A4/R-1 — enumerated, not assumed):**
  `test_implement_attempt_2_consumes_exact_qa_attempt_1` SURVIVES+EXTENDED (digest-in-`implement#2`
  assert added; `_ScriptedReviewRuntime` records requests + its in-scope artifact_refs pass the
  structural gate each REJECTED round WITHOUT blocking — `result.blocked is None`);
  `test_loop_blocks_after_bounded_retries_exceeded` SURVIVES (confirmed retry-EXHAUSTION:
  `"bounded retry" in reason` AND `"artifact evidence" not in reason`);
  `test_loop_completes_on_first_approval` SURVIVES; `test_loop_requires_resolver` SURVIVES. Fakes
  needing in-scope artifact_refs: `_EvidencelessRuntime` (EMPTY artifact_refs → AC-4(b) structural
  BLOCK) and the CLI `_RejectingRuntime` (in-scope ref + REJECTED verdict → retry-exhaustion BLOCK).
  **AC-8 ledger** — SURVIVING: `LifecyclePipeline` + `run_implement_review_loop` (`_run_loop_worker`
  now returns `(result, blocked)` via the evidence-only runner gate; `_scope` gains a `digest_suffix`);
  NEW: `_finalize_structural_block`, the `implement-review` CLI verb + `_implement_review_runtime_factory`
  / `_build_implement_review_pipeline` / `_emit_implement_review_result`. Full suite 4404 passed /
  17 skipped; ruff format+check clean, mypy --strict (302 files) clean, lint-imports 8 kept/0 broken.
  No `specs/backlog/**` staged. Checklist:
  - **Digest injection** (`pipeline.py`): replace `_ = resolved` (l.309) — render
    `WorkflowHandoffResolver.render_digest(resolved)` and inject it into the `implement#N` (N ≥ 1)
    prompt. Thread a per-attempt digest suffix into `_run_loop_worker`'s scope/prompt build so the
    digest reaches the built request the implement worker receives.
  - **Structural runner gate (A3/R-1 — the single fold)** (`pipeline.py`): `_run_loop_worker` runs
    **both** workers through `LifecycleAgentRunner(runtime, state_machine).evaluate_gate_with_result(...,
    is_review=False)` (gate **without** a phase transition, as `release_definition`/`audit` do); the loop
    reads `(worker_result, blocked)`. **Gate on EVIDENCE ONLY** — a non-None `BlockedState` (non-SUCCEEDED
    / empty `artifact_refs` / out-of-scope) BLOCKS the loop. **Do NOT gate the review worker on its
    verdict** (`is_review=True` returns a block on the first REJECTED — `agent_runner` l.196 — killing the
    retry model). Read the APPROVED/REJECTED **verdict from `worker_result.structured_output`** (l.329) to
    drive the ledger: APPROVED→COMPLETED; structurally-valid REJECTED→next attempt (with the digest);
    exhaustion→BLOCK. Stop calling `runtime.run` directly.
  - **CLI verb** `dadaia lifecycle implement-review --context --release-id --run-id --harness
    --step-model [--max-review-retries] --json`: **seed base kinds** → resolve the `implementation`
    snapshot → apply it to the implement + a review step → freeze onto the run; wire the
    `handoff_resolver` the loop requires; report rounds + final verdict/blocked. Register on `app`.
  - **Existing-loop-test fate (A4/R-1 — enumerate, do not assume)** in `test_implement_review_loop.py`
    (all 4 run through `_run_loop_worker`; `_ScriptedReviewRuntime` already returns `artifact_refs`):
    `test_implement_attempt_2_consumes_exact_qa_attempt_1` **SURVIVES+EXTENDED** (add the digest-in-`implement#N`
    assert; confirm the artifact_refs pass the structural gate each REJECTED round **without blocking**);
    `test_loop_blocks_after_bounded_retries_exceeded` **SURVIVES** (confirm the block is retry-**exhaustion**,
    not a premature evidence/verdict block); `test_loop_completes_on_first_approval` **SURVIVES**;
    `test_loop_requires_resolver` **SURVIVES**. Name any fake that needs in-scope `artifact_refs`.
  - **Tests — AC-4**: (a) a **recording** fake runtime shows the `implement#N` prompt CONTAINS the
    `review#N-1` digest (RED-first: absent pre-fix). (b) a fake worker with empty `artifact_refs` /
    out-of-scope paths makes the loop BLOCK via the **structural** gate (RED-first: passes pre-fix,
    verdict read directly). (c) `dadaia lifecycle implement-review` drives an APPROVED round → COMPLETED
    and an all-REJECTED run → BLOCK, each leaving a run-store snapshot (AC-1). **(d) well-formed REJECTED
    round-0 (populated `artifact_refs`) → `implement#1` with the digest → APPROVED round-1 COMPLETES; the
    loop does NOT block on the REJECTED round.** AC-7(b) revert the digest line ⇒ (a) FAILS; AC-7(c) revert
    the **structural-gate wiring** (`evaluate_gate_with_result`, `is_review=False`) ⇒ (b) FAILS. Both reverted.
  - **AC-8 ledger** (surviving: `LifecyclePipeline` + `run_implement_review_loop`; new: CLI verb).
    NO `specs/backlog`.

## W4 — FR4 TRANSITIONS reconciliation

- [x] T-56-40 Remove the unused review→implementation backtrack edges.
  **AC-7 mutation-sanity (captured then reverted):** (d) re-add the `QA_REVIEW → IMPLEMENTATION`
  edge to `TRANSITIONS` ⇒
  `pytest tests/unit/core/test_lifecycle_models.py::test_transitions_table_pins_review_targets_by_frozenset_equality`
  FAILED (`Extra items in the left set: IMPLEMENTATION`) AND
  `::test_review_phases_cannot_backtrack_to_implementation` FAILED (`assert not True`) → reverted.
  **AC-8 ledger** — SURVIVING: the `TRANSITIONS` symbol + `is_legal_transition` (contents edited,
  symbols retained); DEAD (removed): the three review→IMPLEMENTATION edges
  (`QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW` → `IMPLEMENTATION`); NEW tests:
  `test_review_phases_cannot_backtrack_to_implementation` +
  `test_transitions_table_pins_review_targets_by_frozenset_equality`.
  **A9 public-asset grep conclusion:** the only `public/` mentions of
  `TRANSITIONS`/`is_legal_transition` — `public/skills/dadaia-task-manager/SKILL.md:42`
  (`is_legal_transition, TransitionDecision`) and
  `public/skills/project-orchestration/SKILL.md:108/110` (`TRANSITIONS made executable`;
  `is_legal_transition, TransitionDecision`) — name the **symbol generically**, NOT the removed
  edges ⇒ **NO `public/` edit**; CLOSURE `public doctor` zero-change pre-justified.
  **Inverted-test adjudication (AC-8 sweep — tests/ + docstrings):** SPEC §9-B's "no positive test
  asserts them" was imprecise — two synthetic-ladder INTEGRATION tests asserted the removed edges as
  legal end-to-end (`tests/integration/cli/test_lifecycle_pipeline_full.py::test_pipeline_qa_review_backtracks_to_implementation_on_fake`
  + `::test_pipeline_security_and_code_review_backtrack_to_implementation_on_fake`, both former
  T-23-03). "No PRODUCTION consumer" still holds (ladder is forward-only; the loop never touches the
  state machine), but these two invert. Rewritten →
  `test_pipeline_qa_review_cannot_backtrack_to_implementation_on_fake` +
  `test_pipeline_security_and_code_review_cannot_backtrack_to_implementation_on_fake`: each asserts
  `not is_legal_transition(<review>, IMPLEMENTATION)` and that the pipeline run does NOT reach
  IMPLEMENTATION (state machine rejects the illegal transition; run stays at its review phase);
  module docstring's T-23-03 note updated. **Gates:** ruff format+check clean; mypy --strict 302
  files clean; lint-imports 8 kept/0 broken; full unpiped pytest **4406 passed / 17 skipped**
  (exit 0). No `specs/backlog/**` staged. Checklist:
  - **`core/models/lifecycle.py` `TRANSITIONS`**: remove `IMPLEMENTATION` from the `QA_REVIEW`,
    `SECURITY_REVIEW`, and `CODE_REVIEW` target sets. **Retain** every forward edge
    (IMPLEMENTATION→QA_REVIEW→SECURITY_REVIEW→CODE_REVIEW→CLOSURE), every `*→BLOCKED`, and the full
    `BLOCKED → {BACKLOG_DEFINITION, RELEASE_DEFINITION, IMPLEMENTATION, QA_REVIEW, SECURITY_REVIEW,
    CODE_REVIEW, CLOSURE}` resume fan-out.
  - **`tests/unit/core/test_lifecycle_models.py` — frozenset-equality pins (A6)**: assert
    `TRANSITIONS[QA_REVIEW] == frozenset({SECURITY_REVIEW, BLOCKED})`,
    `TRANSITIONS[SECURITY_REVIEW] == frozenset({CODE_REVIEW, BLOCKED})`,
    `TRANSITIONS[CODE_REVIEW] == frozenset({CLOSURE, BLOCKED})` (exact equality, not spot-checks — so a
    future stray edge fails); retain `test_blocked_phase_can_resume_*` (covers `BLOCKED → IMPLEMENTATION`,
    the retained operator-driven rework path).
  - **Public-asset grep (A9)**: confirm the only `public/` mentions of `TRANSITIONS`/`is_legal_transition`
    (`public/skills/dadaia-task-manager/SKILL.md` l.42; `public/skills/project-orchestration/SKILL.md`
    l.108/110) name the **symbol generically**, not the removed edges → no `public/` edit; CLOSURE
    `public doctor` zero-change pre-justified.
  - **Tests — AC-5**: the frozenset-equality table test above. AC-7(d) re-add one removed edge ⇒ AC-5
    equality FAILS; reverted.
  - **AC-8 ledger** (surviving: `TRANSITIONS` symbol; dead: the three edges). NO `specs/backlog`.

## W5 — gates + ship

- [x] T-56-50 Full local gates (AC-6) then ship. **Gate evidence (2026-07-04, tree = 4e6ed9cd):**
  unpiped full pytest **4406 passed / 17 skipped, exit 0** (722s); `ruff format --check` clean (772
  files); `ruff check --no-cache` clean; `mypy --strict` clean (302 files); `lint-imports --no-cache`
  **8 kept / 0 broken**; ignore-cap contract test 4/4 (total == 26, families 9/4/13 UNCHANGED);
  `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0; `dadaia public doctor` exit 0 with
  `[ok] public-privacy` (zero `public/` change, per the W4 A9 pre-justification). Frozen v0.1.50
  no-steal suite **zero-diff** (the two "release"-substring grep hits are `model_by_kind` factory-arg
  repoints, not lease/gate files). **No `specs/backlog/**` staged on the branch** (archival deferred
  to CLOSURE — both anchors survive). **QA ship gate: APPROVE, zero blockers** (5/5 AC coverage
  re-verified in a fresh 77-test targeted run; all three wave adjudications ruled sound; no slop) —
  handoff `2026-07-04T024052Z-qa-engineer-v0156-ship-gate.handoff.json`. Ship steps (security
  push-gate keyed to pushed sha; push; CI watch; PR; merge) executed after this flip. Checklist:
  - **Unpiped** `pytest` (real exit) — full suite green.
  - `ruff format --check`; `ruff check --no-cache`; `mypy --strict dadaia_workspace`.
  - `lint-imports --no-cache` → **`8 kept, 0 broken`**; the ignore-cap test → total `== 26` +
    per-family `9/4/13` **UNCHANGED** (the new builders/verbs import only already-imported lifecycle
    internals — no new cross-feature/infra edge).
  - `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0; `dadaia public doctor` → `[ok]
    public-privacy`, exit 0 (no `public/` change this release).
  - Confirm the v0.1.50 frozen no-steal suite is **zero-diff** (this release never entered
    `spec_context`/lease/gate).
  - **No consumed-backlog archival at SHIP** (both anchors survive; verify no W1-W4 commit staged
    `specs/backlog`). QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch
    CI until every job green**; PR; merge.

## W6 — closure (CLOSURE phase)

- [ ] T-56-60 CLOSURE.md + memory truth + disposition + archive. Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write `CLOSURE.md` (Summary, Tasks completed w/ SHAs,
    Validations triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive decision).
  - **MEMORY (§SPEC 8):** `dadaia-workflows.md` → **7 invocable WORKFLOWS** (A8 — NOT "7 verbs":
    separate the workflow count (7) from the ~12-verb roster; `implement-review` is a **verb on the
    `implementation` workflow**, not a new workflow) — pin the CLOSURE copy to "7 invocable workflows
    surfaced by these CLI verbs: release define, backlog define, pipeline, implement, review
    qa|security|code, close, audit, research, bug_report, implement-review"; the three "no verb —
    pending" rows flip; drop the pending note ⇒ **regenerate `catalog.json` + `index.md`**;
    `lifecycle-foundation.md` → control-plane generalized to every verb + CLI-surface line gains
    audit/research/bug_report/implement-review + loop-fix note + TRANSITIONS-removal note (regen
    catalog only if `tldr`/`summary`/`area` changed); `architecture.md` → verb roster if enumerated;
    `quality-assurance.md` → **confirm no change** (no new byte-golden); `tech-stack.md` → **confirm
    no change**. `release_origin` → v0.1.56 on each edited atom.
  - **Backlog return (ruling)**: file `hard-remove-model-flag-across-run-verbs` (route through PM
    curation) — the `--model` deprecation → hard-removal across all run verbs once callers migrate
    (no-legacy-code path). Record in the CLOSURE `## Backlog returns`.
  - **Disposition**: archive `lifecycle-verb-governance-uniformity` →
    `specs/_archive/v0.1.56/consumed-backlog/` + `consumed_backlog.json`; terminal status `DELIVERED —
    v0.1.56`. Record in the CLOSURE `## Dispositions` table. Bug ledger stays **0 open** (none
    consumed).
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.56 → specs/_archive/releases/`
    (devops/operator); set `ACTIVE.md` → next release or `release: none` (R8 is the final release of
    the R6→R8 mandate); mark candidates R8 row **SHIPPED — v0.1.56**.
