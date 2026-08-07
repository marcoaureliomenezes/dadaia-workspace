# TASKS — Release v0.3.0 — Demolition of the dadaia-workflows engine + de-flag of public_assets

> **Status:** Aprovado

**Release ID:** v0.3.0
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.3.0/PLAN.md`
**Normative map:** `.dadaia/tmp/claude-code/20260806/demolition-map-v030.md`

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **Consumers first, engine last.** Every task ends with an importable package and a
  collectable suite. If a task cannot end green, it is mis-scoped — stop and report.
- **The map §6 MUST-SURVIVE list is binding.** Deletion is driven by the map's explicit
  file list, never by grepping the word "workflow".
- **No `skip`/`xfail` placeholders** in place of deleted tests. Delete the file.
- **History is never rewritten**: `specs/bugs/**` and `specs/_archive/**` are excluded from
  every sweep.
- Suite command from inside the repo:
  `../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q`

---

- [x] **T-30-01 — Sever the CLI edge; delete `cli/commands/lifecycle.py` and `features/ai_surface/`**

**Owner role:** software-engineer

**Preconditions:** SPEC/PLAN `Aprovado`.

**Write set:**

- `dadaia_workspace/cli/main.py` (drop the `lifecycle` import L17 + `add_typer` L92)
- `dadaia_workspace/cli/commands/lifecycle.py` (delete)
- `dadaia_workspace/cli/commands/reports.py` (delete L731–911: `workflow_doctor`, `handoffs_doctor`, `hygiene_status`, `status`, `profiles`, `hygiene_clean`; keep L1–730)
- `dadaia_workspace/cli/commands/public.py` (drop `check_ai_surface_ritual` import+call and the `check_workflow_policy_layer2_residue` call)
- `dadaia_workspace/features/ai_surface/**` (delete)
- `tests/unit/features/ai_surface/**`, `tests/unit/cli/commands/test_lifecycle_harness_map.py`, `tests/integration/cli/test_reports_workflow_hygiene_cli.py` (delete)

**Description:** Cut the CLI's coupling to the engine. `dadaia --help` must no longer list
a `lifecycle` verb group and `dadaia reports --help` must list only the surviving verbs.
`features/ai_surface` is engine-rationale-only with `cli/commands/public.py` as its sole
consumer — it dies with the edge.

**Done criterion:** package imports; `dadaia --help` and `dadaia reports --help` clean;
suite collects.

---

- [x] **T-30-02 — Sever the panel edge; delete the Workflows and Model-policy tabs**

**Owner role:** software-engineer

**Preconditions:** T-30-01 `[x]`.

**Write set:**

- `dadaia_workspace/features/panel/views/{workflows.py,workflow_policy.py}` (delete)
- `dadaia_workspace/features/panel/views/assets/css/{workflows.py,workflow_policy.py}`, `views/assets/js/workflow_policy.js` (delete)
- `dadaia_workspace/features/panel/views/{index.py,static.py,api_agents.py}` (sever)
- `dadaia_workspace/features/panel/{service.py,handler.py}` (drop `WorkflowProvider`, `workflows_service`, `list_dadaia_workflows`, `_workflows_svc`, and the workflow/lifecycle GET/PUT/POST routes)
- `dadaia_workspace/container.py` — **the single panel-wiring sever**: the `workflows_service=build_workflow_catalog_service(workspace_root)` kwarg (L484) **and** the `build_workflow_catalog_service` builder it calls (L458). Everything else in the container is T-30-04.
- `tests/unit/features/panel/{test_fragment_inspector.py,test_panel_api_workflow_policy.py,test_panel_policy_mutation.py,test_workflows_view.py,test_service_di_workflows.py}` (delete); `test_api_golden.py`, `test_api_agents.py` (sever)
- `tests/integration/panel/test_workflow_policy_routes_e2e.py`, `tests/e2e/panel/{workflows-tab.spec.ts,workflow-policy-editor.spec.ts,workflow-policy-harness-toggle.spec.ts}` (delete); `tests/e2e/features/test_panel.py` (sever)

**Description:** The panel drops to 5 tabs. `api_agent_model_templates` and all telemetry
/ Sessions handling **stay** — they are not engine surface.

The container kwarg travels **with** the `PanelService` signature change, in this commit:
severing the constructor in one task and its sole call site in another leaves
`PanelService` construction broken across the task boundary. If
`tests/unit/test_container.py` or `tests/unit/features/panel/test_build_panel_views.py`
assert on the removed kwarg, sever **that assertion** here; the rest of those files dies
in T-30-04 with the builders they pin.

**Done criterion:** panel serves with no dead route, no 404 asset, no orphan tab link;
`PanelService` constructs; panel suites green.

---

- [-] **T-30-03 — Sever certification + capabilities; mint `dadaia-capabilities-v2`**

**Owner role:** software-engineer

**Preconditions:** T-30-02 `[x]`.

**Write set:**

- `dadaia_workspace/features/capabilities/service.py` (remove the `workflows` key L61–74, the workflow capability strings L84–85, and `certification.deterministic_fake_workflows` / `live_harness_canaries_required_for_release`)
- `dadaia_workspace/cli/commands/capabilities.py` (L40 `payload["workflows"]` render)
- `dadaia_workspace/features/certification/service.py` (delete the 8 `workflow-*` checks, L260–420)
- `dadaia_workspace/public/schemas/dadaia-capabilities-v2.schema.json` (new), `dadaia-capabilities-v1.schema.json` (delete)
- `tests/contract/cli/test_cli_capabilities.py`, capabilities/certification unit tests

**Description:** `workflows` is `required` under `additionalProperties: false`, so removal
is a breaking contract change — mint v2 (`$id` and `schema_version` const
`dadaia-capabilities-v2`) rather than mutating v1 in place. `dadaia-certification-v1` is
unchanged (the check list is data). Keep `context-bind-heartbeat`,
`context-specs-doctor` and `handoff_validation`.

**Done criterion:** `dadaia capabilities --json` validates against v2; `dadaia certify
--json` green with the reduced check list.

---

- [ ] **T-30-04 — Sever `container.py` (~1,400 of 2,300 lines)**

**Owner role:** software-engineer

**Preconditions:** T-30-03 `[x]`. **This is the highest-risk task of the release.**

**Write set:**

- `dadaia_workspace/container.py`
- `tests/unit/test_container.py`, `tests/unit/features/panel/test_build_panel_views.py` (sever the workflow-builder pins; delete only if the file pins nothing else)
- `tests/unit/test_build_agent_runtime.py`, `tests/unit/test_container_retention_providers.py` (delete)
- `tests/contract/test_no_silent_optional_wiring.py` (update)

**Description:** Remove every lifecycle/workflow builder: `build_agent_runtime`, all
`build_lifecycle_*` and `build_workflow_*`, `build_fragment_loader`,
`build_local_model_profile_store`, the release/backlog/audit workflow factories, and the
panel workflow route keys (`build_workflow_catalog_service` already died with the panel
kwarg in T-30-02). **Keep** `build_backlog_removal_lifecycle`, the telemetry
`ADAPTER_REGISTRY`, `api_agent_model_templates` and `SlopPolicy`. Verify each retained
builder against the map §6 MUST-SURVIVE list by name before committing.

**A container-pinning test dies in the same commit as the builder it pins** — deferring
them leaves the suite red across a task boundary, which is indistinguishable from a
demolition mistake. `test_no_silent_optional_wiring` is therefore updated **here**, not in
T-30-09, and is updated — never disabled.

**Done criterion:** package imports; suite collects **and passes**;
`test_no_silent_optional_wiring` green against the reduced builder set.

---

- [ ] **T-30-05 — Delete the engine and its adapters, models, protocols and tests**

**Owner role:** software-engineer

**Preconditions:** T-30-04 `[x]` (nothing outside the engine imports the engine).

**Write set:**

- `dadaia_workspace/features/lifecycle/**`, `dadaia_workspace/features/workflows/**` (delete)
- `dadaia_workspace/core/models/{lifecycle,workflow_execution,workflow_handoff}.py`, `core/scope_match.py` (delete)
- `dadaia_workspace/core/protocols/{agent_runtime,lifecycle_run_store,runtime_files,workflow_model_policy_store,workflow_provider,local_model_profile_store}.py` (delete)
- `dadaia_workspace/infrastructure/{codex_runtime,pi_runtime,claude_sdk_runtime,fake_runtime,headless_adapter_base,json_lifecycle_run_store,json_workflow_model_policy_store,runtime_files,git_evidence,json_local_model_profile_store}.py` (delete)
- `dadaia_workspace/core/harness_models.py` (delete if consumer-free); `core/harness_registry.py` (drop `L2_WORKER_HARNESSES` only if consumer-free); `core/models/hygiene.py` (delete `HygieneCounters`/`HygieneSnapshot`; **keep** `SlopPolicy`/`HygieneZone`)
- `dadaia_workspace/infrastructure/json_agent_model_policy_store.py` — **sever the docstring only** (L6 cross-references `json_workflow_model_policy_store.JsonWorkflowModelPolicyStore`, which this task deletes; the module itself survives)
- Tests: the whole of demolition map §2 — `tests/unit/features/{lifecycle,workflows}/**`, the listed `tests/unit/infrastructure/` and `tests/unit/core/` files (**keep** `test_telemetry_lock_*`), the listed `tests/unit/` root files **except** `test_build_agent_runtime.py` and `test_container_retention_providers.py` (both already deleted in T-30-04 with the builders they pin), all `tests/integration/cli/test_lifecycle_*` / `test_pipeline_*` / the listed integration files, `tests/integration/{codex_live,pi_live}/**`, `tests/performance/test_lifecycle_hygiene_scan.py`, `tests/e2e/features/test_lifecycle_journey_e2e.py`, and the 6 listed `tests/contract/` files

**Description:** The cut. Code and its tests die in the same commit. Record the deleted
LOC and test-function counts as you go — T-30-12 needs them.

**Done criterion:** `git grep -lE "features[./](lifecycle|workflows)" dadaia_workspace tests`
returns nothing (`features/backlog/removal_lifecycle.py` survives and must not match);
suite green.

---

- [ ] **T-30-06 — Delete the engine assets and their projection dirs**

**Owner role:** software-engineer

**Preconditions:** T-30-05 `[x]`.

**Write set:**

- `dadaia_workspace/public/lifecycle_fragments/**` (13 md), `dadaia_workspace/public/personas/**` (8 md) (delete)
- `dadaia_workspace/public/schemas/{lifecycle-run-workflow-steps-v1,workflow-model-policy-v1,workflow-step-payload-v1}.schema.json` (delete)
- `dadaia_workspace/infrastructure/public_assets_common.py` (remove the `lifecycle_fragments` and `personas` projection dirs)
- `tests/unit/infrastructure/test_install_target_goldens.py` + affected golden fixtures

**Description:** With the projection dirs gone, `public install` must not leave orphan
`lifecycle_fragments/` or `personas/` trees in an existing workspace — reconciliation
removes them. Golden regen here is legitimate and expected: explain each diff in the
commit message.

**Done criterion:** `dadaia public stage` → `install --target all` → `doctor` green on a
scratch workspace with no orphan directory left behind.

---

- [ ] **T-30-07 — Rewrite `DADAIA.md` §1 (Arm A without the engine) and re-project**

**Owner role:** ai-engineer

**Preconditions:** T-30-06 `[x]`.

**Write set:**

- `dadaia_workspace/public/data/DADAIA.md` (§1 rewrite + §9 panel row)
- projections via `dadaia public stage` / `install --target all` (never hand-edited)

**Description:** §1 keeps both arms. **Arm A** becomes the agent-dispatched SDD flow —
demand → backlog-definition → release-definition → implementation + reviews/gates → audit
— executed by dispatching the owning agent (§2) against the SDD documents. Remove the
four-workflow engine paragraph, every `dadaia lifecycle` command, the `--harness` worker
selection and the Layer-2 entry-harness preference. **Arm B is unchanged, verbatim.** §9's
panel row drops the workflow reference. The projected law files at the workspace root and
in the harness dirs are PROTECTED — they change only via re-projection.

**Done criterion:** `dadaia public doctor` reports `[ok] public-privacy` and zero drift;
the projected `DADAIA.md` copies are byte-identical to the source.

---

- [ ] **T-30-08 — Grep-driven prose sweep to zero residue**

**Owner role:** ai-engineer

**Preconditions:** T-30-07 `[x]`.

**Write set:**

- `dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md`, `public/scaffold/AGENTS.md`, `public/templates/specs-AGENTS.md`, `public/pi/SYSTEM.md`, `public/pi/extensions/dadaia-sdd-gate.ts`
- `dadaia_workspace/public/agents/{ai-engineer,project-auditor,project-manager}.md`
- `dadaia_workspace/public/skills/{dadaia-cli,dadaia-release-definition,dadaia-release-closure,dadaia-task-manager,dadaia-step0-memory-bootstrap,drift-detection,harness-primitives,project-orchestration,ai-harness-claude-code,ai-harness-codex}/SKILL.md` — 10 skills; `dadaia-step0-memory-bootstrap` attributes its load sequence to `features/lifecycle/prompt_builder.py` and must be restated around the `ctx_inject` hook alone
- `dadaia_workspace/hooks/ctx_inject.py` (prose blocks L90–101, L276, L294, L302–305 — prose only, no code coupling)
- `dadaia_workspace/features/academy/knowledge_basis/{07_codex,08_pi_agent}/**`
- `README.md` (16 hits, incl. the stale `dadaia orchestrate` row for a verb that does not exist), `docs/01_medium_codex.md`, the repo-scoped `AGENTS.md`
- `tests/fixtures/tasks/consumer-specs/releases/v0.2.0/TASKS.md`

**Description:** The skills that narrated "ordered lifecycle is owned by the
dadaia-workflows" now state that the ordered lifecycle is agent-dispatched and
document-governed. Re-project after editing public assets. If the repo-scoped `AGENTS.md`
turns out to be a lib projection, edit its source instead of the projection.

**Done criterion:**
`grep -riE "dadaia.workflows|dadaia lifecycle|features[./]lifecycle" dadaia_workspace tests docs README.md AGENTS.md`
returns nothing (`features/backlog/removal_lifecycle.py` survives and must not match).

---

- [ ] **T-30-09 — Prune import-linter contracts, lower the caps, update the contract tests**

**Owner role:** software-architect

**Preconditions:** T-30-08 `[x]`.

**Write set:**

- `setup.cfg`
- `tests/contract/test_import_linter_ignore_cap.py`
- `tests/contract/{test_module_size_ceiling.py,test_architecture_diagrams_current.py,test_bind_resolution_seam_dynamic_walk.py}` (`test_no_silent_optional_wiring.py` was already updated in T-30-04, with the builders it pins)

**Description:** Delete the `lifecycle-no-workflows` contract; remove `ai_surface`,
`lifecycle` and `workflows` from the `features-no-cross-feature` `modules` list; delete
the ~12 now-unmatched ignore edges (panel→lifecycle ×4, panel→workflows ×1,
workflows→lifecycle ×1, lifecycle→reports ×1, lifecycle→backlog ×5) plus
`cli.commands.lifecycle → infrastructure.fake_runtime`. An unmatched ignore makes
`lint-imports` **error** — this is mandatory, not cleanup. Lower the recorded caps in the
same commit and record the new totals in the setup.cfg header comment.

**Done criterion:** `lint-imports --config setup.cfg --no-cache` green with zero unmatched
ignores; contract suite green.

---

- [ ] **T-30-10 — De-flag `infrastructure/public_assets.py` into a flag-free step pipeline**

**Owner role:** software-engineer

**Preconditions:** T-30-09 `[x]`.

**Write set:**

- `dadaia_workspace/infrastructure/public_assets.py`, `infrastructure/public_assets_common.py`
- `dadaia_workspace/cli/commands/public.py`, `cli/commands/plugin.py` (boundary translation only)
- `tests/unit/infrastructure/test_install_target_goldens.py` and the public-assets unit tests

**Description:** **`install()` IS the boundary translator.** Its public,
port-conforming signature (`workspace_root`, `target`, `force`, `scope`, `only`) is
**unchanged**; the `PublicAssetManager` port and the `features/workspace/service.py` and
`features/public/service.py` call sites are **not touched by this release**. The refactor
is entirely below that line: `install()` resolves its arguments **once** into an immutable
`InstallPlan` (resolved harness targets, guardrail target set, overwrite policy, step
selection, agent-model overlay, resolved core models), then runs an ordered list of
flag-free steps and reconciles the ledger. Every step takes data; **zero `bool` parameters
survive in any private step signature**. `force` becomes an overwrite-policy value on the
plan; `scope` and `only` become step *selection* — an unselected step is absent from the
list, not guarded by an internal `if`.

Behavioural invariants that must survive: `install_dadaia_md` runs after the per-harness
projections (copy_tree prunes orphans); `_project_installed_plugins` runs after the core
projection (pack precedence); the source-root refusal and the
`DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL` override stay exactly as they are.

**Byte-neutral for the default path.** `UPDATE_INSTALL_GOLDENS` is **not** authorized in
this task — if a golden moves here, the refactor changed behaviour and is wrong.

**Done criterion:** no `bool`-typed parameter in any **private step** signature in
`dadaia_workspace/infrastructure/public_assets.py` — the public `install()` signature is
**exempt** and must remain byte-identical to the `PublicAssetManager` protocol
(`features/{workspace,public}/service.py` call sites unchanged, verified by diff); goldens
pass **unchanged**; `public stage/install/doctor` byte-stable.

---

- [ ] **T-30-11 — Quality gates, residue grep, CHANGELOG**

**Owner role:** qa-engineer

**Preconditions:** T-30-10 `[x]`.

**Write set:**

- `CHANGELOG.md`

**Description:** Run the full acceptance list: `pytest -p no:cacheprovider -q`,
`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports --no-cache`, then
`dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia certify --json` on
a clean workspace. Add the CHANGELOG entry documenting the engine removal and the
`dadaia-capabilities-v1` → `v2` schema change — CHANGELOG is the **one** place the names
legitimately survive.

**Done criterion:**
`grep -riE "dadaia.workflows|dadaia lifecycle|features[./]lifecycle" dadaia_workspace tests docs README.md CHANGELOG.md`
returns only the historical CHANGELOG entries (`features/backlog/removal_lifecycle.py`
survives and must not match); every gate green.

---

- [ ] **T-30-12 — Quantified removal report (LOC + deleted tests)**

**Owner role:** qa-engineer

**Preconditions:** T-30-11 `[x]`.

**Write set:**

- `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-v030-demolition-metrics.html` + its handoff

**Description:** Measure against the baseline `main @ ec301ae3` (production 70,208 LOC;
tests 92,272 LOC; 2,973 tests passed) and report:

| Metric | Before | After | Δ |
|---|---|---|---|
| Production LOC | 70,208 | | |
| Test LOC | 92,272 | | |
| Tests passed | 2,973 | | |
| Test functions | | | |
| Production modules | | | |
| import-linter ignore edges | 36 | | |
| `public_assets.py` bool parameters | 18 | 0 | −18 |

Include the per-area breakdown from the demolition map (§1 production, §2 tests, §4
assets) with the measured value beside each mapped estimate, and flag any area where the
measured removal differs from the map by more than 10%.

**Done criterion:** report + handoff emitted and validated with `dadaia reports validate`.

---

- [ ] **T-30-13 — Constitution, memory atoms, CLOSURE**

**Owner role:** product-engineer

**Preconditions:** T-30-12 `[x]`; `ACTIVE.md` phase `CLOSURE` (memory writes are
phase-gated).

**Write set:**

- `specs/constitution.md` (Layer-2 prose — **requires explicit operator confirmation**)
- `specs/memory/product/sdd/{dadaia-workflows.md,lifecycle-foundation.md}` → `specs/_archive/legacy-memory/<ts>/`
- `specs/memory/product/{agents/agent-orchestration.md,agents/agent-comms.md,panel/panel.md,philosophy/product-vision.md,philosophy/spec-context-project.md,harness/harness-claude-code.md,harness/harness-codex.md,harness/harness-pi.md,sdd/sdd-gate-v3.md,sdd/sdd-bug-backlog-governance.md,sdd/specs-doctor.md}`
- `specs/memory/{architecture.md,tech-stack.md,quality-assurance.md}`
- `specs/memory/product/{index.md,catalog.json}` (regenerate)
- `specs/releases/v0.3.0/CLOSURE.md`

**Description:** Memory describes the product as it is **after** the demolition — no
changelog, no "we used to have an engine". Run the disposition sweep: backlog Items 1/2/3
terminal (`CONSUMED`/`SUPERSEDED — v0.3.0`), Items 4/5/6 left OPEN with the reason, every
open engine bug `Closed` with `superseded_by`, and
`specs/backlog/20260715-bugfix-workflow-tdd.md` routed to `project-manager`.

**Done criterion:** `dadaia specs doctor` green; CLOSURE.md complete with the T-30-12
metrics table; release archived via `git mv` and `ACTIVE.md` repointed.
