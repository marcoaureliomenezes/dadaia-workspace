# PLAN — v0.1.57 — Injection Canon

**Status:** Aprovado

Seven waves. **FR1 (the dedup base) lands FIRST** — it is the ONE prompt-assembly seam every later FR
lands on. Golden-first for FR1 (behaviour byte-locked before the refactor). `cli/commands/lifecycle.py`,
`container.py`, `pipeline.py`, and the workflow bodies are shared across waves → the waves are
**sequential** (no parallel `[-]`).

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition
  grill on the picked set (report emitted); three operator-unavailable rulings recorded (§9);
  `Aprovado` after dual review; definition commit.

- **W1 — FR1 `FragmentGateWorkflow` base + assembly mixin (golden-first, the seam).**
  1. **Golden capture FIRST.** Add a golden test that runs `release_definition`, `audit`, `research`,
     `bug_report`, `backlog_definition`, and the `pipeline` ladder under `--harness fake` and captures
     each step's built prompt + produced ledger payload; **path-normalize** (v0.1.55) and commit the
     goldens BEFORE any extraction. These are the behaviour lock. **(Q1) the `_scope` capture EXCLUDES
     `model_profile`/`resolved_model`** — the backlog convergence is proven by AC-2's RED-first
     `req.resolved_model is not None`, never a golden diff. **(Q2) byte-identity holds through
     end-of-W1 only**; W2/W3 re-baseline the affected goldens under AC-3/AC-6 (recorded in each wave's
     AC-12 ledger).
  2. **Extract `_fragment_gate.py`.** `FragmentGateWorkflow[StepT, ResultT]` carrying the shared
     members; overridable hooks for command string / initial phase / terminal-gate / result factory /
     `_scope`. `_produce_payload` + `_graph_completeness_block` iterate the **run-scoped sequence**,
     never a module-global `_SEQUENCE`.
  3. **Migrate the 4 bodies.** `release_definition` (terminal gate → IMPLEMENTATION), `audit`,
     `research`, `bug_report` (terminal gate → COMPLETED-no-transition; bug_report overrides `_scope`
     for the ADDITIVE `bug_write`) become thin subclasses. Keep each body's Step/Result types +
     `_SEQUENCE`.
  4. **Assembly mixin for backlog.** Extract `_FragmentAssemblyMixin` (`_prefix_with_static_inputs`,
     `_collect_static_inputs`, `_fragment_bundle`, `_select_context`, `_render_selection`, `_scope`);
     `BacklogDefinitionWorkflow` mixes it in, keeps its kind-dispatch. **Converge `_scope`** so backlog
     threads `model_profile`/`resolved_model` (RED-first — the Problem-#8 fix).
  - Tests: AC-1 goldens byte-identical post-extraction; AC-2 base-is-single-seam + custom-`_SEQUENCE`
    iteration test + backlog `resolved_model is not None` RED-first. AC-10(a) sabotage. AC-12 ledger.
    NO `specs/backlog`.

- **W2 — FR2 role→atom map + phase threading + qa_review atom.**
  1. **Role→atom map + single-sourced inject helper (A1)** (`features/lifecycle/role_atoms.py`):
     declarative `software-architect→architecture.md`, `qa-engineer→quality-assurance.md`,
     `product-engineer→catalog.json`, PLUS **ONE** resolve-and-inject helper (resolve role → read
     `specs/memory/<atom>.md` → append labelled block → record `InjectedContext.refs`) used by all 3
     surfaces. specs_dir source per surface: base via `self._selector.spec_context.specs_dir`;
     `LifecyclePipeline` via a `specs_dir`/resolver **injected into `LifecyclePipeline.__init__`**,
     built in `build_lifecycle_pipeline` from `workspace_root+context`; `LifecyclePhaseWorkflow` via a
     `workspace_root`/resolver **injected into `LifecyclePhaseWorkflow.__init__`**, resolved at `run()`
     from `scope.context`.
  2. **Phase threading**: add `phase` to `SpecContext`; resolve it from `ACTIVE.md` in the 5 container
     builders; fail-open to `None`.
  3. **qa_review atom**: add `quality_assurance_atom` to `implementation.qa_review` `dynamic_inputs`
     (declaration fidelity; the map is the guarantee).
  - Tests: AC-3 map delivers grounding (pipeline `review_qa` RED-first) + base + phase_workflow +
    **(A1) a production-builder wiring assertion** (`build_lifecycle_pipeline` +
    `build_lifecycle_phase_workflow` wire the resolver, not just fixtures); AC-4 phase reaches
    `SpecContext` (+ fail-open). AC-10(b) sabotage. AC-12 ledger. NO `specs/backlog`.

- **W3 — FR3 coherence doctor + sel_constitution + per-input policy.**
  1. **Coherence doctor** (`features/lifecycle/fragment_coherence_doctor.py`) with **stable IDs +
     fixed severities (Q6/A3)**: **FRAG-COH-1** role→persona/shared/python (ERROR); **FRAG-COH-2**
     `dynamic_inputs`→registered selector, **ERROR only for the MAIN fragment of a selector-wired
     workflow step, WARN/skip for shared + selector-less inputs (A2)**; **FRAG-COH-3** orphan/dangling
     shared id (WARN); **FRAG-COH-4** role→atom-map coverage (ERROR). `ok=` from ERRORs only. Wire into
     `dadaia specs doctor`/lifecycle doctor surface. Do NOT re-implement `persona_doctor`.
  2. **`sel_constitution` (A4)**: KEEP registered + static-input path; recorded decision (comment +
     a test asserting `spec_create` static constitution injection is intact) **noting the
     `write_set_guidance` → `sel_write_set_guidance` → `sel_constitution` indirection** so the selector
     is never mistaken for dead; no removal.
  3. **Per-input policy**: add optional `input_policies` fragment frontmatter key; `Fragment` gains the
     field (loader change); `ContextSelector.select_all` accepts per-name policy overrides. **(N2)
     exercised by a TEST-FIXTURE fragment, not a shipped public fragment.**
  - Tests: AC-5 doctor green after FR2/FR3 (RED-first: unregistered input on the selector-wired
    `release_definition.spec_create` fires **FRAG-COH-2**); AC-6 per-input policy resolution + byte-stable
    when absent. AC-10(e) sabotage. AC-12 ledger. NO `specs/backlog`.

- **W4 — FR4 Layer-1 ruling (ratify self-pull; verifiable).**
  1. **Ratify**: `ctx_inject.py` byte-identical (no code change); add/keep an AC-7 golden/assert on
     `_build_memory` output so any future L1 expansion is caught.
  2. **Verifiability**: rely on FR2's `InjectedContext.refs` + FR3's role→atom-map-coverage check
     (AC-5(d)) as the Layer-2 mechanical proof.
  3. **Defer**: the L1 handoff-audit-line is a CLOSURE backlog return (`layer1-selfpull-handoff-audit-line`).
  - Tests: AC-7 ctx_inject byte-identical; the existing ctx_inject tests stay green. **AC-10(f)
    sabotage** (append an atom to `_build_memory` ⇒ AC-7 FAILS ⇒ revert). AC-12 ledger. NO `specs/backlog`.

- **W5 — FR5 bug fix + FR6 `--model` removal.**
  1. **Bug fix (A5)**: add read-only `TransitionDecision.advanced` (`accepted and run.blocked is None`)
     to `state_machine.py`; `LifecyclePipeline.run` → `accepted = decision.advanced`;
     `LifecyclePhaseWorkflow.run` → `accepted = decision.advanced` AND **replace the stale
     `phase_workflow.py` l.138-139 comment** (the reasoning that missed the illegal-transition case).
  2. **`--model` removal (Q7)**: delete `_warn_model_deprecated`; remove the **exactly 12** `--model`
     option decls across the **12** run verbs; **(Q8) invert-vs-delete** the 5 deprecation-warning test
     files (exact ids in T-57-50) to assert "No such option" — `test_pi_runtime.py`'s `pi --model` is
     the sole surviving `--model` reference.
  - Tests: AC-8 illegal-transition RED-first **at both seams**; AC-9 flag unknown **parametrized × 12**
    with the assertion pinned to `result.stderr` / exit_code 2 / empty stdout (Q4, no `mix_stderr`
    kwarg) + step-model still works + pi/codex `--model` unchanged. **AC-10(c-pipeline)+(c-twin)+(d)**
    sabotage. AC-12 ledger. NO `specs/backlog`.

- **W6 — gates + ship.** Full local gates (AC-11): unpiped `pytest` + `ruff format --check` + `ruff
  check --no-cache` + `mypy --strict` + `lint-imports --no-cache` (8 kept / 0 broken; ignore-cap
  unchanged) + `dadaia specs doctor` + `dadaia backlog doctor`. Because `public/lifecycle_fragments/**`
  changed: **`dadaia public stage && dadaia public install --target all && dadaia public doctor`**
  (`[ok] public-privacy`). Confirm the v0.1.50 frozen no-steal suite is **zero-diff**. **Archive the
  dead-anchor entry `hard-remove-model-flag-across-run-verbs` at SHIP** (its `_warn_model_deprecated`
  anchor is deleted — BL-SCHEMA). QA ship-gate; security push-gate keyed to the pushed sha; push;
  **watch CI until every job green**; PR; merge.

- **W7 — closure (CLOSURE phase).** `ACTIVE.md` phase = `CLOSURE`; CLOSURE.md (Summary, Tasks + SHAs,
  Validations triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive). MEMORY (§SPEC
  8): `lifecycle-foundation.md` (base+mixin+role→atom map+phase+per-input policy+coherence doctor;
  regen catalog/index only if tldr/summary/area change — **(Q9) regenerated `tldr` within the length
  cap**; **(N4) L2 grounding = mechanically checked, L1 grounding = self-pull DISCIPLINE not verified**);
  `architecture.md` (module map);
  `dadaia-workflows.md` (verb-surface `--model` retirement / no-change confirm); `quality-assurance.md`
  (golden-authoring note assess); `context-management.md`/`sdd-gate-v3.md`/`tech-stack.md` no-change
  confirm. **Bug**: append `resolved --release v0.1.57` to the `pipeline-accepted-true-on-illegal-transition`
  JSONL stream. **Backlog return**: file `layer1-selfpull-handoff-audit-line` (via PM curation).
  **Dispositions**: archive `context-injection-role-phase-canon` + `fragment-workflow-base-dedup` →
  `specs/_archive/v0.1.57/consumed-backlog/` + `consumed_backlog.json` (`DELIVERED — v0.1.57`);
  `hard-remove-model-flag-across-run-verbs` already archived at SHIP. `dadaia specs doctor` clean;
  request `git mv specs/releases/v0.1.57 → specs/_archive/releases/` (devops/operator); `ACTIVE.md` →
  next release or `release: none`; candidates R9 row → SHIPPED.

## Write sets (disjoint per wave; shared files force sequential order)

| Wave | Files |
|---|---|
| W1 | NEW `dadaia_workspace/features/lifecycle/workflows/_fragment_gate.py` (base + `_FragmentAssemblyMixin`); `workflows/release_definition.py` + `audit.py` + `research.py` + `bug_report.py` (subclass the base); `workflows/backlog_definition.py` (mix in assembly, converge `_scope`); NEW golden test `tests/unit/features/lifecycle/test_fragment_gate_goldens.py` + goldens under `tests/unit/features/lifecycle/_golden/`; FR1 unit tests |
| W2 | NEW `dadaia_workspace/features/lifecycle/role_atoms.py` (map + single-sourced inject helper, A1); `_fragment_gate.py` + `pipeline.py` (`_scope`/`_fragment_prompt` + **`LifecyclePipeline.__init__` specs_dir/resolver**, A1) + `phase_workflow.py` (consume map + **`LifecyclePhaseWorkflow.__init__` workspace_root/resolver**, A1); `features/lifecycle/context_selector.py` (`SpecContext.phase`); `container.py` (**resolve ACTIVE.md phase at 5 builders + `build_lifecycle_pipeline` + `build_lifecycle_phase_workflow` wire the resolver**, A1); `public/lifecycle_fragments/implementation/qa-review.md` (add `quality_assurance_atom`); FR2 tests (incl. production-builder wiring assertion) |
| W3 | NEW `dadaia_workspace/features/lifecycle/fragment_coherence_doctor.py` (FRAG-COH-1..4, Q6/A2); `features/specs/*` (wire doctor into `specs doctor`); `features/lifecycle/context_selector.py` (`select_all` per-name policy); `features/lifecycle/fragments/loader.py` + `_frontmatter_doc.py` (`input_policies` key); `Fragment` dataclass; FR3 tests (N2: `input_policies` on a test-fixture fragment, NOT a shipped public fragment) |
| W4 | (no code change to ctx_inject) NEW/updated `tests/unit/hooks/test_ctx_inject_digest.py` byte-identical golden + AC-10(f) sabotage; FR4 tests |
| W5 | `dadaia_workspace/features/lifecycle/state_machine.py` (**`TransitionDecision.advanced` property**, A5) + `pipeline.py` (`run` → `decision.advanced`) + `phase_workflow.py` (twin + **stale-comment replace**, A5); `cli/commands/lifecycle.py` (delete `_warn_model_deprecated` + remove the 12 `--model` options); FR5/FR6 tests + invert/delete the 5 deprecation-warning test files (Q8) |
| W6 | (gates + `public stage/install/doctor`; archive dead-anchor entry at SHIP) |
| W7 | `specs/releases/v0.1.57/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.57/consumed-backlog/` + bug JSONL terminal event |

**`pipeline.py` shared W2 (map consume) + W5 (accepted fix)** — sequential; disjoint symbols, one
file. **`phase_workflow.py` shared W2 + W5** — sequential. **`context_selector.py` shared W2
(SpecContext.phase) + W3 (select_all per-name policy)** — sequential. **`cli/commands/lifecycle.py`
W5 only.** **No parallel `[-]`.**

## Test strategy

- **Golden-first (FR1, the spine).** Capture + commit goldens of each body's built prompts + produced
  payloads under `--harness fake` BEFORE extraction; prove byte-identity after (fix-the-split-never-
  the-golden). Platform-invariant normalization (v0.1.55) on every path-bearing golden. The
  custom-`_SEQUENCE` iteration test proves the base is sequence-scoped, not module-global.
- **Behaviour-change is a test, not a golden diff.** The backlog `_scope` model-threading convergence
  (Problem #8) is asserted RED-first (`req.resolved_model is not None`), never absorbed into a golden.
- **Role→atom map (AC-3) — RED-first in the selector-less pipeline + PRODUCTION wiring (A1).** The
  pipeline `review_qa` step lacks `quality_assurance_atom` today (no selector wired); post-map the atom
  ref appears in `InjectedContext.refs` and its content in the prompt. Pre-fix assertion FAILS. A
  separate assertion proves `build_lifecycle_pipeline` + `build_lifecycle_phase_workflow` wire the
  resolver (not only fixtures), so the map is not inert in production.
- **Coherence doctor (AC-5) — scoped (A2).** Green on the current tree after FR2/FR3 (the ~10 inert
  shared/implementation unregistered inputs are WARN/skip, not ERROR); RED-first: an unregistered
  `dynamic_inputs` on the selector-wired **`release_definition.spec_create`** fires **FRAG-COH-2**
  (ERROR) and flips `ok`. `persona_doctor` stays green, untouched.
- **Per-input policy (AC-6).** A **test-fixture** fragment with `input_policies` resolves mixed
  policies in one `select_all`; a fragment with none is byte-stable.
- **ctx_inject (AC-7).** Byte-identical `_build_memory` output for a fixture specs tree; existing
  ctx_inject tests green — the FR4 ratification changes no L1 behaviour. AC-10(f) sabotage.
- **Bug fix (AC-8) — both seams, RED-first.** A synthetic illegal-transition ladder makes the step
  `accepted=False` with `run.blocked is None`; pre-fix `accepted=True`. Same for phase_workflow. Both
  seams read `decision.advanced` (A5).
- **`--model` removal (AC-9) — channel-pinned, parametrized × 12 (Q4/Q7).** Parametrized across all 12
  run verbs: `--model X` → `exit_code == 2`, `"No such option: --model"` in **`result.stderr`**,
  `result.stdout` empty; **no `mix_stderr` kwarg** (removed in Click 8.2, TypeErrors on 8.4.1).
  `--step-model <profile-id>` resolves; raw `--step-model label=<id>:<effort>` still rejected; pi/codex
  subprocess `--model` unchanged, `test_pi_runtime.py` the sole surviving reference (Q8).
- **AC-10 mutation-sanity per new test** (a, b, c-pipeline, c-twin, d, e, f): one-line sabotage ⇒ FAIL,
  captured on the task line, reverted.
- **AC-12 surviving/dead ledger per wave**; greps include `tests/` + textual/docstring refs.
- **Frozen suite:** the v0.1.50 no-steal lease/gate suite is untouched (this release never enters
  `spec_context`/lease/gate) — confirm zero-diff. ctx_inject is in scope but not in that suite.
- Full **unpiped** `pytest` + ruff + `mypy --strict` + `lint-imports --no-cache` + `specs doctor` +
  `backlog doctor` + `public doctor` locally before push (AC-11).

## Rollback

Single feature branch `feature/v0.1.57` (base v0.1.56 closure). Each wave is one or a small set of
commits. FR1 is behind committed goldens (revert = restore the five bodies). FR2/FR3 add a map + a
doctor + a fragment frontmatter line + a selector option (additive). FR4 changes no runtime code
(ratification). FR5 is two one-line fixes. FR6 removes a deprecated flag (revert = restore
`_warn_model_deprecated`). No data migration. The dead-anchor archival at SHIP is one commit,
recoverable by revert; the CLOSURE dispositions are recoverable by reverting that closure commit. The
only irreversible-ish step is `public install` (re-run `stage`/`install`/`doctor` to reconcile).
