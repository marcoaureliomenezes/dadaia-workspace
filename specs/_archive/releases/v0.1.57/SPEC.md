# SPEC — v0.1.57 — Injection Canon

**Status:** Aprovado
**Branch:** `feature/v0.1.57` (base: v0.1.56 closure — the orchestrator branches after `Aprovado`)
**Origin:** R9 of the operator-approved 12-release plan; **first** release of the operator's R9→R12
continuation mandate (2026-07-04). The fragment-workflow dedup creates the ONE prompt-assembly seam
**for the 4 handoff-ledger bodies + the backlog assembly mixin** (the `LifecyclePipeline` retains its
own near-identical assembly helpers this release — out of FR1 scope, see §4 non-goals) (N3); the
role→atom map, phase threading, fragment/persona/selector coherence doctor, and the Layer-1
injection ruling are implemented at that seam in the same release — five bodies touched once, not twice.
**Dual definition review 2026-07-04 (software-architect REJECT + qa-engineer REJECT — folded):** all
QA amendments Q1–Q9 and architect amendments A1–A5 + LOW notes N1–N4 are folded into this Draft with
grep-able `(Q#)`/`(A#)`/`(N#)` reconciliation markers. QA re-verifies before `Aprovado`.
**Definition-time inspection** (product-engineer code read, 2026-07-04) — every claim below is a read
fact from the current post-v0.1.56 source, not a restatement of the backlog dossiers (several dossier
claims are now stale and are corrected in §9).
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC —
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-04T043000Z-refine-specs-v0157.html`.
**Consumes:** backlog `context-injection-role-phase-canon` (3 intents) + `fragment-workflow-base-dedup`
(1) + `hard-remove-model-flag-across-run-verbs` (1, INCLUDED per §9 Ruling B). **Bug debt at pick:**
`pipeline-accepted-true-on-illegal-transition` (LOW) — resolved this release (bugs are always solved).

## 1. Problem

Layer-2 prompt assembly is duplicated across five near-identical workflow bodies, so every
role-grounding fix must land five times or land by luck. As a direct consequence, role grounding
today depends on whichever fragment author remembered to declare an atom, injection is never
phase-aware on either agentic layer, and one workflow body already carries a latent model-threading
gap. A reachable state-machine bug lets the pipeline mark an illegal transition as accepted, and a
v0.1.56 `--model` soft-deprecation is now debt whose migration is complete.

**Read facts (source, 2026-07-04):**

1. **Five workflow bodies duplicate the assembly seam.** `release_definition.py`, `audit.py`,
   `research.py`, `bug_report.py` are near-byte-identical across 12+ members
   (`_run_model_step` / `_resolve_upstream` / `_produce_payload` / `_graph_completeness_block` /
   `_prefix_with_static_inputs` / `_collect_static_inputs` / `_fragment_bundle` / `_select_context` /
   `_render_selection` / `_scope` / `_with_step_outcome` / `run`). `backlog_definition.py` is a
   structural outlier (kind-based dispatch, `demand` param, `registry`+`downgrade` seams, **no**
   handoff-ledger data plane) that still duplicates the assembly helpers. v0.1.56 added the
   three-part policy seam to all five, so the dup surface **grew**.

2. **Role grounding depends on per-fragment luck.** There is no declarative role→memory-atom map.
   `implementation.qa_review` (`dynamic_inputs: [spec_criteria, plan_test_strategy, change_diff,
   test_evidence]`) omits `quality_assurance_atom`, while `release_definition.spec_review_qa`
   (`[spec_draft, quality_assurance_atom, test_catalog_summary]`) injects it. **Deeper (grill):** the
   frontmatter fix is *inert* — `container.build_lifecycle_pipeline` / `build_lifecycle_phase_workflow`
   wire **no `ContextSelector`**, and the implementation-workflow fragment inputs (`spec_criteria`,
   `plan_test_strategy`, `change_diff`, `test_evidence`, `dependency_changes`, `plan_slice`,
   `relevant_source_files`, `changed_paths`, `verification_commands`, `implementation_result`) are
   **not registered selectors**. Role grounding must be delivered by a map applied at assembly, not
   by a fragment declaration.

3. **Nothing is phase-aware.** `context_selector.SpecContext` carries `specs_dir` / `release_id` /
   `handoff_dir` — no `phase`. No selector or fragment can gate on the active `ACTIVE.md` phase.

4. **The coherence surface is partial, not absent.** `persona_doctor.check_persona_resolution`
   already asserts every model-driven catalog/pipeline step role resolves to a non-PM persona atom.
   What has **no** doctor: fragment-file role/orphan coverage and **selector coherence**
   (`dynamic_inputs` → a registered selector). The `sel_constitution` selector has **no direct
   fragment consumer**, but is reached indirectly at runtime via `write_set_guidance` (declared by
   `release_definition.tasks_create`) → `sel_write_set_guidance` → `sel_constitution`, and directly as
   `spec_create`'s `static_input` (A4) — it is **not** dead. `max_context_policy` is **fragment-global**
   (`select_all` applies one policy to all inputs).

5. **A reachable pipeline bug.** `LifecyclePipeline.run` computes `accepted = run.blocked is None`.
   On an illegal transition the state machine returns `TransitionDecision(accepted=False,
   run=<unchanged, blocked=None>)`, so `accepted` becomes `True` while the phase never advances.
   `phase_workflow.py` carries the identical latent pattern. (v0.1.56 FR4's edge removal made this
   reachable: a review-phase step targeting IMPLEMENTATION is now an illegal transition.)

6. **`--model` is completed debt.** v0.1.56 kept `--model` as a non-fatal deprecation warning "until
   callers migrate". The only `dadaia lifecycle --model` callers are its own deprecation-warning
   tests; the pi/codex subprocess `--model` args are a different flag (OUT of scope). Migration is
   trivially complete.

## 2. Goals

1. Extract **one** `FragmentGateWorkflow` base for the 4 handoff-ledger bodies (`release_definition`,
   `audit`, `research`, `bug_report`) and a thin assembly mixin for `backlog_definition`, under
   **golden-first** discipline (behaviour byte-locked before the refactor). One-seam-only fixes can
   no longer recur.
2. A **declarative role→memory-atom map** consumed at Layer-2 assembly (base + pipeline +
   phase_workflow) so role grounding is guaranteed, not per-fragment luck; **thread the active phase**
   into `SpecContext`; deliver `quality_assurance_atom` to `implementation.qa_review` via the map.
3. A **fragment/selector/role-map coherence doctor** (extending, not duplicating, `persona_doctor`);
   a recorded `sel_constitution` decision; **per-input `max_context_policy`** overrides.
4. A recorded, operator-overridable **Layer-1 injection ruling**: ratify self-pull (ctx_inject
   byte-identical) and make Layer-2 grounding mechanically verifiable; defer the L1 handoff-audit-line.
5. Fix `pipeline-accepted-true-on-illegal-transition` at root cause (pipeline **and** the
   phase_workflow twin).
6. **Hard-remove** `--model` + `_warn_model_deprecated` across every run verb (deprecation-expiry).

## 3. Functional requirements

### FR1 — `FragmentGateWorkflow` base + assembly mixin (golden-first)

- **Golden capture FIRST (behaviour lock).** Before any extraction, capture goldens of the built
  prompts + produced ledger payloads for `release_definition`, `audit`, `research`, `bug_report`,
  **and** `backlog_definition`, plus the `pipeline` implementation ladder, under a deterministic
  `--harness fake` run. Commit the goldens. Platform-invariant path normalization (v0.1.55 law)
  applies to every golden carrying `.dadaia/handoff/<ctx>/` or `specs/` refs. **Fix-the-split-never-the-golden.**
  **(Q1) The `_scope` capture EXCLUDES the model-selection fields (`model_profile`/`resolved_model`)** —
  the golden pins only the non-model `_scope` fields (role, allowed_paths, required_evidence, task_id,
  prompt); the Problem-#8 model-threading convergence is proven **solely** by the RED-first
  `req.resolved_model is not None` test (AC-2), **never** by a golden diff. **(Q2) These W1 goldens
  are byte-identity-locked only through end-of-W1 (pre-FR2);** W2's role-atom prompt injection and W3's
  per-input policies **intentionally re-baseline** the affected goldens under their own RED-first gates
  (AC-3 / AC-6) — that is NOT "fixing the split". Each wave records in its AC-12 ledger which goldens
  re-baseline and why.
- **Base for the 4 handoff-ledger bodies.** Extract `FragmentGateWorkflow[StepT, ResultT]` in a new
  `features/lifecycle/workflows/_fragment_gate.py` carrying the shared members. It parameterizes the
  5 legitimate divergence axes via abstract/overridable hooks: (i) the Step/Result dataclass types
  (generic `StepT`/`ResultT`); (ii) the `_SEQUENCE` (a class-bound default sequence); (iii) `run()`'s
  command string + initial phase + terminal-gate + result factory — **(N1) the base derives each
  body's empty-sequence `ValueError` message from the class command string** so each body keeps its
  exact text (`"release-definition workflow requires…"`, `"audit workflow requires…"`, …); (iv) the
  terminal gate's phase behaviour (`release_definition` transitions → IMPLEMENTATION;
  audit/research/bug_report COMPLETE with no transition); (v) `_scope` (overridable — `bug_report`
  keeps its ADDITIVE `bug_write` special-case). `release_definition`, `audit`, `research`,
  `bug_report` become thin subclasses.
- **Refactor trap — sequence-scoped iteration.** `_produce_payload` and `_graph_completeness_block`
  must iterate the **sequence passed to `run()`** (threaded through, or a class attribute), never a
  module-global `_SEQUENCE`. This is the exact single-seam defect the dedup removes. **(Q3) The
  module-global `_SEQUENCE` SURVIVES by name per body** — it stays as `run()`'s default `sequence` arg;
  run-scoped iteration is achieved by making `_produce_payload`/`_graph_completeness_block` read the
  run-threaded `sequence` (not the module global). Three guardrail suites import the module-global
  `_SEQUENCE` by name and must not break (see T-57-11 fate ledger). Goldens cannot catch this
  conversion (same object under a normal run) — only the AC-2 custom-`_SEQUENCE` unit test + AC-10(a)
  sabotage can.
- **Assembly mixin for backlog.** Extract the assembly helpers (`_prefix_with_static_inputs`,
  `_collect_static_inputs`, `_fragment_bundle`, `_select_context`, `_render_selection`, `_scope`)
  into a `_FragmentAssemblyMixin` shared by the base and `BacklogDefinitionWorkflow`.
  `backlog_definition` keeps its kind-based dispatch and Python-disposing steps; it does **not** join
  the full base.
- **Convergence bug fix (folded — grill Problem #8).** `backlog_definition._scope` currently drops
  `model_profile`/`resolved_model` from its `PromptScope` although `BacklogStep` carries both. The
  unified mixin `_scope` threads them. This is a **behaviour change**, RED-first (not a silent golden
  diff): backlog_define under fake asserts `req.resolved_model is not None` post-fix.
- **Anchor note.** The dedup's anchor `ReleaseDefinitionWorkflow` **survives** (refactored onto the
  base, class retained) → archival at CLOSURE.

### FR2 — Declarative role→atom map at Layer-2 assembly + phase threading + qa_review atom

- **Role→atom map.** Add a declarative default map (a single source, e.g.
  `features/lifecycle/role_atoms.py`): `software-architect → specs/memory/architecture.md`,
  `qa-engineer → specs/memory/quality-assurance.md`, `product-engineer → product catalog`
  (`specs/memory/product/catalog.json`). Resolve it at prompt assembly from `step.role`, **independent
  of** the fragment's `dynamic_inputs`, and inject the resolved atom as a labelled context block. A
  multi-role step (comma-split, e.g. `qa-engineer, software-architect`) resolves each named role's
  atom. A role with no mapping (e.g. `python`, `security-reviewer` if unmapped) injects nothing. The
  resolved atom refs are recorded in the run record's `InjectedContext.refs` (the Layer-2
  verifiability seam — FR4).
- **Applied at every assembly surface — single-sourced logic + production wiring (A1, blocking).** The
  map DATA **and** the resolve-and-inject LOGIC (resolve role → read `specs/memory/<atom>.md` → append
  a labelled context block → record the ref in `InjectedContext.refs`) live in **ONE helper** in
  `role_atoms.py`, consumed by all three surfaces — never copy-pasted 3×. Each surface supplies the
  helper a `specs_dir`: (a) the `FragmentGateWorkflow` base via `self._selector.spec_context.specs_dir`;
  (b) `LifecyclePipeline` via a `specs_dir`/resolver **injected into `LifecyclePipeline.__init__`** and
  built in `build_lifecycle_pipeline` from `workspace_root + context` (same
  `workspace_root/repos/<ctx>/specs` → self-hosting `workspace_root/specs` fallback as
  `build_release_definition_workflow`); (c) `LifecyclePhaseWorkflow` via a `workspace_root`/resolver
  **injected into `LifecyclePhaseWorkflow.__init__`** and resolved at `run()` from `scope.context`.
  **The W2 write set adds `build_lifecycle_pipeline`, `build_lifecycle_phase_workflow`, and both
  constructor signatures** — without them the map ships INERT in the real pipeline path (reproducing
  the frontmatter-inert defect). **AC-3 asserts the PRODUCTION builders wire the resolver**, not only
  fixture-constructed pipelines.
- **Phase threading.** Add `phase: str | None = None` to `SpecContext` (additive-optional). Resolve
  the active phase from `ACTIVE.md` at the 5 container construction sites
  (`build_release_definition_workflow`, `build_backlog_definition_workflow`, `build_audit_workflow`,
  `build_research_workflow`, `build_bug_report_workflow`) and thread it into `SpecContext`. Expose it
  so a selector/fragment may declare an optional phase gate (the gate mechanism is additive-optional
  and inert unless a fragment declares it — no fragment declares one this release).
- **qa_review atom (secondary).** Add `quality_assurance_atom` to `implementation.qa_review`'s
  `dynamic_inputs` for declaration fidelity; the **guarantee** is the role→atom map (qa-engineer →
  quality-assurance.md), which delivers the atom to the qa_review step regardless of the fragment
  declaration and regardless of the pipeline's missing selector.

### FR3 — Coherence doctor (extending persona_doctor) + sel_constitution + per-input policy

- **Coherence doctor — NEW checks only (do not re-implement persona_doctor).** Add a fragment/selector
  coherence doctor (e.g. `features/lifecycle/fragment_coherence_doctor.py`). Each check carries a
  **stable ID + fixed severity** (Q6) so the doctor output is mechanically grep-assertable, and the
  label order is identical across FR3 / AC-5 / AC-10 / T-57-30 (A3):
  - **FRAG-COH-1 (ERROR)** — every fragment file's `role` resolves to a persona atom OR is
    `shared`/`python`.
  - **FRAG-COH-2 (ERROR, SCOPED — A2)** — a `dynamic_inputs` entry resolves to a **registered
    `ContextSelector` selector**, checked as ERROR **only** for a dynamic_input that is *actually
    resolved at runtime*, i.e. the **MAIN fragment of a selector-wired workflow step**
    (release_definition / audit / research / bug_report / backlog_definition `_SEQUENCE` main
    fragments). It is **WARN (or skipped)** for (i) shared-fragment `dynamic_inputs` (body-only, the
    workflow resolves only the step's main fragment inputs, never the cited shared fragments' inputs)
    and (ii) main-fragment inputs of a **selector-less path** (the `implementation.*` fragments the
    selector-less pipeline/phase_workflow consume). This scope is what makes AC-5 green on the current
    tree while a sabotage of a selector-wired main fragment (release_definition.spec_create) fires the
    ERROR (AC-10(e)).
  - **FRAG-COH-3 (WARN)** — orphan check: every non-shared fragment is bound to some workflow step,
    and every cited shared fragment id exists.
  - **FRAG-COH-4 (ERROR)** — role→atom-map coverage: each model-driven step's role-mapped atom appears
    in its resolved injected refs (the mechanical Layer-2 grounding proof, FR4).
  `ok=` is computed from the **ERROR checks only** (FRAG-COH-1/2/4); WARNs never fail the doctor. Wire
  into `dadaia specs doctor` (or the lifecycle doctor surface).
- **`sel_constitution` decision (recorded — A4 corrected).** `sel_constitution` is **NOT dead**: it
  has no *direct* fragment consumer, but is reached indirectly at runtime via `write_set_guidance`
  (a registered selector declared by `release_definition.tasks_create`, whose `sel_write_set_guidance`
  calls `sel_constitution`) and directly as `spec_create`'s `static_input`. KEEP `sel_constitution`
  registered; KEEP the static-input path canonical; do **not** add constitution to the role→atom
  baseline. No removal, no new consumer. The recorded decision (test/comment) MUST note the
  `write_set_guidance` indirection so the selector is never mistaken for dead.
- **Per-input `max_context_policy`.** Add an optional `input_policies: {input_name: policy}` fragment
  frontmatter key (additive; the loader's existing list-key validation is untouched). `Fragment`
  gains an additive-optional `input_policies` field; `ContextSelector.select_all` accepts a per-name
  policy override map, falling back to the fragment-global `max_context_policy` for unlisted inputs.
  **(N2) `input_policies` is exercised by a TEST-FIXTURE fragment, not a shipped public fragment** —
  no shipped fragment has a real per-input-policy need this release, so shipping speculative config is
  avoided (and a W2 qa-review.md + W3 same-file edit on a shipped fragment is avoided).

### FR4 — Layer-1 injection ruling (ratify self-pull; verifiable; operator-overridable)

- **Decision: RATIFY self-pull — see §9 Ruling A. OPERATOR-OVERRIDABLE.** Constitution / architecture
  / quality-assurance stay self-pull-only at Layer-1; `ctx_inject.py#_build_memory` remains
  **byte-identical** (bounded tech-stack digest + lean catalog digest). Rationale: preserves the
  deliberate v0.1.30 WS-C dehydration; avoids unbounded L1 context growth.
