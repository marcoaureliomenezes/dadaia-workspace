# PLAN — Release: v0.1.29 — Harness as a governed dimension + catalog completion

**Status:** Aprovado
**Release ID:** v0.1.29
**Owner:** product-engineer

> Implementation approach for the approved SPEC. Module-by-module, marking NEW vs
> MODIFIED. Back-compat is a hard constraint throughout: an overlay with no harness field
> resolves exactly as v0.1.28; old run snapshots load unchanged.

---

## Strategy

One shared resolver already feeds both CLI and panel; the doctor and overlay store already
read the governed catalog. The fix is therefore **surgical and centralized**:

1. Teach the resolver to take harness inputs and resolve an **effective harness** per step
   (precedence), match the profile against the **effective** harness, and auto-select the
   harness's default profile when only the harness is overridden.
2. Make the overlay store + schema carry harness (optional, back-compat).
3. Thread `--harness`/`--step-harness` from the pipeline CLI **into** `resolve(...)`, and
   make `apply_resolved_policy` set `runtime_kind` from the resolved harness (single source
   of truth) — removing the CLI's separate post-resolve swap.
4. Complete the governed catalog (closure as a real single step; audit/research/bug_report
   as deferred zero-step workflows).
5. Persist the panel codex/pi toggle through the existing PUT route + reflect harness in
   the catalog diff.
6. Extend the doctor + tests.

Waves are ordered so each ends on a green checkpoint (`pytest` + `ruff` + `mypy`).

---

## Layers affected

| Layer | Modules |
|-------|---------|
| core/models | `core/models/workflow_execution.py` (snapshot/entry already carry `harness` — verify, no change expected) |
| features/lifecycle | `policy_resolver.py`, `pipeline.py`, `policy_doctor.py` |
| features/workflows | `dadaia_catalog.py` (catalog completion) |
| infrastructure | `json_workflow_model_policy_store.py` (overlay harness fields) |
| public/schemas | `workflow-model-policy-v1.schema.json` (optional harness fields) |
| cli | `cli/commands/lifecycle.py` (`pipeline` verb threading) |
| features/panel | `views/workflow_policy.py`, `views/assets/js/workflow_policy.js` |
| container | `container.py` (verify wiring; closure catalog reaches resolver) |

---

## Module-by-module

### MODIFIED — `features/lifecycle/policy_resolver.py` (the keystone)

- **`StepOverride`** (existing): keep for `--step-model` profile overrides.
- **NEW `HarnessOverride`** dataclass (or extend `resolve()` signature): carry
  `{step_label -> harness}` (CLI `--step-harness`) and an optional default harness
  (CLI `--harness`).
- **`resolve(...)` signature** gains: `default_harness: str | None = None`,
  `harness_overrides: tuple[HarnessOverride, ...] | dict[str, str] = ()`. Both optional →
  back-compat default path unchanged.
- **NEW `_resolve_harness(step, context, default_harness, harness_by_step)`** — computes
  the effective harness with precedence:
  `CLI step harness > CLI default harness > overlay step harness > overlay default_harness
  > catalog step default`. Reads overlay harness via the new store accessors (§store).
- **`_resolve_step`** rework:
  1. Compute `effective_harness`.
  2. Resolve the profile id with the existing profile precedence
     (CLI `--step-model` > overlay step profile > library default), **but** when **no**
     explicit profile override exists for the step, the library default becomes
     `step.default_profiles[effective_harness]` (auto-profile-on-harness-override) instead
     of the catalog `default_profile`. `CatalogStep` must expose the per-harness default
     profiles — add a `default_profiles: dict[str, str]` field to `CatalogStep` (populated
     by `governed_workflow_catalog`'s `_governed_step`; back-compat default `{}` →
     falls back to `default_profile` when the effective harness has no entry, raising an
     actionable error if the step does not support the effective harness).
  3. Validate the profile against `effective_harness`.
- **`_validate_profile`** (the `:288` defect): compare `profile.harness` to the
  **effective** harness, not `step.default_harness`. Message updated to name the effective
  harness.
- **`WorkflowPolicyStepEntry`** already carries `harness` — the entry now records the
  effective harness (already wired via `profile.harness`, which now equals effective).
- **Acceptance:** AC-1, AC-2, AC-9, AC-10.

### MODIFIED — `infrastructure/json_workflow_model_policy_store.py`

