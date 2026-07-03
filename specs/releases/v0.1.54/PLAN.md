# PLAN — v0.1.54 — Import Boundaries

**Status:** Aprovado

## Wave map (4 implementation waves + ship + closure)

The cut respects three ordering laws: (1) the **cycle-break seam (FR2) lands before** the
`features-no-cross-feature` contract (FR3) that documents the post-break 13-edge list; (2)
**CI wiring (FR4) lands LAST**, wiring an already-green tree; (3) **pid-probe (FR6) is
independent** and isolated so its frozen-suite adjudication is self-contained.

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-03 inspection (targets
  caller-verified; ports/anchors confirmed; the exact 13 post-FR2 cross-feature edges
  reconstructed from the tree; stale "17"-cap contradiction recorded); dual definition
  review (software-architect + qa-engineer) REJECT×2 — ALL amendments folded; `Aprovado`;
  definition commit.

- **W1 — FR1 red-chain remediation (make reality green).** (a) Relocate the
  `json_workflow_model_policy_store` data types to `core/models/workflow_execution.py` (no
  shim; repoint all importers incl. `container.py:33` TYPE_CHECKING); add the lean
  `load/parse/save` port + `container.build_workflow_model_policy_store`; inject into
  `policy_doctor` (remove default construction l.288) + `panel.views.workflow_policy` ONLY
  (policy_resolver needs none); CLI caller `cli/commands/lifecycle.py:1285` injects. (b) Move
  `_derive_cli_anchors` to a `cli/`-composition helper; thread `cli_anchors` frozenset into
  `build_registry`/`run_backlog_doctor`/`ContextSelector.sel_backlog_index` across the six
  `build_registry` sites. Rationale: fix the 2 broken contracts first for a green base. No
  new contract, no `ignore_imports`/cap change. AC-8 ledger.

- **W2 — FR2 + FR3 cycle break + cross-feature contract (author the guards).** Sequenced
  **FR2 first**: create `features/lifecycle/governed_catalog.py` (the seam); shrink
  `workflows/dadaia_catalog.py` to presentation + a single genuine `governed_catalog` import
  that re-exports `governed_workflow_catalog` (9 test importers ZERO edits); repoint
  `container.py:735` + `policy_doctor.py:405` (intra-lifecycle); add the directed
  `lifecycle-no-workflows` contract **RED-first**; AC-7(a) sabotage; golden byte-identical
  test. Then **FR3**: add `features-no-cross-feature` with the exact 13-edge `ignore_imports`
  **RED-first**; AC-7(b) sabotage; broaden the cap-test docstring; per-family assertions.
  Cap → **28** here (infra 11 + subprocess 4 + cross-feature 13), re-pinned. Rationale: both
  are new-contract, RED-first, sabotaged FRs and are sequentially dependent.

- **W3 — FR5 + FR7 direct-debt DI + core purity (setup.cfg/contract hygiene).** Complete
  `WorkflowProvider`/`AgentsProvider` DI; delete the two direct `markdown_*_store` imports;
  remove the 2 ignore edges; **lower the cap 28 → 26 in the same commit** (infra 9 +
  subprocess 4 + cross-feature 13; correct the stale "(still 17)" comment). Add the AST-based
  `core/` file-I/O purity guard **RED-first**; AC-7(c) sabotage. Rationale: both are
  `setup.cfg`/contract-test edits — one owner after W2. AC-8 ledger.

- **W4 — FR6 pid-probe single public builder (isolated).**
  `infrastructure/process_probe_adapter.build_pid_probe()` (NOT container — hook/lease
  hot-path); repoint the 6 sites (lease keeps its dynamic `importlib` pattern retargeted to
  the infra module → zero new static edge, no ignore); delete the 2 private wrappers;
  extended grep AC (incl. tests/) + positive `lease._main_pid_probe` test; preserve
  `None ⇒ TTL` + no-steal. Run `lint-imports` locally. FROZEN-SUITE partition (2 adjudicated
  repoints, 2 invariant-only untouched, 2 non-frozen forced repoints). Rationale: independent
  + touches the frozen suite — isolate the adjudication.

  > **Ordering note:** FR6 (W4) is the last *implementation* wave; FR4 (CI wiring) is folded
  > into the **ship wave (W5)** as its first task, on the already-green tree, so the first
  > enforced CI run passes.

- **W5 — gates + ship (flat release: single ship gate).** FR4 CI wiring (ci.yml `Lint (ruff)`
  step `poetry run lint-imports --config setup.cfg --no-cache`; preflight check + fail-closed
  `_resolve_tool`; preflight-wiring contract test; AC-7(d) sabotage) on the green tree; full
  local gates (AC-6); **consumed-backlog archival at SHIP** (3 entries →
  `_archive/<id>/consumed-backlog/` + `consumed_backlog.json`, single atomic commit, no W1-W4
  commit staged `specs/backlog`); QA ship-gate review (incl. FR6 frozen-suite adjudication);
  security push-gate APPROVE keyed to the pushed sha; push; CI green; PR; merge.

- **W6 — closure (CLOSURE phase).** CLOSURE.md (Validations + Drifts); MEMORY edits
  (`architecture.md` enforcement-state + cap "17"→26 fix; `quality-assurance.md` FR6
  adjudication note; `tech-stack.md` no-change note); `dadaia specs doctor` clean; archive;
  `ACTIVE.md → next` per the R6→R8 mandate; candidates R6 row marked shipped.

