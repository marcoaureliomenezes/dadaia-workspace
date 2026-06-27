# SPEC — Release: v0.1.29 — Harness as a governed dimension + catalog completion

**Status:** Aprovado
**Release ID:** v0.1.29
**Owner:** product-engineer
**Opened:** 2026-06-27
**Consumes:** none

> This release consumes no backlog item — the model-governance backlog epic was already
> consumed by v0.1.28. v0.1.29 resolves the **v0.1.28 residual** (harness is governed in
> the catalog DTO but not in the resolver/CLI/overlay) and the **code-reviewer MEDIUM**
> (a `--harness pi` run sends a codex model id to the PI worker and records `codex` in the
> snapshot). See the binding `GRILL.md` (decisions D-1..D-5, from a hands-on code-level
> diagnosis on `feature/v0.1.28`).

---

## 1. Problem and context

v0.1.28 shipped model-**profile** governance: a single resolver
(`WorkflowExecutionPolicyResolver`), a built-in profile registry (`model_profiles.py`),
an operator-editable overlay (`workflow-model-policy-v1`), a panel control plane, and a
`WMP-*` doctor. The harness, however, is **not** a governed dimension. Verified at code
level (GRILL §"Diagnosis"):

1. **The resolver derives each step's harness only from the catalog default.** Every
   governed step's `default_harness` is `codex` (a worker step's default is
   `_DEFAULT_WORKER_HARNESS = CODEX_HARNESS`), and `resolve()` never receives a harness
   override. `pi` is never reachable through the governed policy.
2. **The pipeline CLI never threads harness into resolve.** `lifecycle.py pipeline`
   (~line 1081) builds a `dict[label -> AgentRuntimeKind]` from `--harness`/`--step-harness`
   and applies it to each `PipelineStep.runtime_kind` **after** `resolver.resolve(...)`.
   So `--harness pi` swaps the *execution adapter* but leaves the *governed snapshot* on
   codex — the adapter and the auditable record disagree.
3. **The resolver rejects any profile whose harness ≠ the catalog-default step harness.**
   `_validate_profile` (`policy_resolver.py:288`) compares `profile.harness` to
   `step.default_harness`, so neither the CLI, the overlay, nor the panel codex/pi toggle
   can ever move a step to `pi` — a PI profile is rejected against a codex-default step.
4. **Net effect:** PI-as-Layer-2-worker is **unusable through governance**. `--harness pi`
   sends a codex model id to the PI worker and the run snapshot records `codex`. The
   code-reviewer scored this MEDIUM as an auditability divergence; its real impact is that
   the entire PI-worker capability the model layer was built to govern cannot be selected.
5. **The governed catalog is incomplete.** Only 3 of 7 workflows
   (`implementation`, `release_definition`, `backlog_definition`) project onto the resolver
   seam via `governed_workflow_catalog()`. `closure`, `audit`, `research`, `bug_report`
   are absent — `policy show` and `/api/workflow-catalog` cannot inspect them.

The model-governance layer governs *which model* a step runs but not *which harness* runs
it. This release makes **harness a first-class governed dimension** with a clean
precedence rule, makes the **executed harness and the recorded harness a single source of
truth**, lets the **overlay + panel toggle** persist a real harness change, and
**completes the governed catalog to all 7 workflows**.

---

## 2. Objective

Make the worker harness a first-class governed dimension end-to-end — CLI flags, overlay,
and panel toggle all move a step onto PI through the same shared resolver, the executed
adapter and the recorded snapshot always agree, the doctor validates it — and complete the
governed catalog so all 7 dadaia-workflows are inspectable and governable.

---

## 3. Scope

### 3.1 — D-1: Harness becomes a first-class governed dimension (resolver)

The effective harness per step resolves with this precedence (highest wins):

```
CLI --step-harness  >  CLI --harness (default)  >  overlay step harness
                    >  overlay default_harness  >  catalog step default
```

- `resolve()` gains harness inputs: a per-workflow default harness override and a
  `{step_label -> harness}` map (the CLI-`--step-harness` layer), plus it reads the
  overlay's step harness and `default_harness`. The resolved harness per step is computed
  from this precedence chain.
- **The profile must match the effective harness, not the catalog default.**
  `_validate_profile` compares `profile.harness` against the step's **resolved** harness.
  The `policy_resolver.py:288` mismatch-against-`default_harness` check is the defect; it
  becomes a mismatch-against-effective-harness check.
