# TASKS — v0.1.57 — Injection Canon

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets: `pipeline.py`
W2+W5, `phase_workflow.py` W2+W5, `context_selector.py` W2+W3, the workflow bodies W1) are sequential —
one owner, no parallel `[-]`. Every implementation-wave task: **NO `specs/backlog/**` paths staged**
(dead/surviving anchors dispositioned at SHIP/CLOSURE — T-57-60/T-57-70). Every move/rename/repoint
grep **includes `tests/` AND non-import textual references** (docstrings/comments). AC-10
mutation-sanity: each new test is sabotaged → shown to FAIL → reverted, captured on the task line.
**FR1 lands FIRST** — it is the ONE seam FR2–FR6 build on.

## W0 — definition

- [x] T-57-01 SPEC/PLAN/TASKS authored from the 2026-07-04 **code read** (not a dossier restatement):
  4 handoff-ledger bodies near-byte-identical + `backlog_definition` a structural outlier;
  `implementation.qa_review` omits `quality_assurance_atom` AND its inputs are unregistered + the
  pipeline/phase_workflow wire no selector (frontmatter fix is inert — the role→atom map is the real
  fix); `SpecContext` has no `phase`; `persona_doctor` already covers bound step-role persona
  resolution (coherence gap is fragment-file + selector + map coverage); `sel_constitution` has zero
  fragment consumers; `max_context_policy` is fragment-global; `LifecyclePipeline.run` (+ the
  `phase_workflow` twin) computes `accepted = run.blocked is None` (illegal transition → accepted=True);
  the only `dadaia lifecycle --model` callers are the v0.1.56 deprecation-warning tests. Mandatory
  release-definition grill on the picked set (report emitted). **Rulings recorded (§9, operator
  unavailable — overridable):** A ratify self-pull; B include `--model` removal; C base-for-4 +
  assembly-mixin-for-backlog. `Aprovado` after dual definition review; definition commit. Owner:
  product-engineer (orchestrated).

## W1 — FR1 `FragmentGateWorkflow` base + assembly mixin (golden-first)

- [ ] T-57-10 Capture + commit the behaviour goldens BEFORE any extraction.
  **AC-12 ledger** — NEW: `tests/unit/features/lifecycle/test_fragment_gate_goldens.py` + goldens under
  `tests/unit/features/lifecycle/_golden/`. No `specs/backlog/**` staged. Checklist:
  - Run `release_definition`, `audit`, `research`, `bug_report`, `backlog_definition`, and the
    `pipeline` implementation ladder under `--harness fake`; capture each step's built prompt +
    produced ledger payload.
  - **Path-normalize** every golden (v0.1.55 platform-invariant law) — `.dadaia/handoff/<ctx>/` and
    `specs/` refs normalized to placeholders. Commit the goldens. These are the AC-1 behaviour lock.
  - **(Q1) the `_scope` capture EXCLUDES `model_profile`/`resolved_model`** — the golden pins only the
    non-model `_scope` fields (role, allowed_paths, required_evidence, task_id, prompt); the backlog
    model convergence is proven by the T-57-11 RED-first `req.resolved_model is not None`, never a
    golden diff. **(Q2) byte-identity holds through end-of-W1 only** — W2/W3 intentionally re-baseline
    the affected goldens (record which + why in the T-57-20/T-57-30 AC-12 ledgers).

