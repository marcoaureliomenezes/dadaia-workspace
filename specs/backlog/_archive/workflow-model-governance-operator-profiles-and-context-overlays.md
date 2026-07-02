---
name: workflow-model-governance-operator-profiles-and-context-overlays
status: delivered
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/model_profiles.py#list_profiles" }
    change: "WS-PROFILES: load operator-added PI profiles from .dadaia/states/workflow_model_profiles.local.json and merge them with the built-in recommended profiles; validate harness=pi, never store API keys, never project the local store into public assets"
  - subject: { kind: code, ref: "dadaia_workspace/core/protocols/workflow_model_policy_store.py#WorkflowModelPolicyOverlay" }
    change: "WS-OVERLAYS: honor non-default context keys in workflow_model_policy.json with `extends` inheritance, replacing the D-2 collapse where only the `default` context resolves and a non-default key is inert"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/policy_resolver.py#WorkflowCatalog" }
    change: "WS-OVERLAYS: resolve a step's profile through the per-context overlay chain (context -> extends... -> default) instead of collapsing to the `default` context, preserving fail-closed UnknownProfileError on an unresolvable ref"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/policy_resolver.py#DEFAULT_PROFILE_BY_HARNESS_PURPOSE" }
    change: "WS-NITS (code-reviewer LOW): de-duplicate _DEFAULT_PROFILE_BY_HARNESS_PURPOSE (verbatim twin in dadaia_catalog.py) into one shared home, and correct the policy_resolver.py module docstring to name governed_workflow_catalog() as the production resolver source"
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/workflow_policy.py#_semantic_check" }
    change: "WS-NITS (code-reviewer LOW): make panel _semantic_check mirror the doctor's explicit 3-map union (contexts | default_harness_overlay | step_harness_overlay) instead of relying on the empty-steps parse side effect"
---

# EPIC — Workflow Model Governance: operator-added PI profiles + per-context overlays

**ID:** FEAT-WORKFLOW-MODEL-GOVERNANCE-02
**Reported:** 2026-06-27 (PM curation of the v0.1.28/v0.1.29 D-2 deferrals).
**Owner:** project-manager (curates) → product-engineer (release definition after a
MANDATORY grill).
**Status:** OPEN — candidate. Nothing here authorizes work; needs operator pick + grill
per release-governance.
**Parent epic:** `workflow-model-governance-panel-control-plane.md`
(FEAT-WORKFLOW-MODEL-GOVERNANCE-01, DELIVERED v0.1.28) named this candidate by slug as the
follow-up vehicle for its D-2 deferrals.
**Source of truth (operator-confirmed deferrals):**
- `specs/_archive/releases/v0.1.28/CLOSURE.md` → "Drifts" →
  `d-2-deferrals-operator-pi-profiles-and-per-context-overlays`
- `specs/_archive/releases/v0.1.29/CLOSURE.md` → "Drifts" →
  `v0.1.28-d-2-deferrals-still-deferred` and `code-reviewer-low-nits-deferred-as-minor-follow-ups`

## Problem statement

v0.1.28 shipped the workflow-model governance control plane (model-profile registry +
atomic overlay store + `WorkflowExecutionPolicyResolver` + per-run snapshot + panel editor),
and v0.1.29 added per-workflow / per-step harness overlays. Both releases bounded their
scope with a grill-confirmed **D-2** boundary, deferring two operator-facing breadth
features that remain open against current `main@v0.1.29`:

1. **Operator-added PI profiles are not loaded or validated.** The release ships **built-in
   recommended profiles only** (`features/lifecycle/model_profiles.py`). There is no
   local-profile store at `.dadaia/states/workflow_model_profiles.local.json`, so an
   operator cannot register a PI profile beyond the recommended set.
2. **Per-context overlays + `extends` inheritance are not honored.** The overlay store
   (`infrastructure/json_workflow_model_policy_store.py`) **reserves** the `contexts{}`
   shape but the resolver collapses to the `default` context (D-2): a non-`default` context
   key is inert (`overlay_for(...)` returns `None` for any non-default context). There is no
   `extends` inheritance chain.

