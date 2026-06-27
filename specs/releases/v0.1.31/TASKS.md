# TASKS — Release: v0.1.31 — make the dadaia-workflows actually run on a real Layer-2 worker

**Status:** Aprovado
**Release ID:** v0.1.31
**Owner:** product-engineer

> DEFINE-ONLY (GRILL D-6). Tasks are approved but **NOT started** — every marker is `[ ]`.
> Implementation begins only after the operator approves at the DEFINITION checkpoint and
> `ACTIVE.md` phase advances to IMPLEMENTATION. Markers: `[ ]` OPEN → `[-]` IN PROGRESS →
> `[x]` DONE. One `[-]` per owner unless disjoint write sets are declared. **No push** (D-6).
> Tasks are TDD-first: the failing-test task precedes (or accompanies) its implementation task.

---

## Wave A — verdict gate review-only + create-step payload (KEYSTONE; D-1/D-2)

- [ ] **T-31-A-01** — Failing gate-distinction tests (TDD, before the runner change).
  - Goal: write the tests that pin the review-only gate: (a) a review step (`is_review=True`)
    BLOCKs on a missing/`REJECTED` verdict; (b) a create step (`is_review=False`) PASSES on a
    schema-valid payload (fenced `schema == expected_schema` → populated `artifact_refs`)
    **regardless of** the `verdict` field; **(b-adversarial / R-A)** a create step with
    `verdict=REJECTED` (and an absent-verdict variant) BUT a valid payload (schema match +
    `artifact_refs`) is **NOT blocked** — pins the "regardless of verdict" half adversarially;
    (c) a no-op create-step worker (no schema-matching payload → empty `artifact_refs`) still
    BLOCKs; (d) a **pipeline** review step (`review_qa`/`review_security`/`review_code`,
    `is_review=True`) BLOCKs on a missing/`REJECTED` verdict. These fail against the current
    always-verdict gate.
  - Write set: `tests/unit/features/lifecycle/test_agent_runner_review_only_gate.py` (NEW).
  - Acceptance: A2, A3 (incl. R-A), A4, A5, A8 (tests authored and red against current code).

- [ ] **T-31-A-02** — Thread `is_review` into `AgentRunnerInput` + branch `_blocked_result`.
  - Goal: add `is_review: bool = False` to `AgentRunnerInput`; in `_blocked_result`, apply the
    `verdict == "APPROVED"` check **only** when `data.is_review` is true; create steps require
    `succeeded` + a schema-valid fenced payload (the extractor's `schema`-field equality →
    `artifact_refs` populated) + in-scope paths (retain the existing `artifact_refs` +
    out-of-scope checks; **no field-level schema validation added** — D-5). Correct the
    `evaluate_gate` docstring so the pass condition is no longer "an APPROVED verdict" for all steps.
  - Write set: `dadaia_workspace/features/lifecycle/agent_runner.py`.
  - Acceptance: A1 (field), A2, A3, A4, A7 (docstring) — T-31-A-01 (a)/(b)/(b-adv)/(c) now green.

- [ ] **T-31-A-03** — Thread `is_review=step.is_review` at the four review-capable workflow call sites + fix comment.
  - Goal: pass `is_review=step.is_review` into `AgentRunnerInput` at each call site, named with the
    runner METHOD it uses (C2): `release_definition` (~339, `evaluate_gate_with_result`), `audit`
    (~281, `evaluate_gate_with_result`), `bug_report` (~276, `evaluate_gate_with_result`),
    `research` (~265, `evaluate_gate_with_result`); correct the misleading inline comment in
    `release_definition.py` (~329) to describe the review-only gate.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/release_definition.py`;
    `dadaia_workspace/features/lifecycle/workflows/audit.py`;
    `dadaia_workspace/features/lifecycle/workflows/bug_report.py`;
    `dadaia_workspace/features/lifecycle/workflows/research.py`.
  - Acceptance: A1, A6, A7.

- [ ] **T-31-A-04** — Thread `is_review=False` at the fifth caller `backlog_definition`.
  - Goal: pass `is_review=False` into `AgentRunnerInput` (~444, `evaluate_gate` — C2) for the
    `backlog_author` model create step (its `BacklogStep` is kind-based, not `is_review`-boolean)
    so the create step is not falsely gated on a verdict.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`.
  - Acceptance: A1, A6.

