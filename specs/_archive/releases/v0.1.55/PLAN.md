# PLAN — v0.1.55 — Architecture Decomposition

**Status:** Aprovado

Dual definition review folded (software-architect REJECT + qa-engineer REJECT). The wave cut
and write sets below carry the binding reconciliations R-1..R-8 (PidProbe leaf; shared-leaf
pure-helper allocation + external-surface repoint; coordinator-owns-ORDER; deterministic golden;
delete-api.py no-facade + 14 test importers; FR4 harness-id channel; FR5 idea-status gate;
fenced-mermaid `.md`).

## Wave map (5 implementation waves + ship + closure)

Ordering laws: (1) the **three structural moves are independent** — sequenced W1→W2→W3 for clean
per-wave golden + AC-8 ledgers + isolated rollback; (2) each structural wave carries its **own
golden + same-commit `setup.cfg`/cap update + AC-8 ledger**; (3) the **two bug fixes (FR4/FR5) +
the workspace_clean docstring (FR6) are independent** → one wave (W4); (4) **UML assets (FR7)
land LAST** (W5) — they diagram the POST-split shape.

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-03 inspection dossier; mandatory
  release-definition grill; dual definition review REJECT×2 — ALL amendments folded (R-1..R-8 +
  A7/A9 items); `Aprovado` (after QA re-verify); definition commit.

- **W1 — FR1 SpecsDoctor decomposition.** Capture the DETERMINISTIC issue-code golden PRE-split
  (in-process on a fixed fixture root; normalize `specs_dir` + each issue `path` → `<SPECS>`;
  freeze `date.today` + `datetime.now(tz=UTC)` → 2026-07-15; fixture triggers ≥1 issue from EACH
  of the six families, interleaved order). Extract the leaves `doctor_types.py` (types +
  `PidProbe = Callable[[int], bool]`) and `doctor_common.py` (the 5 cross-validator pure free
  functions); extract the six validator classes with the exact family-local helper mapping;
  shrink `doctor.py` to a delegation-only coordinator that **owns check()/fix() ORDER** (exact
  interleaved sequence; fix() code-dispatch TREE-4→structural.fix_tree4,
  SPEC-DOC-034→closure_audit.fix_archive_dir), typed `pid_probe: doctor_types.PidProbe`.
  `spec_context.{lease,session_identity}` ONLY in `doctor_coherence`; `subprocess_runner` ONLY
  in `doctor_memory`; coordinator imports neither. Repoint the external surface (NO new shims):
  `features/specs/__init__.py` (Severity/SpecsDoctorIssue source→doctor_types),
  `cli/commands/specs.py` (`_read_active_md`→`doctor_common.read_active_md`), the 3 test
  importers. Same commit: `setup.cfg` 4 doctor-edge repoints; cap re-verify 26 = 9/4/13.
  AC-1 delegation-only + size-ceiling probes. AC-7(a) golden sabotage; AC-7(c) ceiling sabotage.
  Golden byte-identical. AC-8 ledger. NO `specs/backlog`.

- **W2 — FR3 reports triplet merge.** Create `features/reports/` (`next`/`retention`/`validation`
  submodules); delete the three `reports_*` packages. Repoint the FULL surface (A7): production
  (`container.py`, `cli/commands/reports.py`, `lifecycle/report_workflow.py`,
  `core/protocols/handoff_validator.py:4` docstring) + tests (rename
  `tests/unit/features/reports_{next,retention,validation}/` → `tests/unit/features/reports/`;
  `test_reports_validation_service.py`, `test_reports_retention_cleanup.py`,
  `test_lifecycle_push_preflight.py`, `test_api_contract.py`). Same commit: `setup.cfg`
  `modules =` (−3 reports_* / +1 reports) + edge #7 target (`reports_validation.service` →
  `reports.validation`); cap re-verify 26 = 9/4/13 (unchanged). Reports consumers' suites green.
  AC-8 ledger (incl. textual refs). NO `specs/backlog`.