> **Already resolved — do NOT re-file.** The v0.1.28 code-reviewer MEDIUM
> (snapshot `runtime_kind` vs governed harness divergence under a `--harness` override) was
> **resolved by D-2** per the v0.1.29 CLOSURE drift `v0.1.28-d-2-deferrals-still-deferred`.
> `apply_resolved_policy` now preserves the dry-run FAKE author
> (`test_apply_resolved_policy_preserves_fake_for_dry_run`). This candidate carries only the
> two open D-2 breadth items plus the v0.1.29 code-reviewer LOW nits.

## Workstreams

### WS-PROFILES — operator-added PI profiles (medium)

Load + validate operator profiles from a new local store
`.dadaia/states/workflow_model_profiles.local.json`, merged with the built-in recommended
profiles surfaced by `model_profiles.list_profiles()` / `profiles_for(harness)`.

**Invariants (non-negotiable):**
- Validate `harness: pi` on every operator-added profile (this WS is PI-scoped; reject other
  harnesses or scope them explicitly at grill).
- **Never store API keys** in the local store (consistent with the `pi_runtime` env-allowlist
  + `_redact` posture).
- **Never project the local store into public assets** — it is workspace-local operator
  state under `.dadaia/states/`, not a `public/` asset; `dadaia public doctor` must stay
  `[ok] public-privacy`.
- Preserve `UnknownProfileError` fail-closed behavior for unresolvable profile refs.

**Touches:** `features/lifecycle/model_profiles.py` (loader/merge) + a new local-profile
store (infrastructure adapter + `core/protocols` port injected via `container.py`).

### WS-OVERLAYS — per-context overlay inheritance (medium)

Honor non-`default` context keys in `workflow_model_policy.json` with an `extends` chain so a
context inherits from its parent (ultimately `default`), replacing the D-2 collapse.

**Touches:**
- `infrastructure/json_workflow_model_policy_store.py` —
  `WorkflowModelPolicyOverlay.overlay_for` / `workflow_default_harness` /
  `step_harness_overlay` resolution to walk the `extends` chain instead of returning `None`
  for non-default contexts; extend `_ALLOWED_TOP_LEVEL` / schema validation for `extends`.
- `features/lifecycle/policy_resolver.py` — resolve a step's profile through the per-context
  overlay chain (context → extends… → default), keeping fail-closed on unresolvable refs.

**Guardrails:** cycle detection on `extends`; a missing parent is a hard validation error,
never a silent fallthrough; the `default` context stays the inheritance root.

### WS-NITS — v0.1.29 code-reviewer LOW follow-ups (small; fold in iff cheap)

The v0.1.29 code-reviewer raised 3 non-blocking nits; fold the two that align with this
epic's surface (or split into a separate hygiene pass if they bloat the release):

- `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` is duplicated verbatim in `policy_resolver.py` and
  `features/workflows/dadaia_catalog.py` — hoist into one shared home (guarded by the
  existing import-time `_assert_catalog_defaults_resolve`).
- The `policy_resolver.py` module docstring names `library_workflow_catalog`/`model_profiles`
  as the source, but the **production** resolver is fed `governed_workflow_catalog()` via the
  container — correct the docstring.
- Panel `_semantic_check` (`features/panel/views/workflow_policy.py`) should mirror the
  doctor's explicit 3-map union (`contexts | default_harness_overlay | step_harness_overlay`)
  instead of relying on the empty-steps parse side effect.

## Acceptance shape (for grill)

- An operator can register a PI profile in `.dadaia/states/workflow_model_profiles.local.json`
  and have it selectable by a governed step; the local store carries no API key and is never
  projected into `public/`; `dadaia public doctor` stays `[ok] public-privacy`.
- A non-`default` context key in `workflow_model_policy.json` with `extends` resolves a
  step's profile through the inheritance chain; an unresolvable ref or a broken `extends`
  parent fails closed with an actionable error; cycles are rejected.
- `WMP-*` governance doctor + panel `_semantic_check` agree on the resolved overlay map
  (no parse-side-effect-only coverage); `mypy --strict`, import-linter, and the full suite
  green.
