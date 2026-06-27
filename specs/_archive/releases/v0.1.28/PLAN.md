# PLAN — Release: v0.1.28 — Workflow Model Governance + Panel Control Plane

**Status:** Aprovado
**Release ID:** v0.1.28
**Owner:** product-engineer

> Strategy: extend existing seams (SPEC §3). Four waves A→B→C→D, each its own green
> checkpoint. Composition wired through `container.py` only — no ad-hoc construction in
> view/CLI modules.

---

## 1. Layering and the single resolver seam

```
core/models/workflow_execution.py   (pure DTOs: ResolvedModelConfig, WorkflowPolicySnapshot)
core/models/lifecycle.py            (AgentRunRequest gains resolved model; LifecycleRun gains snapshot)
        │
features/lifecycle/model_profiles.py        (built-in profile registry; resolves to harness_models option)
features/lifecycle/policy_resolver.py        (WorkflowExecutionPolicyResolver — THE shared seam)
features/workflows/dadaia_catalog.py         (governed catalog: default harness + default profile per step)
        │
infrastructure/json_workflow_model_policy_store.py   (atomic overlay store + last-good backup)
        │
container.py   (build_workflow_model_profile_registry, build_workflow_model_policy_store,
                build_workflow_policy_resolver; thread resolver into pipeline/phase/panel)
        │
features/panel/* + cli/commands/lifecycle.py   (consume the resolver; never parse policy JSON themselves)
```

**Precedence (resolver):** `CLI run override > context overlay > default overlay > library
default`. Only the `default` context overlay is honored this release (D-2); a non-`default`
context key is inert. Resolution is **resolve-once-before-first-step**; the snapshot is
written to the `LifecycleRun` before the first worker call (LAW 7). Adapters never parse
overlay JSON — they receive a resolved `AgentRunRequest`.

**Missing ≠ invalid:** absent overlay file ⇒ library defaults (LAW 4). A present-but-invalid
overlay ⇒ resolver/runner fails before the first model call with an actionable error; the
`.last-good.json` backup is left intact (LAW 5).

## 2. Wave A — model-policy foundation

Data models (NEW `core/models/workflow_execution.py`):
- `WorkflowModelProfile` — `id, harness, label, model_id, effort, purpose, availability,
  source="built-in", deprecated, replacement`. Resolves to a `harness_models.HarnessModelOption`.
- `ResolvedModelConfig` — `profile_id, harness, model, reasoning, source`.
- `WorkflowPolicySnapshot` — `workflow_id, policy_id, resolved_at, source_precedence[],
  steps{step → {harness, model_profile, model, reasoning, fragments[], output_schema}}`.

Profiles (NEW `features/lifecycle/model_profiles.py`):
- Built-in tuple of `WorkflowModelProfile` for Codex (e.g. `codex-implementation-standard`,
  `codex-review-deep`) + recommended PI aliases (e.g. `pi-implementation-standard`,
  `pi-reasoning-high`). Import-time assert ties each profile `model_id` to
  `harness_models`/registry (mirror `_assert_ids_known`) — no second drifting table.
- Accessors: `list_profiles()`, `profiles_for(harness)`, `resolve(profile_id) ->
  WorkflowModelProfile`, `to_option(profile) -> HarnessModelOption`.

Overlay store (NEW `infrastructure/json_workflow_model_policy_store.py`):
- Reads/writes `.dadaia/states/workflow_model_policy.json` (schema
  `workflow-model-policy-v1`). Reuses the `JsonLifecycleRunStore` atomic temp+rename pattern
  (`tempfile.mkstemp` in target dir → `os.replace`). `load()` returns `None` on missing
  (defaults); raises a typed `WorkflowModelPolicyStoreError` on invalid JSON / unknown
  top-level fields. `save()` writes `.last-good.json` from the prior valid file first.

Resolver (NEW `features/lifecycle/policy_resolver.py`):
- `WorkflowExecutionPolicyResolver(catalog, profiles, overlay)` →
  `resolve(workflow_id, context, cli_overrides) -> WorkflowPolicySnapshot`. Validates every
  override against catalog step ids + profile ids + harness match; deprecated profile without
  explicit replacement path is a hard failure.

Core wiring (MODIFIED `core/models/lifecycle.py`):
- `AgentRunRequest` gains `resolved_model: ResolvedModelConfig | None` (keep `model_profile`
  for back-compat / observability); `to_dict`/`from_dict` updated.