- **Auto-profile-on-harness-override.** When a harness override lands for a step with **no
  explicit profile override** (neither CLI `--step-model` nor overlay step profile), the
  resolver auto-selects that harness's **default profile for the step's purpose**
  (review/gate step → the harness's deep profile; producing step → the harness's standard
  profile). The per-harness default profiles already exist on the catalog DTO
  (`default_profiles: {harness -> profile_id}`); the resolver reads the effective harness's
  entry instead of only `default_profile`.

### 3.2 — D-2: Single source of truth for the executed harness (pipeline)

- `apply_resolved_policy` sets each `PipelineStep.runtime_kind` from the **resolved**
  harness in the snapshot entry (mapping the harness name → `AgentRuntimeKind` via the
  catalog's `_KIND_TO_HARNESS` inverse). The adapter that runs and the snapshot that is
  recorded therefore always agree.
- The snapshot's `WorkflowPolicyStepEntry.harness` already records the resolved harness;
  the fix guarantees the *runtime adapter* matches it rather than the CLI's separate
  post-resolve `runtime_kind` swap. The CLI's old "build base ladder with `runtime_kind`
  overrides, then `apply_resolved_policy`" two-track logic collapses to one track: resolve
  (with harness inputs) → `apply_resolved_policy` (sets runtime_kind from resolved harness).
- The concrete model that reaches the PI adapter is the resolved PI profile's model
  (carried in `ResolvedModelConfig.model` and threaded into the step request) — fixing the
  v0.1.28 "codex model to the PI worker" divergence.

### 3.3 — D-3: Overlay carries harness + panel toggle persists it

- The overlay schema (`workflow-model-policy-v1.schema.json`) gains an optional per-step
  `harness` field and an optional per-workflow `default_harness` field. The store
  (`json_workflow_model_policy_store.py`) parses, round-trips (`to_dict`), and exposes
  them via new accessors (`step_harness`, `workflow_default_harness`). **Back-compat:** an
  overlay with no harness field resolves exactly as today (catalog default). `default`
  context only (carrying v0.1.28 D-2 forward).
- The panel codex/pi segmented toggle persists a real harness change through the existing
  `PUT /api/workflow-model-policy` route (validate → atomic write → `.last-good.json`).
  The resolver honors the persisted harness; the default-vs-effective diff in
  `/api/workflow-catalog` reflects the harness change (a new `harness`-overridden flag on
  each step row alongside the existing `is_overridden` profile flag).
- The PUT/validate semantic check already resolves every overlaid workflow through the
  shared resolver, so an overlay naming an unsupported harness (e.g. `pi` on a step the
  catalog declares codex-only) is rejected at write time — invalid never persists.

### 3.4 — D-4: Complete the governed catalog to 7 workflows

Add `closure`, `audit`, `research`, `bug_report` to the governed catalog so all 7
workflows are inspectable via `policy show` + `/api/workflow-catalog` and governable in
the panel. Each governed worker step carries role / default harness / default profile per
supported harness / fragments / output schema (the existing `DadaiaWorkflowStepDTO` shape).
The **real** step definitions (found by code inspection — these are NOT invented):

- **`closure`** — the `dadaia lifecycle close` verb (`lifecycle.py:957`) is a **single**
  `_run_phase_step(label="close", role="product-engineer", CODE_REVIEW → CLOSURE)` plus a
  Python-owned `_apply_closure_removal` post-step (the consumed-ledger backlog removal).
  Closure has **no multi-step ladder**, so it is cataloged as its real single worker step
  `close` (product-engineer) + the Python post-step modeled as a gate. Closure's worker
  step is currently generic (no fragment), so per WMP-5 it carries no output-schema
  obligation — cataloged honestly as a partial/generic worker step.
- **`audit`** / **`research`** / **`bug_report`** — these are the three names in
  `workflows/_deferred.DEFERRED_WORKFLOWS`; their entry points raise `NotImplementedError`
  (no real multi-step body exists). They are added to the governed catalog as
  **`deferred`** workflows with **zero governed model steps** (mirroring how
  `governed_workflow_catalog()` already omits zero-step deferred workflows from the
  resolver seam, while `list_dadaia_workflows()` lists them with `availability="deferred"`).
  Their inspectability requirement is satisfied at the **catalog/panel** layer
  (`/api/workflow-catalog` and `policy show` enumerate all 7 with availability), NOT by
  inventing model steps for a workflow that has no runnable body. Where a deferred
  workflow gains a real body in a later release, its steps become governed then.

> **Scope ambiguity resolved (D-4).** "All 7 inspectable via `policy show`" is read as:
> the catalog enumerates all 7 with availability + (for the runnable ones) their governed
> worker steps. Deferred workflows have no steps to resolve a model policy for; inventing
> steps would create a second drifting source the entire v0.1.28 design forbids. The
> resolver continues to reject a `resolve(<deferred-workflow>)` call with no governed
> steps with an actionable "no governed steps" error — that is correct behavior, not a gap.
> `closure` IS made resolvable (it has one real worker step).

Where a runnable workflow has steps that legitimately run on only one harness, the catalog
declares the others unsupported on that harness explicitly (the WMP doctor already
tolerates a per-step single-harness declaration).

### 3.5 — D-5: PI proof obligation (E2E, no live provider)

- **CLI path:** an `implementation` run selected onto PI via `--harness pi` resolves PI
  profiles for every step, sets each `PipelineStep.runtime_kind` to `PI_HEADLESS`, threads
  the resolved **PI** model into each step request, and records `harness=pi` on every
  snapshot step entry — asserted through `FakeAgentRuntime.received_models`
  (`ResolvedModelConfig.harness == "pi"` and `.model` is a PI catalog model) and the
  persisted run's `workflow_policy` snapshot.
- **Overlay path:** the same assertion holds when the harness change comes from a persisted
  overlay (`default_harness: pi` or a per-step `harness: pi`) with no CLI flag.
- **Panel path:** a panel E2E asserts the codex/pi toggle persists through `PUT` and the
  `/api/workflow-catalog` default-vs-effective diff reflects the harness change.

### 3.6 — D-doctor: doctor validates the harness dimension

`policy_doctor.py` (`WMP-*`) validates the new harness field: WMP-6 already resolves every
overlay override through the shared resolver, so an overlay harness that fails resolution
is caught; add explicit coverage that the overlay's `harness`/`default_harness` reference
a supported Layer-2 harness for the step (WMP-PROFILE/WMP-LAYER2-RESIDUE), and that the
completed catalog (closure added) passes WMP-1..WMP-7. No Layer-2 `claude`/`opencode`
residue may appear in any harness field (WMP-LAYER2-RESIDUE, already enforced for
profiles/steps — extend to overlay harness values).

### 3.7 — Carried-forward laws (from v0.1.28 / backlog §3)

These remain invariants and are re-asserted by acceptance:

- **Layer-2 = codex|pi only** (`fake` is the deterministic test adapter;
  `claude`/`opencode` rejected as Layer-2 workers).
- **Default-first** — an unconfigured workspace (no overlay) resolves to library defaults
  (codex), unchanged.
- **Auditability snapshot** — the resolved policy is frozen onto the run before step 1;
  historical runs read their snapshot verbatim (never re-resolved).
- **Panel governance via validated overlay** — loopback + Host guard, atomic write,
  `.last-good.json`, invalid-blocks-execution (missing != invalid).
- **Resolve-once-before-step-1** — one resolver, one catalog, one policy file; CLI and
  panel never disagree.

---

## Acceptance criteria

Each criterion is concrete and falsifiable.

**AC-1 (D-1 precedence).** `resolve("implementation")` with a step-harness override
`implement=pi` resolves `implement.harness == "pi"`; with only a default-harness override
`pi`, every step resolves `harness == "pi"`; with an overlay step `harness: pi` and no CLI
override, the step resolves `pi`; CLI `--step-harness` beats overlay step harness beats
overlay `default_harness` beats catalog default — asserted by a precedence test table.

**AC-2 (D-1 auto-profile).** When a step's harness is overridden to `pi` with **no**
profile override, `resolve` auto-selects the PI default profile for the step's purpose
(`pi-implementation-standard` for `implement`; `pi-reasoning-high` for a review step) and
the resolved profile's harness is `pi`. The pre-fix `policy_resolver.py:288`
mismatch-against-catalog-default no longer rejects a PI profile on a PI-resolved step.

**AC-3 (D-2 single source of truth).** After `apply_resolved_policy`, every
`PipelineStep.runtime_kind` equals the `AgentRuntimeKind` for its snapshot entry's resolved
harness (`pi` → `PI_HEADLESS`, `codex` → `CODEX_EXEC`). No code path swaps `runtime_kind`
independently of the resolved harness.

**AC-4 (D-5 CLI proof).** An `implementation` run with `--harness pi` against
`FakeAgentRuntime`: (a) every `received_models[i].harness == "pi"`; (b) every
`received_models[i].model` is a PI catalog model (`gpt-5.3-codex` or `gpt-5.5`, never a
codex-only id mismatch); (c) the persisted run's `workflow_policy` snapshot records
`harness=pi` for every step.

**AC-5 (D-5 overlay proof).** The same three assertions as AC-4 hold when the harness
comes from a persisted overlay (`default_harness: pi`) with **no** CLI flag.

**AC-6 (D-3 panel persistence).** `PUT /api/workflow-model-policy` with a body setting
`implement.harness = pi` returns 200 and persists; `GET /api/workflow-model-policy`
round-trips the harness; `GET /api/workflow-catalog` shows `implement` with
`harness == "pi"`, `effective_profile` = the PI default, and a harness-overridden flag set.

**AC-7 (D-4 catalog completion).** `policy show` (CLI) and `GET /api/workflow-catalog`
both enumerate all 7 workflows: `release_definition`, `implementation`,
`backlog_definition`, `closure` (with its real `close` worker step), and `audit` /
`research` / `bug_report` (availability `deferred`, zero governed steps). `closure`
resolves a model policy for its `close` step; the three deferred workflows surface in the
catalog with availability and resolve no model steps.

**AC-8 (doctor).** `run_policy_doctor` over the completed catalog returns **zero ERROR
findings**; a deliberately-broken overlay naming `harness: pi` on a codex-only step yields
a `WMP-OVERLAY`/`WMP-PROFILE` ERROR with an actionable message; an overlay naming a
forbidden Layer-2 harness (`claude`/`opencode`) yields `WMP-LAYER2-RESIDUE`.

**AC-9 (no Layer-2 residue).** No harness field anywhere in the resolver, overlay, schema,
or catalog accepts `claude`/`claude_sdk`/`opencode` as a Layer-2 worker harness; the
attempt is rejected with a pointer to codex/pi.

**AC-10 (default-first / back-compat).** With **no** overlay and **no** CLI harness flag,
`resolve("implementation")` is byte-identical to v0.1.28 (every step `harness == "codex"`,
default profiles). An overlay JSON written by v0.1.28 (no harness field) loads and resolves
unchanged. Old persisted run snapshots load (the snapshot shape is unchanged).

**AC-11 (full suite green).** `ruff format --check`, `ruff check`, `mypy --strict`, and
`pytest` all pass; `dadaia public stage && dadaia public install --target all &&
dadaia public doctor` exits 0 (schema is a projected public asset).

---

## 4. Out of scope

- **Per-context overlays** beyond `default` (still D-2 deferred; `contexts` shape reserved,
  non-`default` inert).
- **Inventing model-step ladders for the deferred `audit`/`research`/`bug_report`
  workflows.** They are cataloged as deferred with zero governed steps; their real bodies
  are follow-up releases.
- **A new Layer-2 harness** beyond codex/pi (no `claude`/`opencode` resurrection).
- **Live PI/codex provider calls** in tests — all proof is via `FakeAgentRuntime`.
- **Changing the model profile set** in `model_profiles.py` (the 5 built-ins are stable;
  this release governs *which* of them gets selected by harness, not new ones).
- **Closure becoming a multi-step fragment-driven workflow** — out of scope; closure is
  cataloged as its real single generic worker step.
- **Memory atom updates** — performed in CLOSURE, not this DEFINITION pass.

---

## 5. Dependencies and risks

| Item | Type | Mitigation |
|------|------|-----------|
| Stacked on `feature/v0.1.28` (CLOSED+archived on its branch) | Sequencing | Branch `feature/v0.1.29` is created off `feature/v0.1.28` @ bd710c57; both ship together. |
| Resolver precedence change touches the shared CLI+panel seam | Risk (regression) | AC-10 byte-identical back-compat test pins the default path; the resolver is the single seam both consumers use, so one fix covers both. |
| Overlay schema change must round-trip old files | Risk (back-compat) | Harness fields are **optional**; AC-10 loads a v0.1.28 overlay unchanged. Schema is `additionalProperties:false`, so the new optional fields are added explicitly. |
| `apply_resolved_policy` now owns `runtime_kind` (previously CLI did) | Risk (behavior shift) | The CLI's separate post-resolve swap is removed in the same task; AC-3 asserts the single source of truth. |
| Schema is a projected public asset (`public/schemas/`) | Process | After editing source, run `dadaia public stage && install --target all && doctor` (AC-11); never hand-edit the projection. |
| `policy_doctor` must not regress on the partial/generic closure worker step | Risk | WMP-5 already exempts generic (no-fragment) worker steps from the output-schema obligation; closure's `close` step is generic, so it is cataloged honestly without tripping WMP-5. |
| Pre-push gate currently red under concurrent Playwright load (not v0.1.28/29 code) | Process | Documented in ACTIVE.md; ship when machine load clears. Not a code blocker for this release. |
