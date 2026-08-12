# SPEC — Release v0.3.0 — Demolition of the dadaia-workflows engine + de-flag of public_assets

> **Status:** Aprovado

**Release ID:** v0.3.0
**Owner:** product-engineer
**Source:** operator demand 2026-08-06 ("I don't wanna see dadaia-workflows anymore
anywhere") + `specs/backlog/20260806-clean-architecture-remediation.md` Items 1, 2, 3
**Evidence:** `.dadaia/tmp/claude-code/20260806/demolition-map-v030.md` (normative removal
map), `.dadaia/reports/dadaia-workspace/project-auditor/2026-08-06T210000Z-bug-ledger-architecture-audit.html`

## 1. Problem

The bug-ledger audit of 416 bugs produced one unambiguous finding: **the workflow engine
is the bug factory.**

| Measure | Value |
|---|---|
| Bugs in the `features/lifecycle` cluster | 200 of 416 (48%) — 289 counting the full engine surface |
| Fix-ratio inside `features/lifecycle/` | 96% (95% in `hooks/`) |
| Median `resolved` → same-family re-report | **0.48 day** (239 measured recurrences) |
| Engine share of production LOC | ~20,700 |
| Engine share of the test suite | 493 test functions (29.5%) |

Every sampled bug fix in that cluster was **net-additive** — a new rung, a new retry, a
new digest bound, a new gate. Every surface **deletion** in the project's history
(v0.1.53 purge, v0.1.57 dedup, v0.1.75 test rearchitecture, v0.1.76 NO-LOCKS) went quiet
afterward and stayed quiet.

The empirical law: **deleted surface stops producing bugs; surface added by a fix produces
the next bug in under a day.** Continuing to fix the engine is the one option the data
forbids. The operator has ruled: demolish.

The same accretion signature is already visible in a second file:
`infrastructure/public_assets.py` — 1,498 lines, 18 boolean parameters, 21
compat/legacy/fallback mentions. It is where `lifecycle` was three years of bugs ago. It
gets de-flagged in the same release, before it explodes.

## 2. Objective

Remove the dadaia-workflows engine from the repository — production, tests, assets,
wiring, contracts, law and prose — so that no file under `dadaia_workspace/`, `tests/`,
`docs/` or the repository README mentions `dadaia-workflows` or `dadaia lifecycle`. Then
de-flag `public_assets.py` into a pipeline of flag-free steps.

Architecture after this release: **clean, direct, simple. No mechanism for a demand that
does not need one.** The ordered SDD lifecycle survives as what it always actually was —
an agent-dispatched flow governed by documents (SPEC/PLAN/TASKS/CLOSURE) and the
deterministic gate — with no Python engine driving Layer-2 workers.

## 3. Scope

### FR1 — Delete the engine production surface

Delete entirely (demolition map §1, §4, §3/§5 wiring):

- `dadaia_workspace/features/lifecycle/**` (14,600 LOC, 44 modules — engine core,
  `workflows/{audit,backlog_definition,release_definition,_fragment_gate}.py`,
  `fragments/`, `personas/`, `antislop/`)
- `dadaia_workspace/features/workflows/**` (707 LOC presentation shim)
- `dadaia_workspace/features/ai_surface/**` (188 LOC)
- `dadaia_workspace/cli/commands/lifecycle.py` (1,378 LOC — the `dadaia lifecycle` verb group)
- Core models `lifecycle.py`, `workflow_execution.py`, `workflow_handoff.py`,
  `scope_match.py`; core protocols `agent_runtime`, `lifecycle_run_store`,
  `runtime_files`, `workflow_model_policy_store`, `workflow_provider`,
  `local_model_profile_store`
- Infrastructure runtimes and stores: `codex_runtime`, `pi_runtime`,
  `claude_sdk_runtime`, `fake_runtime`, `headless_adapter_base`,
  `json_lifecycle_run_store`, `json_workflow_model_policy_store`, `runtime_files`,
  `git_evidence`, `json_local_model_profile_store`; `core/harness_models.py` if
  consumer-free after the cut
- Panel views `workflow_policy.py`, `workflows.py` and their CSS/JS assets
- Assets: `public/lifecycle_fragments/**` (13 md), `public/personas/**` (8 md),
  `public/schemas/{lifecycle-run-workflow-steps-v1,workflow-model-policy-v1,workflow-step-payload-v1}.schema.json`;
  the `lifecycle_fragments` and `personas` projection dirs in `public_assets_common.py`
- `container.py`: all lifecycle/workflow builders (~1,400 of 2,300 lines)

The map's §6 **MUST SURVIVE** list is binding — do not overreach.

**Acceptance:** none of the deleted modules exists; `python -c "import dadaia_workspace"`
succeeds; `dadaia --help` lists no `lifecycle` verb group.

### FR2 — Delete the engine test surface

Delete the test surface enumerated in demolition map §2 (~26,000 LOC, 493 test
functions): the lifecycle/workflows/ai_surface unit trees, the engine infrastructure and
core unit tests, the lifecycle/pipeline integration suites, `tests/integration/codex_live/**`
and `pi_live/**`, the engine performance and e2e suites, the workflow panel e2e specs, and
the six engine contract tests. `test_telemetry_lock_*` stays.

**Acceptance:** the suite collects and passes with zero references to deleted modules; no
skipped/xfail placeholder is left behind in their place.

### FR3 — Sever the survivors

Per demolition map §3, each surviving file loses only its engine coupling:

| Surface | Loses |
|---|---|
| `cli/main.py` | lifecycle import + `add_typer` |
| `cli/commands/reports.py` | the 6 workflow verbs (`workflow_doctor`, `handoffs_doctor`, `hygiene_status`, `status`, `profiles`, `hygiene_clean`) |
| `cli/commands/public.py` | `check_ai_surface_ritual` import+call; `check_workflow_policy_layer2_residue` call |
| `cli/commands/capabilities.py` + `features/capabilities/service.py` | the `workflows` key, the workflow capability strings in `surfaces.panel`/`surfaces.evidence`, and `certification.deterministic_fake_workflows` / `live_harness_canaries_required_for_release` |
| `features/certification/service.py` | the 8 `workflow-*` checks (L260–420). Keeps context-bind-heartbeat, context-specs-doctor, handoff_validation |
| `features/panel/{service,handler}.py`, `views/{index,static,api_agents}.py` | Workflows + Model-policy tabs, their routes, asset registry entries and payload keys. Keeps `api_agent_model_templates`, telemetry/Sessions |

**Capabilities schema decision:** `workflows` is a `required` key under
`additionalProperties: false`, so its removal is a breaking contract change. The release
mints `public/schemas/dadaia-capabilities-v2.schema.json` (`$id` and `schema_version`
const `dadaia-capabilities-v2`) and deletes the v1 file. `dadaia-certification-v1` is
unchanged — the check list is data, not schema shape. The change is announced in
`CHANGELOG.md` and in `CONSUMER_VALIDATION_RECIPE.md`.

**Acceptance:** panel serves 5 tabs with no dead routes or 404 assets; `dadaia certify
--json` is green with the reduced check list; `dadaia capabilities --json` validates
against v2.

### FR4 — Law and prose: zero remaining references

`public/data/DADAIA.md` §1 is rewritten: **Arm A becomes the agent-dispatched SDD flow**
— demand → backlog-definition → release-definition → implementation + reviews/gates →
audit, executed by dispatching the owning agent (§2) against the SDD documents, with no
Python engine, no `dadaia lifecycle` command, no `--harness` worker selection, and no
Layer-2 worker-harness preference paragraph. **Arm B (bugs) is unchanged.** §9's panel row
drops the workflow reference. The file is then re-projected (`public stage` →
`public install --target all` → `public doctor`).

Severed in the same sweep (map §4 plus the surfaces the map did not enumerate, found by
grep): `public/data/CONSUMER_VALIDATION_RECIPE.md`, `public/scaffold/AGENTS.md`,
`public/templates/specs-AGENTS.md`, `public/pi/SYSTEM.md`,
`public/pi/extensions/dadaia-sdd-gate.ts`, `public/agents/{ai-engineer,project-auditor,project-manager}.md`,
the 9 skills (`dadaia-cli`, `dadaia-release-definition`, `dadaia-release-closure`,
`dadaia-task-manager`, `drift-detection`, `harness-primitives`, `project-orchestration`,
`ai-harness-claude-code`, `ai-harness-codex`), `hooks/ctx_inject.py` prose blocks,
`features/academy/knowledge_basis/{07_codex,08_pi_agent}/**`, `README.md` (16 hits,
including the stale `dadaia orchestrate` row for a verb that no longer exists), `docs/01_medium_codex.md`,
the repo-scoped `AGENTS.md`, and the fixture
`tests/fixtures/tasks/consumer-specs/releases/v0.2.0/TASKS.md`.

**History is not rewritten.** `specs/bugs/bugs.jsonl` (113 hits) and
`specs/bugs/_archive/archive.jsonl` are append-only by law and stay verbatim.
`specs/_archive/**` stays verbatim. `CHANGELOG.md` documents the removal and is the one
place the names legitimately survive.

**Acceptance:**
`grep -riE "dadaia.workflows|dadaia lifecycle|features[./]lifecycle" dadaia_workspace tests docs README.md CHANGELOG.md`
returns only the historical `CHANGELOG.md` entries. The third alternative catches dangling
module cross-references in prose and docstrings; it does **not** match the surviving
`features/backlog/removal_lifecycle.py`.

### FR5 — Contracts and caps

- `setup.cfg`: delete the `lifecycle-no-workflows` contract; remove
  `ai_surface`/`lifecycle`/`workflows` from `features-no-cross-feature` `modules`; remove
  the ~12 now-unmatched ignore edges (panel→lifecycle ×4, panel→workflows ×1,
  workflows→lifecycle ×1, lifecycle→reports ×1, lifecycle→backlog ×5) and the
  `cli.commands.lifecycle → infrastructure.fake_runtime` edge. An unmatched ignore makes
  `lint-imports` error — this is not optional cleanup.
- Lower the recorded caps in `tests/contract/test_import_linter_ignore_cap.py` in the same
  commit (the file's own law: lowering is encouraged, and the cap moves with the edges).
- Update `tests/contract/test_module_size_ceiling.py`,
  `test_architecture_diagrams_current.py`, `test_no_silent_optional_wiring.py`,
  `test_bind_resolution_seam_dynamic_walk.py`, `tests/contract/cli/test_cli_capabilities.py`.

**Acceptance:** `lint-imports --config setup.cfg --no-cache` green with zero unmatched
ignores; contract suite green.

### FR6 — De-flag `infrastructure/public_assets.py`

`install()` stops being a 5-parameter flag funnel threading `force: bool` through ~15
private signatures. **`install()` IS the boundary translator** — the flags stop at it
instead of travelling through it:

1. `install()` keeps its **port-conforming public signature** (`workspace_root`, `target`,
   `force`, `scope`, `only`). The `PublicAssetManager` port signature and the
   `features/workspace/service.py` and `features/public/service.py` call sites are
   **unchanged** — this release does not touch the port contract or its consumers.
2. Inside `install()`, those arguments are resolved **once** into an immutable plan value
   (resolved harness targets, guardrail target set, overwrite policy, step selection,
   loaded agent-model overlay, resolved core models).
3. `install()` then executes an ordered list of flag-free steps. **Each step takes data,
   not booleans** — no `bool` parameter survives in any *private step* signature.
4. `force`/`scope`/`only` never travel past the translator: `force` becomes an
   overwrite-policy value on the plan; `scope` and `only` become explicit **step
   selection** (a step that is not selected is absent from the list, instead of being
   guarded by an `if` inside it).

**Behaviour is byte-neutral for the default path.** The install goldens
(`tests/unit/infrastructure/test_install_target_goldens.py` and siblings) must pass
unchanged; `UPDATE_INSTALL_GOLDENS` may be used **only** for projections that legitimately
changed because FR1 deleted their source asset (lifecycle_fragments, personas, the 3
schemas, and the prose files rewritten by FR4). A golden regen for any other file is a
defect, not a rebase.

**Acceptance:** zero `bool`-typed parameters in the **step** functions (the private
signatures); the port-conforming public `install()` signature is **exempt** and must stay
byte-identical to the `PublicAssetManager` protocol; goldens green with a regen diff
explainable line-by-line by FR1/FR4; `dadaia public stage/install/doctor` byte-stable on a
clean workspace.

## 4. Out of scope (non-goals)

- The **SDD document lifecycle** — `specs/**`, backlog, bugs, memory, `specs doctor`,
  `features/specs/**`, `cli/commands/specs.py`. The documents are the lifecycle; only the
  engine that drove workers over them dies.
- **Telemetry / Sessions panel**, `features/telemetry/**` and the telemetry locks.
- **Layer-1 agents** — `public/agents/**` bodies keep their roles; only engine prose is severed.
- **Gate and hooks semantics** — `hooks/**`, `gate_policy`, the git chokepoints. Only
  `ctx_inject.py` prose changes.
- **Git history rewrite** — no rebase, no filter-branch, no bug-ledger edit.
- Backlog Items 4 (context-resolution rung), 5 (conduct law), 6 (deferred-debt triage) —
  they stay OPEN for a later release.

## 5. Backlog and audit dispositions

Recorded here for the CLOSURE sweep; the backlog file's own frontmatter is PM-curated and
is not edited by this SPEC.

| Item | Disposition |
|---|---|
| Item 1 — fate of dadaia-workflows | **CONSUMED — v0.3.0** (demolish; the operator's ruling) |
| Item 2 — retry/bounded-revision machinery | **SUPERSEDED — v0.3.0** (the machinery is deleted with the engine; nothing remains to de-retry) |
| Item 3 — de-flag `public_assets.py` | **CONSUMED — v0.3.0** (FR6) |
| Item 4 — one context-resolution rung | **DEFERRED** — out of scope, stays OPEN |
| Item 5 — conduct law (DADAIA.md §6) | **DEFERRED** — out of scope, stays OPEN |
| Item 6 — deferred-debt triage | **DEFERRED** — out of scope, stays OPEN |
| Open engine bugs in `specs/bugs/` | **superseded by v0.3.0** — the surface that produced them no longer exists; each gets a `superseded_by` disposition at CLOSURE, none is silently dropped |
| `specs/backlog/20260715-bugfix-workflow-tdd.md` | routed to `project-manager` for re-scoping or terminal disposition — it targets a deleted surface |

## 6. Memory atoms affected at closure

Written by product-engineer in the CLOSURE phase, not during implementation:

- **Delete** `product/sdd/dadaia-workflows.md`, `product/sdd/lifecycle-foundation.md`
  (archive to `_archive/legacy-memory/<ts>/`)
- **Rewrite** `product/agents/agent-orchestration.md`, `product/panel/panel.md`,
  `product/philosophy/{product-vision,spec-context-project}.md`,
  `product/harness/{harness-claude-code,harness-codex,harness-pi}.md`,
  `product/sdd/{sdd-gate-v3,sdd-bug-backlog-governance,specs-doctor}.md`,
  `product/agents/agent-comms.md`, `architecture.md`, `tech-stack.md`,
  `quality-assurance.md`
- **Regenerate** `product/index.md` + `product/catalog.json` (catalog order and
  `depends_on` edges lose the two deleted atoms)
- `specs/constitution.md` §Layer-2 prose — PE-owned, **requires explicit operator
  confirmation** before the edit

## 7. Acceptance criteria (release-level)

1. Full suite green: `pytest -p no:cacheprovider -q`.
2. `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports --no-cache` green.
3. `grep -riE "dadaia.workflows|dadaia lifecycle|features[./]lifecycle" dadaia_workspace tests docs README.md CHANGELOG.md`
   → only historical `CHANGELOG.md` entries (`features/backlog/removal_lifecycle.py`
   survives and must not match).
4. `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia certify --json`
   green on a clean workspace.
5. **Quantified removal report**: deleted production LOC, deleted test LOC, deleted test
   functions, suite count before/after, module count before/after — measured against the
   baseline `main @ ec301ae3` (production 70,208 LOC; tests 92,272 LOC; 2,973 tests
   passed). Expected order of magnitude: ≈52,800 LOC total (≈26,800 production, ≈26,000
   tests) and 493 test functions.
6. Zero `bool` parameters in `public_assets.py` **step** functions (the public
   port-conforming `install()` signature is exempt and unchanged); install goldens
   explained.

## 8. Dependencies and risks

| Risk | Mitigation |
|---|---|
| `container.py` loses ~60% of its body; a survivor silently loses its wiring. | Sever consumers **before** deleting the engine (PLAN lane order), so every intermediate state imports and collects. `test_no_silent_optional_wiring` is updated, not disabled. The map §6 MUST-SURVIVE list is checked builder-by-builder. |
| `dadaia-capabilities-v1` has external consumers pinning the schema. | Explicit v2 mint with the removal announced in CHANGELOG + consumer recipe; the consumer validation agent re-runs against v2 before ship. |
| Golden regen used to paper over an unintended behaviour change in FR6. | `UPDATE_INSTALL_GOLDENS` permitted only for FR1/FR4-caused diffs; every regenerated golden line is explained in the task's commit message. |
| Over-reach: deleting a survivor that merely mentions "workflow". | Map §6 is binding; `features/backlog/removal_lifecycle.py`, `features/specs/**`, `cli/commands/ci.py`, `core/agent_model_templates.py`, `core/role_atom_map.py`, `core/models/hygiene.py` (SlopPolicy/HygieneZone), telemetry and `hooks/**` are named survivors. |
| The demolition map is incomplete for prose (README, academy, docs, fixtures). | FR4 acceptance is a **grep**, not a checklist — the residue sweep is the authority, the map is the starting point. |
| The panel is left with dead tabs/assets. | Panel e2e specs for the surviving tabs run in the quality lane. |