- **W3 — FR2 panel api.py per-domain decomposition (delete api.py; no facade).** Capture the
  route-response golden PRE-split. Split the 24 functions into per-domain modules
  (`api_agents` holds `render_api_agents_canonical` — anchor dies); **DELETE `api.py`** (no
  facade/barrel); `container.py` imports each `render_api_*` from its per-domain module via
  named imports. Repoint ALL 14 test importers (verbatim list in the write set) + the
  `reports_doc.py:5` textual ref. NO `setup.cfg` change (AC-3 re-verifies untouched). Golden
  byte-identical. AC-1 api ceiling (≤ 450; trivially met with api.py deleted). AC-7(b) golden
  sabotage. AC-8 ledger. NO `specs/backlog`.

- **W4 — FR4 + FR5 + FR6 (independent).**
  - **FR4 (harness-id channel):** at `bind`, persist the harness-native session id
    (`CODEX_SESSION_ID`/`CLAUDE_CODE_SESSION_ID`) into the session record / harness-id→context
    index (`cli/commands/context.py`); extend `_session_context` (`core/specs_resolver.py`) to
    resolve via harness-native ids when `DADAIA_SESSION_ID` absent, **guarded** to live records
    only (heartbeat-fresh/pid-alive). Contingency: actionable error, NEVER a blind fallback.
    Regression: disjoint-`ancestry_pids` modeling (RED pre-fix; GREEN drives the harness-id
    channel; concurrent two-marker never-cross-attribute; descendant still resolves;
    stale/inherited-id must NOT resolve to a foreign context). AC-7(d) revert-fix sabotage.
  - **FR5 (idea-status gate — ROOT):** status-gate `features/backlog/doctor.py` `_check_schema`
    (idea EXEMPT from no-intents + unresolved-subject; mandatory at candidate+; malformed-intents
    still fires). `_BACKLOG_STUB` keeps `status: idea`, gains `description:` + a commented
    `intents[]` template (teaching, no live dummy). Edit the PUBLIC asset
    `public/scaffold/backlog/README.md` (idea-freedom + intents@candidate+ + 5 subject kinds +
    `dadaia backlog subjects` + non-Python-repo note); `dadaia public stage && install --target
    all && doctor`. E2E: fresh scaffold w/o catalog.json → `backlog new` → `backlog doctor` exit
    0. AC-7(e) flip-to-candidate sabotage.
  - **FR6:** one-line STANDS-ALONE scope docstring on `features/workspace_clean`.
  AC-8 ledger. NO `specs/backlog`.

