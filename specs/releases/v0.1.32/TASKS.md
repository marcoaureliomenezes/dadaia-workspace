# TASKS — Release: v0.1.32 — harden real-worker workflows (coherent worker-output contract + live review path)

**Status:** Aprovado
**Release ID:** v0.1.32
**Owner:** product-engineer

> DEFINE-ONLY (GRILL D-7). Tasks are approved but **NOT started** — every marker is `[ ]`.
> Implementation begins only after the operator approves at the DEFINITION checkpoint and
> `ACTIVE.md` phase advances to IMPLEMENTATION. Markers: `[ ]` OPEN → `[-]` IN PROGRESS →
> `[x]` DONE. One `[-]` per owner unless disjoint write sets are declared. **No push** (D-7).
> Tasks are TDD-first: the failing-test task precedes (or accompanies) its implementation task.

---

## Wave A — coherent worker-output contract (KEYSTONE; D-1/D-2/D-3)

- [x] **T-32-A-01** — Failing suffix-contract tests (TDD, before the prompt change).
  - Goal: write the tests that pin the coherent contract: (a) a **review**-step
    `build_fragment_suffix` (`is_review=True`) instructs `structured_output.verdict` =
    APPROVED/REJECTED + evidence; a **create**-step (`is_review=False`) does NOT instruct a
    verdict; (b) the assembled "## Required output" names exactly ONE schema target — the literal
    field `schema` = `agent-run-result-v1` — and does NOT surface the fragment's
    `output_schema` (domain schema) as a competing schema-to-emit; (c) **C6 / A4b** —
    `pipeline._generic_prompt` is step-kind-aware: review → verdict instruction, create → NO
    self-verdict (this is the second stale surface, not a `build_fragment_suffix` caller). These
    fail against the current universal-verdict + two-schema text.
  - Write set: `tests/unit/features/lifecycle/test_fragment_suffix_is_review.py` (NEW).
  - Acceptance: A1, A2, A4b (tests authored and red against current
    `build_fragment_suffix` / `_generic_prompt`).

- [x] **T-32-A-02** — Make `build_fragment_suffix` `is_review`-aware + one-schema/canonical text.
  - Goal: add a **keyword-only, NO-default** `is_review: bool` parameter to
    `build_fragment_suffix` (signature `build_fragment_suffix(bundle, *, selected_context,
    is_review)` — DEFINITION-review C2; no default so a forgotten flag is a call/type error, never
    a silent miss). Branch the "## Required output" section — review → emit
    `structured_output.verdict` APPROVED/REJECTED + evidence; create → emit artifact +
    `artifact_refs`, NO verdict. Name exactly ONE schema target: the literal field `schema` =
    `agent-run-result-v1`; stop surfacing `{bundle.output_schema}` as a competing "output schema
    to conform to" (the fragment `output_schema` stays in `FragmentBundle` for Python tagging, not
    as a worker emit target). Do NOT add per-step `expected_schema` wiring; leave
    `PromptScope.expected_schema`'s `agent-run-result-v1` default unchanged.
  - Write set: `dadaia_workspace/features/lifecycle/prompt_builder.py`.
  - Acceptance: A1, A2, A5 (default unchanged) — T-32-A-01 (a)/(b) now green.

- [x] **T-32-A-03** — Failing threading test (TDD, before threading the call sites).
  - Goal (C2): a test that **ENUMERATES the `build_fragment_suffix` callers** and asserts each
    passes the correct `is_review`: the four release-style workflows (`release_definition`,
    `audit`, `bug_report`, `research`) and `pipeline` thread `step.is_review`;
    `backlog_definition` threads `False` for `backlog_author`. The enumeration is explicit so the
    test **FAILS when a new caller omits the flag** (the back-compat guard for the no-default
    param). Assert via the assembled prompt text per workflow (review path produces the verdict
    instruction; create path does not) rather than mocking. Also assert no new `expected_schema=`
    appears at the call sites. Fails today (callers pass no `is_review`).
  - Write set: `tests/unit/features/lifecycle/test_suffix_is_review_threading.py` (NEW).
  - Acceptance: A4 (enumerating test authored and red).

