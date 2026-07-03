# TASKS — v0.1.54 — Import Boundaries

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets:
`container.py` W1-W4, `setup.cfg` W2-W3, `policy_doctor.py` W1-W2) are sequential — one
owner, no parallel `[-]`. Every implementation-wave task: NO `specs/backlog/**` paths staged
(archival is the single atomic SHIP commit, T-54-20). Every deletion/rename/repoint grep
includes `tests/`.

## W0 — definition

- [x] T-54-01 SPEC/PLAN/TASKS authored from the 2026-07-03 inspection dossier (ports
  verified: `WorkflowProvider`/`AgentsProvider` exist → FR5 is DI completion; no
  `workflow_model_policy_store` port → FR1 creates a lean one; the `json_wmp_store` data
  types are relocatable to `core/models`; cycle confirmed bidirectional; 6 pid-probe sites
  confirmed incl. the dynamic `importlib` lease path; `core/specs_backup.py` uses
  `shutil.copytree`; the exact 13 post-FR2 cross-feature module-pair edges reconstructed;
  stale "(still 17)" contradiction in `setup.cfg:112` + `architecture.md:139` recorded).
  Dual definition review REJECT×2 — architect (A1 type-relocation + lean port +
  policy_resolver-needs-no-port; A2 cli_anchors seam + six build_registry sites; R-1 FR2
  seam split w/ re-export = zero test-importer edits; R-2/A3 exact 13-edge cap 15+13−2=26 +
  per-family; R-3/A6 FR6 infra-home + partition; R-4 strike features-no-hooks; A8 extended
  grep + positive test; A9 FR7 AST guard; A10 container.py W1-W4 + FR4 fail-closed) + QA
  (A4 exact sabotage targets; A5 `Lint (ruff)` job; A6 "5 chains"=5 pairs/4 edges) — ALL
  folded; `Aprovado`; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 red-chain remediation

- [x] T-54-10 Fix the 5 red chains (4 edges) → `features-no-infrastructure` +
  `features-no-subprocess` GREEN. Checklist:
  - **(a) json_wmp_store — relocate types + lean port (architect A1):** move
    `WorkflowModelPolicyOverlay`, `WorkflowModelPolicyStoreError`, `DEFAULT_CONTEXT` from
    `infrastructure/json_workflow_model_policy_store.py` to
    `core/models/workflow_execution.py` (NO re-export shim); repoint EVERY importer incl.
    `container.py:33` (TYPE_CHECKING). `policy_resolver` now imports the types from
    `core/models` (legal features→core) — **no port for it**. Add lean Protocol
    `core/protocols/workflow_model_policy_store.py` (exactly `load`/`parse`/`save`) +
    `container.build_workflow_model_policy_store`; inject into `policy_doctor` (remove
    default construction l.288) + `panel.views.workflow_policy` ONLY; CLI caller
    `cli/commands/lifecycle.py:1285` injects.
  - **(b) subject_registry break (architect A2):** move `_derive_cli_anchors` out of the
    feature to a `cli/`-composition helper; derive a `cli_anchors` frozenset at each
    composition boundary; thread into `build_registry` + `run_backlog_doctor` +
    `ContextSelector.sel_backlog_index`. Update the SIX `build_registry` sites:
    `container.py:1069`, `container.py:1139`, `newartifacts.py:186`, `newartifacts.py:281`,
    `backlog/doctor.py:240`, `context_selector.py:428`. `subject_registry` keeps only a
    `TYPE_CHECKING` `typer` import (no runtime `cli.main` edge).
  - `lint-imports --no-cache`: `6 kept, 0 broken`; the 4 red sources no longer import their
    targets (per-chain grep, incl. `tests/`).
  - Behavior-preserving: policy resolution + subject-registry `cli`-subject derivation
    unchanged (targeted before/after assertions); mypy --strict clean (no missed importer);
    full affected-scope suite green.
  - AC-8 ledger (surviving: policy resolution, cli-subject anchors via injected frozenset,
    panel workflow-policy view; dead: none — pure rewire). NO `specs/backlog` staged.
  Owner: software-engineer.
  - **DONE (software-engineer):** reservation `2c304dbb` (`chore(tasks): start T-54-10`).
    Mechanism (a): `WorkflowModelPolicyOverlay`/`WorkflowModelPolicyStoreError`/
    `DEFAULT_CONTEXT` (+ `_SCHEMA_VERSION`) relocated to `core/models/workflow_execution.py`
    (no re-export shim; store imports them from core); lean port
    `core/protocols/workflow_model_policy_store.py` (`load`/`parse`/`save`);
    `container.build_workflow_model_policy_store` returns the port and is injected into
    `policy_doctor` (default construction removed) + `panel.views.workflow_policy`;
    `policy_resolver` imports the types from `core` (no port needed). Mechanism (b):
    `_derive_cli_anchors`/`_walk_typer` moved to `cli/anchors.py`; `build_registry` takes a
    pre-derived `cli_anchors: frozenset[str]`; threaded through `run_backlog_doctor` +
    `ContextSelector` (constructor attr); 6 `build_registry` sites + 2 `run_backlog_doctor`
    sites updated at composition boundaries. Gates: `lint-imports --no-cache` → **6 kept,
    0 broken** (`features-no-infrastructure` + `features-no-subprocess` now KEPT);
    `ruff format --check` + `ruff check --no-cache` + `mypy --strict` all exit 0;
    full suite `4322 passed, 17 skipped` (exit 0). Per-chain greps (incl. `tests/`) clean:
    subject_registry has zero runtime `cli.main` import; no module imports the moved types
    from `infrastructure`. **AC-8 ledger** — surviving: policy resolution (WMP doctor +
    resolver tests green), cli-subject anchor derivation via injected frozenset (82 real
    anchors; `test_cli_anchor_resolves_command_id` green), panel workflow-policy view
    (panel route tests green); dead: none — pure rewire. Deviation: `core/models/
    workflow_execution.py` already existed (SPEC said "NEW") — added the types to it
    (its exact semantic home); the `cli_anchors REPLACES cli_app` decision drops the
    now-unused `TYPE_CHECKING typer` import from `subject_registry` (the SPEC's "keeps only
    a TYPE_CHECKING typer import" clause is unsatisfiable alongside moving `_derive_cli_anchors`
    out under the feature-layering law). No `specs/backlog/**` staged.

