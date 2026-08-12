# PLAN — Release v0.3.0 — Demolition of the dadaia-workflows engine + de-flag of public_assets

> **Status:** Aprovado

**Release ID:** v0.3.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.3.0/SPEC.md`
**Normative map:** `.dadaia/tmp/claude-code/20260806/demolition-map-v030.md`

## 1. Planning problem

A ~52,800-LOC removal cannot be done as one commit and cannot be done bottom-up. Deleting
`features/lifecycle/` first leaves ~20 import sites broken and the suite uncollectable —
no intermediate state is verifiable, and a mistake is indistinguishable from a cascade.

The plan therefore runs **consumers first, engine last**: every lane ends with an
importable package and a collectable suite. The engine is only deleted once nothing
imports it.

## 2. Execution lanes

### Lane A — Sever the consumers (engine still present, tree green)

Cut the edges from the outside in, one surface per commit:

1. **CLI edge** — drop the `lifecycle` import + `add_typer` in `cli/main.py`; delete
   `cli/commands/lifecycle.py`; delete the 6 workflow verbs in `cli/commands/reports.py`
   (L731–911, keep L1–730); drop the `check_ai_surface_ritual` and
   `check_workflow_policy_layer2_residue` calls in `cli/commands/public.py`; delete
   `features/ai_surface/**` and its tests.
2. **Panel edge** — delete `views/workflows.py`, `views/workflow_policy.py` and their
   CSS/JS; strip the tab/section/asset entries in `views/index.py` and `views/static.py`;
   drop the workflow keys in `views/api_agents.py`; drop `WorkflowProvider`, the
   `workflows_service` param/attr, `list_dadaia_workflows` and `_workflows_svc` in
   `features/panel/service.py`; delete the workflow/lifecycle routes in
   `features/panel/handler.py` (keep `api_agent_model_templates` + telemetry). Delete the
   panel workflow tests and e2e specs in the same commit. The container's single
   panel-wiring edge — the `workflows_service=build_workflow_catalog_service(...)` kwarg
   (L484) and that builder (L458) — travels **with** the `PanelService` signature change,
   in this commit: splitting a constructor from its sole call site across a task boundary
   breaks `PanelService` construction.
3. **Contract edge** — `features/capabilities/service.py` drops the `workflows` key, the
   workflow capability strings and the two `certification` workflow booleans;
   `cli/commands/capabilities.py` drops the `payload["workflows"]` render;
   `features/certification/service.py` drops the 8 `workflow-*` checks.
   Mint `public/schemas/dadaia-capabilities-v2.schema.json`, delete v1, repoint the
   validator and `tests/contract/cli/test_cli_capabilities.py`.

After Lane A: `features/lifecycle/` and `features/workflows/` are imported by nobody but
`container.py` and their own tests.

### Lane B — Delete the engine

4. **Container** — remove all remaining lifecycle/workflow builders (~1,400 of 2,300
   lines): `build_agent_runtime`, every `build_lifecycle_*` and `build_workflow_*`,
   `build_fragment_loader`, `build_local_model_profile_store`, the release/backlog/audit
   workflow factories and the panel workflow route keys. **Keep**
   `build_backlog_removal_lifecycle`, the telemetry `ADAPTER_REGISTRY`,
   `api_agent_model_templates` and `SlopPolicy`. **Every container-pinning test dies in
   this same commit** — `tests/unit/test_container.py`,
   `tests/unit/features/panel/test_build_panel_views.py`,
   `tests/unit/test_build_agent_runtime.py`,
   `tests/unit/test_container_retention_providers.py`, and the
   `test_no_silent_optional_wiring` update (pulled forward from Lane D). A pin that
   outlives its builder leaves the suite red across a task boundary, which is
   indistinguishable from a demolition mistake.
5. **Engine + adapters** — delete `features/lifecycle/**`, `features/workflows/**`, the 4
   core models, the 6 core protocols, the 10 infrastructure runtime/store modules, and
   `core/harness_models.py` if consumer-free (`core/harness_registry.py` survives; drop
   `L2_WORKER_HARNESSES` only if consumer-free).
6. **Tests** — delete the entire engine test surface (map §2) in the same commit as the
   code it covers. No `skip`/`xfail` placeholders are left behind.

### Lane C — Assets, law and prose

7. **Assets** — delete `public/lifecycle_fragments/**`, `public/personas/**` and the 3
   workflow schemas; remove the `lifecycle_fragments` and `personas` projection dirs from
   `infrastructure/public_assets_common.py`.
8. **Law** — rewrite `public/data/DADAIA.md` §1 (Arm A = agent-dispatched SDD flow; no
   engine, no `dadaia lifecycle`, no Layer-2 harness preference; Arm B unchanged) and the
   §9 panel row. Then `dadaia public stage` → `install --target all` → `doctor`, so the
   projections at the workspace root and in every harness dir follow. The projected law
   files are PROTECTED — they are never hand-edited.
9. **Prose sweep** — the remaining public assets, skills, agents, `hooks/ctx_inject.py`
   prose, academy knowledge_basis, `README.md`, `docs/`, the repo-scoped `AGENTS.md` and
   the consumer-specs test fixture. Driven by grep, not by a checklist.

### Lane D — Contracts and caps

10. `setup.cfg`: delete `lifecycle-no-workflows`; remove `ai_surface`/`lifecycle`/`workflows`
    from `features-no-cross-feature` `modules`; delete the ~12 now-unmatched ignore edges
    plus `cli.commands.lifecycle -> infrastructure.fake_runtime`. Lower the caps in
    `tests/contract/test_import_linter_ignore_cap.py` in the **same commit** (that file's
    own law). Update `test_module_size_ceiling`, `test_architecture_diagrams_current`,
    `test_bind_resolution_seam_dynamic_walk` (`test_no_silent_optional_wiring` was already
    updated in Lane B step 4, with the builders it pins).

### Lane E — De-flag `public_assets.py`

11. **`install()` IS the boundary translator** — the port stops here. Its public,
    port-conforming signature (`workspace_root`, `target`, `force`, `scope`, `only`) is
    **unchanged**, and the `PublicAssetManager` port plus the
    `features/workspace/service.py` and `features/public/service.py` call sites are **not
    touched by this release**. Everything below that line changes: `install()` resolves
    its arguments once into an immutable `InstallPlan` (resolved harness targets,
    guardrail target set, overwrite policy replacing `force`, step selection replacing
    `scope`/`only`, the loaded agent-model overlay, the resolved core models), then runs
    ordered steps and reconciles the ledger. Each step is a flag-free function taking the
    plan (or a slice of it); a step that is not selected is **absent from the list**,
    never guarded by an internal `if`. `_copy_file`, `_copy_tree`, `_write_generated`,
    `_install_codex_*`, `_project_installed_plugins` and the module-level `install_*`
    helpers lose their `force: bool` parameter in favour of the plan's policy value. Any
    other port-conforming public method (e.g. `install_plugin`) keeps its signature for
    the same reason `install()` does.

    Ordering constraint that must survive the refactor: `install_dadaia_md` runs **after**
    the per-harness projections (copy_tree prunes orphans), and
    `_project_installed_plugins` runs **after** the core projection (pack precedence).
    These are behavioural invariants, not incidental ordering.

### Lane F — Quality gates, residue grep, metrics

12. Full suite, ruff, mypy `--strict`, `lint-imports --no-cache`; `dadaia doctor`,
    `specs doctor`, `public doctor`, `certify --json`; the acceptance grep; the
    LOC/test-function removal report; the `CHANGELOG.md` entry.

## 3. Risk points

**Container is a 60% removal.** The highest-risk edit in the release. Mitigation: it lands
*after* Lane A, when the only remaining importers are the engine's own modules, and
*before* Lane B step 5, so a broken survivor surfaces as an import error on a tree that
still has the engine to compare against. Every retained builder is checked against the
map §6 MUST-SURVIVE list by name.

**Capabilities schema consumers.** `workflows` is `required` under
`additionalProperties: false` — removing it invalidates every v1 payload. The v2 mint is
announced in `CHANGELOG.md` and `CONSUMER_VALIDATION_RECIPE.md`, and the consumer
validation agent re-runs against v2 before ship. `dadaia-certification-v1` is untouched.

**Goldens regen discipline.** `UPDATE_INSTALL_GOLDENS` is authorized **only** for
projections whose source asset FR1 deleted or FR4 rewrote. Lane E is byte-neutral by
construction: if a golden moves during the de-flag refactor, that is a behaviour change
and the refactor is wrong. Every regenerated golden diff is explained line-by-line in the
commit message.

**Over-reach.** "workflow" appears in surviving names (`features/backlog/removal_lifecycle.py`,
`core/models/hygiene.py`, telemetry). Deletion is driven by the map's explicit file list,
never by a name grep. The grep is the *residue* authority (FR4), not the deletion
authority.

**Prose sweep is larger than the map.** Grep found engine references in `README.md` (16),
academy knowledge_basis, `docs/`, the repo-scoped `AGENTS.md` and a test fixture — none in
the map. Lane C step 9 is grep-driven and iterates until the acceptance grep is clean.

**History stays.** `specs/bugs/bugs.jsonl` (113 hits), `specs/bugs/_archive/`, and
`specs/_archive/**` are excluded from every sweep. Append-only law outranks tidiness.

## 4. Validation strategy

- Per-lane: `pytest -p no:cacheprovider -q` on the touched trees; the package must import
  and the suite must collect at the end of every task.
- After Lane D: `lint-imports --config setup.cfg --no-cache` with zero unmatched ignores.
- After Lane E: install goldens + `public stage/install/doctor` on a scratch workspace.
- Lane F: the full acceptance list in SPEC §7, then the standard ship gates (security
  review handoff, push, PR, CI green, consumer validation round).

## 5. Expected end state (to be confirmed by the Lane F report)

| Measure | Before (`main @ ec301ae3`) | Expected after |
|---|---|---|
| Production LOC | 70,208 | ≈43,400 (−38%) |
| Test LOC | 92,272 | ≈66,300 (−28%) |
| Tests passed | 2,973 | ≈2,480 |
| Test functions removed | — | ≈493 |
| import-linter ignore edges | 36 | ≈23 |
