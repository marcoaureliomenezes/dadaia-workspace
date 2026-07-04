# PLAN — v0.1.56 — Lifecycle Verb Governance

**Status:** Aprovado

Four implementation waves (one per FR) + ship + closure. FR1 lays the governed seam; FR2 and FR3
are **born on it**; FR4 is an independent table change. `cli/commands/lifecycle.py`, `pipeline.py`,
and `container.py` are shared across FR1/FR2/FR3 → the waves are **sequential** (no parallel `[-]`).

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-03 verb-by-verb code read; mandatory
  release-definition grill on the picked set; surfaced Decision A (WIRE) + Decision B (REMOVE);
  `Aprovado` after review; definition commit.

- **W1 — FR1 resolver on every run-a-worker verb (the biggest wave).**
  1. **Extract `apply_entry_to_step(entry, *, base_kind, preserve_fake)`** (`pipeline.py`) as the
     single FAKE-preserving per-step author; `apply_resolved_policy(steps, snapshot)` maps it over the
     **structural** Protocol `PolicyApplicableStep` (`label`/`runtime_kind`/`resolved_model`/`model_profile`).
     The existing pipeline `apply_resolved_policy` tests stay the invariant.
  2. **Add `resolved_model`/`model_profile` to `ReleaseStep` + the backlog step** (additive-optional,
     mirror `PipelineStep`); thread `step.resolved_model` into their `_scope` → `PromptScope.resolved_model`.
  3. **`ReleaseDefinitionWorkflow`/backlog workflow `__init__`** gain optional `policy_snapshot`,
     frozen onto the `LifecycleRun` they build (mirror `LifecyclePipeline`/`LifecyclePhaseWorkflow`).
  4. **`release define` / `backlog define` CLI**: build resolver → `resolve("<workflow_id>", …,
     default_harness=(None if fake else harness))`; **seed each base step `runtime_kind = default_kind`
     (FAKE for a fake run) BEFORE applying** (A5/R-3); `apply_resolved_policy` over `_SEQUENCE` → freeze
     onto run; **remove** the CLI `_replace(step, runtime_kind=…)` swap; `--step-model` → profile-ids
     (`_parse_step_profile_overrides`); `--model` → **non-fatal deprecation warning** (stderr → `workflow
     profiles list`; proceed under resolved policy); delete the per-verb `_resolve_model` raw path.
  5. **`_run_phase_step` (implement / review qa|security|code / close)**: add `workflow_id` +
     `catalog_step_label` (map: `implement→implement`, `qa→review_qa`, `security→review_security`,
     `code→review_code`, `close→close`); resolve the workflow snapshot, select the step entry, call
     `apply_entry_to_step` **once** (`base_kind=kind`, `preserve_fake=(default_harness is None)`) → local
     kind + `scope.resolved_model`; pass `policy_snapshot` to `LifecyclePhaseWorkflow.run`. Does NOT
     route through `apply_resolved_policy`. `--model` same deprecation warning.
  6. **Container builders**: `build_release_definition_workflow`/`build_backlog_definition_workflow`
     accept + forward `policy_snapshot`; retire the `models`-by-kind arg (snapshot carries the model).
  - Tests: **per-verb AC-1 RED-first over ALL 7 exact verb ids** (`release define`, `backlog define`,
    `implement`, `review qa`, `review security`, `review code`, `close`) — parametrized, `workflow_policy
    None` pre-wire → resolver-derived snapshot in the **run-store record** post-wire; **AC-2** FAKE-aware
    (runtime_kind stayed FAKE + snapshot resolver-derived + `req.resolved_model.profile_id`; harness→kind
    equality is a **non-fake** unit test of `apply_entry_to_step`; FAKE-adapter-executed AC); profile-ids-only
    rejection + `--model` deprecation-warning assertion on every verb. **Rewrite the 3 inverted CLI tests**
    (`test_lifecycle_cli.py::test_lifecycle_implement_rejects_invalid_model_with_valid_set` l.128,
    `test_cli_backlog_define.py::test_bad_model_rejected_law2` l.101 + `::test_fake_harness_takes_no_model_law2`
    l.118) → each asserts (a) raw `--step-model label=<id>:<effort>` D-3 rejection + (b) the `--model`
    deprecation warning. Confirm `test_pi_runtime.py --model` (pi subprocess arg) OUT of scope; audit
    `test_lifecycle_policy_cli.py` + `test_policy_resolver_harness_governance.py`. AC-7(a)+(e) sabotage.
    AC-8 ledger. NO `specs/backlog`.