## W2 — FR2 + FR3 cycle break + cross-feature contract

- [x] T-54-11 Break the `workflows ↔ lifecycle` cycle, then add the cross-feature contract.
  **FR2 first**, then **FR3**. Checklist:
  - **FR2 RED:** add the directed `forbidden` contract `lifecycle-no-workflows`
    (`features.lifecycle` ⊬ `features.workflows`) to `setup.cfg`; `lint-imports` FAILS on
    today's `policy_doctor → dadaia_catalog` (capture the RED tail).
  - **FR2 fix (R-1 seam split):** create `features/lifecycle/governed_catalog.py`
    (`DadaiaWorkflowStepDTO`, purpose/display dicts, every `_*_steps` builder, SVG-free
    `_all_workflows`, `_governed_step`, `governed_workflow_catalog`,
    `_assert_catalog_defaults_resolve`, availability constants; imports ONLY lifecycle
    internals + core). Shrink `workflows/dadaia_catalog.py` to `DadaiaWorkflowDTO`,
    `_build_workflow`, `_steps_to_stage_dtos`, `_node_meta_for_steps`,
    `list_dadaia_workflows`, `get_dadaia_workflow` + EXACTLY ONE lifecycle import
    (`governed_catalog`) that **re-exports `governed_workflow_catalog`** → **9 test importers
    ZERO edits**. Repoint `container.py:735` (lifecycle home) + `policy_doctor.py:405`
    (intra-lifecycle). `lifecycle-no-workflows` GREEN.
  - **AC-7(a):** plant `from dadaia_workspace.features.workflows import dadaia_catalog` atop
    `features/lifecycle/policy_doctor.py` ⇒ `lifecycle-no-workflows` FAILS; revert.
  - **Golden test:** `list_dadaia_workflows()` output + diagram SVG byte-identical
    before/after.
  - **FR3 RED:** add `features-no-cross-feature` as an `independence` contract (a
    self-referential `forbidden` is REJECTED by import-linter 2.11 — "Modules have
    shared descendants"; QA-verified) listing EVERY `dadaia_workspace.features.<pkg>`
    sub-package under `modules =`, with NO ignores; `lint-imports` FAILS on the real
    cross-feature edges (capture the RED tail).
  - **FR3 fix:** add the exact **13** documented `ignore_imports` (full `dadaia_workspace.`
    prefixes, no wildcards, rationale comments) per SPEC FR3 list #1-#13. `lint-imports`:
    `8 kept, 0 broken`.
  - **AC-7(b):** plant `from dadaia_workspace.features.spec_context import lease` atop
    `features/backlog/subject_registry.py` ⇒ `features-no-cross-feature` FAILS; revert.
  - Cap: `test_import_linter_ignore_cap.py` → `_RECORDED_IGNORE_EDGE_CAP = 28`; broaden the
    `test_every_ignored_edge_is_a_features_layering_exception` docstring; add **per-family
    per-contract-section assertions** (infra 11 / subprocess 4 / cross-feature 13);
    `test_recorded_cap_is_not_stale_above_reality` GREEN.
  - AC-8 ledger. NO `specs/backlog` staged. Owner: software-engineer.
  - **DONE (software-engineer):** reservation folded into the FR2 RED commit `f3a968a0`
    (`test(T-54-11): lifecycle-no-workflows RED`). Commits, in order:
    `f3a968a0` FR2 RED · `05578415` FR2 fix (governed_catalog seam) · `cd852932` FR3 RED ·
    `60e43c09` FR3 fix (13 ignores, cap 28).
    - **FR2 RED tail** (`lint-imports --no-cache`): `6 kept, 1 broken` —
      `lifecycle.policy_doctor -> workflows.dadaia_catalog (l.411)` (the direct edge, W1
      having already removed `subject_registry -> cli.main`).
    - **FR2 fix (R-1 seam split):** new `features/lifecycle/governed_catalog.py` (imports
      only lifecycle internals + core; ZERO `features/workflows`) holds
      `DadaiaWorkflowStepDTO`/`DadaiaWorkflowDTO`, the purpose/display dicts, every
      `_*_steps` builder, the SVG-free `_all_workflows` (via `_svg_free_workflow`),
      `_governed_step`, `governed_workflow_catalog`, `_assert_catalog_defaults_resolve`,
      the availability constants, and a `resolve_default_model_id` seam helper.
      `features/workflows/dadaia_catalog.py` shrunk to a presentation shim importing EXACTLY
      ONE lifecycle module (`governed_catalog`) and re-exporting the public names — 9
      `governed_workflow_catalog` test importers + panel + service unchanged (ZERO edits).
      Repoints: `container.py` + `policy_doctor.py:411` → `lifecycle.governed_catalog`.
      `lifecycle-no-workflows` GREEN (`7 kept, 0 broken`).
      **Deviation (recorded):** `DadaiaWorkflowDTO` is *defined* in `governed_catalog` and
      *re-exported* by `dadaia_catalog` (not defined-in-dadaia_catalog as the literal SPEC
      wording reads) — the cycle constraint is absolute (governed_catalog cannot import
      `workflows`), so the shared DTO must live on the lifecycle side; the public path
      `dadaia_catalog.DadaiaWorkflowDTO` is preserved by re-export (zero importer edits).
      Likewise `_node_meta_for_steps` stays in `dadaia_catalog` but resolves model ids via
      the `resolve_default_model_id` seam helper instead of a direct
      `lifecycle.model_profiles` import — otherwise a 14th cross-feature edge would leak.
    - **AC-7(a) sabotage:** planted `from dadaia_workspace.features.workflows import
      dadaia_catalog` atop `policy_doctor.py` ⇒ `lifecycle-no-workflows` FAILED
      (`policy_doctor -> dadaia_catalog (l.1)`, `6 kept, 1 broken`); reverted (tree clean).
    - **Golden test:** `tests/unit/features/workflows/test_dadaia_catalog_golden.py` +
      `_golden/dadaia_catalog_v0154.json` (captured PRE-split) — `list_dadaia_workflows()`
      output + all 7 diagram SVGs (30464 SVG bytes) byte-identical before/after: **PASS**.
    - **FR3 RED tail** (`lint-imports --no-cache`): `7 kept, 1 broken` —
      `features-no-cross-feature` (`independence`, 25 modules, NO ignores) BROKEN on
      exactly the SPEC FR3 list #1–#13. **SPEC-vs-tree:** the tree's 13 cross-feature edges
      matched SPEC #1–#13 **exactly (0 missing, 0 extra)** — no discrepancy; FR2 leaked no
      edge. Seam edge #13 (`workflows.dadaia_catalog -> lifecycle.governed_catalog`) present.
    - **FR3 fix:** added the exact 13 `ignore_imports` (full prefixes, no wildcards, grouped
      rationale comments: panel→lifecycle 4, panel→workflows 1, workflows→lifecycle 1,
      lifecycle→reports_validation 1, lifecycle→backlog 4, specs→spec_context 2) ⇒
      `8 kept, 0 broken`.
    - **AC-7(b) sabotage:** planted `from dadaia_workspace.features.spec_context import
      lease` atop `backlog/subject_registry.py` ⇒ `features-no-cross-feature` FAILED
      (`backlog.subject_registry -> spec_context.lease (l.1)`, `7 kept, 1 broken`);
      reverted (tree clean).
    - **Cap:** `_RECORDED_IGNORE_EDGE_CAP = 28` (15 + 13); broadened
      `test_every_ignored_edge_is_a_features_layering_exception` docstring; ADDED
      `test_ignore_edge_count_matches_recorded_per_family_breakdown` (infra 11 / subprocess 4
      / cross-feature 13); `test_recorded_cap_is_not_stale_above_reality` counts across all
      three sections and stays GREEN.
    - **Final gates:** `lint-imports --no-cache` → `8 kept, 0 broken`; full `pytest tests/
      --ignore=tests/e2e/panel` → **4325 passed, 17 skipped (exit 0)**; `ruff format --check`
      + `ruff check --no-cache` + `mypy --strict dadaia_workspace` (288 files) all exit 0.
    - **AC-8 ledger** — surviving (test now asserts each): governed catalog data
      (`governed_workflow_catalog` resolver projection — `test_policy_doctor` + resolver
      tests green); panel Workflows view (`list_dadaia_workflows` presentation DTOs +
      diagram SVG — `test_workflows_api` green); policy_doctor governed checks (WMP-* over
      the intra-lifecycle governed catalog); list/get presentation DTOs (byte-identical via
      the golden test). Dead (intentionally removed): the bidirectional
      `workflows ↔ lifecycle` import cycle — lifecycle no longer imports workflows (pinned
      dead by the `lifecycle-no-workflows` forbidden contract). NO `specs/backlog/**` staged.

## W3 — FR5 + FR7 direct-debt DI + core purity

- [x] T-54-12 Complete `features → infrastructure` DI (remove 2 ignores, lower cap) + core
  file-I/O AST guard. Checklist:
  - **FR5:** inject `WorkflowProvider` into `WorkflowsService` and `AgentsProvider` into
    `read_canonical_agents` via `container.py`; delete the direct `markdown_workflow_store` /
    `markdown_agent_store` imports. Remove the two `ignore_imports` edges from `setup.cfg`'s
    `features-no-infrastructure`; **lower the cap in the same commit** →
    `_RECORDED_IGNORE_EDGE_CAP = 26` (infra 9 + subprocess 4 + cross-feature 13; per-family
    assertions updated); **correct the stale "(still 17)" comment** at `setup.cfg:112`.
    `test_recorded_cap_is_not_stale_above_reality` GREEN.
  - **FR7 RED (architect A9):** add `tests/contract/test_core_file_io_purity.py` — an
    **AST-based walker** over `core/*.py` flagging `open`/`Path.read_text`/`write_text`/
    `mkdir`/`exists`/`glob`/`iterdir`/`rglob`/`shutil.copy*`/`copytree`/`move` outside the
    authorized set `{specs_backup, specs_version, specs_resolver, workspace_resolver}`
    (`platform.py` in the `sys` note, no file-I/O). Prove RED via the AC-7(c) plant, then
    remove → GREEN.
  - **AC-7(c):** create `dadaia_workspace/core/_io_sabotage_probe.py` with
    `Path(...).read_text()` ⇒ the AST guard FAILS; revert (delete the probe).
  - `lint-imports --no-cache`: `8 kept, 0 broken`; agent/workflow read behavior unchanged
    (before/after assertion). AC-8 ledger. NO `specs/backlog` staged. Owner: software-engineer.
  - **DONE (software-engineer):** reservation folded into the FR5 commit `56a51148`
    (`[ ]`→`[-]` in this file). Commits, in order:
    `56a51148` FR5 (DI completion, cap 26) · `735950e1` FR7 (core file-I/O AST ratchet).
    - **FR5 (features→infrastructure DI completion):** genuine `store_factory` DI. Each
      feature depends on a **feature-local Protocol** for the store surface, not the concrete
      adapter: `features/workflows/service.py` gains `_WorkflowStore` (`list`/`get`) +
      `WorkflowStoreFactory`; `features/agents/reader.py` gains `_AgentStore` (`list_raw`) +
      `AgentStoreFactory`. The concrete `MarkdownWorkflowStore` / `MarkdownAgentStore` is
      injected from `container.py` (`build_orchestration_catalog_service`,
      `build_workflow_catalog_service`, `build_panel_service`→`FileSystemAgentsProvider(store_factory=…)`).
      Both direct `from dadaia_workspace.infrastructure.markdown_*_store import …` lines are
      DELETED. `setup.cfg`: the 2 `markdown_*_store` ignores removed from
      `features-no-infrastructure`; header "Current count = 15" → **26 (9/4/13)** and the
      stale "(still 17)" → **26** corrected in the same edit. Cap test:
      `_RECORDED_IGNORE_EDGE_CAP` 28→**26**, per-family infra 11→**9** (subprocess 4,
      cross-feature 13); `test_recorded_cap_is_not_stale_above_reality` GREEN.
    - **FR7 (core file-I/O purity, architect A9 GUARD):** new
      `tests/contract/test_core_file_io_purity.py` — AST walker over `core/**/*.py` flagging
      `open()` / `Path.read_text|write_text|mkdir|exists|glob|iterdir|rglob` /
      `shutil.copy*|copytree|move` outside `{specs_backup, specs_version, specs_resolver,
      workspace_resolver}`. Only `ast.Call` nodes (no `d.get("open")` false-fire); shutil tied
      to a `shutil` receiver; `platform.py` `sys.platform` is attribute access, not flagged
      (sys-note). **AC-7(c) RED tail:** transient `core/_io_sabotage_probe.py` with
      `Path(...).read_text()` ⇒ guard FAILED —
      `dadaia_workspace/core/_io_sabotage_probe.py:11 .read_text(...)` (`1 failed, 1 passed`);
      probe DELETED ⇒ GREEN (`2 passed`). Probe not committed.
    - **Per-chain grep (incl. `tests/`):** `service.py` / `reader.py` carry **zero**
      `features -> infrastructure` import statements (only docstring mentions of the concrete
      class names, documenting the boundary). Live cap: infra **9** / subprocess **4** /
      cross-feature **13** = **26**.
    - **Final gates:** `lint-imports --no-cache` → **8 kept, 0 broken**; full
      `pytest tests/ --ignore=tests/e2e/panel` → **4327 passed, 17 skipped (exit 0)**;
      `ruff format --check` + `ruff check --no-cache` + `mypy --strict dadaia_workspace`
      (288 files) all exit 0.
    - **AC-8 ledger** — surviving (test now asserts each): workflow definitions listing via
      the injected store port (`list_summaries`/`get_detail`/`list_definitions`/
      `get_definition` — workflows service unit + panel `/api/workflows` integration green);
      canonical agents read via the injected store port (`read_canonical_agents` +
      `FileSystemAgentsProvider` — reader unit + panel `/api/agents` integration green); core
      file I/O confined to the 4 authorized modules (AST guard GREEN). Dead (intentionally
      removed): the 2 direct `features→infrastructure` imports
      (`workflows.service -> markdown_workflow_store`, `agents.reader -> markdown_agent_store`)
      — pinned dead by `features-no-infrastructure` (9 ignores) + zero-import grep; the stale
      "(still 17)" lie (and the collateral "Current count = 15" header) — corrected to 26.
    - **Deviations (recorded):** (1) the literal "depend on the EXISTING
      `core/protocols/workflow_provider.py`/`agents_provider.py` port" is unsatisfiable — those
      ports describe the panel-facing **service** surface (`list_summaries` /
      `read_canonical_agents`+`get_prompt`), NOT the **store** surface (`list`/`get`,
      `list_raw`) the feature injects. Per DIP (consumer-owned interface) and to stay inside
      the W3 write set (which lists `service.py`/`reader.py`/`container.py`/`setup.cfg`/tests,
      not `core/protocols/`), the store Protocols are defined feature-locally; the existing
      panel ports are untouched. Result: zero infra edge, no `core/protocols/` edit, no new
      ignore. (2) Also corrected the setup.cfg header "Current count = 15" (a W2 collateral
      miss, stale after W2's +13) to 26 alongside the mandated "(still 17)" fix. (3) Test
      churn: the direct-construction test sites now inject the concrete store class from
      infrastructure (legal in tests) — anticipated by the task. NO `specs/backlog/**` staged.

## W4 — FR6 pid-probe single public builder (isolated)

- [x] T-54-13 One public `infrastructure/process_probe_adapter.build_pid_probe()`; repoint 6
  sites; preserve the no-steal invariant (frozen-suite partition). Checklist:
  - Add public `build_pid_probe()` to `infrastructure/process_probe_adapter.py` (lazy
    `OsProcessProbe` wiring moves here). **Delete** the two private wrappers
    (`container.py:237`, `cli/commands/specs.py:69`); stop exporting
    `hooks.sdd_gate._build_pid_probe`.
  - Repoint: `hooks/sdd_gate.py` (calls the infra factory — hooks→infra declared exception);
    `cli/commands/lock.py:12` (`_build_pid_probe` → infra factory; keep `_active_field`);
    `cli/commands/context.py:514` (infra factory); `features/spec_context/lease._main_pid_probe`
    (l.883-894) **retarget the dynamic `importlib.import_module` lookup** to
    `dadaia_workspace.infrastructure.process_probe_adapter` + `build_pid_probe` — stays
    dynamic ⇒ zero new static features→infra edge ⇒ no ignore, cap stays 26.
  - **Extended grep AC-4 (architect A8):** zero hits (incl. `tests/`) of
    `hooks.sdd_gate._build_pid_probe`, `import_module("dadaia_workspace.hooks.sdd_gate")` for
    the probe, `sdd_gate._build_pid_probe` attribute access, and bare `_build_pid_probe`
    outside `hooks/sdd_gate.py`.
  - **Positive unit test (A8):** `lease._main_pid_probe` resolves the new public builder and
    returns a live probe. **Invariant test:** `None ⇒ TTL-only` degrade preserved.
  - **FROZEN-SUITE partition (R-3):** *frozen, adjudication required* —
    `tests/unit/cli/test_lock_steal.py:63` + `test_lease_main_probe.py` (symbol-forced
    repoints; QA-gate adjudication with byte-level no-steal evidence); *frozen, invariant-only*
    — `test_two_actor_lease.py` + `test_doctor_lock_gc.py` (confirm untouched); *non-frozen
    forced repoints* — `tests/unit/cli/commands/test_context_release_cmd.py:61` (monkeypatch
    retargets the infra factory as bound in `cli/commands/context.py`'s namespace) +
    `tests/unit/test_container.py:126` (comment update).
  - Run `lint-imports --no-cache` locally: `8 kept, 0 broken`, no new cycle/edge. **No
    `features-no-hooks` contract** (R-4 — `slop_scan.py:23` has a real features→hooks edge;
    re-scoped).
  - AC-8 ledger (surviving: pid-liveness probe, TTL degrade, no-steal; dead: the 3 private
    builders). NO `specs/backlog` staged. Owner: software-engineer.
  - **DONE (software-engineer):** reservation `[ ]`→`[-]` folded into the feat commit
    `d5e21494`. Commits, in order: `d5e21494` feat (public `build_pid_probe` + 6 repoints +
    3 deletions + lease dynamic retarget + existing-test repoints) · `1a9a0fd2` test (positive
    `_main_pid_probe` probe test) · this `[x]` mark.
    - **New public builder:** `infrastructure/process_probe_adapter.build_pid_probe() ->
      Callable[[int], bool] | None` — the SPEC-named home already existed (`OsProcessProbe`
      lives there), so the factory landed in-module (no parallel module; cohesion). Lazy
      `OsProcessProbe` wiring preserved; any construction error ⇒ `None` ⇒ TTL-only degrade.
      Typed `Callable[[int], bool] | None` (NOT `lease.PidProbe`) so the adapter keeps zero
      `infrastructure → features` edge (`infrastructure-no-upper-layers` KEPT).
    - **Deleted the 3 private builders:** `hooks/sdd_gate.py:38`, `container.py:237`,
      `cli/commands/specs.py:69`. Repoints: `sdd_gate` l.293 (top-level infra import; hooks→infra
      declared exception) · `container.build_doctor_service` (import extended to
      `OsProcessProbe, build_pid_probe`) · `specs doctor` l.137 (`lease` import dropped — became
      unused) · `lock.py:12` (keeps `_active_field` from `sdd_gate`, takes `build_pid_probe` from
      infra) · `context.py:514` (infra factory bound in `context_cmd`'s namespace) ·
      `lease._main_pid_probe` l.882-897 (dynamic `importlib.import_module(
      "dadaia_workspace.infrastructure.process_probe_adapter")` → `build_pid_probe`; **stays
      dynamic** ⇒ zero new static features→infra edge ⇒ no ignore, cap stays 26).
    - **AC-4 extended grep (incl. `tests/`) — ALL ZERO:** (i) `hooks.sdd_gate._build_pid_probe`
      → 0; (ii) `import_module("dadaia_workspace.hooks.sdd_gate")` → 0; (iii)
      `sdd_gate._build_pid_probe` attribute access → 0; (iv) bare `_build_pid_probe` ANYWHERE →
      0. The private name no longer exists in the tree (prose docstrings reworded to
      "private probe-builder wrappers" to keep the grep truly clean).
    - **Positive test (A8):** `tests/unit/features/spec_context/test_lease_pid_probe_public_builder.py`
      (NEW sibling — `test_lease_main_probe.py` is frozen, not expanded). 4 tests: resolves the
      public builder (RED pre-retarget: `AttributeError`/wrong-identity; GREEN after), live probe
      (`probe(os.getpid()) is True`), builder→None degrade, builder-raises fail-open. **RED tail
      captured pre-change:** `3 failed, 1 passed`; **GREEN after:** `4 passed`.
    - **Frozen-suite discipline (vs `777f0e0c`):** `test_two_actor_lease.py` +
      `test_doctor_lock_gc.py` — **zero diff** (verified `git diff 777f0e0c -- …` empty).
      Adjudicated: `test_lock_steal.py` — diff is monkeypatch-target (`_build_pid_probe` →
      `build_pid_probe`) + docstring pointer ONLY; every assertion / TTL / seed record
      byte-identical. `test_lease_main_probe.py` — **zero diff** (it monkeypatches
      `lease._main_pid_probe` wholesale; the function name/signature are unchanged, so no
      symbol repoint was needed — trivially target-only).
    - **Gates:** `lint-imports --config setup.cfg --no-cache` → **8 kept, 0 broken** (no new
      cycle/edge; `features-no-cross-feature` + `lifecycle-no-workflows` still GREEN);
      `test_import_linter_ignore_cap.py` → **4 passed** (cap 26 intact); full
      `pytest tests/ --ignore=tests/e2e/panel` (unpiped) → **4331 passed, 17 skipped (exit 0)**;
      `ruff format --check` + `ruff check --no-cache` + `mypy --strict dadaia_workspace`
      (288 files) all exit 0.
    - **AC-8 ledger** — surviving (test now asserts each): pid-liveness probe via the one
      public builder (`test_lease_pid_probe_public_builder` + `test_lock_steal` +
      `test_context_release_cmd` + `test_container` LOCK-GC green); no-steal pid-veto
      (TTL-expired + live pid ⇒ never stolen — frozen invariants byte-identical); `None ⇒
      TTL-only` degrade (unit test); doctor LOCK-GC gating (container end-to-end test). Dead
      (intentionally removed): the three private `_build_pid_probe` wrappers + the de-facto
      `hooks.sdd_gate._build_pid_probe` shared seam — pinned dead by the AC-4 extended grep
      (name absent everywhere).
    - **Deviations (recorded):** (1) SPEC/task said "check whether an infra module for
      `OsProcessProbe` already exists" — it did (`process_probe_adapter.py`), so `build_pid_probe`
      landed there (matches the SPEC-named home; no parallel module). (2) `specs.py`'s
      `from …spec_context import lease` import was removed (it became unused once the wrapper —
      its only `lease.PidProbe` user — was deleted); ruff would else flag F401. (3) `sdd_gate`
      + `context.py` gained top-level infra imports (previously the sdd_gate probe import was
      lazy) — clean under import-linter (no `hooks`/`cli`-no-infrastructure contract). NO
      `specs/backlog/**` staged; the pre-existing `specs/bugs/*.jsonl` change is not this task's.

## W5 — FR4 CI wiring + gates + ship (flat release: single ship gate)

- [x] T-54-20 DONE. FR4 `ff883f99` (ci.yml lint-imports step; preflight 5th Check
  fail-closed; wiring contract test; AC-7(d) captured). Archival `d1f7e988` (single
  atomic: 3 R100 renames → `_archive/v0.1.54/consumed-backlog/` + ledger + candidates
  prune; backlog doctor clean; invariants i+ii verified). QA ship gate: **APPROVE
  10/10** (handoff 2026-07-03T171013Z-qa-engineer-v0154-ship-gate, validated):
  lint-imports 8 kept/0 broken; cap 26 = 9/4/13 self-counted; RED ancestry genuine
  ×2; 4 sabotages zero-residue; golden byte-identical (101 KB fixture); **FROZEN
  SUITE ADJUDICATED HONORED** (2 files zero-diff, test_lease_main_probe zero-diff,
  test_lock_steal monkeypatch-target+docstring-only 9 lines, AC-4 greps all zero,
  positive live-probe test, 50-test no-steal suite green); FR4 collateral
  strengthens; 5 deviations = sound root-cause fixes; unpiped 4333 passed/17
  skipped exit 0 + ruff/mypy/public doctor/specs doctor 0 errors; no W1-W4 commit
  staged backlog; bug-ledger commits legitimately ADDITIVE. Routed to W6 closure:
  architecture.md "17 edges"→26, candidates R6 row → SHIPPED. Original checklist:
  FR4 CI wiring on the green tree, then ship:
  - **FR4 (first — on the already-green tree, architect A5/A10):** add a step to the existing
    `Lint (ruff)` job in `.github/workflows/ci.yml` (l.62): `poetry run lint-imports --config
    setup.cfg --no-cache` (no extra install). Add a `lint-imports --no-cache` check to
    `features/ci_preflight/service.py` `checks_for()` (executable via `_resolve_tool`, which
    **fails closed** when the tool is absent). Add
    `tests/contract/test_ci_preflight_includes_lint_imports.py` asserting the preflight tuple
    contains it AND covers the `_resolve_tool` fail-closed path. **AC-7(d):** delete the
    `lint-imports` Check from `checks_for()` ⇒ the test FAILS; revert.
    - **FR4 DONE (marker stays `[-]` — ship gate + archival complete the task).** software-engineer
      2026-07-03. Reservation `bf124922`; FR4 code `ff883f99`. **ci.yml:** `Lint (ruff)` job gains a
      `lint-imports (import-boundary contracts)` step running `poetry run lint-imports --config
      setup.cfg --no-cache` (no extra install — import-linter is in the dev group). **preflight:**
      `checks_for()` now returns 5 checks; `dadaia ci preflight` →
      `Running 5 preflight check(s)… [PASS] ruff format --check / [PASS] ruff check /
      [PASS] mypy --strict / [PASS] lint-imports / [PASS] pytest → All preflight checks passed.`
      (exit 0). Fail-closed: `_resolve_tool(..., require=True)` returns an actionable error argv
      (names `lint-imports` + `poetry install --with dev`) when the binary is absent — never a
      silent skip (architect A10). **AC-7(d):** deleting the `lint-imports` Check from
      `checks_for()` ⇒ contract test FAILS at
      `assert "lint-imports" in by_name` (check list collapses to
      `['ruff format --check', 'ruff check', 'mypy --strict', 'pytest']`); reverted. **Gates (AC-6):**
      `ruff format --check` + `ruff check --no-cache` + `mypy --strict` exit 0; `lint-imports`
      `8 kept, 0 broken`; full `dadaia ci preflight` exit 0 (covers full pytest); `dadaia specs doctor`
      exit 0 (12 pre-existing SPEC-DOC-031 WARNs, dispositioned at closure); `dadaia public doctor`
      `[ok] public-privacy`, exit 0. Consequence: the pre-push hook runs `dadaia ci preflight`, so
      every push now enforces the import contracts. Collateral test-side edits (AC-8 grep-tests
      discipline): `tests/unit/features/ci_preflight/test_service.py` (count 4→5) and
      `tests/e2e/features/test_ci_preflight_poetry_off_path.py` (fake-venv lint-imports stub +
      actionable fail-closed distinction) — flagged for qa ship-gate review. Remaining on this task:
      consumed-backlog archival at SHIP, QA ship gate, security push gate, push, PR, merge.
  - **Gates (AC-6):** unpiped `pytest` + `ruff format --check` + `ruff check` +
    `mypy --strict` + `lint-imports --no-cache` (`8 kept, 0 broken`) +
    `dadaia specs doctor` + `dadaia public doctor` all exit 0, locally and in CI.
  - **Consumed-backlog archival AT SHIP (single atomic commit):** move the 3 consumed
    entries → `specs/_archive/v0.1.54/consumed-backlog/` + write `consumed_backlog.json`;
    `dadaia backlog doctor` clean; verify no W1-W4 commit staged `specs/backlog`; exactly
    ONE push, after this commit (pid-probe anchors already killed in W4).
  - **QA ship gate** (attention: FR6 frozen-suite adjudication evidence for the 2
    forced-repoint frozen tests + the 2 untouched; cross-feature 13-edge completeness;
    cap==26 + per-family; CI-first-run green): APPROVE handoff.
  - **Security push gate:** APPROVE handoff `metrics.commit_sha` = pushed sha; push; CI
    green (watch until every job green); PR; merge.
  Owner: qa-engineer + security-reviewer + orchestrator.

## W6 — closure (CLOSURE phase)

- [ ] T-54-30 CLOSURE.md (Summary, Tasks, Validations, Drifts, Memory updates, Dispositions,
  Backlog returns, Archive=MOVE — SPEC-DOC-006). MEMORY edits (CLOSURE phase): update
  `architecture.md` Enforcement-state (CI-wired contracts; new `lifecycle-no-workflows` +
  `features-no-cross-feature`; **cap "17 edges" → 26** with the three-family breakdown 9/4/13;
  `json_workflow_model_policy_store` types in `core/models` + lean core port; single
  `infrastructure.process_probe_adapter.build_pid_probe`; `core/` file-I/O exceptions now
  AST-guarded — drop the "pending backlog" qualifier); record the FR6 frozen-suite
  adjudication in `quality-assurance.md`; note `tech-stack.md` unchanged. Disposition sweep:
  3 consumed entries terminal (`DELIVERED — v0.1.54`). `dadaia specs doctor` clean; archive
  (`git mv` via devops/operator); `ACTIVE.md → next` per the R6→R8 mandate; candidates R6
  row marked shipped. Owner: product-engineer.