- [x] **T-32-A-04** — Thread `is_review` at the six `build_fragment_suffix` call sites.
  - Goal: pass the correct `is_review` into `build_fragment_suffix`:
    `release_definition.py` (~320) `is_review=step.is_review`; `audit.py` (~267)
    `is_review=step.is_review`; `bug_report.py` (~262) `is_review=step.is_review`;
    `research.py` (~251) `is_review=step.is_review`; `pipeline.py` `_fragment_prompt` (~415)
    `is_review=step.is_review`; `backlog_definition.py` (~432) `is_review=False`. **C6 — the
    second stale surface:** make `pipeline._generic_prompt` (~395-400) step-kind-aware too (review
    → verdict instruction; create → emit artifact + refs, NO self-verdict), keyed on
    `step.is_review` — it is NOT a `build_fragment_suffix` caller and hard-codes universal-verdict
    text today. Verify (do not duplicate) the v0.1.31 review-only gate comment in
    `release_definition.py` (~331). `phase_workflow.py` is NOT a caller — no change there (it
    already threads `is_review` into `AgentRunnerInput`).
  - Write set: `dadaia_workspace/features/lifecycle/workflows/release_definition.py`;
    `dadaia_workspace/features/lifecycle/workflows/audit.py`;
    `dadaia_workspace/features/lifecycle/workflows/bug_report.py`;
    `dadaia_workspace/features/lifecycle/workflows/research.py`;
    `dadaia_workspace/features/lifecycle/pipeline.py`;
    `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`.
  - Acceptance: A4 (six callers threaded — T-32-A-03 green), A4b (`_generic_prompt` step-kind-aware
    — T-32-A-01 (c) green).

- [x] **T-32-A-05** — Canonical field `schema` in the shared fragment (D-3).
  - Goal: edit `shared/output-handoff.md` so the documented result field is **`schema`** (literal
    transport id `agent-run-result-v1`), not `schema_version`. Keep the review-only
    `verdict`/`verdict_reason`/`findings` rows and the `output_schema: handoff-v1.1` frontmatter
    id (distinct from the `schema` field value). After the edit: `dadaia public stage` →
    `dadaia public install --target all` → `dadaia public doctor` (`[ok]` incl. public-privacy).
  - Write set: `dadaia_workspace/public/lifecycle_fragments/shared/output-handoff.md`.
  - Acceptance: A3 — `dadaia public doctor` `[ok]`.

- [x] **T-32-A-06** — Fragment-guard test — both halves of Drift 2/3 die in the body (C1).
  - Goal (DEFINITION-review C1): a test that asserts in the `shared/output-handoff.md` **body**:
    (a) **NO `schema_version` field** AND it instructs exactly `schema` = `agent-run-result-v1`
    as the field to emit (kills Drift 3); AND (b) **NO residual "conform to the `output_schema`"
    emit-framing** — no instruction to emit/conform-to the fragment's domain schema as the
    worker-emitted field (kills Drift 2). Both assertions explicit. The frontmatter
    `output_schema: handoff-v1.1` stays UNCHANGED (distinct concept — assert it is still present).
    Also: no fragment under `public/lifecycle_fragments/` instructs `schema_version`; no
    `create_handoff` fragment exists; `shared.output_handoff` is the single output contract.
    Extend the existing fragment-bundle test if one fits.
  - Write set: `tests/unit/features/lifecycle/test_output_handoff_fragment_canonical.py` (NEW, or
    extend an existing fragment test).
  - Acceptance: A3 (both Drift-2 and Drift-3 halves), A5.

> **Wave A green checkpoint (KEYSTONE):** suffix is `is_review`-aware (review vs create text — A1);
> one schema target `schema=agent-run-result-v1`, no competing domain schema (A2); fragment says
> `schema` not `schema_version`, no `schema_version`/`create_handoff` anywhere (A3/A5); all six
> call sites thread the correct `is_review`, no new `expected_schema=` (A4); faked suite +
> mypy/lint + `public doctor` green. **No Wave C task starts before this is green.**

---

## Wave B — strict accept primary + structural fallback + codex parity (D-4/D-5)

