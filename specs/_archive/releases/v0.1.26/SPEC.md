# SPEC — Release: v0.1.26 — `backlog_definition` workflow body + removal-on-release (R2 of FEAT-BACKLOG-DEFINITION-WORKFLOW-01)

**Status:** Aprovado
**Release ID:** v0.1.26
**Owner:** product-engineer
**Opened:** 2026-06-26
**Branch:** `feature/v0.1.26`
**Consumes (R2 slice):** `specs/backlog/backlog-definition-workflow-dedup-conflict-control.md`
(FEAT-BACKLOG-DEFINITION-WORKFLOW-01) — this release is **§11 R2** of that epic. R1
(v0.1.25, shipped + archived) delivered the foundation: the `intents[]` item schema, the
auto-derived canonical-subject **registry**, the deterministic Python-disposes
**classifier**, the `dadaia backlog doctor` BL-* checks wired into pre-commit/CI, and the
backfill of the surviving items. R2 layers the human-facing workflow + the
removal-on-release lifecycle on top of that already-consistent foundation.

---

## 1. Problem and context

R1 made the backlog **mechanically consistent**: the registry binds subjects to canonical
anchors, the classifier disposes UNRELATED/DUPLICATE/DIVERGENT_CONFLICT by Python
set-intersection (model offline), and `backlog doctor` rejects a hand-written divergent
twin at the pre-commit chokepoint. But R1 deliberately shipped **only the enforced
backstop** (epic §11, ADR-D). Two things are still missing:

1. **No ORIENTED happy-path.** There is no workflow that *walks* an operator demand
   through subject-binding, existing-backlog review, reconciliation, and authoring — so
   the only way a consistent item gets written today is by hand, validated after the fact
   by the doctor. The epic §4 `backlog_definition` workflow is the oriented path that
   produces a consistent item by construction (and feeds the R1 classifier as its
   review step), rather than relying solely on the doctor to catch a mistake at commit.
   The `dadaia lifecycle backlog define` CLI verb exists but routes to the `_deferred`
   fail-loud stub.

2. **No removal-on-release.** A shipped backlog item still lingers in the live SET of
   `specs/backlog/` (epic §1 staleness; the 2026-06-26 cleanup hand-deleted 22 such
   files). R1 defined the `consumed_backlog` ledger **format** and made `backlog doctor`
   **read** it for BL-STALE, but **nothing writes the ledger** and nothing removes a
   consumed item at closure. Until R2 supplies the writer + the residual-aware removal
   hook, BL-STALE is an inert check over an empty ledger.

### Verified current-state facts (source-inspected; engineers rely on these)

- **`features/lifecycle/workflows/_deferred.py`** still carries the fail-loud
  `backlog_definition(*_args, **_kwargs)` stub (raises `NotImplementedError`). It is
  re-exported by `workflows/__init__.py`. R2 replaces this entry with a real body in a
  new `workflows/backlog_definition.py`, mirroring `release_definition.py`.
- **`release_definition.py`** is the exact structural model: a `_SEQUENCE` tuple of
  frozen `ReleaseStep` dataclasses (label + role + `fragment_id` + `shared_fragment_ids`
  + `is_review` + `runtime_kind`), a workflow class whose `run()` folds each fragment's
  `static_inputs` into a cacheable `PromptPrefix`, selects dynamic context per fragment
  via `ContextSelector`, builds a suffix via `build_fragment_suffix`, runs the worker on
  an injected `RuntimeFactory(kind)`, reads a Python-owned typed gate
  (`LifecycleAgentRunner.evaluate_gate`), and advances only on success; a terminal
  Python step (`fragment_id=None`) commits with no model.
- **`cli/commands/lifecycle.py:327` `backlog_define`** already wires `--harness`/`--model`
  (LAW 1 pi/codex/fake; LAW 2 discrete model) and currently calls the generic
  `_run_phase_step` helper (a single `"Run the {label} step"` prompt). R2 re-points it at
  the fragment-driven `BacklogDefinitionWorkflow`, mirroring how `release_define`
  (`:357`) drives `ReleaseDefinitionWorkflow` with per-step harness/model overrides.