- [ ] **T-31-A-05** — C1 fix: add `is_review` to `PipelineStep` + thread `pipeline` review steps.
  - Goal (DEFINITION-review C1, must-fix): add an `is_review: bool = False` field to `PipelineStep`
    (~lines 79–91); set `is_review=True` on the `review_qa`/`review_security`/`review_code` steps
    (~495–519) and keep `implement` at `is_review=False`; thread `is_review=step.is_review` into
    `AgentRunnerInput` at `pipeline.py:~205` (`run` method — C2). Without this the qa/security/code
    review gates that protect the push boundary silently lose `verdict == APPROVED`.
  - Write set: `dadaia_workspace/features/lifecycle/pipeline.py`.
  - Acceptance: A1, A6, A8 (T-31-A-01 (d) pipeline-review test now green).

- [ ] **T-31-A-06** — C1 fix: thread `phase_workflow` review-phase steps.
  - Goal: in `phase_workflow.run()` thread `is_review` into `AgentRunnerInput` (~102, `run` method
    — C2) so a step targeting a **review phase** (`QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW`) runs
    as `is_review=True`. Derive `is_review` from whether `target_phase`/`from_phase` is a review
    phase, or accept it as a `run()` argument.
  - Write set: `dadaia_workspace/features/lifecycle/phase_workflow.py`.
  - Acceptance: A1, A6 (+ a test asserting a review-phase step gates on the verdict).

- [ ] **T-31-A-07** — Failing fragment-bundle test (TDD, before bundling).
  - Goal (C3 / R-B): a test that **derives the producing-step set programmatically from each
    workflow's `_SEQUENCE`** (not a hard-coded list) and asserts `release_scope`, `spec_create`,
    `plan_create`, `tasks_create`, and `backlog_author` each carry a handoff-emission instruction
    (`shared.output_handoff`) in their fragment bundle, and that no parallel `create_handoff`
    fragment exists. Fails today because `release_scope` bundles only `shared.grill_questionnaire`
    and `plan_create`/`tasks_create`/`backlog_author` bundle no output contract.
  - Write set: `tests/unit/features/lifecycle/test_create_step_handoff_bundles.py` (NEW).
  - Acceptance: A10, A11 (tests authored and red).

