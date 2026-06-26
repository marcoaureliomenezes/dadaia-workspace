# TASKS — Release: v0.1.28 — Workflow Model Governance + Panel Control Plane

**Status:** Aprovado
**Release ID:** v0.1.28
**Owner:** product-engineer (authoring) → software-engineer (implementation)

> Marker contract: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner
> unless disjoint write sets are declared. Each wave ends at a green checkpoint; do not start
> the next wave's tasks before the prior wave's checkpoint is `[x]`.
> Tests run with `-p no:cacheprovider`; mypy `--strict`; ruff `--no-cache`.

---

## Wave A — model-policy foundation

### [x] T-28-A-01 — Resolved-policy core DTOs
Goal: add the pure DTOs the governance layer threads through every layer.
Write set: `dadaia_workspace/core/models/workflow_execution.py` (NEW);
`tests/unit/core/models/test_workflow_execution.py` (NEW).
Acceptance: `ResolvedModelConfig`, `WorkflowModelProfile`, `WorkflowPolicySnapshot` frozen
dataclasses with `to_dict`/`from_dict` round-trip; zero I/O; import-linter clean (`core` no
OS primitives).

### [x] T-28-A-02 — Built-in model-profile registry
Goal: named profiles (Codex + recommended PI aliases) resolving to `harness_models` options.
Write set: `dadaia_workspace/features/lifecycle/model_profiles.py` (NEW);
`tests/unit/features/lifecycle/test_model_profiles.py` (NEW).
Acceptance: built-in-only (D-2); import-time assert ties every profile `model_id` to the
registry (mirror `_assert_ids_known`); `resolve`, `profiles_for(harness)`, `to_option`;
no `claude-*` id; deprecated profiles carry a `replacement`.

### [x] T-28-A-03 — Overlay JSON store (atomic + last-good)
Goal: read/write `.dadaia/states/workflow_model_policy.json`, missing ≠ invalid.
Write set: `dadaia_workspace/infrastructure/json_workflow_model_policy_store.py` (NEW);
`dadaia_workspace/public/data/schemas/workflow-model-policy-v1.schema.json` (NEW);
`tests/unit/infrastructure/test_json_workflow_model_policy_store.py` (NEW).
Acceptance: atomic temp+rename (mkstemp in target dir → `os.replace`); `load()` returns
`None` on missing; raises typed error on invalid JSON / unknown top-level field; `save()`
writes `.last-good.json` from the prior valid file; only `default` context honored (D-2).

### [x] T-28-A-04 — WorkflowExecutionPolicyResolver (precedence)
Goal: the single shared resolver consumed by CLI and panel.
Write set: `dadaia_workspace/features/lifecycle/policy_resolver.py` (NEW);
`tests/unit/features/lifecycle/test_policy_resolver.py` (NEW).
Acceptance: precedence CLI > context overlay > default overlay > library default; validates
overrides vs catalog step ids + profile ids + harness match; deprecated-without-replacement
fails; returns a `WorkflowPolicySnapshot`; only `default` context honored (D-2).

### [x] T-28-A-05 — AgentRunRequest + LifecycleRun carry resolved policy
Goal: thread resolved model into the request; persist the snapshot on the run.
Write set: `dadaia_workspace/core/models/lifecycle.py`;
`dadaia_workspace/infrastructure/json_lifecycle_run_store.py`;
`tests/unit/core/models/test_lifecycle_models.py`;
`tests/unit/infrastructure/test_json_lifecycle_run_store.py`.
Acceptance: `AgentRunRequest.resolved_model` + `LifecycleRun.workflow_policy` additive
optional; `to_dict`/`from_dict` + `prompt_composition()` updated; old v1 records (no
snapshot) still load (back-compat); no `_SCHEMA_VERSION` change that rejects v1.

### [x] T-28-A-06 — Adapters consume resolved model config
Goal: Codex/PI/fake honor the per-request resolved model.
Write set: `dadaia_workspace/infrastructure/codex_runtime.py`;
`dadaia_workspace/infrastructure/pi_runtime.py`;
`dadaia_workspace/infrastructure/fake_runtime.py`;
`tests/unit/infrastructure/test_codex_runtime.py`;
`tests/unit/infrastructure/test_pi_runtime.py`;
`tests/unit/infrastructure/test_fake_runtime.py`.
Acceptance: Codex prefers `request.resolved_model` in `_model_and_effort`; PI `_command()`
adds `--model <id>` from the per-request resolved model; fake echoes the resolved config;
AC-12 asserted.