- **W2 — FR2 wire audit / research / bug_report (born governed).**
  1. **Workflow-body seam edit (A1/R-4 — NOT builder+verb only)**: `audit.py`/`research.py`/`bug_report.py`
     each get the three-part FR1 seam — (a) `resolved_model`/`model_profile` on `AuditStep`/`ResearchStep`/
     `BugReportStep`; (b) `step.resolved_model` → `_scope` → `PromptScope.resolved_model`; (c) optional
     `policy_snapshot` on `__init__`, frozen in `run()` via `workflow_policy=`. **Decoupling:** the
     structural Protocol (W1) makes these field additions auto-satisfy `apply_resolved_policy` — **no
     `pipeline.py` edit in W2**.
  2. **Container builders** `build_{audit,research,bug_report}_workflow` (mirror
     `build_release_definition_workflow`; accept `policy_snapshot`). The `bug_report` driving fake
     returns an **in-scope** `.dadaia/handoff/<ctx>/**` artifact_ref (A4/R-5) so its run COMPLETES.
  3. **CLI verbs** `dadaia lifecycle audit|research|bug_report` (shape like `release define` minus the
     demand; `run(run_id, sequence=_SEQUENCE)`); each seeds base kinds → resolves its snapshot
     (`resolve("audit"|…)`) → applies (W1 seam) → freezes onto the run. Register on `app`.
  - Tests: AC-3 (each verb → COMPLETED under fake, leaves a run-store snapshot; `bug_report`
    ADDITIVE/no-lease asserted **structurally**, not via a fake-run lease observation); AC-1 extends to
    the three verbs. AC-8 ledger. NO `specs/backlog`.

- **W3 — FR3 loop fixes + CLI caller.**
  1. **Digest injection** (`pipeline.py run_implement_review_loop`): replace `_ = resolved` — render
     `WorkflowHandoffResolver.render_digest(resolved)` and inject it into the `implement#N` prompt
     (thread a per-attempt digest suffix into `_run_loop_worker`'s scope build).
  2. **Structural runner gate (A3/R-1)**: `_run_loop_worker` → `LifecycleAgentRunner(runtime,
     state_machine).evaluate_gate_with_result(..., is_review=False)` — gate on **evidence only**
     (non-SUCCEEDED / empty artifact_refs / out-of-scope ⇒ block); read the verdict from
     `worker_result.structured_output` to drive the ledger (APPROVED→COMPLETED; structurally-valid
     REJECTED→next attempt with digest; exhaustion→BLOCK). **Do NOT gate the review worker on its
     verdict** (`is_review=True` would block round-0 REJECTED). Stop calling `runtime.run` directly.
  3. **CLI verb** `dadaia lifecycle implement-review` (seed base kinds → resolve `implementation`
     snapshot → apply to an implement + review step → freeze onto run; wire the `handoff_resolver`;
     `--max-review-retries` optional). Register on `app`.
  - **Existing-loop-test fate (A4/R-1 — enumerate, do not assume)** in `test_implement_review_loop.py`:
    `test_implement_attempt_2_consumes_exact_qa_attempt_1` SURVIVES+EXTENDED (add digest-in-`implement#N`
    assert; confirm the `_ScriptedReviewRuntime` artifact_refs pass the structural gate each REJECTED
    round **without blocking**); `test_loop_blocks_after_bounded_retries_exceeded` SURVIVES (confirm the
    block is **retry-exhaustion**, not a premature evidence/verdict block); `test_loop_completes_on_first_approval`
    SURVIVES; `test_loop_requires_resolver` SURVIVES. Name any fake needing in-scope artifact_refs.
  - Tests: AC-4(a) digest capture (RED-first: prompt lacks digest pre-fix); AC-4(b) structural-gate
    BLOCK on an evidence-less worker (RED-first: passes pre-fix); AC-4(c) CLI drive + snapshot; **AC-4(d)
    well-formed REJECTED round-0 → implement#1-with-digest → APPROVED round-1 COMPLETES (never blocks on
    the REJECTED round)**. AC-7(b)+(c) sabotage (c = structural-gate wiring). AC-8 ledger. NO `specs/backlog`.

- **W4 — FR4 TRANSITIONS reconciliation (independent).**
  1. Remove `IMPLEMENTATION` from the `QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW` target sets in
     `TRANSITIONS` (`core/models/lifecycle.py`); retain all forward edges + the `BLOCKED → {…}` resume
     fan-out.
  2. Update `tests/unit/core/test_lifecycle_models.py`: **frozenset-equality pins (A6)** —
     `TRANSITIONS[QA_REVIEW]==frozenset({SECURITY_REVIEW,BLOCKED})`,
     `[SECURITY_REVIEW]==frozenset({CODE_REVIEW,BLOCKED})`, `[CODE_REVIEW]==frozenset({CLOSURE,BLOCKED})`;
     retain `test_blocked_phase_can_resume_*` (BLOCKED→IMPLEMENTATION). Grep-confirm the two public
     `SKILL.md` `TRANSITIONS`/`is_legal_transition` refs are generic symbols → no `public/` edit.
  - Tests: AC-5 frozenset table test. AC-7(d) re-add-edge sabotage. AC-8 ledger. NO `specs/backlog`.