- **Verifiability (delivered on the Layer-2 side R9 already builds).** The role→atom map's injected
  atoms are recorded in `InjectedContext.refs`; the FR3 coherence doctor asserts each model-driven
  step's role-mapped atom appears in its injected refs — the mechanical proof grounding fired.
- **Deferred (backlog return at CLOSURE).** The Layer-1 self-pull **handoff-audit-line** (a
  schema-level "prove the atoms were read" field) needs a handoff-v1.1 schema bump + all-agent
  adoption + a validator; it is filed as `layer1-selfpull-handoff-audit-line` rather than ballooning
  R9's surface. If the operator prefers bounded phase-aware L1 digests instead, this ruling reopens.
- **Anchor note.** `ctx_inject.py#main` **survives** (byte-identical) → archival at CLOSURE.

### FR5 — Fix `pipeline-accepted-true-on-illegal-transition` (root cause, both seams)

- **Single-source the accept predicate (A5).** Add a read-only property
  `TransitionDecision.advanced` (`self.accepted and self.run.blocked is None`) to
  `state_machine.py` so the correct dual-signal predicate is the state-machine's own contract, not
  caller lore — protecting any third caller of `runner.run`.
- **Pipeline.** In `LifecyclePipeline.run`, replace `accepted = run.blocked is None` with
  `accepted = decision.advanced`. Correct across all decision shapes: illegal transition
  (`decision.accepted=False`) → not advanced; blocked review (`_block` returns `accepted=True`, run
  blocked) → not advanced; missing-req block → not advanced; success → advanced.