- **`WorkflowModelPolicyOverlay`**: the per-workflow / per-step shape currently maps
  `step_label -> profile_id` (a `str`). Extend a step's value to carry an optional
  `harness`. Two viable shapes; choose **back-compat-preserving**: keep
  `step_label -> profile_id` for the profile, and add a **parallel** harness map
  `step_label -> harness` under the workflow (`harnesses`), plus a workflow-level
  `default_harness`. (Avoids changing the existing `steps` value type → old files parse.)
- **NEW accessors:** `step_harness(context, workflow_id, step) -> str | None`,
  `workflow_default_harness(context, workflow_id) -> str | None`. Both honor `default`
  context only (D-2), mirroring `step_profile`.
- **`_parse_workflow`**: accept the new optional `default_harness` (str) and `harnesses`
  (object: step_label -> str) fields; unknown fields still hard-error.
- **`to_dict`**: round-trip the harness fields when present (omit when empty → byte-stable
  old output for a profile-only overlay).
- **Acceptance:** AC-5, AC-6, AC-10 (old overlay loads).

### MODIFIED — `public/schemas/workflow-model-policy-v1.schema.json`

- Under `workflowOverlay`: add optional `default_harness` (`{type:string, enum:[codex,pi]}`)
  and `harnesses` (`{type:object, additionalProperties:{type:string, enum:[codex,pi]}}`).
- Keep `additionalProperties:false`; both new fields optional → old files validate.
- This is a **projected public asset**: edit source, then
  `dadaia public stage && install --target all && doctor`.
- **Acceptance:** AC-6, AC-9, AC-11.

### MODIFIED — `features/lifecycle/pipeline.py`

- **`apply_resolved_policy`**: in addition to threading `resolved_model` + `model_profile`,
  set `runtime_kind` from the snapshot entry's resolved harness. Map harness name →
  `AgentRuntimeKind` via the catalog's `_KIND_TO_HARNESS` inverse (add a small
  `harness_to_kind` helper or import the mapping). A snapshot entry whose harness has no
  kind mapping (e.g. an unexpected value) raises an actionable error rather than silently
  keeping the caller's kind.
- `implementation_ladder` unchanged (it still produces the base ladder; the runtime_kind it
  carries is now overwritten by `apply_resolved_policy` from the resolved harness).
- **Acceptance:** AC-3, AC-4.

### MODIFIED — `cli/commands/lifecycle.py` (`pipeline` verb, ~line 1012)

- Build `harness_by_step: dict[str, str]` from `--step-harness` (label=harness) and pass it,
  plus the default `--harness`, **into** `resolver.resolve("implementation", ...,
  default_harness=harness, harness_overrides=harness_by_step)`.
- **Remove** the separate post-resolve `runtime_kind` swap (`base = tuple(replace(step,
  runtime_kind=overrides.get(...)) ...)`); the ladder's `runtime_kind` now comes from
  `apply_resolved_policy` (D-2 single source of truth). The CLI still selects the **default
  execution kind** for `fake` runs (when neither harness is governed, e.g. `--harness fake`
  for a dry-run) — preserve `fake` as the default-execution adapter while the governed
  snapshot records the governed harness. (Resolve the `fake`-vs-governed nuance: `fake` is
  a test-execution adapter, not a governed Layer-2 harness; when `--harness fake`, the
  snapshot resolves the catalog/overlay harness for auditability but the *adapter* runs
  fake. Encode this explicitly so dry-runs still work — see Risk table.)
- `--step-harness`/`--harness` rejected values (`claude`/`opencode`) keep failing via
  `_resolve_harness`.
- `--show-policy` now reflects the harness override in the printed table.
- **Acceptance:** AC-4, AC-7 (`policy show`), AC-9.

### MODIFIED — `features/workflows/dadaia_catalog.py` (catalog completion, D-4)

- **`closure`**: add a `_closure_steps()` builder returning the real single worker step
  `close` (role `product-engineer`, generic — no fragment, so no output-schema obligation)
  plus the Python post-step (`closure_removal_gate`, `is_gate=True`, no worker). Add
  `closure` to `_all_workflows()` with `availability=AVAILABILITY_PARTIAL` (it runs today
  but its worker step is generic). Add purpose/display-name entries.
  `governed_workflow_catalog()` will project the `close` worker step (it has a
  `default_harness`) onto the resolver seam, so `policy show closure` resolves.
- **`audit`/`research`/`bug_report`**: already appended from `DEFERRED_WORKFLOWS` with
  zero steps and `availability=AVAILABILITY_DEFERRED`. **No change needed** to list them —
  confirm they appear in `list_dadaia_workflows()` and `/api/workflow-catalog`. They have
  zero governed steps so `governed_workflow_catalog()` correctly omits them from the
  resolver seam (resolving them raises "no governed steps", which is correct).