- `LifecycleRun` gains `workflow_policy: WorkflowPolicySnapshot | None`; `to_dict`/`from_dict`
  + `prompt_composition()` updated; run-store `_SCHEMA_VERSION` left at `lifecycle-run-v1`
  with additive optional field (back-compat read of old records).

Pipeline + adapters:
- MODIFIED `features/lifecycle/pipeline.py` — build steps from the resolved snapshot instead
  of the hard-coded `_DEFAULT_STEP_MODEL` effort literal; thread the per-step
  `ResolvedModelConfig` into the scope/request; snapshot written to the run before step 1.
- MODIFIED `features/lifecycle/prompt_builder.py` — carry resolved model metadata into the
  request and the `InjectedContext`/snapshot.
- MODIFIED `features/lifecycle/phase_workflow.py` — accept/thread a resolved single-step
  config (the implementation-pipeline demo path, D-4).
- MODIFIED `infrastructure/codex_runtime.py` — prefer `request.resolved_model` over the
  registry tier-view fallback in `_model_and_effort`.
- MODIFIED `infrastructure/pi_runtime.py` — accept the per-request resolved PI model so
  `_command()` adds `--model <id>` from the request (not only adapter construction).
- MODIFIED `infrastructure/fake_runtime.py` — echo the resolved model config so tests assert
  policy resolution without a live provider.

CLI (MODIFIED `cli/commands/lifecycle.py`):
- `--step-model` resolves a **profile id** via the profile registry (D-3), not
  `harness_models.validate` on a raw `<id>:<effort>`; reject raw strings / unknown /
  mismatch / deprecated with actionable messages.
- Add `--show-policy` and resolved-policy in `--json` for the run verbs.
- Add `workflow policy show <workflow> --context --json` and `workflow profiles list
  --harness --json` inspection subcommands (under the existing `lifecycle`/`workflow` group).

Container (MODIFIED `container.py`):
- `build_workflow_model_profile_registry`, `build_workflow_model_policy_store`,
  `build_workflow_policy_resolver(workspace_root, context)`. Thread the resolver into
  `build_lifecycle_pipeline`, `build_lifecycle_phase_workflow`.

**Wave A acceptance:** AC-2, AC-3, AC-4, AC-6, AC-7, AC-8, AC-11, AC-12 + green checkpoint.

## 3. Wave B — Python workflow catalog as the governed source

- MODIFIED `features/workflows/dadaia_catalog.py` — extend `DadaiaWorkflowStepDTO` /
  `DadaiaWorkflowDTO` with `default_harness`, `default_profile` per supported harness, and
  the fragment ids already introspected. The catalog becomes the governed source the
  resolver and panel both read (one source — no second table).
- MODIFIED `features/workflows/service.py` — keep `*.workflow.md` `get_detail`/`list_summaries`
  as **reference/doc-only**; add a docstring + (optional) deprecation note that it is no
  longer the executable authority.
- Diagrams unchanged: continue to use `render_dag_svg` + `render_step_mermaid` from Python
  metadata.

**Wave B acceptance:** AC-15 + green checkpoint.

## 4. Wave C — panel model-governance UX + mutation API

Panel routes (MODIFIED `features/panel/handler.py`):
- Add to `_ROUTE_TABLE`: `GET /api/workflow-catalog`, `GET /api/workflow-catalog/<id>`,
  `GET /api/workflow-model-profiles`, `GET /api/workflow-model-policy`,
  `GET /api/lifecycle-runs`.
- Add **PUT** support (`do_PUT`) + a real `do_POST` body path:
  `PUT /api/workflow-model-policy`, `POST /api/workflow-model-policy/validate`. Read the
  request body with content-length, reject non-`application/json` content type (415),
  reject oversized payload (413), return structured field-path validation errors (400).
  Reuse the Host-header allowlist guard already on every method (no bearer — LAW 5).
- A `_DELETE`-style ordered table for the new mutation routes if needed; route registration
  is asserted by a handler-classification test.

Panel service + views (MODIFIED):
- `features/panel/service.py` — methods for catalog / profiles / policy read / validate /
  write / run-snapshot, all delegating to the container-wired resolver + overlay store
  (the service never parses policy JSON itself beyond the store API).
- `features/panel/views/api.py` (+ `container.build_panel_views`) — new render callables:
  `render_api_workflow_catalog[_detail]`, `render_api_workflow_model_profiles`,
  `render_api_workflow_model_policy` (GET), the PUT/validate handlers, and
  `render_api_lifecycle_runs`.