- **Phase workflow twin.** Apply the identical fix to `LifecyclePhaseWorkflow.run`
  (`accepted=decision.run.blocked is None` → `accepted=decision.advanced`), since it carries the same
  latent pattern. **(A5, MANDATORY) replace the stale `phase_workflow.py` l.138-139 comment**
  ("`decision.accepted` is True even for a (legal) transition INTO BLOCKED; the gate's pass/fail
  signal is whether the run carries a blocked state") — that reasoning is exactly what MISSED the
  illegal-transition case; the new comment must cite the dual-signal `advanced` contract.
- **Bug disposition.** Resolved this release; a `resolved --release v0.1.57` terminal event is
  appended to the JSONL bug stream at CLOSURE.

### FR6 — Hard-remove `--model` across every run verb (deprecation-expiry)

- **Remove the flag + seam.** Delete `_warn_model_deprecated` and remove the **exactly 12** `--model`
  option declarations across the **12** `dadaia lifecycle` run verbs (Q7 — `release define`,
  `backlog define`, `implement`, `review qa`, `review security`, `review code`, `close`, `pipeline`,
  `audit`, `research`, `bug_report`, `implement-review`; option decls at `cli/commands/lifecycle.py`
  lines 350, 484, 660, 993, 1032, 1071, 1110, 1245, 1308, 1368, 1532, 1618). `--step-model
  <profile-id>` (profile-ids-only, D-3) is the sole model-selection surface.
- **Scope guard.** The pi/codex subprocess `--model <id>` args (`infrastructure/pi_runtime.py`,
  `infrastructure/codex_runtime.py`, `tests/unit/infrastructure/test_pi_runtime.py`) are a **different
  flag** and are UNCHANGED (established OUT of scope by v0.1.56).
- **Tests.** Delete or rewrite the ~5 deprecation-warning tests to assert the flag is now **unknown**
  (Click "No such option"), preserving the profile-ids-only rejection assertions.
- **Anchor note.** `hard-remove-model-flag-across-run-verbs` anchors `_warn_model_deprecated`, which
  this removal **DELETES** → dead anchor → **archival at SHIP** (BL-SCHEMA dead-anchor law).

## 4. Non-goals

- **No Layer-1 memory expansion.** Ratifying self-pull (FR4) means `ctx_inject.py` is byte-identical;
  no constitution/architecture/QA is added to the L1 bootstrap.
- **No new workflows and no fragment-body semantic rewrite.** FR1 is a mechanical dedup; the shipped
  fragment prompts are byte-identical through end-of-W1 (golden-locked); FR2/FR3 intentionally
  re-baseline the affected goldens (Q2). FR2 adds a role→atom map + one fragment frontmatter line,
  not new fragment prose.
- **(N3) The `LifecyclePipeline` is NOT folded into the FR1 base.** The pipeline retains its own
  near-identical assembly helpers (`_select_context`/`_render_selection`/`_fragment_bundle`/`_scope`)
  this release — its implement→review ladder is a different control-flow shape. "One prompt-assembly
  seam" refers to the **4 handoff-ledger bodies + the backlog assembly mixin**; residual pipeline
  dedup is deliberately out of scope.
- **No lease/gate/spec_context change.** This release touches `features/lifecycle/**`,
  `hooks/ctx_inject.py` (byte-identical), `cli/commands/lifecycle.py`, `container.py`, the public
  fragments, and lifecycle tests — it does **not** enter `spec_context`/lease/gate. The v0.1.50 frozen
  no-steal suite is expected **zero-diff** (see §6).
- **No constitution change; no roster change.** No `constitution.md` edit.
- **No hard Layer-1 handoff-audit gate.** Deferred to a backlog return (FR4).

## 5. Acceptance criteria

- **AC-1 (golden-first behaviour lock — RED-safe):** goldens of the built prompts + produced ledger
  payloads for `release_definition`, `audit`, `research`, `bug_report`, `backlog_definition`, and the
  `pipeline` ladder are captured under `--harness fake`, path-normalized (v0.1.55), and committed
  **before** the FR1 extraction. After extraction the goldens are **byte-identical** (the base +
  mixin reproduce every body's prompt/payload). **(Q1) The `_scope` capture EXCLUDES `model_profile`/
  `resolved_model`** — a `_scope` divergence fails the golden ONLY on non-model fields (role,
  allowed_paths, required_evidence, task_id, prompt); the backlog model-threading convergence is
  proven solely by AC-2's RED-first `req.resolved_model is not None`, never by a golden diff. **(Q2)
  Byte-identity is asserted at end-of-W1 (pre-FR2) only;** FR2's role-atom prompt injection and FR3's
  per-input policies INTENTIONALLY re-baseline the affected goldens under AC-3/AC-6 — recorded per
  wave in the AC-12 ledger — which is NOT "fixing the split".
- **AC-2 (dedup base is the single seam):** `release_definition`, `audit`, `research`, `bug_report`
  subclass `FragmentGateWorkflow`; the shared members exist once in the base; `_produce_payload` /
  `_graph_completeness_block` iterate the run-scoped sequence (a unit test proves a base subclass with
  a **custom `_SEQUENCE`** produces/validates that sequence, not a module global).
  `backlog_definition` shares `_FragmentAssemblyMixin`; a RED-first test asserts backlog_define under
  fake yields a request with `resolved_model is not None` (the converged `_scope` model-threading fix).
- **AC-3 (role→atom map delivers grounding — incl. PRODUCTION wiring, A1):** for each mapped role, a
  model-driven step run records the role's atom ref in `InjectedContext.refs` and the atom content
  appears in the assembled prompt — asserted for the `FragmentGateWorkflow` base, the
  `LifecyclePipeline` `review_qa` step (`qa-engineer → quality-assurance.md`, RED-first: absent
  pre-fix because no selector is wired), and the single-step `LifecyclePhaseWorkflow` path. A
  `product-engineer` step records the catalog ref; a `software-architect` step records
  `architecture.md`. **(A1) A dedicated assertion proves the PRODUCTION builders
  (`build_lifecycle_pipeline`, `build_lifecycle_phase_workflow`) wire the role→atom resolver** (with a
  real `specs_dir`), not only fixture-constructed pipelines — so the map is not inert in the real
  path. The resolve-and-inject helper is single-sourced in `role_atoms.py` (asserted used by all
  three surfaces).
- **AC-4 (phase threading):** `SpecContext` carries `phase`; each of the 5 container builders resolves
  it from `ACTIVE.md` and threads it into `SpecContext`; a test with a fixture `ACTIVE.md` asserts the
  resolved phase reaches `SpecContext.phase`. Absent/malformed `ACTIVE.md` degrades to `phase=None`
  (fail-open), asserted.
- **AC-5 (coherence doctor — the new checks, stable IDs Q6/A3):** the fragment/selector coherence
  doctor reports **FRAG-COH-1** (ERROR — fragment role with no persona atom, not shared/python),
  **FRAG-COH-2** (ERROR — a `dynamic_inputs` entry unregistered, **scoped to the MAIN fragment of a
  selector-wired workflow step** per A2; WARN/skip for shared-fragment and selector-less inputs),
  **FRAG-COH-3** (WARN — orphan fragment / dangling shared id), **FRAG-COH-4** (ERROR — model-driven
  step whose role-mapped atom is absent from its injected refs). `ok=` is computed from ERROR checks
  only. On the current tree, after the FR2 map + FR3 fixes, the doctor is **green** (`ok=True`)
  despite the ~10 legitimately-inert shared/implementation unregistered inputs (they are WARN/skip,
  not ERROR). RED-first: a temporary unregistered `dynamic_inputs` entry **on a selector-wired main
  fragment (`release_definition.spec_create`)** makes **FRAG-COH-2** report an ERROR and flips `ok` to
  False (the doctor output string contains `FRAG-COH-2`). `persona_doctor.check_persona_resolution`
  stays green and is **not** re-implemented.
- **AC-6 (per-input policy — N2 fixture):** a **test-fixture** fragment (not a shipped public
  fragment) declaring `input_policies: {spec_draft: exact-files-only, architecture_summary: summary}`
  resolves `spec_draft` at `exact-files-only` and `architecture_summary` at `summary` in one
  `select_all` call, while an input not listed falls back to the fragment-global `max_context_policy`.
  A fragment with no `input_policies` behaves exactly as today (byte-stable).
- **AC-7 (Layer-1 ratification + verifiability):** `ctx_inject.py`'s injected bootstrap is
  **byte-identical** to pre-release (a golden/assert on `_build_memory` output for a fixture specs
  tree); the existing `test_ctx_inject.py` / `test_ctx_inject_digest.py` remain green with no
  behavioural change. The Layer-2 verifiability is AC-3 + FRAG-COH-4.
- **AC-8 (bug fix — RED-first, both seams):** a synthetic pipeline ladder whose step requests an
  illegal transition (e.g. a review phase targeting IMPLEMENTATION post-v0.1.56) makes the step's
  `accepted` be **False** and `run.blocked is None` (the run is unchanged, not advanced); RED-first:
  pre-fix `accepted` is `True`. The identical assertion holds for `LifecyclePhaseWorkflow.run`. A
  legal blocked review still reports `accepted=False`; a legal success reports `accepted=True`.
- **AC-9 (`--model` removed — parametrized × 12, channel-pinned Q4/Q7):** `--model` is **no longer a
  registered option** on any run verb. A test **parametrized across ALL 12 run verbs** (Q7) asserts a
  `--model X` invocation exits with **`exit_code == 2`**, the string **`No such option: --model` is in
  `result.stderr`**, and **`result.stdout` is empty** (Q4 — under Click 8.4.1 a `UsageError` lands in
  stderr with an empty stdout; this is the R-QA-1 trap that bit v0.1.56). **`CliRunner` MUST NOT be
  passed `mix_stderr`** — the kwarg was removed in Click 8.2 and the installed 8.4.1 `TypeError`s on
  it. `_warn_model_deprecated` is deleted (grep: zero references in `dadaia_workspace/` + `tests/`).
  `--step-model <profile-id>` resolves; a raw `--step-model label=<id>:<effort>` is still rejected
  (D-3). The pi/codex subprocess `--model` args are unchanged — `tests/unit/infrastructure/test_pi_runtime.py`'s
  `pi --model` is the **sole surviving** `--model` reference (Q8).
- **AC-10 (mutation-sanity per new test — sabotage → FAIL → revert):** (a) point `_produce_payload`
  back at a module-global `_SEQUENCE` ⇒ AC-2 custom-sequence test FAILS; (b) drop the role→atom map
  injection for qa-engineer ⇒ AC-3 pipeline `review_qa` FAILS; **(c-pipeline)** revert ONLY the
  `LifecyclePipeline.run` `accepted` fix ⇒ AC-8 pipeline seam FAILS; **(c-twin)** revert ONLY the
  `LifecyclePhaseWorkflow.run` fix ⇒ AC-8 phase_workflow seam FAILS (Q5 — each seam sabotaged
  independently); (d) restore `_warn_model_deprecated` + `--model` ⇒ AC-9 "No such option" FAILS;
  (e) make one **selector-wired main fragment** (`release_definition.spec_create`) `dynamic_inputs`
  name an unregistered selector ⇒ AC-5 **FRAG-COH-2** FAILS; **(f)** append any atom to
  `ctx_inject._build_memory`'s L1 bootstrap ⇒ AC-7 byte-identical assert FAILS (Q5 — the Ruling-A
  no-expansion enforcement gets its own mutation check). Each captured on its task line, then reverted.
- **AC-11 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the full
  **unpiped** `pytest` (real exit), `lint-imports --no-cache` (`8 kept, 0 broken`; ignore-cap
  UNCHANGED unless a justified edge is added and documented), `dadaia specs doctor` (exit 0),
  `dadaia backlog doctor` (exit 0). Because `public/lifecycle_fragments/**` changed (FR2 qa_review
  frontmatter + FR3 any `input_policies`), the ship wave runs `dadaia public stage && dadaia public
  install --target all && dadaia public doctor` (`[ok] public-privacy`, exit 0).
- **AC-12 (surviving/dead behavior ledger, per wave):** each wave records a two-column ledger on its
  task line; every move/rename/repoint grep includes `tests/` **and** non-import textual references.
  The FR6 wave's grep confirms no non-test caller of the CLI `--model` flag survives. **No**
  implementation-wave commit stages any `specs/backlog/**` (dead/surviving anchors are dispositioned
  at SHIP/CLOSURE, but the discipline holds).

## 6. Consumed bugs & backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `context-injection-role-phase-canon` | backlog (candidate) | HIGH | role→atom map + phase → FR2; coherence doctor + sel_constitution + per-input policy → FR3; L1 ruling → FR4 | Anchors `ContextSelector` (survives, extended), `FragmentLoader` (survives, extended), `ctx_inject#main` (survives, byte-identical) → **CLOSURE** |
| `fragment-workflow-base-dedup` | backlog (candidate) | MEDIUM | base + mixin → FR1 | Anchors `ReleaseDefinitionWorkflow` (survives, onto base) → **CLOSURE** |
| `hard-remove-model-flag-across-run-verbs` | backlog (candidate) | MEDIUM | removal → FR6 | Anchors `_warn_model_deprecated` (**DELETED**) → dead anchor → **SHIP** (BL-SCHEMA) |
| `pipeline-accepted-true-on-illegal-transition` | bug (JSONL, LOW) | LOW | root-cause fix → FR5 | Terminal `resolved --release v0.1.57` at CLOSURE |

**Archival timing.** Two consumed backlog anchors SURVIVE (dedup + injection-canon) → dispositioned +
archived at CLOSURE. One consumed anchor DIES (`_warn_model_deprecated` deleted by FR6) → the entry is
archived **at SHIP** (dead-anchor BL-SCHEMA law, so `dadaia backlog doctor` never sees a live entry
referencing a dead anchor mid-branch). Discipline: **no `specs/backlog/**` staged in W1–W5** (AC-12).

**Frozen-suite check — NO interaction.** The v0.1.50 no-steal lease/gate suite
(`tests/unit/features/spec_context/test_lease_*`, `test_gate_policy.py`) is untouched: this release
lives in `features/lifecycle/**`, `hooks/ctx_inject.py` (byte-identical), `cli/commands/lifecycle.py`,
`container.py`, `public/lifecycle_fragments/**`, and lifecycle tests — it enters no `spec_context`/lease/
gate path. Expect **zero** frozen-file diff. `hooks/ctx_inject.py` **is** in scope but is NOT a member
of the frozen no-steal suite; its own tests (`test_ctx_inject.py` / `test_ctx_inject_digest.py`) stay
green and, under the FR4 ratification, unchanged in behaviour (AC-7).

## 7. Risks

- **Golden brittleness / over-normalization (FR1).** A golden that captures a host path or a
  non-deterministic ordering would false-fail on the refactor. Mitigation: v0.1.55 platform-invariant
  normalization on every path-bearing golden; capture under a fixed fixture specs tree + `--harness fake`.
- **Base coupling the wrong bodies (FR1).** Forcing `backlog_definition` into the full base would
  couple two control-flow shapes. Mitigation: assembly mixin only for backlog (Ruling C); the full
  base is the 4 handoff-ledger bodies.
- **Silent behaviour change hidden in a golden (FR1 Problem #8).** The backlog `_scope` model-threading
  convergence is a real behaviour change. Mitigation: an explicit RED-first test (not a golden diff)
  gates it.
- **Role→atom map delivery in the selector-less pipeline (FR2).** The pipeline/phase_workflow wire no
  `ContextSelector`, so the map must resolve atoms via a light direct-read path. Mitigation: a
  standalone role→atom resolver that reads the atom file (not the full selector); AC-3 RED-first proves
  delivery in the pipeline.
- **Coherence doctor over-reach (FR3, A2 DECIDED).** A doctor that hard-errors on the (legitimately
  inert) shared/implementation-fragment declarations would break the tree. Resolved (not an either/or):
  **FRAG-COH-2 ERRORs only for the MAIN fragment of a selector-wired workflow step**; shared-fragment
  inputs (body-only, never resolved) and selector-less-path inputs (`implementation.*`) are WARN/skip;
  `ok=` counts ERRORs only. After the FR2 map + FR3 fixes the doctor is green on the current tree (AC-5).
- **`--model` removal breaking a hidden caller (FR6).** Mitigation: AC-9 greps `dadaia_workspace/` +
  `tests/` to prove only the deprecation-warning tests referenced the CLI flag; the pi/codex subprocess
  `--model` is a different flag, asserted unchanged.
- **Public-asset projection drift (FR2/FR3).** Editing `public/lifecycle_fragments/**` requires
  re-projection. Mitigation: the ship wave runs `stage`/`install`/`doctor` (AC-11); doctor must show
  `[ok] public-privacy`.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/sdd/lifecycle-foundation.md` — **primary edit.** The prompt-assembly control
  plane generalizes: one `FragmentGateWorkflow` base + assembly mixin behind the 4 handoff-ledger
  bodies (+ backlog mixin); the declarative role→atom map as the guaranteed grounding mechanism;
  phase threading into `SpecContext`; per-input `max_context_policy`; the fragment/selector/role-map
  coherence doctor. Assess `tldr`/`summary` (regenerate `catalog.json` + `index.md` only if
  `tldr`/`summary`/`area` change; **(Q9) the regenerated `tldr` must stay within the established
  length cap** so the CLOSURE catalog regen + `dadaia specs doctor` at W7 stays clean).
  `release_origin` → v0.1.57. **(N4) Memory-honesty guard:** memory may state that **Layer-2**
  grounding is mechanically recorded/checked (role→atom map + coherence doctor); **Layer-1** memory
  grounding must be described as **self-pull DISCIPLINE**, not mechanically verified, pending the
  deferred `layer1-selfpull-handoff-audit-line`.
- `specs/memory/product/sdd/dadaia-workflows.md` — confirm the 7-workflow roster copy still holds
  (no workflow added/removed); note the `--model` surface retirement if the verb surface is enumerated.
  Likely a small edit or no-change-confirm.
- `specs/memory/architecture.md` — the lifecycle module map gains `workflows/_fragment_gate.py` (the
  base) + `role_atoms.py` + the coherence doctor; the workflow-body count/description updates.
  Feature count unchanged. `release_origin` → v0.1.57 if edited.
- `specs/memory/quality-assurance.md` — **assess at CLOSURE.** FR1 introduces byte-goldens for the
  workflow bodies; if the golden-authoring + platform-invariant-normalization law needs a note, add
  it. Confirm.
- `specs/memory/product/platform/context-management.md` / `specs/memory/product/sdd/sdd-gate-v3.md` —
  **no change expected** (ctx_inject byte-identical under FR4). Confirm at CLOSURE.
- `specs/memory/tech-stack.md` — **no change** (no dependency/harness/model roster change). Confirm.

## 9. Definition rulings (grill, operator-unavailable — OPERATOR-OVERRIDABLE)

The operator is unavailable mid-flow; the three intent-level decisions are pre-ruled here with full
rationale and marked overridable. Full evidence: the grill report cited in the header.

- **Ruling A — Layer-1 injection: RATIFY self-pull.** Constitution/architecture/quality-assurance stay
  self-pull-only at L1; `ctx_inject.py` byte-identical. Rationale: adding them to every L1 session is
  the unbounded-context growth v0.1.30 deliberately removed; Layer-2 grounding is made *guaranteed and
  mechanically recorded* by the role→atom map + coherence doctor; the L1 hard handoff-audit-line is
  deferred to a backlog return (`layer1-selfpull-handoff-audit-line`). **Override:** if the operator
  prefers bounded phase-aware L1 digests, FR4 reopens.

- **Ruling B — `--model` removal: INCLUDE in R9.** Deprecation-expiry law: v0.1.56 promised removal
  once callers migrate; the only `dadaia lifecycle --model` callers are the deprecation-warning tests;
  the pi/codex subprocess `--model` is a different, out-of-scope flag. Migration is trivially complete
  ⇒ remove now. **Override:** if the operator wants a longer deprecation window, FR6 defers to N+2.

- **Ruling C — dedup shape.** Full `FragmentGateWorkflow` base for the 4 handoff-ledger bodies;
  assembly mixin for `backlog_definition` (the structural outlier). Rationale: forcing the outlier into
  the full base couples two control-flow shapes; the mixin captures the genuinely shared assembly.

- **Stale-claim corrections (dossier vs source).** (1) The coherence doctor is not absent —
  `persona_doctor` already covers bound step-role persona resolution; FR3 adds only the fragment-file +
  selector + role-map checks. **`sel_constitution` is NOT dead** — it has no *direct* fragment consumer
  but is reached at runtime via `write_set_guidance` (`release_definition.tasks_create`) →
  `sel_write_set_guidance` → `sel_constitution`, and directly as `spec_create`'s `static_input` (A4).
  (2) The `implementation.qa_review` frontmatter fix is inert on its own — the pipeline/phase_workflow
  wire no selector and its inputs are unregistered; the role→atom map is the real delivery mechanism
  (FR2). (3) The dup surface is not uniform across 5 bodies — `backlog_definition` is a structural
  outlier (Ruling C). (4) A latent convergence bug exists: `backlog_definition._scope` drops the
  resolved model (FR1, RED-first fix).