### [x] T-28-A-07 — Pipeline + phase workflow + prompt builder use the resolver
Goal: build steps from the resolved snapshot; snapshot before step 1 (LAW 7).
Write set: `dadaia_workspace/features/lifecycle/pipeline.py`;
`dadaia_workspace/features/lifecycle/phase_workflow.py`;
`dadaia_workspace/features/lifecycle/prompt_builder.py`;
`tests/unit/features/lifecycle/test_pipeline.py`;
`tests/unit/features/lifecycle/test_phase_workflow.py`;
`tests/unit/features/lifecycle/test_prompt_builder.py`.
Acceptance: pipeline replaces the hard-coded `_DEFAULT_STEP_MODEL` effort literal with the
resolved per-step config; snapshot persisted to the run before the first worker call; an
overlay mutated after start does not change the in-flight run (AC-6).

### [x] T-28-A-08 — Container wiring for the governance layer
Goal: compose registry/store/resolver and thread the resolver into pipeline/phase builders.
Write set: `dadaia_workspace/container.py`;
`tests/unit/test_container.py`.
Acceptance: `build_workflow_model_profile_registry`, `build_workflow_model_policy_store`,
`build_workflow_policy_resolver(workspace_root, context)`; `build_lifecycle_pipeline` and
`build_lifecycle_phase_workflow` accept/use the resolver; no ad-hoc construction in CLI/views.

### [x] T-28-A-09 — CLI: profile-id `--step-model`, `--show-policy`, inspection verbs
Goal: D-3 (profile ids only) + scriptable inspection.
Write set: `dadaia_workspace/cli/commands/lifecycle.py`;
`tests/integration/cli/test_lifecycle_policy_cli.py` (NEW).
Acceptance: `--step-model <step>=<profile-id>` resolves through the profile registry; raw
`<id>:<effort>` / unknown / harness-mismatch / deprecated rejected with actionable message;
`--show-policy` + `--json` print the resolved policy; `workflow policy show` + `workflow
profiles list` read-only verbs (AC-3, AC-4).

### [x] T-28-A-10 — Wave A green checkpoint (D-4 end-to-end demo)
Goal: prove resolver + run snapshot end-to-end on the implementation pipeline.
Write set: `tests/integration/cli/test_pipeline_policy_e2e.py` (NEW) (+ fixtures under
`tests/` only).
Acceptance: `dadaia lifecycle pipeline --harness fake` (with overlay + CLI overrides) writes
a `workflow_policy` snapshot whose per-step profile/model/reasoning/fragments match the
resolved policy; invalid overlay blocks before the first step with last-good intact;
`ruff format --check`, `ruff check`, `mypy --strict`, `pytest` all green.

---

## Wave B — Python workflow catalog as governed source

### [x] T-28-B-01 — Catalog carries default harness + default profile per step
Goal: make `dadaia_catalog` the governed source the resolver + panel read.
Write set: `dadaia_workspace/features/workflows/dadaia_catalog.py`;
`tests/unit/features/workflows/test_dadaia_catalog.py`.
Acceptance: `DadaiaWorkflowStepDTO`/`DadaiaWorkflowDTO` expose `default_harness` +
`default_profile` per supported harness + fragment ids; resolver reads catalog defaults;
diagrams still from `render_dag_svg`/`render_step_mermaid`; one source (no second table).

### [x] T-28-B-02 — Demote `*.workflow.md` to reference/doc-only
Goal: stop treating Markdown workflows as the executable authority (AC-15).
Write set: `dadaia_workspace/features/workflows/service.py`;
`tests/unit/features/workflows/test_workflows_service.py`.
Acceptance: `get_detail`/`list_summaries` documented as reference-only; no executable
behavior reads them as authority; existing read path still functions for the legacy view.