- [x] **T-32-B-01** — Failing extractor strict/structural tests (TDD, pi + codex).
  - Goal: write tests pinning: (pi) strict-primary accept of a correctly-labelled fenced AND bare
    payload (A6); structural fallback accept of a mis-labelled/unlabelled but structurally-valid
    payload (A7); no-op worker → `None` → empty `artifact_refs` (A8); **strict-primacy BEHAVIOUR
    test (C5/A9)** — a payload that is BOTH structurally-valid AND `schema`-matched takes the
    strict path, and a structurally-valid but `schema`-mismatched payload is accepted ONLY via the
    fallback; a future reorder that lets structural shadow strict FAILS this test (NOT asserted via
    docstring). (codex) fenced AND bare codex payload parse (A10); strict-primary +
    structural-fallback parity (A11); no-op codex worker → empty `artifact_refs`; **codex
    reject-guard (C4/A11)** — arbitrary JSON lacking the result shape (a dict with no `schema`
    match and no non-empty `artifact_refs`) yields empty `artifact_refs` (codex no longer maps ANY
    dict to a result). The codex tests fail today (codex does a single `json.loads` with no
    fenced/bare fallback, no `schema` acceptance, and accepts ANY dict — OQ-3 finding).
  - Write set: `tests/unit/infrastructure/test_pi_runtime.py` (additions);
    `tests/unit/infrastructure/test_codex_runtime.py` (additions).
  - Acceptance: A6, A7, A8, A9, A10, A11 (tests authored; codex half + C5 behaviour test red).

- [x] **T-32-B-02** — Factor the shared extraction/acceptance helper once (A12).
  - Goal: lift `_json_candidates` + the verdict-payload extraction + `_is_result_payload`
    (strict-primary + structural-fallback) into ONE shared implementation on
    `SubprocessAdapterMixin` (`headless_adapter_base`); rewire `pi_runtime` to call it (behaviour
    identical — existing pi extractor tests stay green). Make strict
    `payload["schema"] == expected_schema` the **explicitly primary** path and structural the
    **documented fallback**; update the docstrings to state strict-primary + structural-as-
    defence-in-depth + no-op→BLOCK (A9).
  - Write set: `dadaia_workspace/infrastructure/headless_adapter_base.py`;
    `dadaia_workspace/infrastructure/pi_runtime.py`.
  - Acceptance: A6, A7, A8, A9, A12 (pi half) — pi tests from T-32-B-01 green; existing pi
    extractor tests still green.

- [x] **T-32-B-03** — Codex parity: rewire `_result_from_output` to the shared helper.
  - Goal: replace codex's single `json.loads(raw)` with the shared candidate scan
    (fenced/bare/sliced) + shared strict-primary/structural-fallback acceptance against
    `request.expected_schema` (so codex gains the **reject-guard** — a shapeless dict no longer
    maps to a result, C4). Thread `request` into `_result_from_output` so it has
    `expected_schema`. Preserve the existing degraded fallbacks (unparseable → prose-summary
    SUCCEEDED; non-dict → `structured_output` value). **C3 — positively prove one implementation:**
    add a test that patches the shared extraction helper in `headless_adapter_base` and asserts
    BOTH `pi_runtime` AND `codex_runtime` call it (not a grep).
  - Write set: `dadaia_workspace/infrastructure/codex_runtime.py`;
    `tests/unit/infrastructure/test_codex_runtime.py` (the patch-the-helper proof — A12/C3).
  - Acceptance: A10, A11 (codex half incl. reject-guard C4) — codex tests from T-32-B-01 green;
    A12/C3 — the patch-the-helper test proves pi and codex resolve through the same shared helper.

> **Wave B green checkpoint:** pi strict-primary (fenced+bare) + structural fallback + no-op→BLOCK
> + explicit docstrings (A6/A7/A8/A9); codex parity (A10/A11) via the single shared helper (A12);
> faked suite + mypy/lint green.

---

## Wave C — prove the REVIEW path live (CORE DELIVERABLE; D-6)

- [x] **T-32-C-01** — Extend the real-worker e2e chain to include a real review step.
  - Goal (OQ-2, PLAN-selected): extend `_truncated_sequence()` in the v0.1.31 e2e module to
    `release_scope` → `spec_create` → `spec_arch_review` (the first real `is_review=True` step,
    sliced verbatim from `_SEQUENCE`; + the terminal `definition_commit_gate` if needed for clean
    completion). Update the v0.1.31 module docstring framing from "advances past step 1" to
    "advances through a real review/gate step" and document the run command (A16).
  - Write set: `tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py`.
  - Acceptance: A13, A16 (chain includes ≥1 review step; env-gated; SKIPPED by default; run
    command documented).