- Ensure `_governed_step` populates the new `CatalogStep.default_profiles` field so the
  resolver can auto-select per-harness.
- `_assert_catalog_defaults_resolve()` already guards default profiles — extend to the
  closure step's defaults.
- **Acceptance:** AC-7, AC-2 (per-harness defaults reach the resolver).

### MODIFIED — `features/lifecycle/policy_doctor.py`

- WMP-6 already resolves every overlay override through the shared resolver — with the
  resolver change it now also catches an overlay harness that fails (unsupported harness on
  a step, harness/profile mismatch). Add explicit assertions/messages:
  - WMP-PROFILE/WMP-OVERLAY: an overlay `harness`/`default_harness` referencing a harness
    the step does not support → actionable ERROR.
  - WMP-LAYER2-RESIDUE: an overlay harness value of `claude`/`opencode` → ERROR.
- Confirm WMP-1..WMP-7 pass over the completed catalog (closure added). The generic
  `close` worker step has no fragments → WMP-5 exempts it (no false positive).
- **Acceptance:** AC-8.

### MODIFIED — `features/panel/views/workflow_policy.py`

- `_effective_steps`: add a `"harness_overridden"` flag per row (`entry.harness !=
  catalog_step.default_harness`) alongside the existing `is_overridden` profile flag, and
  surface `default_harness` on each row.
- The PUT/validate path is unchanged structurally — it already validates candidate
  overlays through the resolver, so an overlay harness that the resolver rejects yields the
  existing 400 with a field path. Confirm a harness-only overlay (no profile override)
  passes validation (auto-profile-on-harness-override makes it resolvable).
- **Acceptance:** AC-6.

### MODIFIED — `features/panel/views/assets/js/workflow_policy.js`

- Wire the codex/pi segmented toggle to write the step's `harness` into the overlay body
  sent to `PUT /api/workflow-model-policy`, and render the harness-overridden flag in the
  default-vs-effective diff. (Projected asset — edit source, re-stage/install.)
- **Acceptance:** AC-6 (panel E2E).

### VERIFY (likely no change) — `container.py`, `core/models/workflow_execution.py`

- `build_workflow_policy_resolver` already injects `governed_workflow_catalog()` + overlay;
  no structural change. Confirm the closure catalog reaches it.
- `WorkflowPolicyStepEntry`/`ResolvedModelConfig` already carry `harness`; confirm no shape
  change is needed. If `resolve()` gains new params, the container call sites
  (`pipeline`, `policy show`, panel resolver factory) pass them through where relevant.

---

## Execution order

1. **Wave A** — resolver precedence + auto-profile + effective-harness validation; overlay
   store + schema harness fields; CLI `pipeline` threading; `apply_resolved_policy`
   runtime_kind-from-resolved-harness.
2. **Wave B** — catalog completion (closure real step; audit/research/bug_report deferred).
3. **Wave C** — panel toggle persistence + catalog diff harness flag + E2E.
4. **Wave D** — doctor harness validation + final full-suite + projection checkpoint.

---

## Technical risks

| Risk | Mitigation |
|------|-----------|
| Overlay value-type change breaks old files | Add a **parallel** `harnesses`/`default_harness` map; do not change the existing `steps` (profile) value type. AC-10 loads a v0.1.28 overlay. |
| Default path regresses (codex) | AC-10 byte-identical test; resolver falls back to `default_profile` when no harness override. |
| `fake` dry-run breaks when runtime_kind comes from resolved harness | `fake` is a test-execution adapter, not a governed harness; keep `--harness fake` selecting the fake adapter for execution while the snapshot resolves the governed harness. Explicit branch + test. |
| Deferred workflows have no steps → resolve raises | Correct behavior; cataloged at the panel layer only. Test asserts the actionable "no governed steps" message. |
| Schema is a projected asset | Run `public stage/install/doctor` in Wave D; never hand-edit projection. |

---

## Validation plan

- Unit: resolver precedence table (AC-1), auto-profile (AC-2), effective-harness validation
  (AC-2/AC-9), back-compat (AC-10), store round-trip (AC-10), `apply_resolved_policy`
  runtime_kind (AC-3), doctor harness findings (AC-8), catalog completion (AC-7).
- Integration/E2E: CLI `--harness pi` capture via `FakeAgentRuntime` (AC-4); overlay
  `default_harness: pi` capture (AC-5); panel PUT→GET→catalog harness round-trip (AC-6).
- Suite: `ruff format --check && ruff check && mypy --strict && pytest` (AC-11), then
  `dadaia public stage && install --target all && doctor` exit 0 (AC-11).