### [x] T-28-B-03 — Wave B green checkpoint
Write set: none (verification only).
Acceptance: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` green; catalog is
the single governed workflow source.

---

## Wave C — panel model-governance UX + mutation API

### [x] T-28-C-01 — Panel GET routes: catalog, profiles, policy, runs
Goal: read endpoints for the control plane.
Write set: `dadaia_workspace/features/panel/handler.py`;
`dadaia_workspace/features/panel/service.py`;
`dadaia_workspace/features/panel/views/api.py`;
`dadaia_workspace/container.py` (build_panel_views entries);
`tests/unit/features/panel/test_handler_route_classification.py`;
`tests/unit/features/panel/test_panel_api_workflow_policy.py` (NEW).
Acceptance: `GET /api/workflow-catalog[/<id>]`, `GET /api/workflow-model-profiles`,
`GET /api/workflow-model-policy`, `GET /api/lifecycle-runs?workflow=&context=` registered +
served; Host-guard applies; no secrets exposed; route registration asserted.

### [x] T-28-C-02 — Panel mutation routes: PUT/validate policy
Goal: guarded writes (LAW 5) — handler currently has no PUT and a near-empty POST.
Write set: `dadaia_workspace/features/panel/handler.py`;
`dadaia_workspace/features/panel/service.py`;
`dadaia_workspace/features/panel/views/api.py`;
`tests/unit/features/panel/test_panel_policy_mutation.py` (NEW).
Acceptance: `PUT /api/workflow-model-policy` + `POST /api/workflow-model-policy/validate`
read the body via content-length, reject non-`application/json` (415), reject oversized (413),
validate before write, atomic write + `.last-good.json` backup, return structured field-path
errors (400); Host-guard-first invariant preserved; no bearer (AC-5).

### [x] T-28-C-03 — First-class Workflows nav + detail/step-matrix/editor
Goal: promote Workflows to top-level; build the editor UX (D-5).
Write set: `dadaia_workspace/features/panel/views/index.py`;
`dadaia_workspace/features/panel/views/workflows.py`;
`dadaia_workspace/features/panel/views/assets/js/workflows.js`;
`dadaia_workspace/features/panel/views/assets/css/*.css`;
`tests/unit/features/panel/test_workflows_view.py`.
Acceptance: Workflows is a first-class nav area; Agents + Kanban remain available (Ops subtab
not deleted); detail shows diagram + step matrix (Step|Role|Harness|Effective profile|
Concrete model|Fragments|Gate) + default-vs-effective diff + run-snapshot evidence; per-step
profile dropdown filtered by harness + reset + validate-before-save + save via mutation API;
CSP hashes updated for any new inline script (AC-9, AC-13).

### [x] T-28-C-04 — Wave C green checkpoint (panel E2E)
Write set: `tests/e2e/features/test_panel_workflow_policy_editor.py` (NEW) (+ tests only).
Acceptance: E2E proves save / reset / default-vs-effective / invalid-policy-banner;
`ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, panel E2E green.

---

## Wave D — fragment inspector + doctor

### [ ] T-28-D-01 — Read-only fragment inspector per step
Goal: surface fragment ids/body + dynamic inputs + output schema per model step (AC-14).
Write set: `dadaia_workspace/features/panel/views/workflows.py`;
`dadaia_workspace/features/panel/views/assets/js/workflows.js`;
`dadaia_workspace/features/panel/service.py`;
`tests/unit/features/panel/test_fragment_inspector.py` (NEW).
Acceptance: inspector renders each model step's fragment ids + resolved body (via
`FragmentLoader`), dynamic-context selectors, output schema; read-only (no fragment editing).

### [ ] T-28-D-02 — Doctor checks for the governance layer
Goal: keep the layer from rotting (AC-10).
Write set: `dadaia_workspace/features/lifecycle/policy_doctor.py` (NEW or doctor extension);
`dadaia_workspace/cli/commands/lifecycle.py` (doctor verb surface) and/or the public-doctor
seam; `tests/unit/features/lifecycle/test_policy_doctor.py` (NEW).
Acceptance: fails on invalid policy JSON, unknown profile, harness/profile mismatch, stale
workflow/step id, missing default profile per supported harness, unresolved fragment/output
schema, and any `claude`/`opencode` Layer-2 policy/profile residue; never crashes the panel.

### [ ] T-28-D-03 — Wave D green checkpoint
Write set: none (verification only).
Acceptance: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, panel E2E green;
all SPEC §6 acceptance criteria satisfied.

---

## Closure

### [ ] T-28-Z-01 — Release closure + memory atoms + ship
Goal: close v0.1.28 per `dadaia-release-closure`.
Write set: `specs/releases/v0.1.28/CLOSURE.md` (NEW);
`specs/memory/architecture.md`; `specs/memory/product/index.md`;
`specs/memory/product/<workflow-control-plane>.md`; `specs/memory/tech-stack.md`
(only as needed); `specs/releases/ACTIVE.md`.
Acceptance: ACTIVE.md phase = CLOSURE before memory writes; CLOSURE.md carries Summary,
Tasks-completed (with commit SHAs), Validations (triples), Drifts, Memory updates,
Dispositions sweep (the `workflow-model-governance-panel-control-plane` backlog item flipped
to `DELIVERED — v0.1.28` per the `**Consumes:**` ledger), Backlog returns (file the deferred
operator-profiles/context-overlays follow-up per SPEC §7), Archive decision MOVE;
`dadaia specs doctor` green; `git mv` to `_archive/releases/` requested via devops/operator;
ACTIVE.md repointed.