- **W5 — FR7 UML assets (LAST).** Create `specs/assets/architecture/*.md` with fenced ```mermaid
  blocks (doctor classDiagram, api classDiagram/module graph, 23-feature package graph) authored
  from the W1-W3 result; add the **introspection** drift-guard (`test_architecture_diagrams_
  current.py` imports `doctor_*`, the per-domain api modules, `features.reports` — no hardcoded
  name list). NO `.mmd`, NO `.svg`. AC-7(f) rename-without-diagram-update sabotage. AC-8 ledger.
  (The `architecture.md` "Visual evidence" reference is a CLOSURE/memory edit — W7.)

- **W6 — gates + ship.** Full local gates (AC-6): unpiped `pytest` + `ruff format --check` +
  `ruff check --no-cache` + `mypy --strict` + `lint-imports --no-cache` (8 kept, 0 broken) +
  `dadaia specs doctor` + **`dadaia backlog doctor`** + `dadaia public doctor`. **Consumed-backlog
  archival AT SHIP (single atomic commit — the release kills the `api.py#render_api_agents_
  canonical` anchor):** move `architecture-uml-decomposition` → `specs/_archive/v0.1.55/
  consumed-backlog/` + `consumed_backlog.json`; `backlog doctor` clean; verify no W1-W5 commit
  staged `specs/backlog`. QA ship-gate; security push-gate keyed to the pushed sha; push; CI
  green (watch until every job green); PR; merge.

- **W7 — closure (CLOSURE phase).** CLOSURE.md (Validations + Drifts + Dispositions). MEMORY edits
  (§SPEC 8): `architecture.md` (23 features; doctor coordinator+validators+leaves; api per-domain
  / api.py deleted; cap unchanged 26 = 9/4/13 with repointed edges + PidProbe-leaf note; Visual
  evidence → the fenced-mermaid `.md` + regeneration law); `agent-comms.md`; `specs-doctor.md`;
  `sdd-bug-backlog-governance.md` (idea-status gate); `quality-assurance.md` (golden + ratchet
  precedent); `tech-stack.md` no-change. Bug disposition: `resolved --release v0.1.55` for both
  bugs. `catalog`/`index` regenerated. `dadaia specs doctor` clean; archive (`git mv` via
  devops/operator); `ACTIVE.md → next`; candidates R7 row shipped.

## Write sets (disjoint per wave; `container.py` + `setup.cfg` + the cap test shared → sequential)

| Wave | Files |
|---|---|
| W1 | `features/specs/doctor.py` (→ thin coordinator, owns ORDER), `features/specs/doctor_types.py` (new: types + `PidProbe`), `features/specs/doctor_common.py` (new: 5 pure helpers), `features/specs/doctor_{structural,memory,release,closure_audit,governance,coherence}.py` (new validators), `features/specs/__init__.py` (re-export source repoint), `cli/commands/specs.py` (`_read_active_md`→`doctor_common.read_active_md`), `setup.cfg` (4 edge repoints), `tests/contract/test_import_linter_ignore_cap.py` (re-verify 26 = 9/4/13), `tests/contract/test_module_size_ceiling.py` (new), the doctor golden test + fixtures, `tests/…/test_active_md_schema_v2.py` + `test_specs_evolution.py` + `test_scaffolder_doctor.py` (repoint), `tests/unit/features/specs/test_doctor_lint.py` (RE-HOME to `doctor_memory` — QA R10) + `test_doctor_ledger_invariants.py` (re-widen introspection), `container.py` (`build_doctor_service` — only if the factory signature changes) |
| W2 | `features/reports/{__init__,next,retention,validation}.py` (new), delete `features/reports_{next,retention,validation}/`, `container.py` (l.97-99 imports + l.465/484/514/835 factories), `cli/commands/reports.py`, `features/lifecycle/report_workflow.py`, `core/protocols/handoff_validator.py` (docstring), `setup.cfg` (`modules =` −3/+1; edge #7 target), `tests/contract/test_import_linter_ignore_cap.py` (re-verify), rename `tests/unit/features/reports_{next,retention,validation}/`→`tests/unit/features/reports/`, `tests/unit/test_reports_validation_service.py`, `tests/contract/test_reports_retention_cleanup.py`, `tests/integration/test_lifecycle_push_preflight.py`, `tests/unit/features/panel/test_api_contract.py` |
| W3 | **delete** `features/panel/views/api.py`, `features/panel/views/api_{servers,contexts,agents,workflows,sessions,academy,reports,health}.py` (new), `container.py` (l.63 + build_panel_views named-import repoint), `features/panel/views/assets/css/reports_doc.py` (docstring), `tests/contract/test_module_size_ceiling.py` (api ceiling), the api route-response golden test + fixtures, the **14** test importers: `tests/integration/panel/test_api_workflows.py`, `tests/integration/panel/test_api_agents.py`, `tests/integration/panel/test_workflows_api.py`, `tests/integration/panel/test_academy_route.py`, `tests/integration/test_panel_sessions_endpoint.py`, `tests/unit/features/panel/test_api_agents.py`, `test_api_agent_prompt.py`, `test_api_academy.py`, `test_api_workflows_list.py`, `test_api_workflows_detail.py`, `test_api_contract.py`, `test_views_api_sessions.py`, `test_build_panel_views.py`, `test_serve_report_identity.py` |
| W4 | `cli/commands/context.py` (bind persists harness-native session id), `core/specs_resolver.py` (`_session_context` harness-id resolve + staleness guard), the session-record schema/helper touched (verify: `features/spec_context/session_identity.py` and/or `hooks/_common.py resolve_session_id`), `features/backlog/doctor.py` (`_check_schema` idea-status gate), `features/spec_artifacts/new_artifacts.py` (`_BACKLOG_STUB`), `public/scaffold/backlog/README.md` (FR5, then stage/install), `features/workspace_clean/__init__.py` (FR6 docstring), FR4/FR5 regression tests |
| W5 | `specs/assets/architecture/*.md` (fenced mermaid), `tests/contract/test_architecture_diagrams_current.py` (new introspection drift-guard) |
| W6 | (gates only) then `specs/_archive/v0.1.55/consumed-backlog/` + `consumed_backlog.json` per the ship ritual |
| W7 | `specs/releases/v0.1.55/CLOSURE.md` + `specs/memory/**` per the closure ritual |

**`container.py` is shared W1/W2/W3** — sequential (W1 optional factory tweak, W2 reports
repoint, W3 named-import panel repoint). **`setup.cfg` + `test_import_linter_ignore_cap.py`** are
shared W1/W2 (sequential; cap stays 26 — every repoint is 1:1; if a per-family count moves the
release is wrong). **`test_module_size_ceiling.py`** is W1 (create + doctor ceiling) and W3 (api
ceiling). No parallel `[-]`.

## Test strategy

- **Golden behavior-preservation (FR1/FR2).** Capture pre-refactor output, assert byte-identical
  post. FR1 = DETERMINISTIC in-process capture: fixed fixture root, `<SPECS>` path normalization
  (CLI `specs_dir` + every issue `path`), clock frozen to 2026-07-15, ≥1 issue per family,
  interleaved order preserved. FR2 = each panel route's `(status, ct, body)` on a fixture state.
  FR3 (relocation) rides the existing reports consumer suites.
- **Coordinator-owns-ORDER (FR1).** The golden pins the interleaved sequence; AC-1 asserts the
  coordinator class has no `_check_*` body and no validator imports a sibling.
- **Cap tracking (FR1/FR3).** total `== 26` + per-family `9/4/13` re-run at each `setup.cfg`
  edit; the coordinator's PidProbe-leaf keeps cross-feature at 13 (a `lease.PidProbe` annotation
  would fail the per-family test at 14).
- **Anti-erosion ratchet (AC-1).** `test_module_size_ceiling.py` pins doctor ≤ 700, api ≤ 450.
- **Bug regressions (FR4/FR5).** FR4: disjoint-`ancestry_pids` deterministic modeling (four
  cases incl. the stale-inherited-id negative). FR5: fresh-scaffold-without-catalog E2E → clean;
  flip-to-candidate → BL-SCHEMA fires.
- **Drift-guard (FR7).** `test_architecture_diagrams_current.py` imports the decomposed modules
  and asserts the diagram `.md` mentions the live names (introspection — no hardcoded list).
- **AC-7 mutation-sanity per new test** (a-f): one-line sabotage ⇒ FAIL, captured, reverted.
- **AC-8 surviving/dead ledger per wave**, greps include `tests/` AND textual/docstring refs.
- **Frozen file:** `tests/unit/features/spec_context/test_doctor_lock_gc.py` confirmed
  **zero-diff** (different subsystem — `spec_context.doctor`, not `specs.doctor`).
- Full unpiped `pytest` + ruff + `mypy --strict` + `lint-imports --no-cache` + `specs doctor` +
  `backlog doctor` + `public doctor` locally before push (AC-6).

## Rollback

Single feature branch `feature/v0.1.55` (base `26c5089b`, v0.1.54 closure). Each wave is one or a
small set of commits; the goldens are captured on the wave's first commit as the baseline.
Rollback = revert the wave's commits or drop the branch. The relocations (doctor split, reports
merge, api delete/split) are git-recoverable single moves; no data migration, no irreversible
step before SHIP. The consumed-backlog archival is the last atomic commit before the single push
— recoverable by reverting that one commit. The public README edit is re-projectable via
`dadaia public install --target all --force`.