## Write sets (disjoint per wave; `container.py` + `setup.cfg` shared → sequential ownership)

| Wave | Files |
|---|---|
| W1 | `core/models/workflow_execution.py` (new — relocated types), `core/protocols/workflow_model_policy_store.py` (new port), `features/lifecycle/policy_resolver.py` (type import repoint), `features/lifecycle/policy_doctor.py` (inject + drop default l.288), `features/panel/views/workflow_policy.py`, `features/backlog/subject_registry.py`, `cli/` composition helper (new `_derive_cli_anchors` home), `cli/main.py`, `cli/commands/lifecycle.py`, `dadaia_workspace/container.py` (port wiring + `:33` TYPE_CHECKING + `:1069`/`:1139` cli_anchors), `newartifacts.py`, `features/backlog/doctor.py`, `features/lifecycle/context_selector.py`, their tests |
| W2 | `features/lifecycle/governed_catalog.py` (new seam), `features/lifecycle/policy_doctor.py` (`:405` repoint), `features/workflows/dadaia_catalog.py`, `dadaia_workspace/container.py` (`:735` repoint), `setup.cfg` (+2 contracts, +13 cross-feature ignores), `tests/contract/test_import_linter_ignore_cap.py` (cap→28 + per-family + docstring), their tests |
| W3 | `dadaia_workspace/container.py` (provider DI), `features/workflows/service.py`, `features/agents/reader.py`, `setup.cfg` (−2 ignores, cap→26, fix "(still 17)"), `tests/contract/test_import_linter_ignore_cap.py` (cap→26 + per-family), `tests/contract/test_core_file_io_purity.py` (new AST guard), their tests |
| W4 | `infrastructure/process_probe_adapter.py` (`build_pid_probe`), `dadaia_workspace/container.py` (delete `:237`), `hooks/sdd_gate.py`, `cli/commands/specs.py`, `cli/commands/lock.py`, `cli/commands/context.py`, `features/spec_context/lease.py` (`_main_pid_probe` retarget), the 4 frozen tests (2 adjudicated / 2 untouched) + `test_context_release_cmd.py` + `test_container.py`, their tests |
| W5 | `.github/workflows/ci.yml`, `features/ci_preflight/service.py`, `tests/contract/test_ci_preflight_includes_lint_imports.py` (new), then `specs/**` per the ship ritual |
| W6 | `specs/**` per the closure ritual (CLOSURE.md + `specs/memory/**`) |

**`dadaia_workspace/container.py` is shared W1/W2/W3/W4** (architect A10 — sequential, one
owner, disjoint edits: W1 port+cli_anchors wiring, W2 `:735` catalog repoint, W3 provider DI,
W4 delete `:237`). `setup.cfg` is shared W2/W3 (sequential). `features/lifecycle/policy_doctor.py`
is shared W1 (inject) / W2 (`:405` repoint) — sequential, disjoint lines. No parallel `[-]`.

## Test strategy

- **RED-first per new contract (FR2, FR3, FR7).** The RED commit proves the new contract
  fails against the pre-fix tree; capture the failure tail on the task line; the fix commit
  greens it. RED ancestor verifiable in branch history (AC-3).
- **AC-7 mutation-sanity per new contract/test** with the exact QA A4 targets (a-d): one-line
  sabotage ⇒ FAIL, captured, reverted.
- **AC-8 surviving/dead ledger per wave**, greps include `tests/` (v0.1.53 lesson).
- **Behavior-preserving rewires** (FR1/FR2/FR5/FR6): the existing unit/integration suites are
  the regression net; add targeted before/after assertions where a rewire could silently drop
  behavior — FR2 uses the **golden byte-identical** `list_dadaia_workflows()` + diagram-SVG
  test; FR6 adds the positive `lease._main_pid_probe` test.
- **FR6 frozen suite:** invariant-preserving only; QA adjudication handoff with byte-level
  no-steal evidence for the 2 forced-repoint frozen tests is a ship-gate deliverable; the 2
  invariant-only frozen tests are confirmed untouched.
- **Cap contract:** `test_recorded_cap_is_not_stale_above_reality` (total) + per-family
  per-contract-section assertions re-pin exactly at each `setup.cfg` edit — a wrong 13-edge
  set fails loudly.
- **FR4 fail-closed:** the preflight-wiring test covers both presence of the `lint-imports`
  check AND `_resolve_tool` hard-erroring when the tool is absent (architect A10).
- Full unpiped `pytest` + ruff + mypy + `lint-imports --no-cache` + `public doctor` +
  `specs doctor` locally before push (AC-6). `lint-imports` runs `--no-cache` everywhere.

## Rollback

Single feature branch `feature/v0.1.54` (base `d48ef6db`). Each wave is one or a small set
of commits; RED commits mark where a contract is established. Rollback = revert the wave's
commits or drop the branch. The relocations (FR1 types, FR2 seam, FR6 builder) are
single-commit recoverable via git; no data migration, no irreversible step before SHIP.
Consumed-backlog archival is the last atomic commit before the single push — recoverable by
reverting that one commit if the push is aborted.
