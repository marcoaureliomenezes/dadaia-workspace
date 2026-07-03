# TASKS — v0.1.54 — Import Boundaries

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets:
`container.py` W1-W4, `setup.cfg` W2-W3, `policy_doctor.py` W1-W2) are sequential — one
owner, no parallel `[-]`. Every implementation-wave task: NO `specs/backlog/**` paths staged
(archival is the single atomic SHIP commit, T-54-20). Every deletion/rename/repoint grep
includes `tests/`.

## W0 — definition

- [ ] T-54-01 SPEC/PLAN/TASKS authored from the 2026-07-03 inspection dossier (ports
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

- [ ] T-54-10 Fix the 5 red chains (4 edges) → `features-no-infrastructure` +
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

## W2 — FR2 + FR3 cycle break + cross-feature contract

- [ ] T-54-11 Break the `workflows ↔ lifecycle` cycle, then add the cross-feature contract.
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

## W3 — FR5 + FR7 direct-debt DI + core purity

- [ ] T-54-12 Complete `features → infrastructure` DI (remove 2 ignores, lower cap) + core
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

## W4 — FR6 pid-probe single public builder (isolated)

- [ ] T-54-13 One public `infrastructure/process_probe_adapter.build_pid_probe()`; repoint 6
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

## W5 — FR4 CI wiring + gates + ship (flat release: single ship gate)

- [ ] T-54-20 FR4 CI wiring on the green tree, then ship. Checklist:
  - **FR4 (first — on the already-green tree, architect A5/A10):** add a step to the existing
    `Lint (ruff)` job in `.github/workflows/ci.yml` (l.62): `poetry run lint-imports --config
    setup.cfg --no-cache` (no extra install). Add a `lint-imports --no-cache` check to
    `features/ci_preflight/service.py` `checks_for()` (executable via `_resolve_tool`, which
    **fails closed** when the tool is absent). Add
    `tests/contract/test_ci_preflight_includes_lint_imports.py` asserting the preflight tuple
    contains it AND covers the `_resolve_tool` fail-closed path. **AC-7(d):** delete the
    `lint-imports` Check from `checks_for()` ⇒ the test FAILS; revert.
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