- **W5 — gates + ship.** Full local gates (AC-6): unpiped `pytest` + `ruff format --check` + `ruff
  check --no-cache` + `mypy --strict` + `lint-imports --no-cache` (8 kept, 0 broken; cap 26 = 9/4/13
  UNCHANGED) + `dadaia specs doctor` + `dadaia backlog doctor` + `dadaia public doctor`. QA ship-gate;
  security push-gate keyed to the pushed sha; push; CI green (watch until every job green); PR; merge.
  **No consumed-backlog archival at SHIP** (both anchors survive — archival is at CLOSURE).

- **W6 — closure (CLOSURE phase).** CLOSURE.md (Validations + Drifts + Dispositions). MEMORY edits
  (§SPEC 8): `dadaia-workflows.md` (**7 invocable WORKFLOWS** — not "7 verbs"; separate the workflow
  count from the ~12-verb roster incl. `implement-review` as a verb on the `implementation` workflow;
  `tldr`/`summary` change → regen catalog+index); `lifecycle-foundation.md` (control-plane generalized
  + verb roster + loop fix + TRANSITIONS note); `architecture.md` (verb roster if enumerated);
  `quality-assurance.md` no-change confirm; `tech-stack.md` no-change confirm. **Backlog return:** file
  `hard-remove-model-flag-across-run-verbs` (the `--model` deprecation → removal once callers migrate).
  Disposition: archive `lifecycle-verb-governance-uniformity` → `specs/_archive/v0.1.56/consumed-backlog/`
  + `consumed_backlog.json` (`DELIVERED — v0.1.56`). `dadaia specs doctor` clean; `public doctor`
  zero-change pre-justified (§SPEC 4); archive release (`git mv` via devops/operator); `ACTIVE.md → next`
  (or `release: none` — R8 is the final release of the R6→R8 mandate); candidates R8 row → SHIPPED.

## Write sets (disjoint per wave; shared files force sequential order)

| Wave | Files |
|---|---|
| W1 | `dadaia_workspace/features/lifecycle/pipeline.py` (`apply_entry_to_step` + structural `PolicyApplicableStep` Protocol; `apply_resolved_policy` maps it), `dadaia_workspace/features/lifecycle/workflows/release_definition.py` (`ReleaseStep` `resolved_model`/`model_profile` + `_scope` thread + `__init__` snapshot), `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py` (same), `dadaia_workspace/cli/commands/lifecycle.py` (`release_define`, `backlog_define`, `_run_phase_step` + verb→catalog map; seed base FAKE; `--model` deprecation warning; retire raw path), `dadaia_workspace/container.py` (`build_release_definition_workflow`/`build_backlog_definition_workflow` accept snapshot), FR1 tests + **rewrite** `tests/integration/cli/test_lifecycle_cli.py` + `test_cli_backlog_define.py` (the 3 inverted raw-`--model` tests) to D-3 rejection + `--model` deprecation warning |
| W2 | `dadaia_workspace/features/lifecycle/workflows/audit.py` + `research.py` + `bug_report.py` (three-part FR1 seam — A1/R-4; **NO `pipeline.py` edit**), `dadaia_workspace/container.py` (`build_{audit,research,bug_report}_workflow`), `dadaia_workspace/cli/commands/lifecycle.py` (three new verbs + registration), FR2 tests (`tests/integration/cli/`, `tests/unit/features/lifecycle/`) |
| W3 | `dadaia_workspace/features/lifecycle/pipeline.py` (`run_implement_review_loop` + `_run_loop_worker`), `dadaia_workspace/cli/commands/lifecycle.py` (`implement-review` verb), `tests/unit/features/lifecycle/test_implement_review_loop.py` (digest + gate) + a CLI-caller test |
| W4 | `dadaia_workspace/core/models/lifecycle.py` (`TRANSITIONS`), `tests/unit/core/test_lifecycle_models.py` |
| W5 | (gates only) |
| W6 | `specs/releases/v0.1.56/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.56/consumed-backlog/` per the closure ritual |

**`pipeline.py` shared W1 (`apply_entry_to_step`/`apply_resolved_policy`) + W3 (`run_implement_review_loop`)**
— sequential; disjoint symbols but one file, so no parallel `[-]`. **W2 does NOT touch `pipeline.py`** —
the structural `PolicyApplicableStep` Protocol (W1) makes the Wave-E step-field additions auto-satisfy
`apply_resolved_policy` (A2/R-2 decoupling). **`cli/commands/lifecycle.py` shared W1/W2/W3** — sequential;
each wave adds/edits distinct verb functions. **`container.py` shared W1/W2** — sequential. **No parallel
`[-]`.**