- [ ] T-57-11 Extract `FragmentGateWorkflow` + `_FragmentAssemblyMixin` and migrate the bodies.
  **AC-10(a) evidence:** point `_produce_payload` back at a module-global `_SEQUENCE` ⇒ the
  custom-`_SEQUENCE` iteration test FAILS → reverted. **AC-12 ledger** — NEW:
  `workflows/_fragment_gate.py`; SURVIVING: `ReleaseDefinitionWorkflow`/`AuditWorkflow`/
  `ResearchWorkflow`/`BugReportWorkflow` (now thin subclasses) + `BacklogDefinitionWorkflow` (mixin);
  DEAD (folded into base/mixin): the per-body duplicated members. No `specs/backlog/**` staged.
  Checklist:
  - **`_fragment_gate.py`**: `FragmentGateWorkflow[StepT, ResultT]` with the shared members; overridable
    hooks for command string / initial phase / terminal-gate / result factory / `_scope`.
    `_produce_payload` + `_graph_completeness_block` iterate the **run-scoped sequence** (threaded), never
    a module-global `_SEQUENCE`. **(N1) derive each body's empty-sequence `ValueError` message from the
    class command string** so each keeps its exact text (`"release-definition workflow requires…"`, …).
  - **(Q3) the module-global `_SEQUENCE` SURVIVES by name per body** — it stays as `run()`'s default
    `sequence` arg; run-scoping is achieved by `_produce_payload`/`_graph_completeness_block` reading the
    run-threaded `sequence`.
  - **Migrate the 4 bodies** to thin subclasses: `release_definition` (terminal → IMPLEMENTATION),
    `audit`/`research`/`bug_report` (terminal → COMPLETED-no-transition; `bug_report` overrides `_scope`
    for the ADDITIVE `bug_write`). Keep each body's Step/Result types + `_SEQUENCE`.
  - **(Q3) existing-test fate ledger:** SURVIVE-unchanged (module-global `_SEQUENCE` retained by name) —
    `test_fragment_coverage_guardrail.py`, `test_fragment_loader.py`, `test_persona_injection_all_verbs.py`
    (all import `<body>._SEQUENCE` by name). SURVIVE/EXTEND — `test_release_definition_workflow.py`,
    `test_audit_workflow.py`, `test_research_workflow.py`, `test_bug_report_workflow.py`,
    `test_release_definition_handoff_ledger.py`, `test_pipeline.py`,
    `test_backlog_definition_workflow.py`/`test_backlog_review_step.py`.
  - **`_FragmentAssemblyMixin`**: `_prefix_with_static_inputs`, `_collect_static_inputs`,
    `_fragment_bundle`, `_select_context`, `_render_selection`, `_scope`; `BacklogDefinitionWorkflow`
    mixes it in, keeps kind-dispatch.
  - **Converge `_scope` (Problem #8 fix)**: the mixin `_scope` threads `model_profile` +
    `resolved_model`; backlog now forwards its resolved model.
  - **Tests — AC-1** goldens byte-identical post-extraction; **AC-2** shared members exist once in the
    base; a base subclass with a **custom `_SEQUENCE`** produces/validates that sequence (not a module
    global); a **RED-first** backlog test asserts backlog_define under fake yields `req.resolved_model
    is not None`. AC-10(a) sabotage. AC-12 ledger. NO `specs/backlog`.

## W2 — FR2 role→atom map + phase threading + qa_review atom

- [ ] T-57-20 Declarative role→atom map + phase into `SpecContext` + qa_review atom.
  **AC-10(b) evidence:** drop the map injection for qa-engineer ⇒ AC-3 pipeline `review_qa` grounding
  test FAILS → reverted. **AC-12 ledger** — NEW: `features/lifecycle/role_atoms.py` (map + single-sourced
  inject helper); SURVIVING/EDITED: `SpecContext` (gains `phase`), the 5 container builders (resolve
  ACTIVE.md phase), **`build_lifecycle_pipeline` + `build_lifecycle_phase_workflow` (wire the resolver,
  A1)**, **`LifecyclePipeline.__init__` + `LifecyclePhaseWorkflow.__init__` (new specs_dir/workspace_root
  param, A1)**, `pipeline._scope`/`_fragment_prompt`, `phase_workflow.run`, the `FragmentGateWorkflow`
  base assembly; EDITED public: `public/lifecycle_fragments/implementation/qa-review.md`. No
  `specs/backlog/**` staged. Checklist:
  - **`role_atoms.py` (A1 — single-sourced)**: declarative map `software-architect→specs/memory/architecture.md`,
    `qa-engineer→specs/memory/quality-assurance.md`, `product-engineer→specs/memory/product/catalog.json`,
    PLUS **ONE** resolve-and-inject helper (resolve role → read atom file → append labelled block →
    record `InjectedContext.refs`) used by all 3 surfaces (never copy-pasted). Multi-role comma-split;
    unmapped role → no injection.
  - **Consume the map + wire specs_dir per surface (A1)**: base via `self._selector.spec_context.specs_dir`;
    `LifecyclePipeline` via a specs_dir/resolver injected into `LifecyclePipeline.__init__` and built in
    `build_lifecycle_pipeline` from `workspace_root+context` (mirror `build_release_definition_workflow`'s
    `workspace_root/repos/<ctx>/specs` → self-hosting `workspace_root/specs` fallback);
    `LifecyclePhaseWorkflow` via a `workspace_root`/resolver injected into
    `LifecyclePhaseWorkflow.__init__` (the builder already receives `workspace_root`) and resolved at
    `run()` from `scope.context`. Record atom refs in `InjectedContext.refs`.
  - **Phase threading**: `SpecContext` gains `phase: str | None = None`; the 5 container builders
    (`build_release_definition_workflow`, `build_backlog_definition_workflow`, `build_audit_workflow`,
    `build_research_workflow`, `build_bug_report_workflow`) resolve the active phase from `ACTIVE.md`
    and thread it; absent/malformed `ACTIVE.md` → `phase=None` (fail-open).
  - **qa_review atom**: add `quality_assurance_atom` to `implementation.qa_review` `dynamic_inputs`
    (declaration fidelity; the map is the guarantee).
  - **Tests — AC-3** map delivers grounding (pipeline `review_qa` RED-first: absent pre-map) + base +
    phase_workflow; product-engineer step records catalog ref; software-architect step records
    architecture.md ref; **(A1) a PRODUCTION-builder wiring assertion** — `build_lifecycle_pipeline` +
    `build_lifecycle_phase_workflow` wire the resolver with a real `specs_dir`, not just fixtures.
    **AC-4** phase reaches `SpecContext` (fixture ACTIVE.md) + fail-open on absent/malformed. AC-10(b)
    sabotage. AC-12 ledger. NO `specs/backlog`.

## W3 — FR3 coherence doctor + sel_constitution + per-input policy

- [ ] T-57-30 Fragment/selector/role-map coherence doctor + `sel_constitution` decision + per-input
  policy. **AC-10(e) evidence:** make the selector-wired **`release_definition.spec_create`** main
  fragment declare an unregistered `dynamic_inputs` entry ⇒ **FRAG-COH-2** ERROR fires and `ok` flips
  → reverted. **AC-12 ledger** — NEW: `features/lifecycle/fragment_coherence_doctor.py`; SURVIVING:
  `persona_doctor` (untouched), `sel_constitution` (kept, indirection documented),
  `ContextSelector.select_all` (per-name policy), `FragmentLoader`/`_frontmatter_doc` (`input_policies`
  key), `Fragment` (gains field). No `specs/backlog/**` staged. Checklist:
  - **Coherence doctor** (`fragment_coherence_doctor.py`) — NEW checks with **stable IDs + fixed
    severity (Q6), label order aligned across FR3/AC-5/AC-10/T-57-30 (A3)**:
    - **FRAG-COH-1 (ERROR)** — fragment `role` resolves to a persona atom OR is `shared`/`python`.
    - **FRAG-COH-2 (ERROR, SCOPED — A2)** — `dynamic_inputs` entry resolves to a registered selector,
      **ERROR only for the MAIN fragment of a selector-wired workflow step**; **WARN/skip** for (i)
      shared-fragment inputs (body-only, never resolved) and (ii) selector-less-path inputs
      (`implementation.*`).
    - **FRAG-COH-3 (WARN)** — orphan fragment / dangling shared id.
    - **FRAG-COH-4 (ERROR)** — role→atom-map coverage (each model-driven step's role-mapped atom in its
      injected refs).
    `ok=` from ERROR checks only. Wire into `dadaia specs doctor` / lifecycle doctor surface. **Do NOT
    re-implement `persona_doctor`.**
  - **`sel_constitution` (A4)**: KEEP registered + the static-input path (`spec_create` static
    constitution); a recorded decision (comment + a test asserting `spec_create` static constitution
    injection is intact) that **notes the `write_set_guidance` → `sel_write_set_guidance` →
    `sel_constitution` indirection** (declared by `release_definition.tasks_create`) so the selector is
    never mistaken for dead; no removal.
  - **Per-input policy**: optional `input_policies: {input_name: policy}` fragment frontmatter key
    (additive; loader list-key validation untouched); `Fragment` gains `input_policies`;
    `ContextSelector.select_all` accepts per-name overrides, default = fragment-global
    `max_context_policy`. **(N2) exercised by a TEST-FIXTURE fragment, NOT a shipped public fragment.**
  - **Tests — AC-5** doctor green after FR2/FR3 (RED-first: unregistered input on the selector-wired
    `release_definition.spec_create` fires **FRAG-COH-2**; the doctor output string contains
    `FRAG-COH-2`) + `persona_doctor` still green; **AC-6** per-input policy resolves mixed policies in
    one `select_all` (test-fixture fragment) + byte-stable when `input_policies` absent. AC-10(e)
    sabotage. AC-12 ledger. NO `specs/backlog`.

## W4 — FR4 Layer-1 ruling (ratify self-pull; verifiable)

- [ ] T-57-40 Ratify self-pull; lock ctx_inject byte-identical; verifiability via Layer-2 refs.
  **AC-12 ledger** — SURVIVING: `hooks/ctx_inject.py` (byte-identical, no code change); NEW/updated:
  a byte-identical `_build_memory` golden/assert. No `specs/backlog/**` staged. Checklist:
  - **Ratify**: no `ctx_inject.py` code change (constitution/architecture/QA stay self-pull-only at L1).
  - **Lock**: add/keep an assert-golden on `_build_memory` output for a fixture specs tree so any future
    L1 expansion is caught (AC-7).
  - **Verifiability**: rely on FR2's `InjectedContext.refs` + FR3's role→atom-map-coverage check
    (AC-5(d)) as the Layer-2 mechanical proof — no new hard gate this release.
  - **Defer**: the L1 handoff-audit-line is a CLOSURE backlog return (`layer1-selfpull-handoff-audit-line`,
    T-57-70).
  - **Tests — AC-7** ctx_inject bootstrap byte-identical; existing `test_ctx_inject.py` /
    `test_ctx_inject_digest.py` green. **(Q5) AC-10(f) evidence:** append any atom to `_build_memory`'s
    L1 bootstrap ⇒ AC-7 byte-identical assert FAILS → reverted. AC-12 ledger. NO `specs/backlog`.

## W5 — FR5 bug fix + FR6 `--model` removal

- [ ] T-57-50 Fix the pipeline accepted computation (both seams) + hard-remove `--model`.
  **AC-10(c-pipeline) evidence:** revert ONLY the `LifecyclePipeline.run` fix ⇒ AC-8 pipeline-seam test
  FAILS → re-applied. **AC-10(c-twin) evidence:** revert ONLY the `LifecyclePhaseWorkflow.run` fix ⇒
  AC-8 phase_workflow-seam test FAILS → re-applied (Q5 — each seam sabotaged independently).
  **AC-10(d) evidence:** restore `_warn_model_deprecated` + the `--model` option ⇒ AC-9 "No such option"
  test FAILS → reverted. **AC-12 ledger** — NEW: `TransitionDecision.advanced` property (A5); SURVIVING:
  `LifecyclePipeline.run` + `LifecyclePhaseWorkflow.run` (both read `decision.advanced`); DEAD (removed):
  `_warn_model_deprecated`, the 12 `--model` option decls, the 5 deprecation-warning tests
  (inverted/deleted). No `specs/backlog/**` staged. Checklist:
  - **Single-source the predicate (A5)**: add a read-only `TransitionDecision.advanced` property
    (`self.accepted and self.run.blocked is None`) to `state_machine.py`.
  - **Bug fix (A5)**: `LifecyclePipeline.run` → `accepted = decision.advanced`;
    `LifecyclePhaseWorkflow.run` → `accepted = decision.advanced`, AND **replace the stale
    `phase_workflow.py` l.138-139 comment** (the "decision.accepted is True even for a legal transition
    INTO BLOCKED…" reasoning that MISSED the illegal-transition case) with a note citing the dual-signal
    `advanced` contract.
  - **`--model` removal (Q7)**: delete `_warn_model_deprecated`; remove the **exactly 12** `--model`
    option decls (`cli/commands/lifecycle.py` lines 350, 484, 660, 993, 1032, 1071, 1110, 1245, 1308,
    1368, 1532, 1618) across the **12** run verbs (`release define`, `backlog define`, `implement`,
    `review qa`, `review security`, `review code`, `close`, `pipeline`, `audit`, `research`,
    `bug_report`, `implement-review`). **Do NOT touch** the pi/codex subprocess `--model` args
    (`pi_runtime.py`, `codex_runtime.py`, `test_pi_runtime.py` — the sole surviving `--model` reference, Q8).
  - **Deprecation tests — exact ids, INVERT vs DELETE (Q8)**: INVERT (rewrite to assert `No such option:
    --model` in `result.stderr`) the parametrized deprecation cases —
    `test_lifecycle_verb_governance.py::test_verb_model_flag_is_nonfatal_deprecation`,
    `test_lifecycle_fr2_wire_verbs.py::test_wire_verb_model_flag_is_nonfatal_deprecation`,
    `test_implement_review_cli.py::test_implement_review_model_flag_is_nonfatal_deprecation`, and the
    `--model` deprecation cases in `test_cli_backlog_define.py` + `test_lifecycle_cli.py`; keep each
    file's profile-ids-only D-3 rejection assertions (DELETE only a case with no invertible assertion).
  - **Tests — AC-8** a synthetic illegal-transition ladder → step `accepted=False`, `run.blocked is None`
    (RED-first: pre-fix `accepted=True`) at **both** seams; legal blocked review still `accepted=False`;
    legal success `accepted=True`. **AC-9 (Q4/Q7)** parametrized across ALL 12 run verbs: `--model X` →
    `exit_code == 2`, `"No such option: --model"` in **`result.stderr`**, `result.stdout` empty; **no
    `mix_stderr` kwarg on `CliRunner`**; `--step-model <profile-id>` resolves; raw
    `--step-model label=<id>:<effort>` still rejected; pi/codex `--model` unchanged (grep — sole
    surviving reference `test_pi_runtime.py`). AC-10(c-pipeline)+(c-twin)+(d) sabotage. AC-12 ledger.
    NO `specs/backlog`.

## W6 — gates + ship

- [ ] T-57-60 Full local gates (AC-11) + public re-projection, then ship. Checklist:
  - **Unpiped** `pytest` (real exit) — full suite green; `ruff format --check`; `ruff check --no-cache`;
    `mypy --strict dadaia_workspace`.
  - `lint-imports --no-cache` → **`8 kept, 0 broken`**; ignore-cap contract UNCHANGED (the new
    `_fragment_gate.py` / `role_atoms.py` / coherence doctor import only already-imported lifecycle
    internals — verify no new cross-feature/infra edge; if one is unavoidable, document it).
  - `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0.
  - **`public/lifecycle_fragments/**` changed — ONLY `implementation/qa-review.md`** (the FR2
    `quality_assurance_atom` line; **(N2) `input_policies` is a test-fixture fragment, NOT shipped**) →
    `dadaia public stage && dadaia public install --target all && dadaia public doctor`
    (`[ok] public-privacy`, exit 0). *(PE surfaces these to PM/operator or requests devops-engineer;
    PE runs no shell.)*
  - Confirm the v0.1.50 frozen no-steal suite is **zero-diff** (this release never entered
    `spec_context`/lease/gate; ctx_inject is in scope but not that suite).
  - **Dead-anchor archival AT SHIP**: archive `hard-remove-model-flag-across-run-verbs` →
    `specs/_archive/v0.1.57/consumed-backlog/` (its `_warn_model_deprecated` anchor is deleted —
    BL-SCHEMA). Verify no W1–W5 commit staged `specs/backlog`.
  - QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job
    green**; PR; merge.

## W7 — closure (CLOSURE phase)

- [ ] T-57-70 CLOSURE.md + memory truth + disposition + archive. Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write `CLOSURE.md` (Summary, Tasks completed w/ SHAs, Validations
    triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive decision).
  - **MEMORY (§SPEC 8):** `lifecycle-foundation.md` → `FragmentGateWorkflow` base + assembly mixin +
    declarative role→atom map + phase threading + per-input `max_context_policy` + fragment/selector/
    role-map coherence doctor (regen `catalog.json` + `index.md` only if `tldr`/`summary`/`area` change;
    **(Q9) keep the regenerated `tldr` within the established length cap** so the catalog regen +
    `dadaia specs doctor` at W7 stays clean); `architecture.md` → lifecycle module map
    (`workflows/_fragment_gate.py`, `role_atoms.py`, coherence doctor); `dadaia-workflows.md` →
    `--model` verb-surface retirement / no-change confirm; `quality-assurance.md` → assess the
    golden-authoring note; `context-management.md` / `sdd-gate-v3.md` / `tech-stack.md` → **confirm no
    change** (ctx_inject byte-identical). **(N4) memory-honesty guard: state that LAYER-2 grounding is
    mechanically recorded/checked (role→atom map + coherence doctor), but LAYER-1 grounding is self-pull
    DISCIPLINE, NOT mechanically verified** (pending the deferred `layer1-selfpull-handoff-audit-line`).
    `release_origin` → v0.1.57 on each edited atom.
  - **Bug**: append `resolved --release v0.1.57` terminal event to the
    `pipeline-accepted-true-on-illegal-transition` JSONL stream. Bug ledger returns to 0 open.
  - **Backlog return (Ruling A)**: file `layer1-selfpull-handoff-audit-line` (route through PM
    curation). Record in the CLOSURE `## Backlog returns`.
  - **Dispositions**: archive `context-injection-role-phase-canon` + `fragment-workflow-base-dedup` →
    `specs/_archive/v0.1.57/consumed-backlog/` + `consumed_backlog.json`; terminal status
    `DELIVERED — v0.1.57`. `hard-remove-model-flag-across-run-verbs` already archived at SHIP (T-57-60).
    Record all in the CLOSURE `## Dispositions` table.
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.57 → specs/_archive/releases/`
    (devops/operator); set `ACTIVE.md` → next release or `release: none`; mark candidates R9 row
    **SHIPPED — v0.1.57**.