- [ ] **T-31-A-08** — Bundle `shared.output_handoff` into EVERY producing create step.
  - Goal (C3 / R-B): add `shared.output_handoff` to the `shared_fragment_ids` of `release_scope`
    (alongside `shared.grill_questionnaire`), `plan_create`, `tasks_create`, and `backlog_author`
    (`spec_create` already has it). Reuse the single existing fragment — do NOT fork a
    `create_handoff` fragment. Re-stage + install if a `public/` fragment body changes.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/release_definition.py`;
    `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`;
    `dadaia_workspace/public/lifecycle_fragments/release_definition/release-scope.md` (if the body
    needs a verdict-free emission note).
  - Acceptance: A9, A10, A11 — T-31-A-07 tests now green; `dadaia public doctor` `[ok]`.

> **Wave A green checkpoint (KEYSTONE):** review step blocks on missing/REJECTED verdict — for a
> release-def review AND a pipeline review step (A5/A8); create step passes on schema-valid payload
> regardless of `verdict` incl. `verdict=REJECTED`/absent (A3, R-A); no-op create-step worker still
> BLOCKs (A4); **all seven** callers thread the flag + `PipelineStep` gains `is_review` (A1/A6);
> every producing create step bundles `shared.output_handoff`, no `create_handoff` fragment
> (A9/A10/A11); comments/docstrings corrected (A7); faked suite + mypy/lint + `public doctor`
> green. **No Wave C task starts before this is green.**

---

## Wave B — PI command re-verify + real `pi` smoke (adopt `c8513fa5`; D-3)

- [ ] **T-31-B-01** — Re-verify the PI argv unit assertion.
  - Goal: confirm `_command` appends `["-p"]` with no trailing `-` and that
    `test_pi_adapter_builds_controlled_command_and_env` asserts `argv[-1] == "-p"` and
    `"-" not in argv` (lines ~105–106). Do NOT re-fix or weaken; this is a verification pass that
    the landed `c8513fa5` is intact and pinned.
  - Write set: `tests/unit/infrastructure/test_pi_runtime.py` (only if a missing assertion must be
    re-added — otherwise no change, verification only).
  - Acceptance: A12.

- [ ] **T-31-B-02** — Real `pi` smoke (env-gated, skipped by default).
  - Goal: a smoke that runs the real `pi` binary through `PiHeadlessAdapter` and proves the
    command executes without "Unknown option: -", yielding a typed `AgentRunResult`. Mirror the
    `tests/integration/pi_live/` opt-in gate (`DADAIA_PI_LIVE`/`PI_BIN`/`ANTHROPIC_API_KEY`),
    sharing the Wave-C `DADAIA_E2E_REAL_WORKER` gate per D-4. Auto-SKIP by default. Document the
    run command in the module docstring.
  - Write set: `tests/integration/pi_live/test_pi_command_smoke.py` (NEW) or fold into the Wave-C
    e2e module.
  - Acceptance: A13.

> **Wave B green checkpoint:** PI argv assertion re-verified (A12); real `pi` smoke present,
> env-gated, SKIPPED in a default run (A13).

---

## Wave C — anti-fake real-worker e2e (CORE DELIVERABLE; D-4)

- [ ] **T-31-C-01** — Anti-fake real-worker e2e: fixed minimal chain `release_scope` → `spec_create`.
  - Goal: an e2e that drives a **real** (non-fake) `pi` Layer-2 worker through the **fixed** chain
    `release_scope` → `spec_create` — the exact shipped-failure path (OQ-3, fixed by QA review; no
    alternative chain). Assert **concrete post-step-1 state, NOT "no exception" (R-C):** (a) the
    real command executed (catches the D-3 class); (b) the `release_scope` step is **not blocked**
    and yields a parsed `SUCCEEDED` `AgentRunResult`; (c) the run carries **no**
    `"agent result missing APPROVED verdict"` `BlockedState`; (d) the run **advanced beyond
    `release_scope`** (reached/ran `spec_create`). Env-gated (`DADAIA_E2E_REAL_WORKER=1` + live
    preconditions); auto-SKIP by default so a default `pytest`/CI run is fully faked + green.
    Document the run command in the module docstring.
  - Write set: `tests/integration/<real_worker>/test_real_layer2_worker_workflow_e2e.py` (NEW).
  - Acceptance: A14, A15, A17.

- [ ] **T-31-C-02** — Prove worker payload compliance OR harden extraction (record residual).
  - Goal: from the T-31-C-01 run, determine whether the real `pi` worker reliably emits the fenced
    structured payload for the chosen step(s). If it does → the e2e asserts it (compliance proven).
    If it does not → harden `pi_runtime._verdict_payload` / the structured-output read to degrade
    safely, keep the e2e green via the hardened path, and record the residual for CLOSURE.
  - Write set: `dadaia_workspace/infrastructure/pi_runtime.py` (only if hardening is required);
    `tests/integration/<real_worker>/test_real_layer2_worker_workflow_e2e.py`.
  - Acceptance: A16.

- [ ] **T-31-C-03** — (Optional) codex real-worker second case.
  - Goal: add a codex variant of the e2e ONLY if cheap and credentials are available (OQ-2; `pi`
    is the required case). Same env gate + auto-SKIP. Skip this task if codex creds/cost make it
    impractical — `pi` alone satisfies the core deliverable.
  - Write set: `tests/integration/codex_live/test_real_layer2_worker_workflow_e2e.py` (NEW, optional).
  - Acceptance: A14 (codex half — optional).

> **Wave C green checkpoint (CORE):** real-worker e2e present, env-gated, SKIPPED in a default run
> (A14/A17); with the env flag set it asserts concrete post-step-1 state — not blocked, no
> missing-verdict BlockedState, advanced beyond `release_scope`, parsed SUCCEEDED result (A15);
> worker-compliance proven or extraction hardened with the residual recorded (A16).

---

## Closure / disposition (DEFINE-ONLY — NOT run this release cycle)

- [ ] **T-31-Z-01** — Release closure + memory atoms + disposition sweep.
  - Goal (CLOSURE phase only, after every Wave A/B/C task `[x]` and the QA/trio cadence per
    `release-governance`): write `CLOSURE.md` (template `dadaia-release-closure`); update
    `specs/memory/architecture.md` (review-only gate contract), `specs/memory/tech-stack.md` (the
    live-verified pinned `pi` build), and the affected `specs/memory/product/` workflow atom(s);
    run the disposition sweep — flip `pi-headless-command-trailing-dash-breaks-layer2` and
    `lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate` to `status: Closed` with the
    real-`pi`-smoke (A13) and real-worker-e2e (A15) evidence respectively (never deleted); record
    the Wave-C worker-compliance decision (proven vs hardened) as a CLOSURE drift; request the
    `git mv` of the release to `_archive/` (delegate to devops/operator); point `ACTIVE.md` at the
    next release or `release: none`.
  - Write set: `specs/releases/v0.1.31/CLOSURE.md`; `specs/memory/**`;
    `specs/bugs/pi-headless-command-trailing-dash-breaks-layer2.md`;
    `specs/bugs/lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate.md` (status only);
    `specs/releases/ACTIVE.md`.
  - Acceptance: A18 — CLOSURE evidence complete (summary, tasks+SHAs, validations triples, drifts,
    memory updates, dispositions, archive decision); both bugs `Closed` with evidence;
    `dadaia specs doctor` green.

---

## Parallelism notes

- **Wave A** is a tight chain on the shared runner + the seven call sites: sequence
  T-31-A-01 → T-31-A-02 (runner). After A-02 lands, the call-site tasks T-31-A-03 (four
  review-capable workflows), T-31-A-04 (`backlog_definition`), T-31-A-05 (`pipeline` + `PipelineStep`
  field), and T-31-A-06 (`phase_workflow`) have disjoint write sets and may run in parallel.
  T-31-A-07 → T-31-A-08 (fragment bundle) are independent of the runner branch and may run in
  parallel with A-02..A-06 (disjoint write set: fragment + `_SEQUENCE`/`backlog_definition` bundle
  vs `agent_runner`/`pipeline`/`phase_workflow`). NOTE: T-31-A-05 (pipeline) and T-31-A-08 both
  touch nothing in common, but T-31-A-01's pipeline-review test case (d) depends on A-05's
  `PipelineStep.is_review` field existing — keep A-01 red until A-02+A-05 land.
- **Wave B** (T-31-B-01/B-02) is independent of Wave A and may run in parallel with it (disjoint
  write set: `pi_runtime` / pi tests).
- **Wave C** depends on **both** Wave A and Wave B green; T-31-C-01 → T-31-C-02 are sequential
  (C-02 reacts to the C-01 run); T-31-C-03 is optional and disjoint.
- **T-31-Z-01** is CLOSURE-only and runs after every Wave A/B/C task is `[x]` and the review cadence
  clears.