## Test strategy

- **Snapshot-artifact assertion (AC-1, the FR1/FR2 spine) — run-store channel.** Every verb run under
  `--harness fake` persists `LifecycleRun.workflow_policy`; the test reads it from the **run-store
  record** (`JsonLifecycleRunStore`), NOT `--show-policy` (pipeline-only, not added elsewhere).
  Parametrized over all 7 (+3+1) exact verb ids. **RED-first per verb**: `workflow_policy is None`
  pre-wire → resolver-derived snapshot post-wire — the mechanical proof each verb is now governed.
- **`apply_entry_to_step` + FAKE-aware AC-2.** Keep the pipeline `apply_resolved_policy` tests as the
  invariant. A **non-fake** unit test of `apply_entry_to_step` asserts the harness→kind mapping
  (codex→CODEX_EXEC, pi→PI_HEADLESS) + FAKE preservation. Under `--harness fake`, each verb asserts:
  `runtime_kind` stayed FAKE; the snapshot entry harness/model_profile/model/reasoning are resolver-derived;
  `req.resolved_model.profile_id == resolved`; the FAKE adapter (not codex/pi) executed. **Never** assert
  `FAKE == codex`. Profile-ids-only: a raw `<id>:<effort>` `--step-model` is rejected on every run verb;
  `--model` emits the deprecation warning and proceeds — asserted with
  `CliRunner(mix_stderr=False)`: warning in `result.stderr`, stdout stays parseable JSON on the
  `--json` path (R-QA-1).
- **Inverted CLI-test rewrites (A5).** `test_lifecycle_cli.py::test_lifecycle_implement_rejects_invalid_model_with_valid_set`,
  `test_cli_backlog_define.py::test_bad_model_rejected_law2` + `::test_fake_harness_takes_no_model_law2`
  assert the DELETED raw-`--model` LAW-2 rejection — each REWRITTEN to (a) raw `--step-model` D-3 rejection
  + (b) `--model` deprecation warning. `test_pi_runtime.py --model` (pi subprocess arg) is OUT of scope;
  audit `test_lifecycle_policy_cli.py` + `test_policy_resolver_harness_governance.py`.
- **Loop fixes (AC-4).** A **recording** fake proves the `implement#N` prompt contains the `review#N-1`
  digest (RED-first: absent pre-fix). An evidence-less fake worker proves the loop BLOCKs via the
  **structural** gate (RED-first: passes pre-fix). The 4 existing loop tests' fate is enumerated on
  T-56-30 (case1 SURVIVES+EXTENDED, case2 SURVIVES/exhaustion-confirm, case3/4 SURVIVE). **AC-4(d):** a
  well-formed REJECTED round-0 retries (never blocks) → APPROVED round-1 COMPLETES. The `implement-review`
  CLI verb drives APPROVED→COMPLETED and all-REJECTED→BLOCK, each leaving a run-store snapshot.
- **TRANSITIONS (AC-5).** `test_lifecycle_models.py` pins the post-removal targets by **frozenset
  equality** (not spot-checks); retains `test_blocked_phase_can_resume_*` (BLOCKED→IMPLEMENTATION).
- **AC-7 mutation-sanity per new test** (a-e): one-line sabotage ⇒ FAIL, captured on the task line,
  reverted; (c) targets the structural-gate wiring.
- **AC-8 surviving/dead ledger per wave**; greps include `tests/` + textual/docstring refs; the FR4
  grep confirms the two public `SKILL.md` symbol refs are generic.
- **Frozen file:** the v0.1.50 no-steal suite is untouched (this release does not enter
  `spec_context`/lease/gate) — confirm zero-diff.
- Full **unpiped** `pytest` + ruff + `mypy --strict` + `lint-imports --no-cache` + `specs doctor` +
  `backlog doctor` + `public doctor` locally before push (AC-6). Cap `== 26` (9/4/13) UNCHANGED —
  verified because the new builders/verbs import only already-imported lifecycle internals.

## Rollback

Single feature branch `feature/v0.1.56` (base v0.1.55 closure `53a14e57`). Each wave is one or a
small set of commits. **No irreversible step, no data migration, no public-asset projection.**
Rollback = revert the wave's commits or drop the branch. FR1's `apply_resolved_policy` generalization
and the CLI raw-path retirement are single-file edits recoverable by revert. FR2/FR3 add verbs +
builders (pure additions). FR4 is a table edit. Because both consumed anchors survive, there is **no
SHIP-time archival commit** — the consumed-backlog disposition happens at CLOSURE and is recoverable
by reverting that one closure commit.