- `features/panel/views/index.py` — promote **Workflows** to a first-class top-level nav
  area; keep Agents + Kanban available (D-5) — do not delete the Ops subtab.
- `features/panel/views/workflows.py` + `views/assets/js/workflows.js` +
  `views/assets/css/*.css` — detail view (diagram + step matrix Step|Role|Harness|Effective
  profile|Concrete model|Fragments|Gate), default-vs-effective diff, per-step profile
  dropdown filtered by harness, reset-to-default, validate-before-save, save via the mutation
  API, and the run-snapshot evidence panel.

**Wave C acceptance:** AC-1, AC-5, AC-9, AC-13 + panel E2E green checkpoint.

## 5. Wave D — fragment inspector + doctor

- MODIFIED `features/panel/views/workflows.py` + `workflows.js` — per-step read-only
  fragment inspector (ids + resolved body via `FragmentLoader`), dynamic-context selectors,
  output schema.
- Doctor (NEW check module or extend existing, e.g. `features/lifecycle/policy_doctor.py`
  surfaced via `dadaia lifecycle doctor` and/or `dadaia public doctor`):
  - every workflow id unique; every step id unique inside a workflow;
  - every model step has a default profile per supported harness (or explicit unsupported);
  - every fragment id resolves; every output schema id resolves;
  - every policy override references an existing workflow/step/profile; profile harness
    matches the resolved step harness;
  - no product policy/profile exposes `claude`/`opencode` as a Layer-2 worker choice;
  - invalid policy files fail with actionable messages and never crash the panel.

**Wave D acceptance:** AC-10, AC-14 + green checkpoint.

## 6. Module list — NEW vs MODIFIED

NEW:
- `dadaia_workspace/core/models/workflow_execution.py`
- `dadaia_workspace/features/lifecycle/model_profiles.py`
- `dadaia_workspace/features/lifecycle/policy_resolver.py`
- `dadaia_workspace/infrastructure/json_workflow_model_policy_store.py`
- `dadaia_workspace/features/lifecycle/policy_doctor.py` (or doctor extension)
- `dadaia_workspace/public/data/schemas/workflow-model-policy-v1.schema.json` (overlay schema)
- tests: `tests/unit/features/lifecycle/` (profiles, resolver, precedence, snapshot),
  `tests/unit/infrastructure/` (store resilience, Codex/PI model config),
  `tests/unit/features/panel/` (routes, validation, service), `tests/integration/cli/`
  (profile-id precedence + `--json`), `tests/e2e/features/` (panel editor — C/D).

MODIFIED:
- `core/models/lifecycle.py` (AgentRunRequest, LifecycleRun)
- `features/lifecycle/pipeline.py`, `phase_workflow.py`, `prompt_builder.py`
- `infrastructure/codex_runtime.py`, `pi_runtime.py`, `fake_runtime.py`,
  `json_lifecycle_run_store.py` (additive snapshot field read)
- `features/workflows/dadaia_catalog.py`, `features/workflows/service.py`
- `features/panel/handler.py`, `service.py`, `views/index.py`, `views/api.py`,
  `views/workflows.py`, `views/assets/js/workflows.js`, `views/assets/css/*.css`
- `cli/commands/lifecycle.py`
- `container.py`

## 7. Validation plan

- Per wave: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`
  (`-p no:cacheprovider`); panel E2E for waves C and D.
- D-4 end-to-end: `dadaia lifecycle pipeline --harness fake` asserts the persisted
  `workflow_policy` snapshot (profile id, concrete model, reasoning, fragments per step) and
  that a mutated overlay after start does not affect the in-flight run.
- Projection smoke for any `public/` asset edit (overlay schema): `dadaia public stage &&
  dadaia public install --target all && dadaia public doctor` (run by devops/operator).
- Never push red: pre-push CI gate + security APPROVE per push-cycle (release-governance).

## 8. Technical risks

- `LifecycleRun` schema evolution must stay back-compat read (old records lack
  `workflow_policy`) — additive optional field, no `_SCHEMA_VERSION` bump that rejects v1.
- `pi_runtime._command()` currently builds args without the request; threading the
  per-request model requires passing the request into `_command` (unit test asserts
  `--model <id>` reaches the command).
- Panel handler has no PUT and a near-empty POST — adding body-reading mutation must keep the
  Host-guard-first invariant and the no-bearer posture; oversized/non-JSON guards are
  mandatory, asserted by tests.
- Catalog as governed source must not reintroduce `*.workflow.md` as authority (Wave B
  demotes it explicitly).