- **`features/backlog/classifier.py`** (R1) exposes `classify(new, existing, *,
  downgrade=no_downgrade) -> list[Classification]` over pre-bound `BoundItem`s. R2 feeds
  this into the `existing_backlog_review` step; the model is invoked **only** for the
  same-anchor differing-change downgrade adjudication (fail-closed →
  `DIVERGENT_CONFLICT`).
- **`features/backlog/subject_registry.py`** (R1) binds a proposed subject to a canonical
  anchor (or HALTs on UNRESOLVED/AMBIGUOUS). R2's `subject_bind` step calls it; no new
  binding logic is authored.
- **`features/backlog/ledger.py`** (R1) `read_consumed(archive_root) -> {slug:
  shipped_anchors}` reads `specs/_archive/*/consumed_backlog.json`
  (`LEDGER_FILENAME = "consumed_backlog.json"`). R2 adds the **writer** of that exact
  sidecar shape and the closure removal hook keyed on it.
- **`features/lifecycle/context_selector.py`** has a `_SELECTORS` registry mapping each
  dynamic-input name to a bound method. R2 adds a `backlog_index` selector (every
  existing item's bound intents + status), registered in `_SELECTORS`.
- **`public/lifecycle_fragments/backlog_definition/`** holds only `_README.md` (the
  scaffolded stub). R2 ships real step fragments here. Fragment file format is fixed by
  `release_definition/*.md` (YAML frontmatter: `id`, `role`, `workflow`, `step`,
  `static_inputs`, `dynamic_inputs`, `output_schema`, `max_context_policy`; markdown body).
- **`shared/grill-questionnaire.md`** already exists and is cited by `release_scope`. R2's
  grill steps reuse it; R2 ships only `backlog_definition`-specific fragments
  (`conflict-scan`, `backlog-authoring`, and the per-step fragments §4 names).

---

## 2. Objective

Ship the **ORIENTED `backlog_definition` workflow** (epic §4) as a Python-owned
fragment-driven sequence behind `dadaia lifecycle backlog define`, feeding the R1
deterministic classifier into its review step (Python disposes; model only adjudicates
same-anchor differing-change merges, fail-closed); **plus the removal-on-release
lifecycle** (epic §6) — the `consumed_backlog` ledger **writer** keyed on the verified
shipped subject-anchor set, and the residual-aware closure removal hook
(rewrite-down-to-residual by default; full removal with a durable archive copy only when
zero residual intents remain). R2 builds **on** R1's registry/classifier/doctor/ledger
reader; it does not duplicate or re-do any R1 deliverable, and it does not re-run the
already-completed backfill.

---

## 3. Scope (R2 — the workflow + removal lifecycle)

Six clusters (3.1–3.6). Implementer = `software-engineer` unless noted. Each carries
verifiable acceptance (consolidated in §3.7); binding constraints are §3.8.

### 3.1 — The `backlog_definition` workflow body (epic §4)

`features/lifecycle/workflows/backlog_definition.py` (new) — the §4 seven-step sequence,
modelled structurally on `release_definition.py`: a `_SEQUENCE` tuple of frozen step
dataclasses (label + role + `fragment_id` + `shared_fragment_ids` + `is_review` +
`runtime_kind`), a `BacklogDefinitionWorkflow` whose `run()` folds `static_inputs` into a
cacheable `PromptPrefix`, selects dynamic context per fragment, builds the suffix, runs
the worker on the injected `RuntimeFactory(kind)`, reads the Python-owned typed gate, and
advances only on success. Python steps (`fragment_id=None`) run no model.

| # | step | role / runtime | fragment + injected context | output schema | Python gate |
|---|------|----------------|-----------------------------|---------------|-------------|
| 1 | `intake_grill` | project-manager (MANDATORY grill) | `backlog_definition.intake_grill` + `shared.grill_questionnaire`; ctx: demand + `product_catalog_summary` + `backlog_index` | `backlog-demand-v1` (proposed intents) | grill reaches shared understanding (worker handoff present) |
| 1b | `subject_bind` | **Python** (no model) | the R1 canonical-subject registry | `bound-intents-v1` | **HALT** on any UNRESOLVED/AMBIGUOUS subject (no silent NEW) |
| 2 | `existing_backlog_review` | **Python** + model only for shared-anchor adjudication (§3.3) | `backlog_definition.conflict_scan`; ctx: bound intents + `backlog_index` (every existing item's bound intents) | `overlap-report-v1` | report total + every existing item classified |
| 3 | `reconcile_decision` | **Python** (+ product-engineer if ambiguous) | the overlap report | `reconcile-plan-v1` (NEW \| UPDATE(t) \| MERGE(t..) \| SUPERSEDE(t)) | **blocks NEW if any non-`UNRELATED` class** |
| 4 | `conflict_resolution_grill` | project-manager (MANDATORY iff any `DIVERGENT_CONFLICT`) | `backlog_definition.conflict_resolution_grill` + `shared.grill_questionnaire`; ctx: each conflict rendered "you previously asked X@anchor; now Y@anchor" | `conflict-resolution-v1` | no unresolved divergence may pass |
| 5 | `backlog_author` | product-engineer | `backlog_definition.backlog_authoring`; ctx: reconcile plan + resolution | `backlog-item-v1` (bound intents, status, scope) | NEW file XOR edit EXISTING — never both, never a twin |
| 6 | `backlog_review_gate` | **Python** (no model) | the result + rest of backlog | `backlog-verdict-v1` | re-run R1 classifier on the RESULT: zero `DUPLICATE`/`DIVERGENT_CONFLICT`; valid metadata |

**Python owns order and gates** exactly as `release_definition` does. Steps 1b, 2, 3, and
6 are **Python-disposing** steps: step 1b binds via the R1 registry; step 2 runs the R1
classifier; step 3 enforces the NEW-only-if-all-UNRELATED gate; step 6 re-runs the
classifier over the authored result as the closing self-check (mirroring `backlog
doctor`'s checks, in-workflow). A blocked step stops the sequence with a `BlockedState`;
advancement is never on model say-so.

`conflict_resolution_grill` (step 4) is **conditional**: it runs only when step 2's
overlap report contains at least one `DIVERGENT_CONFLICT`. When the report is clean the
step is skipped (recorded as skipped, not blocked) and the sequence proceeds to authoring.

### 3.2 — CLI wiring: `dadaia lifecycle backlog define` → the real workflow

`cli/commands/lifecycle.py` `backlog_define` (`:327`) is re-pointed from the generic
`_run_phase_step` stub to `BacklogDefinitionWorkflow`, mirroring `release_define`
(`:357`). It keeps `--context`, `--release-id`, `--run-id`, `--harness` (LAW 1:
pi/codex/fake; `claude` rejected via `_resolve_harness`), `--model` (LAW 2 discrete model
via `_resolve_model`), and `--json`. Per-step `--step-harness`/`--step-model` overrides
(keyed by the §4 step labels) follow the `release_define` pattern. The workflow is
assembled via the container (a `build_backlog_definition_workflow` factory, mirroring the
release-definition container wiring) so it is harness-agnostic. The `_deferred.py`
`backlog_definition` stub is replaced (see 3.3); `workflows/__init__.py` re-exports the
new `BacklogDefinitionWorkflow`/result types instead of the deferred callable.

### 3.3 — Feed the R1 classifier into `existing_backlog_review` (epic §3, §4 step 2)

The `existing_backlog_review` step consumes `features/backlog/classifier.py`'s
`classify(new, existing, *, downgrade)` over the **bound** intents (step 1b output) and
every existing item's bound intents (the `backlog_index` selector, §3.5). **Python
disposes** every verdict it can decide deterministically (empty intersection →
`UNRELATED`; same-anchor + same-change → `DUPLICATE`; same-anchor + differing-change →
`DIVERGENT_CONFLICT` by default). The **model is invoked only** through the classifier's
`downgrade` seam — and only for a same-anchor differing-change pair — to *adjudicate* a
compatible merge. **Fail-closed:** absent an explicit, structured proven-compatible merge
verdict, the class stays `DIVERGENT_CONFLICT`. The model can only downgrade with evidence;
it can never miss a conflict. This is the live exercise of the seam R1 shipped offline.

### 3.4 — Real fragments (epic §5)

`public/lifecycle_fragments/backlog_definition/` (replace `_README.md` with real step
fragments). At minimum the model-step fragments the §4 sequence names:
`intake_grill.md`, `conflict_scan.md` (the `existing_backlog_review` reasoning frame for
the model's shared-anchor adjudication only), `conflict_resolution_grill.md`, and
`backlog_authoring.md`. Each carries the fixed frontmatter (`id`, `role`, `workflow:
backlog_definition`, `step`, `static_inputs`, `dynamic_inputs`, `output_schema`,
`max_context_policy`) and a markdown body, modelled on `release_definition/*.md`. Pure
Python steps (`subject_bind`, `reconcile_decision`, `backlog_review_gate`) carry **no**
fragment (`fragment_id=None`). Because fragments are `public/` assets, the change is
staged + installed (a dedicated TASK, §3.8).

### 3.5 — `backlog_index` context selector (epic §8)

`features/lifecycle/context_selector.py` gains a `sel_backlog_index` method registered in
`_SELECTORS` under the name `backlog_index`. It returns, for **every** existing
`specs/backlog/*.md` item (excluding `ideas.md`/`candidates.md`/the catalog), a compact
record: the item's **bound intents** (subject anchors + change) and its **status** —
the index the `intake_grill` and `existing_backlog_review` steps reason over. It reuses
the existing `_dir_files("backlog")` discovery + the R1 `intents[]` frontmatter parse;
it must not read item bodies beyond frontmatter (bounded by policy). Paths are resolved
under the injected `SpecContext`, never cwd.

### 3.6 — Removal-on-release: ledger writer + residual-aware closure hook (epic §6)

The lifecycle that takes a backlog item out of the live SET once its content ships:

- **Ledger writer.** The **release-definition** path writes the `consumed_backlog` ledger
  to `specs/_archive/<release-id>/consumed_backlog.json` (the exact R1 reader shape:
  `{"release": <id>, "consumed": [{"slug", "shipped_anchors": [...]}, ...]}`), keyed on
  the **verified subject-anchor set actually shipped** in the release SPEC — the bound
  anchors of the items the release consumed, **not** the slug string alone. The writer is
  a pure `features/backlog/` function (injected archive root); it is invoked by the
  release-definition/closure surface.
- **Residual-aware closure removal hook.** At closure, for each item the release
  consumed, compute the **residual** = the item's intents whose anchors are **not** in the
  shipped set:
  - **Rewrite-down-to-residual is the DEFAULT.** When residual intents remain, the item
    is rewritten to its residual (strip the shipped intents only) and **kept** in
    `specs/backlog/` — never deleted whole. This is the 2026-06-26 hand pattern, mechanised.
  - **Full removal only when zero residual intents remain.** Before `rm`, the hook
    **copies the file to `specs/_archive/<release-id>/consumed-backlog/<slug>.md`** — a
    durable trace — then drops it from the live SET (so it can never re-enter a future
    release). Because `specs/backlog/` is gitignored in this source repo, the archive copy
    is the **only** surviving copy of a CRITICAL safety record; the copy is non-negotiable
    and happens **before** removal.
- The hook is a pure `features/backlog/` function (injected backlog dir + archive dir +
  the shipped-anchor set), so it is unit-testable with no real filesystem outside
  `tmp_path`. BL-STALE (R1) then mechanically rejects any consumed slug that survives in
  `specs/backlog/` against the ledger this writer produced — closing the loop R1 left open.

### 3.7 — Consolidated R2 acceptance criteria (maps from epic §9, R2 subset)

1. **Workflow runs the §4 sequence with Python-owned gates.** `BacklogDefinitionWorkflow`
   executes steps 1→6 in order, stops at the first blocked gate, and advances only on
   success — mirrored on `ReleaseDefinitionWorkflow`'s gate semantics — tested
   end-to-end on the `fake` harness.
2. **Unresolved subject HALTs at `subject_bind`.** A proposed demand whose subject
   resolves to no registry anchor (or ambiguous) blocks step 1b (no silent NEW), with an
   actionable message naming the ref — tested.
3. **Classifier feeds `existing_backlog_review`; divergence is caught by Python.** A
   `C→D`-then-`C→E` demand against an existing `C→D` item is classified
   `DIVERGENT_CONFLICT` by the R1 classifier **with the model OFFLINE**, surfaces in the
   `overlap-report-v1`, blocks NEW at step 3, and routes to `conflict_resolution_grill` —
   tested with a FAKE fixture.
4. **`reconcile_decision` blocks NEW unless all-`UNRELATED`.** A demand with any
   non-`UNRELATED` class cannot produce a NEW file; a demand where every existing item is
   `UNRELATED` is permitted NEW — tested both directions.
5. **`backlog_review_gate` re-validates the authored result.** Step 6 re-runs the R1
   classifier over the authored item against the rest of the backlog and **blocks** on any
   `DUPLICATE`/`DIVERGENT_CONFLICT` in the result — tested.
6. **CLI wires the real workflow.** `dadaia lifecycle backlog define --harness fake`
   drives `BacklogDefinitionWorkflow` (not the `_deferred` stub); `--harness claude` is
   rejected (LAW 1); a bad `--model` is rejected (LAW 2) — tested.
7. **`backlog_index` selector returns bound intents + status per item.** Over a fixture
   backlog tree, `backlog_index` yields each surviving item's bound intents + status and
   excludes `ideas.md`/`candidates.md`/catalog — tested.
8. **Ledger writer produces the R1 reader shape, keyed on shipped anchors.** The writer
   emits `specs/_archive/<release-id>/consumed_backlog.json` whose entries
   `{slug, shipped_anchors[]}` are the **verified shipped anchor set**, and `read_consumed`
   (R1) reads it back round-trip — tested.
9. **Residual-aware removal at closure.** A consumed item with surviving intents is
   **rewritten to its residual** and kept; an item with zero residual is **copied to
   `specs/_archive/<release-id>/consumed-backlog/<slug>.md` then removed** from
   `specs/backlog/`; the archive copy exists before the removal — tested with both cases.
10. **BL-STALE closes the loop.** After the writer + removal hook run, `backlog doctor`
    (R1) reports zero BL-STALE on the post-removal tree, and reports BL-STALE if a
    consumed slug is artificially left behind — tested.
11. **Test pyramid + no copy-paste fan-out.** The suite follows the ~70/20/10 pyramid;
    the workflow gate behaviours are exercised by a parameterized step-matrix test (one
    fixture matrix), not copy-pasted per step.

### 3.8 — Constraints (binding)

- **Build on R1 — never duplicate.** `subject_bind` calls the R1 registry;
  `existing_backlog_review` and `backlog_review_gate` call the R1 `classify`; the ledger
  writer emits the exact R1 `ledger.py` reader shape (`LEDGER_FILENAME`). No second
  registry, classifier, or ledger schema is authored.
- **Injected paths, never cwd lookups.** Every pure function (the ledger writer, the
  removal hook, the `backlog_index` selector resolution) takes its roots (backlog dir,
  archive dir, specs dir) as **explicit injected arguments**, never `os.getcwd()` —
  mirroring R1's injected-path constraint and the conftest repo-root write guard.
- **Module-relative anchors only — no operator-local paths (privacy).** The ledger's
  `shipped_anchors[]` and any anchor the workflow writes are always module-relative
  `path#symbol` (or a non-path anchor id); never an operator-local absolute path or a
  private repo name.
- **Archive copy before removal (safety).** The full-removal branch must copy the file to
  `specs/_archive/<release-id>/consumed-backlog/<slug>.md` **before** any `unlink`. The
  unit test asserts the copy exists at the moment of removal — never delete the only copy
  of a CRITICAL safety record.
- **Public-asset propagation.** Editing `public/lifecycle_fragments/backlog_definition/`
  requires `dadaia public stage && dadaia public install --target all && dadaia public
  doctor` (exit 0, `[ok] public-privacy`) so the instance reflects the source — a
  dedicated TASK. Engineers run these via Bash; product-engineer surfaces them.
- **LAW 1 / LAW 2.** Workflow model steps run on a selectable Layer-2 harness
  (`fake|codex|pi`); `claude` is Layer-1 only and is rejected at the CLI; `--model`
  selects a discrete Layer-2 model — exactly as `release_define` declares it.

---

## 4. Out of scope (R1-done or later — explicit)

- **All R1 deliverables** — the `intents[]` schema, the canonical-subject **registry**,
  the deterministic **classifier**, `backlog doctor` (BL-SCHEMA/DUP/CONFLICT/STALE) and
  its pre-commit/CI wiring, and the **backfill** of the surviving items. Shipped + archived
  in v0.1.25. R2 consumes them; it does not modify or re-do them. (BL-* doctor's
  pre-commit rejection is the R1 acceptance, not R2's.)
- **`workflow-model-governance-panel-control-plane`** — the per-workflow model/harness
  governance + panel control plane. The **NEXT** release, explicitly not in R2 (epic §11;
  operator-confirmed 2026-06-26). R2 adds no panel surface for the backlog workflow.
- **Auto-derivation of `panel`/`api` subject kinds.** Deferred from R1 (no route registry
  exists); still alias-only. R2 introduces no route registry.
- **A new backlog doctor check or any change to BL-* semantics.** R2 wires the ledger
  *writer* + removal hook; BL-STALE's read logic is unchanged from R1.
- **Re-running the migration/backfill.** Done in R1; out of scope.

---

## 5. Architecture decision records (ADRs — fixed for this release)

### ADR-A — `BacklogDefinitionWorkflow` mirrors `ReleaseDefinitionWorkflow` structurally

The §4 body is a `_SEQUENCE` of frozen step dataclasses + a workflow class whose `run()`
folds `static_inputs` into a cacheable `PromptPrefix`, selects dynamic context per
fragment, builds a suffix via `build_fragment_suffix`, runs the worker on the injected
`RuntimeFactory`, reads the Python-owned typed gate, and advances only on success —
byte-for-byte the `release_definition.py` pattern. *Rationale:* the two-layer redesign
fixed this as the canonical workflow-body shape; a divergent structure would be slop and
would not reuse the audited prompt-composition/gate seams. Pure Python steps carry
`fragment_id=None` and run no model, exactly like the terminal release commit gate.

### ADR-B — Python disposes; model only adjudicates same-anchor merges (fail-closed)

`existing_backlog_review` uses the R1 `classify` over bound anchors. Python decides every
deterministic verdict; the model is invoked **only** via the classifier's `downgrade`
seam for a same-anchor differing-change pair, and **only to downgrade with evidence**.
Absent a structured proven-compatible merge, the class stays `DIVERGENT_CONFLICT`.
*Rationale:* the dangerous twin must be caught by Python arithmetic, not model attention
(epic §3, §5); R2 exercises live the seam R1 shipped offline — without weakening the
fail-closed default.

### ADR-C — Removal is residual-aware; full removal archives before deleting

Default closure behaviour is **rewrite-down-to-residual** (strip only shipped intents,
keep the item). Full removal happens **only** at zero residual, and **only after** a
durable copy to `specs/_archive/<release-id>/consumed-backlog/<slug>.md`. The ledger that
keys removal is written to `specs/_archive/<release-id>/consumed_backlog.json` in the R1
reader shape, keyed on the **verified shipped anchor set**, not the slug string.
*Rationale:* `specs/backlog/` is gitignored — the archive copy is the only surviving copy
of a CRITICAL safety record, so it must precede deletion; residual-aware rewrite prevents
silently dropping an item's unshipped scope (OQ-2 — RESOLVED).

### ADR-D — `backlog_index` is a frontmatter-only, injected-path selector

The new selector reads only each item's `intents[]` frontmatter + status (never the
body), under the injected `SpecContext`, and is registered in `_SELECTORS` like every
other dynamic input. *Rationale:* the review steps need the bound-intent index, not full
bodies; bounding to frontmatter keeps the prompt small and the selector deterministic.

---

## 6. Dependencies and risks

### Sequencing (within R2)

- 3.5 (`backlog_index` selector) lands early — steps 1 and 2 of the workflow depend on it.
- 3.4 (fragments) lands before 3.1 (workflow body) wires fragment ids — the fragment
  loader fails on a reference to a fragment id with no source.
- 3.1 (workflow body) depends on 3.3 (classifier feed) and 3.5 (selector); 3.2 (CLI
  wiring) depends on 3.1.
- 3.6 (ledger writer + removal hook) is independent of the workflow body and can land in
  parallel; it depends only on R1's `ledger.py` reader shape. BL-STALE loop-close (3.7.10)
  depends on 3.6 landing.
- The public-asset propagation TASK runs after 3.4 (fragments authored).

### Risk table

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Container/runtime wiring divergence from `release_definition`.** The new workflow must thread the injected `RuntimeFactory`, `ContextSelector`, `FragmentLoader`, `PromptPrefix`, and `LifecycleAgentRunner` exactly as `release_definition` does; a missed seam silently degrades gates. | HIGH | Mirror `release_definition.py` field-for-field (ADR-A); add a `build_backlog_definition_workflow` container factory paralleling the release one; an end-to-end `fake`-harness test asserts the full gate semantics (acceptance §3.7.1). |
| **Conditional step 4 (`conflict_resolution_grill`) skip logic.** Running it always (slow/needless grill) or never (missed divergence) both break the contract. | MEDIUM | Make the skip a Python decision driven solely by step 2's overlap report containing a `DIVERGENT_CONFLICT`; record skip vs run in the step result; test both branches (acceptance §3.7.3). |
| **Removal hook deletes the only copy of a CRITICAL record.** `specs/backlog/` is gitignored; a bug in the full-removal branch could `rm` before/without the archive copy. | HIGH | Copy-before-remove is an ADR-C invariant + a binding constraint (§3.8); the unit test asserts the archive copy exists at the moment of removal; residual-aware rewrite is the DEFAULT so full removal is the rare path. |
| **Ledger shape drift from R1 reader.** The writer must emit exactly the `{"release", "consumed":[{"slug","shipped_anchors"}]}` shape `read_consumed` expects, or BL-STALE silently never matches. | MEDIUM | Round-trip test: writer output → `read_consumed` → expected map (acceptance §3.7.8); reuse `LEDGER_FILENAME` from `ledger.py`; no second schema (§3.8). |
| **Model-downgrade seam over-trusts the model.** A live model could erroneously downgrade a real conflict. | LOW | Fail-closed default (ADR-B): the model can only downgrade with an explicit structured merge verdict; tests prove the offline path defaults to `DIVERGENT_CONFLICT`; `backlog_review_gate` (step 6) re-validates the authored result regardless. |
| **`specs/backlog/` gitignored — new/edited items may not reach CI.** | LOW | The removal hook edits/removes **existing** tracked-or-archived items; the archive copy lands under `specs/_archive/` (tracked); `backlog doctor` runs in pre-commit/CI on the working/checked-out tree regardless (R1 wiring, unchanged). |

### Memory files affected at closure (CLOSURE phase only)

- `specs/memory/architecture.md` — add the `backlog_definition` workflow to the
  dadaia-workflows surface; note the `consumed_backlog` ledger **writer** + residual-aware
  closure removal hook in `features/backlog/`; note the `backlog_index` selector. (R1 had
  already added `features/backlog/` and the doctor/chokepoint wiring.)
- `specs/memory/product/*` — only if a product atom describes the backlog/governance
  workflow surface; otherwise "no change" recorded in CLOSURE.
- `specs/memory/tech-stack.md` — no change expected (no new dependency).

### Open decisions (grill output — none blocking; all resolved)

All epic OQs were RESOLVED at R1 SPEC time (epic §12); the one decision deferred **by
design** to R2 — the exact prompt shape of the model-adjudication downgrade step — is
fixed by this SPEC (§3.3 + ADR-B: the model is invoked only through the classifier's
`downgrade` seam, fail-closed). The R2 release-definition grill on the picked epic-R2
slice surfaced no new open question: the scope is the epic's own §4/§6/§8 with the R1
foundation in place. **No open decision blocks SPEC approval.**

---

## 7. Traceability

This release **consumes the R2 slice** (§11) of backlog
`FEAT-BACKLOG-DEFINITION-WORKFLOW-01`
(`specs/backlog/backlog-definition-workflow-dedup-conflict-control.md`). At R2 CLOSURE the
backlog item's R2 residual (the workflow body, the classifier feed, the real fragments,
the removal-on-release lifecycle, the `backlog_index` selector) is **delivered**; with R1
+ R2 both shipped, the epic's residual scope is exhausted and the item is dispositioned
terminally (`DELIVERED — v0.1.26`, or rewritten to any genuinely-surviving residual) per
the never-delete law and the epic's §3 OVERLAP→UPDATE discipline — and, fittingly, R2's
own removal hook is the mechanism that takes a consumed item out of the live SET. The
next release is `workflow-model-governance-panel-control-plane`.
