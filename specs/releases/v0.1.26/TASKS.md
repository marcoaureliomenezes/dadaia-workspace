# TASKS — Release: v0.1.26 — `backlog_definition` workflow body + removal-on-release (R2)

**Status:** Aprovado
**Release ID:** v0.1.26
**Owner:** product-engineer
**Opened:** 2026-06-26
**Implements:** `specs/releases/v0.1.26/SPEC.md` + `PLAN.md`

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. One `[-]` per owner at a time. Owner
is `software-engineer` unless noted. Every task's **Done-when** includes: `mypy --strict`
exit 0 on `dadaia_workspace/`, `ruff format --check` + `ruff check` clean, the task's tests
green, and **no in-repo `.dadaia/`/cache pollution** left in the working tree.

Tasks follow the PLAN §3 execution order: selector + fragments + pure removal logic land
before the workflow body; CLI wiring + §6 lifecycle wiring follow; propagation + live-tree
verification last. **Build on R1; never re-do R1 (SPEC §3.8).**

---

## [x] T-26-01 — `backlog_index` context selector

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/context_selector.py`,
  `tests/unit/test_context_selector_backlog_index.py`
- **Preconditions:** none (consumes R1 `intents[]` frontmatter).
- **Description:** Add `sel_backlog_index(self, name, policy) -> SelectionResult` and
  register `"backlog_index"` in `_SELECTORS`. For every existing `specs/backlog/*.md`
  (reuse `_dir_files("backlog")`, exclude `ideas.md`/`candidates.md`/catalog) return a
  compact record per item: its **bound intents** (subject anchors + change) + **status**,
  parsed from the R1 `intents[]` frontmatter only (never the body). Injected `SpecContext`
  paths, never cwd (SPEC §3.8). Maps SPEC §3.5.
- **Done-when:** unit test over a fixed `tmp_path` backlog fixture asserts bound intents +
  status per item and the exclusions (acceptance §3.7.7); mypy/ruff clean.

## [x] T-26-02 — Real `backlog_definition` step fragments

- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/public/lifecycle_fragments/backlog_definition/intake_grill.md`,
  `dadaia_workspace/public/lifecycle_fragments/backlog_definition/conflict_scan.md`,
  `dadaia_workspace/public/lifecycle_fragments/backlog_definition/conflict_resolution_grill.md`,
  `dadaia_workspace/public/lifecycle_fragments/backlog_definition/backlog_authoring.md`,
  (delete `dadaia_workspace/public/lifecycle_fragments/backlog_definition/_README.md`),
  `tests/unit/test_backlog_definition_fragments.py`
- **Preconditions:** none (authored before the workflow references the ids — the loader
  fails on a fragment id with no source).
- **Description:** Author the four model-step fragments with the fixed frontmatter (`id:
  backlog_definition.<step>`, `role`, `workflow: backlog_definition`, `step`,
  `static_inputs`, `dynamic_inputs` incl. `backlog_index`/`product_catalog_summary`,
  `output_schema` per §4 (`backlog-demand-v1`, `overlap-report-v1`,
  `conflict-resolution-v1`, `backlog-item-v1`), `max_context_policy`) + markdown body,
  modelled on `release_definition/*.md`. Pure Python steps carry no fragment. Maps SPEC
  §3.4. `intake_grill`/`conflict_resolution_grill` cite `shared.grill_questionnaire`.
- **Done-when:** a fragment-loader test loads each id and validates frontmatter +
  declared output schema; `_README.md` removed; mypy/ruff clean. (Propagation is T-26-08.)

## [ ] T-26-03 — `consumed_backlog` ledger writer (R1 reader shape)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/ledger_writer.py`,
  `tests/unit/test_backlog_ledger_writer.py`
- **Preconditions:** none (consumes R1 `ledger.py` shape + `LEDGER_FILENAME`).
- **Description:** `write_consumed(*, archive_root, release_id, consumed)` emits
  `specs/_archive/<release-id>/consumed_backlog.json` in the exact R1 reader shape
  (`{"release": <id>, "consumed": [{"slug", "shipped_anchors": [...]}, ...]}`), keyed on
  the **verified shipped subject-anchor set** (not the slug string). Reuse `LEDGER_FILENAME`
  from `ledger.py`; injected `archive_root` (SPEC §3.8); module-relative anchors only.
  Maps SPEC §3.6 (writer).
- **Done-when:** round-trip unit test `write_consumed` → R1 `read_consumed` → expected map
  (acceptance §3.7.8); mypy/ruff clean.

## [ ] T-26-04 — Residual-aware closure removal hook (copy-before-remove)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/removal.py`,
  `tests/unit/test_backlog_removal.py`
- **Preconditions:** none (pure; consumes the shipped-anchor set).
- **Description:** `apply_removal(*, backlog_dir, archive_root, release_id,
  shipped_anchors) -> RemovalResult`. Per consumed item compute residual = intents whose
  anchors are NOT shipped. **residual > 0 → rewrite-down-to-residual and KEEP** (strip
  only shipped intents). **residual == 0 → copy to
  `specs/_archive/<release-id>/consumed-backlog/<slug>.md` THEN `unlink`** — the archive
  copy MUST exist before removal (ADR-C, SPEC §3.8 safety). Injected paths, never cwd.
  Maps SPEC §3.6 (removal hook).
- **Done-when:** unit tests cover both branches; the residual==0 test asserts the archive
  copy exists at the moment of removal (acceptance §3.7.9); mypy/ruff clean.

## [ ] T-26-05 — `BacklogDefinitionWorkflow` body (§4 sequence, Python gates)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`,
  `dadaia_workspace/features/lifecycle/workflows/_deferred.py` (remove the
  `backlog_definition` entry from `DEFERRED_WORKFLOWS` + the stub callable),
  `dadaia_workspace/features/lifecycle/workflows/__init__.py` (re-export the new types),
  `tests/integration/test_backlog_definition_workflow.py`
- **Preconditions:** T-26-01 (selector), T-26-02 (fragments).
- **Description:** The §4 `_SEQUENCE` of frozen `BacklogStep` dataclasses + the
  `BacklogDefinitionWorkflow` class, mirroring `release_definition.py` field-for-field
  (fold `static_inputs` → cacheable `PromptPrefix`; per-fragment dynamic context;
  `build_fragment_suffix`; injected `RuntimeFactory`; Python gate via
  `LifecycleAgentRunner.evaluate_gate`; advance only on success). Python steps
  (`fragment_id=None`): **1b** `subject_bind` calls R1 registry (HALT on
  UNRESOLVED/AMBIGUOUS); **2** `existing_backlog_review` runs R1 `classify` (model OFFLINE
  by default; downgrade seam for same-anchor differing-change only, fail-closed — T-26-06);
  **3** `reconcile_decision` blocks NEW unless every class is `UNRELATED`; **4**
  `conflict_resolution_grill` skipped unless step 2 reports a `DIVERGENT_CONFLICT`; **6**
  `backlog_review_gate` re-runs `classify` over the authored result (block on
  `DUPLICATE`/`DIVERGENT_CONFLICT`). Maps SPEC §3.1.
- **Done-when:** end-to-end `fake`-harness test runs steps 1→6 in order, stops at the
  first blocked gate (acceptance §3.7.1); `subject_bind` HALT (§3.7.2); offline
  `DIVERGENT_CONFLICT` routes to grill (§3.7.3); `reconcile_decision` both directions
  (§3.7.4); `backlog_review_gate` blocks a dirty result (§3.7.5). Gate behaviours are
  **one parameterized** step-matrix test (§3.7.11). mypy/ruff clean.

## [ ] T-26-06 — Feed the R1 classifier into `existing_backlog_review` (model downgrade seam)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`
  (the step-2 disposition + downgrade wiring),
  `tests/unit/test_backlog_review_step.py`
- **Preconditions:** T-26-05.
- **Description:** Wire step 2 to call R1 `classify(new, existing, *, downgrade)` over the
  bound intents (step 1b) + `backlog_index` (T-26-01). Python disposes every
  deterministic verdict; the model is invoked **only** through the `downgrade` seam for a
  same-anchor differing-change pair, **fail-closed** → `DIVERGENT_CONFLICT` absent an
  explicit structured proven-compatible merge. Produce the `overlap-report-v1` total +
  every existing item classified. Maps SPEC §3.3, ADR-B.
- **Done-when:** unit test proves the offline path defaults to `DIVERGENT_CONFLICT`
  (§3.7.3) and a stubbed compatible-merge downgrade yields `OVERLAP`/`SUPERSEDES`;
  mypy/ruff clean.

## [ ] T-26-07 — CLI wiring + container factory

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py` (re-point `backlog_define`
  `:327` at the workflow + per-step `--step-harness`/`--step-model`),
  `dadaia_workspace/container.py` (`build_backlog_definition_workflow` factory),
  `tests/integration/test_cli_backlog_define.py`
- **Preconditions:** T-26-05.
- **Description:** Re-point `backlog_define` from `_run_phase_step` to
  `BacklogDefinitionWorkflow` via a `build_backlog_definition_workflow` container factory
  (mirror `release_define` `:357` + the release container wiring). Keep `--context`,
  `--release-id`, `--run-id`, `--harness` (LAW 1: `_resolve_harness` rejects `claude`),
  `--model` (LAW 2: `_resolve_model`), `--json`, and per-step overrides keyed by the §4
  labels. Maps SPEC §3.2.
- **Done-when:** integration test — `--harness fake` drives the real workflow (not
  `_deferred`); `--harness claude` rejected; bad `--model` rejected (acceptance §3.7.6);
  mypy/ruff clean.

## [ ] T-26-08 — Wire removal-on-release into the lifecycle + BL-STALE loop

- **Owner:** software-engineer
- **Write set:** the release-definition/closure lifecycle surface that invokes the writer
  (T-26-03) + removal hook (T-26-04) (e.g.
  `dadaia_workspace/features/lifecycle/workflows/release_definition.py` and/or the closure
  surface + container wiring), `tests/integration/test_backlog_removal_loop.py`,
  `tests/e2e/features/test_backlog_define_e2e.py`
- **Preconditions:** T-26-03, T-26-04, T-26-05.
- **Description:** Invoke `write_consumed` (keyed on the verified shipped anchor set) at
  release-definition and `apply_removal` at closure. Prove the BL-STALE loop closes:
  after writer + removal, R1 `backlog doctor` reports zero BL-STALE; an artificially
  retained consumed slug → BL-STALE ERROR (acceptance §3.7.10). Add the `fake`-harness e2e
  for `dadaia lifecycle backlog define`. Maps SPEC §3.6 + §3.7.10.
- **Done-when:** BL-STALE loop integration test green (both directions); e2e green;
  mypy/ruff clean.

## [ ] T-26-09 — Stage + install + doctor the new fragments (public propagation)

- **Owner:** software-engineer
- **Write set:** none (runs `dadaia public stage && dadaia public install --target all &&
  dadaia public doctor`; may touch `.dadaia/agentic/manifest.json` via the tooling).
- **Preconditions:** T-26-02 (fragments authored).
- **Description:** Propagate the new `backlog_definition/*.md` fragments + the `_README.md`
  removal from `public/` source to all projections so the instance reflects the source
  (SPEC §3.8 public-asset propagation; source-vs-instance rule). product-engineer surfaces
  the commands; software-engineer (with Bash) runs them.
- **Done-when:** `dadaia public doctor` exit 0 with `[ok] public-privacy`; the new
  fragments present in projections; no stray root artefacts.

## [ ] T-26-10 — Final live-tree verification

- **Owner:** software-engineer
- **Write set:** none (verification only; touch a test fixture only if a gap is found,
  else raise to operator).
- **Preconditions:** T-26-01..T-26-09 all `[x]`.
- **Description:** Run the **full** `pytest` suite, `dadaia backlog doctor`, `dadaia
  specs doctor`, and `dadaia public doctor` on the live tree; confirm all exit 0/green and
  no in-repo cache/`.dadaia` pollution remains.
- **Done-when:** full `pytest` green; `dadaia backlog doctor` exit 0; `dadaia specs
  doctor` green; `dadaia public doctor` exit 0; mypy/ruff clean; working tree clean of
  pollution.