- [x] **T-32-C-02** — Live: real `pi` review step emits APPROVED and the gate PASSES.
  - Goal: add `test_real_pi_worker_review_step_emits_approved_and_gate_passes` — env-gated (reuse
    `requires_real_worker`), with the flag set asserts CONCRETE state (A14): (a) `spec_arch_review`
    ran; (b) it yielded a parsed `SUCCEEDED` result carrying `verdict == APPROVED` from the real
    worker; (c) the run is NOT blocked at `spec_arch_review` (the verdict gate fired on real output
    and PASSED). Record whether strict or fallback acceptance carried it (R5 — for CLOSURE).
    SKIPPED by default so CI stays faked + green.
  - Write set: `tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py`.
  - Acceptance: A14 (live, concrete state — verdict gate fired on real worker output and PASSED).

- [x] **T-32-C-03** — REJECTED-blocks negative (faked gate path, default-CI green).
  - Goal (OQ-2): prove a review step with `verdict == REJECTED` (and a missing-verdict variant)
    BLOCKs the run, using the faked gate path so no second live credit-burning run is needed and
    default CI stays green. Add/point an explicit assertion in a faked review-gate test (extend
    the existing v0.1.31 review-gate test or add a focused one).
  - Write set: `tests/unit/features/lifecycle/test_agent_runner_review_only_gate.py` (extend) or a
    NEW focused test module.
  - Acceptance: A15 (REJECTED/missing verdict BLOCKs; faked path; CI green).

> **Wave C green checkpoint (CORE):** live review-path test present, env-gated, SKIPPED in a default
> run (A13/A16); with the flag set it asserts `spec_arch_review` ran, yielded a real
> `verdict == APPROVED` SUCCEEDED result, the gate PASSED on real output (A14); REJECTED-blocks
> negative proven via the faked gate path (A15); strict-vs-fallback outcome recorded (R5).

---

## Closure / disposition (DEFINE-ONLY — NOT run this release cycle)

- [ ] **T-32-Z-01** — Release closure + memory atoms + disposition sweep.
  - Goal (CLOSURE phase only, after every Wave A/B/C task `[x]` and the QA/trio cadence per
    `release-governance`): write `CLOSURE.md` (template `dadaia-release-closure`); update
    `specs/memory/architecture.md` (coherent worker-output contract — one transport schema in
    `schema`, step-kind-aware emission, strict-primary + structural-defence-in-depth, shared
    pi/codex extraction), `specs/memory/product/sdd/lifecycle-foundation.md` (review/verdict path
    proven live; codex parity), and `specs/memory/tech-stack.md` (live-verified `pi` build if
    changed); run the disposition sweep — flip
    `lifecycle-prompt-names-two-schemas-confusing-real-workers` to `status: Closed` with the
    coherent-contract test evidence (A1-A3) + the live review-path e2e evidence (A14) (never
    deleted — L7); record the Wave-C strict-vs-fallback outcome (R5) as a CLOSURE drift if
    relevant; request the `git mv` of the release to `_archive/` (delegate to devops/operator);
    point `ACTIVE.md` at the next release or `release: none`.
  - Write set: `specs/releases/v0.1.32/CLOSURE.md`; `specs/memory/**`;
    `specs/bugs/lifecycle-prompt-names-two-schemas-confusing-real-workers.md` (status only);
    `specs/releases/ACTIVE.md`.
  - Acceptance: A17 — CLOSURE evidence complete (summary, tasks+SHAs, validations triples, drifts,
    memory updates, dispositions, archive decision); the bug `Closed` with evidence;
    `dadaia specs doctor` green.

---

## Parallelism notes

- **Wave A** is a tight chain on the shared `build_fragment_suffix` seam: sequence
  T-32-A-01 → T-32-A-02 (prompt builder). After A-02 lands, T-32-A-03 → T-32-A-04 (call-site
  threading) follow; T-32-A-05 → T-32-A-06 (fragment text) are independent of the suffix builder
  and may run in parallel with A-02..A-04 (disjoint write set: `public/` fragment + fragment test
  vs `prompt_builder` + workflow call sites).
- **Wave B** depends on Wave A (the contract must be coherent before strict accept is restored as
  primary). T-32-B-01 (tests) → T-32-B-02 (pi + shared helper) → T-32-B-03 (codex) is a sequence
  (codex reuses the helper B-02 factors).
- **Wave C** depends on **both** Wave A and Wave B green. T-32-C-01 (chain) → T-32-C-02 (live
  APPROVED) is sequential; T-32-C-03 (faked REJECTED negative) is independent of the live half and
  may run in parallel with C-01/C-02 (disjoint write set: faked gate test vs the live e2e module).
- **T-32-Z-01** is CLOSURE-only and runs after every Wave A/B/C task is `[x]` and the review cadence
  clears.
