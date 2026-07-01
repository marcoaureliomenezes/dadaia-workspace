---
name: v0145-t4506-kimi-raw-model-cannot-persist-via-profile-overlay
status: Resolved
severity: MEDIUM
reported: 2026-07-01
resolved: 2026-07-01
surface: panel workflow model-governance editor (workflow_policy.py / workflow_model_policy overlay / policy_resolver)
session_id: null
---

**RESOLUTION (2026-07-01, route (b) — operator directive):** Fixed by adding ONE
governed built-in pi profile `pi-openrouter-kimi-high` (label "OpenRouter — kimi-2.7
(high)", model_id `kimi-2.7`, effort `high`) to `features/lifecycle/model_profiles.py`
`_BUILT_IN`. It passes the no-second-table guard because `kimi-2.7:high` is already a pi
catalog option (`options_for('pi')`) and its id is in `known_layer2_model_ids()` (v0.1.44).
The per-step pi picker now offers it, and selecting+saving persists the PROFILE ID
`pi-openrouter-kimi-high` through `PUT /api/workflow-model-policy`; the resolver resolves
that profile to the discrete pi option `kimi-2.7:high` (model `kimi-2.7` at effort `high`).
No change to `core/harness_models.py` allowed-set logic, the overlay store, or the
resolver — kimi is now selectable end-to-end via governance, exactly as intended.
Round-trip proven by `test_kimi_profile_round_trips_through_put_get_and_resolver`
(tests/unit/features/panel/test_panel_policy_mutation.py) +
`test_openrouter_kimi_profile_is_a_governed_pi_option`
(tests/unit/features/lifecycle/test_model_profiles.py).
---

**Symptom:** Task T-45-06 (release v0.1.45) requires the per-step pi model picker to
persist the OpenRouter option with the **exact effort-suffixed value `kimi-2.7:high`**
through `PUT /api/workflow-model-policy`, asserting "the round-trip value is exactly
`kimi-2.7:high`". This is not achievable with the shipped model-governance architecture,
which is **profile-based**, not raw-model-based.

**Repro:**
```
.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.features.lifecycle.policy_resolver import (
    WorkflowExecutionPolicyResolver, StepOverride)
r = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
r.resolve('implementation', cli_overrides=(StepOverride(step='implement', profile_id='kimi-2.7:high'),))
"
# -> PolicyResolutionError: unknown model profile 'kimi-2.7:high'; valid profiles:
#    codex-implementation-standard, codex-review-deep, pi-implementation-standard,
#    pi-reasoning-high, pi-reasoning-low
```

**Root cause (architecture mismatch, arch finding #3 vs the shipped overlay):**
- The panel editor + overlay store + resolver persist a **profile id** per step
  (`WorkflowModelPolicyOverlay.contexts[ctx].workflows[wf].steps[step] = <profile_id>`),
  validated against the built-in `model_profiles` registry.
- `model_profiles` has **no kimi profile** — v0.1.44 added `kimi-2.7` to the *allowed
  concrete-model set* (`harness_models.LAYER2_EXTRA_MODEL_IDS` / `known_layer2_model_ids()`)
  but did **not** add a governed profile that resolves to it.
- Therefore a step override of the raw model id `kimi-2.7:high` is rejected by the
  resolver, and `validate`-before-`save` blocks the PUT. Even if a kimi profile were
  added, the **persisted** overlay value would be the *profile id*, never the literal
  `kimi-2.7:high`, so the T-45-06 round-trip assertion (persisted value ==
  `kimi-2.7:high`) still could not hold.

**Expected (per T-45-06 / SPEC AC-3):** selecting the OpenRouter kimi option persists
`kimi-2.7:high` verbatim and the resolver honours it — with **no changes to
`core/harness_models.py` allowed-set logic, the overlay store, or the resolver** (T-45-06
constraint) and **no new model-governance semantics** (SPEC §4). These constraints are
mutually exclusive with the requirement: a raw-model overlay would require changing the
store + resolver; a profile route would require new governance data and still would not
persist the literal `kimi-2.7:high`.

**Decision required (route to product-engineer via project-manager):** either
(a) relax the T-45-06 constraint to permit a raw-model step override in the overlay
    (store + resolver change) so `kimi-2.7:high` persists verbatim; or
(b) add a governed `pi` profile resolving to `kimi-2.7:high` and restate the round-trip
    assertion in terms of the *resolved concrete model* (persisted value = profile id);
    or
(c) scope T-45-06 to a **display-only** surface (the panel lists the full allowed pi set
    incl. the labelled `kimi-2.7:high` option, with persistence deferred to a governance
    release).

**Interim (this session):** implemented the honest, in-scope panel-presentation portion —
the workflow model-governance editor now *surfaces* the full per-harness allowed concrete
model set (`harness_models.model_choices(...)`), with the OpenRouter option labelled
"OpenRouter — kimi-2.7 (high)" and its value carried un-stripped as `kimi-2.7:high`
(display/reference). Actual per-step selection+persistence of a raw model is left to the
decision above. T-45-06 kept `[-]` pending that decision.

**Notes:** environment = repos/dadaia-workspace @ feature/v0.1.45; profile-based
overlay is `infrastructure/json_workflow_model_policy_store.py` + resolver
`features/lifecycle/policy_resolver.py`; profile registry
`features/lifecycle/model_profiles.py`.
