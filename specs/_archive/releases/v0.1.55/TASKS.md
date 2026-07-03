# TASKS — v0.1.55 — Architecture Decomposition

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets:
`container.py` W1-W3, `setup.cfg` + the cap test W1-W2) are sequential — one owner, no parallel
`[-]`. Every implementation-wave task: NO `specs/backlog/**` paths staged (archival is the single
atomic SHIP commit, T-55-60 — the release kills the `api.py#render_api_agents_canonical` anchor).
Every move/rename/repoint grep **includes `tests/` AND non-import textual references**
(docstrings/comments/README).

## W0 — definition

- [x] T-55-01 SPEC/PLAN/TASKS authored from the 2026-07-03 inspection dossier (live shapes
  re-derived: doctor 2,830 / 54 methods; api 1,279 / 24 fns / 8 domains — audit's 1,402 stale;
  reports 845; post-split edge enumeration reconstructed — cap invariant 26 = 9/4/13; frozen-suite
  misattribution recorded). Mandatory release-definition grill on the picked set (1 backlog + 2
  open bugs). **Dual definition review (software-architect REJECT + qa-engineer REJECT) — ALL
  amendments folded:** R-1 PidProbe leaf alias; R-2 shared-leaf pure-helper allocation +
  external-surface repoint (no new shims); R-3 coordinator owns check()/fix() ORDER; R-4
  deterministic golden (path-normalize + clock-freeze + all-six-families); R-5 delete api.py, no
  facade, 14 test importers; R-6 FR4 harness-id channel + staleness guard + no-blind-fallback;
  R-7 FR5 idea-status BL-SCHEMA gate (root fix, self-subject rejected); R-8 fenced-mermaid `.md`,
  no mermaid-cli/`.svg`, introspection drift-guard; + A7 FR3 full move surface; A9 textual-ref
  greps; FR6 STANDS ALONE; AC-6 adds `backlog doctor`. `Aprovado` (after QA re-verify);
  definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 SpecsDoctor decomposition

- [x] T-55-10 Decompose `features/specs/doctor.py` into a thin `SpecsDoctor` coordinator (owns
  ORDER) + validator classes; behavior byte-identical. Checklist:
  - **Golden PRE-split, DETERMINISTIC (R-4):** capture `SpecsDoctor.check()` + `dadaia specs
    doctor --json` **in-process on a fixed committed fixture root**; normalize every absolute path
    (the CLI top-level `specs_dir` AND each issue `path`) to `<SPECS>`; **freeze the clock**
    (monkeypatch `date.today` + `datetime.now(tz=UTC)` → 2026-07-15). The fixture triggers **≥1
    issue from EACH of the six families** and preserves the interleaved `check()` order → committed
    golden.
  - **Extract the leaves (R-1/R-2, imports only stdlib + core, NO sibling-validator import):**
    `doctor_types.py` — `Severity`, `SpecsDoctorIssue`, `_MemoryMdSummary`, `PidProbe =
    Callable[[int], bool]`; `doctor_common.py` — the 5 cross-validator pure free functions
    `read_active_md`, `is_release_dir`, `iter_archive_release_dirs`, `is_legacy_nested_release`,
    `iter_all_release_dirs`.
  - **Extract the six validator classes** with the exact family-local helper mapping:
    `doctor_structural` (tree1-7, required dirs, agents.md; `fix_tree4`);
    `doctor_memory` (memory files/atomicity/image-links/mermaid, LINT-1, CAT-1 — **holds the lazy
    `infrastructure.subprocess_runner` import** + `_parse_memory_md`/`_iter_memory_md_files`);
    `doctor_release` (active.md, active-release artifacts, plan-line-limit, phase markers,
    unique/naming/semver + `_extract_status`/`_extract_created_date`);
    `doctor_closure_audit` (archive closures, archive-dirs-exist `fix_archive_dir`, audit
    disposition, loose-undisposed-audits, audits-naming-canon, no-orphan-specs);
    `doctor_governance` (bug status canon, bugs-jsonl invariant, backlog schema, consumed-backlog
    disposition, unarchived-terminal-backlog);
    `doctor_coherence` (constitution + file-refs + no-runtime-enum, orchestration-registry,
    specs-pattern-version, lease/session coherence — **holds the `spec_context.{lease,
    session_identity}` import** + `_validate_ctx_name` [single caller l.1394, verified] +
    `_split_tier_blocks`/`_extract_tier1_names`/`_extract_tier2_names`/`_extract_playbook_headings`).
  - **Coordinator (R-3):** `doctor.py` keeps `SpecsDoctor` (anchor SURVIVES); `__init__` public
    signature preserved but typed `pid_probe: doctor_types.PidProbe | None`; imports NEITHER
    `spec_context` NOR `subprocess_runner`. `check()` invokes the validators' public check methods
    in the EXACT original interleaved sequence; `fix()` code-dispatch TREE-4→structural.fix_tree4,
    SPEC-DOC-034→closure_audit.fix_archive_dir. No `_check_*` body remains in the coordinator.
  - **External-surface repoint (R-2, NO new shims):** `features/specs/__init__.py`
    (`Severity`/`SpecsDoctorIssue` source → `doctor_types`; `SpecsDoctor` stays from `doctor`);
    `cli/commands/specs.py` (`_read_active_md` → `doctor_common.read_active_md`); the 3 test
    importers `test_active_md_schema_v2.py` [`_read_active_md`], `test_specs_evolution.py`
    [`Severity`], `test_scaffolder_doctor.py` [`Severity`]. PLUS (QA R10):
    `tests/unit/features/specs/test_doctor_lint.py` RE-HOMED to `doctor_memory` (5
    `_check_lint1_memory_atoms()` call sites → the validator's public LINT-1 method;
    `doctor._LINT_SCRIPT` monkeypatch → `doctor_memory._LINT_SCRIPT`); and
    `test_doctor_ledger_invariants.py` l.677-684 re-widened so the
    `process_probe_adapter`-avoidance introspection covers the validator modules.
  - **Cap invariant:** `setup.cfg` SAME-commit edge repoints — cross-feature #12/#13 source
    `specs.doctor` → `specs.doctor_coherence`; features-no-infrastructure + features-no-subprocess
    `specs.doctor -> subprocess_runner` → `specs.doctor_memory -> subprocess_runner`. `lint-imports
    --no-cache`: `8 kept, 0 broken` (no "No matches for ignored import"). Cap test re-verify total
    `== 26` + per-family `9/4/13` (the coordinator's PidProbe-leaf keeps cross-feature at 13).
  - **AC-1 probes:** `SpecsDoctor` defines no `_check_*`; no validator imports a sibling validator;
    `tests/contract/test_module_size_ceiling.py` (new) — no `features/specs/doctor*.py` module >
    700 lines.
  - **AC-2 golden byte-identical** before/after. **AC-7(a):** mutate one validator issue
    description ⇒ golden FAILS; revert. **AC-7(c):** add a doctor stub module > 700 lines ⇒ ceiling
    test FAILS; revert.
  - **Frozen:** `tests/unit/features/spec_context/test_doctor_lock_gc.py` confirmed ZERO-diff
    (different subsystem — `spec_context.doctor.DoctorService`).
  - AC-8 ledger (surviving: every issue code + `check()`/`fix()`/`--json` surface + ORDER via the
    coordinator, asserted by the golden; the externally-consumed `Severity`/`SpecsDoctorIssue`/
    `read_active_md`; dead: none — pure decomposition). NO `specs/backlog`.
  Owner: software-engineer. (software-architect reviews the class boundaries.)
  - **DONE (software-engineer, 2026-07-03).** Commits: golden behavior lock `1213dafb`
    (`test(T-55-10)`), split `8511d0ab` (`refactor(T-55-10)`), closeout `<this commit>`.
    **Golden verdict:** BYTE-IDENTICAL — `test_doctor_golden.py` GREEN pre- and post-split
    (22 issues, 8 errors / 14 warnings, six families interleaved, clock frozen 2026-07-15,
    paths `<SPECS>`-normalized). **AC-7(a):** mutated `doctor_coherence.check_constitution`
    description ⇒ golden FAILED on the byte diff; reverted → GREEN. **AC-7(c):** added a
    719-line `doctor_sabotage_tmp.py` ⇒ `test_module_size_ceiling` FAILED; removed → GREEN.
    **Per-module line counts (all ≤ 700 ceiling; was 2,830):** coordinator `doctor.py` 224;
    leaves `doctor_types.py` 53, `doctor_common.py` 113; validators `doctor_structural.py`
    357, `doctor_memory.py` 479, `doctor_release.py` 480, `doctor_closure_audit.py` 312,
    `doctor_governance.py` 516, `doctor_coherence.py` 464. **Cap/lint:** `lint-imports
    --no-cache` = `8 kept, 0 broken` (zero "No matches for ignored import"); cap test
    `== 26` + per-family `9/4/13` GREEN (coordinator holds no `spec_context` edge — PidProbe
    leaf). **Gates:** full `pytest` 4337 passed / 17 skipped (exit 0); `ruff format --check`
    exit 0; `ruff check --no-cache` exit 0; `mypy --strict dadaia_workspace` exit 0.
    **AC-8 ledger — surviving:** every issue code + `check()`/`fix()`/`--json` surface + the
    interleaved ORDER (golden-pinned); the externally-consumed `Severity`/`SpecsDoctorIssue`
    (now sourced from `doctor_types`, package-re-exported) + `read_active_md` (public name in
    `doctor_common`); the coordinator's public `__init__`/`check`/`fix` signatures. **dead:**
    the 2,830-line god-module shape — the single `SpecsDoctor` class holding all 54
    validator/helper methods (now a 224-line delegation-only coordinator); no `_check_*` body
    remains in the coordinator; no re-export shims added. Frozen suite
    `spec_context/test_doctor_lock_gc.py` untouched (different subsystem — zero-diff).

## W2 — FR3 reports triplet merge

- [x] T-55-20 Merge `reports_next` / `reports_retention` / `reports_validation` into one
  `features/reports/` package. Checklist:
  - Create `features/reports/{next,retention,validation}.py` (current service + result classes;
    optional `__init__` re-exports to minimize consumer churn); **delete** the three
    `features/reports_*/` packages.
  - **Repoint the FULL surface (A7):** production — `container.py` (l.97-99 imports; l.465/484/514/835
    factories), `cli/commands/reports.py` (l.22/26), `features/lifecycle/report_workflow.py` (l.17
    — edge #7), `core/protocols/handoff_validator.py:4` (docstring `reports_validation` →
    `reports.validation`); tests — rename `tests/unit/features/reports_{next,retention,validation}/`
    → `tests/unit/features/reports/`, `tests/unit/test_reports_validation_service.py`,
    `tests/contract/test_reports_retention_cleanup.py`,
    `tests/integration/test_lifecycle_push_preflight.py`,
    `tests/unit/features/panel/test_api_contract.py` (+ AC-8 grep sweeps the rest).
  - **`setup.cfg` SAME-commit:** `features-no-cross-feature` `modules =` remove the three
    `dadaia_workspace.features.reports_{next,retention,validation}`, add
    `dadaia_workspace.features.reports`; edge #7 target repoint
    `...report_workflow -> ...features.reports.validation`. `lint-imports --no-cache`: `8 kept, 0
    broken`. Cap test re-verify total `== 26` + per-family `9/4/13` (unchanged — 1:1 target
    repoint; `modules =` is not edge-counted).
  - Reports consumers' suites green (validation/retention/next units + panel reports view + `cli
    reports`).
  - AC-8 ledger (surviving: handoff validation, reports retention, next-handoff discovery via the
    merged package; dead: the three top-level `reports_*` packages — pinned by the zero-import grep
    + `modules =` + the corrected docstrings). NO `specs/backlog`.
  Owner: software-engineer.
  - **DONE (software-engineer, 2026-07-03).** Commits: relocation `8f918dcf`
    (`refactor(T-55-20)`), closeout `<this commit>` (`chore(T-55-20)`). **Pure relocation —
    zero behavior change; no golden needed (rides existing reports consumer suites).**
    **Move (git mv, history-preserving):** `reports_next/service.py`→`reports/next.py`,
    `reports_retention/service.py`→`reports/retention.py`,
    `reports_validation/service.py`→`reports/validation.py`; new `reports/__init__.py`
    (package docstring, NO re-export barrel); three old packages DELETED. **Production
    repoints:** `container.py` l.97-99 imports; `cli/commands/reports.py` l.22/26 imports;
    `lifecycle/report_workflow.py` l.17; `core/protocols/handoff_validator.py:4` docstring
    (`reports_validation`→`reports.validation`). Factory NAMES `build_reports_*_service`
    UNCHANGED by design (identifiers, not module paths — SPEC repoints imports only, not
    l.57/316/643/465/484/514/835). **`setup.cfg` SAME commit:** `modules =` −3 reports_* /
    +1 `features.reports`; edge #7 1:1 target repoint
    `lifecycle.report_workflow -> features.reports.validation`. **Tests:**
    `reports_{next,retention,validation}/` merged → `tests/unit/features/reports/`
    (the two `test_service.py` collisions disambiguated →
    `test_next_service.py`/`test_retention_service.py`; `test_resolve_artifact_path.py`
    kept); imports repointed in `test_reports_validation_service.py`,
    `test_reports_retention_cleanup.py`, `panel/test_api_contract.py`;
    `tests/contract/README.md` asymmetry-map three rows collapsed to one live `reports` row
    (drives `test_lifecycle_asymmetry_map.py`). **Cap/lint:** `lint-imports --no-cache` =
    `8 kept, 0 broken` (zero "No matches for ignored import"); cap test `== 26` + per-family
    `9/4/13` GREEN (1:1 repoint, no count change; `modules =` is not edge-counted).
    **Grep evidence:** zero `features.reports_*` / `reports_*/` module-path references remain
    anywhere in `dadaia_workspace/`, `tests/`, `setup.cfg` (only the surviving factory
    identifiers `build_reports_*_service` + the unchanged contract filenames
    `test_reports_retention_cleanup.py`/`test_reports_validation_service.py` match a naive
    substring grep; memory/spec/archive refs deferred to W7 CLOSURE per §SPEC 8).
    **AC-7 (mutation-sanity, FR3):** planted a cross-feature import
    `features.reports.validation -> features.backlog.doctor` ⇒ `features-no-cross-feature`
    BROKEN (`7 kept, 1 broken`) — proves the merged package is enforced by the independence
    contract; reverted → `8 kept, 0 broken`. **Gates:** full `pytest` (tests/
    --ignore=tests/e2e/panel) 4337 passed / 17 skipped (exit 0); `ruff format --check`
    exit 0; `ruff check --no-cache` exit 0; `mypy --strict dadaia_workspace` exit 0;
    `specs doctor` exit 0. **AC-8 ledger — surviving:** report next-pointer discovery
    (`tests/unit/features/reports/test_next_service.py`), report retention
    (`tests/unit/features/reports/test_retention_service.py` +
    `tests/contract/test_reports_retention_cleanup.py`), handoff validation
    (`tests/unit/test_reports_validation_service.py` +
    `tests/unit/features/reports/test_resolve_artifact_path.py`) — all via the merged
    `features.reports` package; consumers green
    (`tests/integration/test_lifecycle_push_preflight.py`,
    `tests/unit/features/panel/test_api_contract.py`,
    `tests/contract/test_lifecycle_asymmetry_map.py`). **dead:** the three top-level
    `features/reports_{next,retention,validation}` packages (deleted, no facade/shim) —
    pinned by the zero-module-path grep + the `modules =` list + the corrected docstrings.

## W3 — FR2 panel api.py per-domain decomposition (delete api.py; no facade)

- [x] T-55-30 Split `features/panel/views/api.py` (24 fns / 8 domains) into per-domain view
  modules; DELETE api.py. Checklist:
  - **Golden PRE-split (R6 pattern):** each route's `(status, content_type, body)` on a fixture
    panel state → committed golden fixture.
  - Split into `api_{servers,contexts,agents,workflows,sessions,academy,reports,health}.py`
    (domain-private helpers move with their domain). `render_api_agents_canonical` moves into
    `api_agents` — the `api.py#render_api_agents_canonical` anchor DIES (archival-at-SHIP, T-55-60).
  - **Wiring (R-5): NO facade, NO barrel; DELETE `api.py`.** `container.py` imports each
    `render_api_*` from its per-domain module via explicit named imports (extend the l.63-91
    named-import pattern).
  - **Repoint ALL 14 test importers** (verbatim): `tests/integration/panel/test_api_workflows.py`,
    `tests/integration/panel/test_api_agents.py`, `tests/integration/panel/test_workflows_api.py`,
    `tests/integration/panel/test_academy_route.py`, `tests/integration/test_panel_sessions_endpoint.py`,
    `tests/unit/features/panel/test_api_agents.py`, `test_api_agent_prompt.py`, `test_api_academy.py`,
    `test_api_workflows_list.py`, `test_api_workflows_detail.py`, `test_api_contract.py`,
    `test_views_api_sessions.py`, `test_build_panel_views.py`, `test_serve_report_identity.py`.
    Plus the textual ref `features/panel/views/assets/css/reports_doc.py:5`.
  - **NO `setup.cfg` change** — verify each new module imports only `features.panel.service`. AC-3:
    `lint-imports` `8 kept, 0 broken`, cap 26 = 9/4/13 UNCHANGED by FR2.
  - **AC-1 size probe:** no `features/panel/views/api*.py` module > 450 lines (trivially met — api.py
    deleted).
  - **AC-2 golden byte-identical** before/after. **AC-7(b):** mutate one route body ⇒ golden FAILS;
    revert.
  - AC-8 ledger (surviving: every route response via the per-domain modules — golden; dead: the
    monolithic `api.py` module — deleted, no facade). NO `specs/backlog`.
  Owner: software-engineer.
  - **DONE (software-engineer, 2026-07-03).** Commits: golden behavior lock `e72c49ef`
    (`test(T-55-30)`), split `5cde83b4` (`refactor(T-55-30)`), closeout `<this commit>`
    (`chore(T-55-30)`). **Golden verdict:** BYTE-IDENTICAL — `test_api_golden.py` GREEN
    pre- and post-split (24 routes across all 8 domains captured; timestamps `<TS>`-,
    version `<VER>`-, and fixture workspace_root `<WS>`-normalized; determinism confirmed
    across separate pytest invocations). Pre==post proven by regenerating the golden
    against the restored monolith `api.py`, then reproducing it byte-identically from the
    per-domain modules. **AC-7(b):** mutated `api_academy` route body (`"modules"` →
    `"MODULES"`) ⇒ golden FAILED on the byte diff; reverted → GREEN. **AC-1 ceiling
    (≤ 450):** all `api_*.py` ≤ 429 — `api_agents.py` 429, `api_reports.py` 354,
    `api_workflows.py` 326, `api_sessions.py` 85, `api_servers.py` 67, `api_contexts.py`
    50, `api_academy.py` 49, `api_health.py` 23 (was one 1,279-line module);
    `test_module_size_ceiling.py` extended with the api ceiling + an `api.py`-stays-deleted
    guard. **Wiring (R-5):** `container.py` imports each `render_api_*` from its per-domain
    module via explicit named imports; `build_panel_views` route→function table UNCHANGED
    (no facade, no barrel; `api.py` DELETED). **14 test importers repointed** (verbatim):
    `tests/integration/panel/{test_academy_route,test_api_agents,test_api_workflows,
    test_workflows_api}.py`, `tests/integration/test_panel_sessions_endpoint.py`,
    `tests/unit/features/panel/{test_api_academy,test_api_agent_prompt,test_api_agents,
    test_api_contract,test_api_workflows_detail,test_api_workflows_list,test_build_panel_views,
    test_serve_report_identity,test_views_api_sessions}.py` (the last re-homes both its
    `views import api as api_module` and `views.api import render_api_sessions` to
    `api_sessions`). **Textual refs swept (AC-8/A9):**
    `features/panel/views/assets/css/reports_doc.py:5` and
    `tests/unit/features/panel/test_serve_report_identity.py:3` (`views/api.py` →
    `views/api_reports.py`). Zero `panel.views.api`-non-`api_` references remain in
    `dadaia_workspace/` or `tests/`. **Cap/lint:** `setup.cfg` UNTOUCHED (FR2 changes zero
    edges — each new module imports only `features.panel.service`); `lint-imports
    --no-cache` = `8 kept, 0 broken`; cap test `== 26` + per-family `9/4/13` GREEN. **Gates:**
    full unpiped `pytest` (tests/ --ignore=tests/e2e/panel) 4340 passed / 17 skipped (exit 0);
    `ruff format --check` (764 files) exit 0; `ruff check --no-cache` exit 0; `mypy --strict
    dadaia_workspace` (301 files) exit 0; `dadaia specs doctor` exit 0.
    **AC-8 ledger — surviving (route behaviors preserved via the per-domain modules, golden-
    pinned + per-domain suites):** servers = `render_api_servers`
    (`test_api_contract.py`/`test_build_panel_views.py`); contexts = `render_api_contexts`
    (same); agents = `render_api_agents_canonical`+`render_api_agent_prompt`
    (`unit/.../test_api_agents.py`, `test_api_agent_prompt.py`, `integration/panel/test_api_agents.py`);
    workflows = `render_api_workflows_list`/`render_api_workflow_detail`/
    `render_api_dadaia_workflows_list`/`render_api_dadaia_workflow_detail`
    (`test_api_workflows_list.py`, `test_api_workflows_detail.py`,
    `integration/panel/test_api_workflows.py`, `test_workflows_api.py`); sessions =
    `render_api_sessions` (`test_views_api_sessions.py`,
    `integration/test_panel_sessions_endpoint.py`); academy = `render_api_academy`
    (`test_api_academy.py`, `integration/panel/test_academy_route.py`); reports =
    `render_api_reports`/`serve_report_file`/`mark`/`unmark`/`delete_report_file`
    (`test_api_contract.py`, `test_serve_report_identity.py`, `test_views_reports.py`);
    health = `render_health` (`test_api_golden.py`, panel handler tests) — all cross-cut by
    `test_api_golden.py` (24-route golden) + `test_build_panel_views.py` (real
    `container.build_panel_views` wiring). **dead:** the 1,279-line monolithic
    `features/panel/views/api.py` (deleted, no facade/shim) AND the
    `panel.views.api` import path (pinned by the zero-`views.api` grep + the
    `api.py`-stays-deleted ceiling guard); the anchor
    `api.py#render_api_agents_canonical` DIES (archival-at-SHIP, T-55-60). NO
    `specs/backlog` staged in any W3 commit.

## W4 — FR4 + FR5 + FR6 bug fixes + scope docstring (independent)

- [x] T-55-40 Fix `bugs-append-ignores-persisted-bind` (FR4), `backlog-new-stub-readme-lag-
  intents-schema` (FR5), and add the `workspace_clean` scope docstring (FR6). Checklist:
  - **FR4 fix channel (R-6, DECIDED):** at `bind` (`cli/commands/context.py`), persist the
    harness-native session id (`CODEX_SESSION_ID`/`CLAUDE_CODE_SESSION_ID`, via
    `hooks/_common.resolve_session_id` l.132-138) into the session record / a harness-id→context
    index. Extend `_session_context` (`core/specs_resolver.py:25`) to resolve via harness-native
    ids **when `DADAIA_SESSION_ID` is absent** — ahead of `_persisted_bind_context`. **Staleness
    guard (NON-NEGOTIABLE):** a harness-id match resolves ONLY when its session record is live
    (heartbeat-fresh/pid-alive) — a stale/inherited id must NOT resolve to a foreign context.
    **Contingency:** if no stable per-session channel exists, emit an ACTIONABLE ERROR (point to
    `--specs-dir`/`--print-env` eval), NEVER a blind first-ALIVE/single-marker fallback.
  - **FR4 regression (AC-4, deterministic — disjoint `ancestry_pids`, no spawned processes):** (i)
    bind-epoch marker chain `[A1,A2]`, resolve with disjoint `{B1,B2}` → RED `BadParameter`
    pre-fix; GREEN drives the harness-id session-record channel; (ii) two markers → never
    cross-attribute; (iii) descendant/same-shell still resolves; (iv) STALE/inherited harness-id
    must NOT resolve to a foreign bound context. **AC-7(d):** revert the fix line ⇒ (i) FAILS;
    revert.
  - **FR5 doctor gate (R-7, ROOT fix):** status-gate `features/backlog/doctor.py` `_check_schema`
    — `status: idea` entries EXEMPT from the "no intents[] declared" (l.127) + unresolved-subject
    (l.145-149) errors; mandatory at `candidate`+. NOT a blanket exemption (malformed-`intents:`
    still fires at any status). The self-referential-subject path is REJECTED.
  - **FR5 stub:** `_BACKLOG_STUB` (`features/spec_artifacts/new_artifacts.py` l.103) keeps
    `status: idea`, gains a `description:` frontmatter field + a **commented `intents[]` template**
    in the body (teaching template, NO live dummy subject).
  - **FR5 README (PUBLIC asset):** `public/scaffold/backlog/README.md` documents idea-stage freedom
    (intents optional at `idea`), the typed `intents[]` requirement at `candidate`+, the five
    subject kinds (code/cli/catalog/doc/invariant), a `dadaia backlog subjects` pointer, and the
    non-Python-repo note (code anchors are Python-derived only). Run `dadaia public stage && dadaia
    public install --target all && dadaia public doctor` (`[ok] public-privacy`).
  - **FR5 E2E regression (AC-4):** fresh scaffold **without `catalog.json`** → `dadaia backlog new
    <slug>` → `dadaia backlog doctor` exit 0, zero BL-SCHEMA. **AC-7(e):** flip the fresh stub's
    `status` to `candidate` ⇒ `backlog doctor` BL-SCHEMA FIRES; revert.
  - **FR6:** one-line module scope docstring on `features/workspace_clean` — STANDS ALONE
    (`WorkspaceCleanService` = TTL reclaim of ephemeral `.dadaia/` zones vs `WorkspaceService` =
    bootstrap/init — opposite lifecycle ends), records the create-vs-reclaim rationale. No behavior
    change.
  - AC-8 ledger (surviving: codex bound-context resolution via the harness-id channel, concurrent
    multi-session safety, the stub generator + README contract, the idea-status gate,
    `workspace_clean`'s scope; dead: none — restorative fixes + one scoped doctor semantics
    refinement). NO `specs/backlog`. Owner: software-engineer.
  - **DONE (software-engineer, 2026-07-03).** Commits: FR4 RED `4f964b1c`
    (`test(T-55-40)` — folds the `[-]` reservation), FR4 fix `e95f145f` (`fix(T-55-40)`),
    FR5 E2E RED `98077727` (`test(T-55-40)`), FR5+FR6 fix `e71edb06` (`fix(T-55-40)`),
    closeout `<this commit>` (`chore(T-55-40)`).
    **FR4 — harness-native bind channel (bug bugs-append-ignores-persisted-bind).** Root
    cause: a codex `dadaia bugs append` is not a process-descendant of the bind, so its
    ancestry is disjoint from the bind-epoch marker → `_persisted_bind_context` misses →
    `BadParameter`. Fix (per-session-deterministic, no blind fallback): new leaf
    `core/session_env.py` = single source of the harness env-name list
    (`CLAUDE_CODE_SESSION_ID`/`CODEX_SESSION_ID`); `hooks/_common.resolve_session_id`
    consumes it (no duplicated literal); `bind` (`cli/commands/context.py`) also persists a
    session record keyed by the harness-native id (best-effort; the PostToolUse heartbeat
    renews `sessions/<harness_id>.json`); `_session_context` (`core/specs_resolver.py`)
    resolves via that id when `DADAIA_SESSION_ID` is absent, AHEAD of the ancestry path,
    gated by a **staleness guard** (`core.lock_liveness.is_stale` over
    `last_seen_at`/`ttl_seconds`, pid_probe=None — the bind pid is dead by construction). No
    new import edge (all core→core / hooks→core / cli→core). **Four AC-4 regression cases
    (deterministic, disjoint `ancestry_pids`, no spawned processes; RED tail:
    `2 failed, 5 passed` — the two harness-channel GREEN-targets fell through to
    BadParameter / None pre-fix):** (i) disjoint-ancestry marker + LIVE harness record ⇒
    resolves via the channel (GREEN); (ii) two markers with disjoint chains ⇒ ancestry
    matching exactly one never cross-attributes; (iii) descendant/same-shell still resolves
    via the unchanged ancestry path; (iv) STALE (heartbeat-old) harness record ⇒ does NOT
    resolve, falls through to the actionable BadParameter. **AC-7(d):** sabotaged the
    harness-channel fix line (`if False and harness_id:`) ⇒ (i) FAILED
    (`2 failed, 5 passed`); restored ⇒ `7 passed`. Eval-flow + ancestry paths unchanged
    (existing `test_specs_resolver.py` + `test_cli_bound_session_resolution.py` +
    `test_sdd_post_gate.py` green).
    **FR5 — idea-status BL-SCHEMA gate (bug backlog-new-stub-readme-lag-intents-schema, ROOT
    fix OQ-1 INVERSION).** `backlog/doctor._check_schema` status-gates the resolvable-typed-
    intents requirement: `status: idea` is EXEMPT from "no intents[] declared" + the
    unresolved-subject errors; both mandatory at `candidate`+. NOT blanket — malformed
    `intents:` and invalid status still fire at any status. `_BACKLOG_STUB` keeps
    `status: idea`, gains a `description:` field + a COMMENTED `intents[]` teaching template
    (five subject kinds + non-Python-repo note; no live dummy subject). PUBLIC asset
    `public/scaffold/backlog/README.md` documents idea-freedom, intents@candidate+, the five
    subject kinds, `dadaia backlog subjects`, and the non-Python-repo note; re-projected
    (`stage`+`install --target all`+`doctor` → `[ok] public-privacy`, exit 0). **E2E RED tail:
    `1 failed, 1 passed` — the fresh stub fired BL-SCHEMA "no intents[] declared" pre-fix.**
    **AC-7(e):** flipping the fresh stub `idea`→`candidate` FIRES BL-SCHEMA (permanent guard
    `test_fresh_stub_flipped_to_candidate_fires_bl_schema`, PASSED alongside the clean-idea
    E2E). Existing BL-SCHEMA plants that used `status: idea` (integration
    `test_backlog_doctor._plant_schema`, `test_precommit_backlog_scoping`, e2e
    `test_backlog_precommit`) moved to `candidate` — the SPEC's only intentional behavior
    change; live-backlog error count UNCHANGED by FR5 (pre-FR5 baseline 1 → post-FR5 1).
    **FR6:** one-line STANDS-ALONE scope docstring on `features/workspace_clean/__init__.py`
    (WorkspaceCleanService reclaim vs workspace WorkspaceService bootstrap — create-vs-reclaim).
    **Projection state:** `dadaia public doctor` exit 0, `[ok] public-privacy`; no runtime
    projection of the scaffold README (it is a scaffold asset, staged to `.dadaia/agentic/`).
    **Gates:** full unpiped `pytest` (tests/ --ignore=tests/e2e/panel) **4350 passed / 17
    skipped (exit 0)**; `ruff format --check` exit 0; `ruff check --no-cache` exit 0;
    `mypy --strict dadaia_workspace` (302 files) exit 0; `lint-imports --no-cache`
    **`8 kept, 0 broken`**; cap test `== 26` + per-family `9/4/13` (4 passed — FR4 adds only
    core→core/hooks→core/cli→core edges, zero ignore edges); `dadaia specs doctor` exit 0
    (10 warns, 0 errors); `dadaia public doctor` exit 0 (`[ok] public-privacy`).
    **`dadaia backlog doctor` = exit 1 with EXACTLY ONE BL-SCHEMA error** —
    `architecture-uml-decomposition` (status `candidate`) references the dead anchor
    `api.py#render_api_agents_canonical` KILLED by W3. This is the SPEC §6 archival-at-SHIP
    condition (the live consuming entry references its own dead anchor mid-branch), owned by
    **T-55-60** (consumed-backlog archival in the single atomic SHIP commit); it pre-exists
    W4 (the ref was in the entry at the W3 tip `f8aa799b`), is a `candidate` (not `idea`) so
    unaffected by FR5, and W4 stages NO `specs/backlog`. NOT a W4 defect.
    **AC-8 ledger — surviving:** codex bound-context resolution via the harness-id channel
    (incl. the unchanged ancestry-membership path for descendants); concurrent multi-session
    safety (disjoint chains never cross-attribute); the `backlog new` stub generator +
    README contract; the idea-status BL-SCHEMA gate + candidate-and-beyond enforcement;
    `features/workspace_clean`'s STANDS-ALONE scope. **dead:** the disjoint-ancestry
    resolution hole (a bound codex session could not resolve its context for a non-descendant
    CLI call) and the idea-stage BL-SCHEMA false-positive (a fresh `idea` stub failed
    `backlog doctor`) — both are restorative removals; plus one scoped doctor semantics
    refinement (idea entries exempt from typed-intents). Every move/grep swept `tests/` AND
    textual refs (the stub's commented template, the README). NO `specs/backlog` staged.

## W5 — FR7 UML assets (LAST — diagram the post-split shape)

- [x] T-55-50 Commit the canonical UML diagrams of the post-split shape. Checklist:
  - Create `specs/assets/architecture/` with **Markdown files carrying fenced ```mermaid blocks**
    (R-8): (a) a `classDiagram` of the `SpecsDoctor` coordinator + the six validator classes; (b)
    a `classDiagram`/module graph of the panel per-domain view modules; (c) a package graph of the
    post-merge feature map (**23 features**). Single-sourced, diffable — NO `.mmd`, NO `.svg`, NO
    mermaid-cli.
  - **Introspection drift-guard:** `tests/contract/test_architecture_diagrams_current.py` (new)
    derives the live names by IMPORTING `doctor_*`, the per-domain api modules, and
    `features.reports` (a hardcoded expectation list is FORBIDDEN) and asserts each diagram `.md`
    mentions them. **AC-7(f):** rename a decomposed class without updating the `.md` ⇒ the
    drift-guard FAILS; revert.
  - AC-5 assets exist + guarded. (The `architecture.md` "Visual evidence" reference is a
    CLOSURE/memory edit — T-55-70.) AC-8 ledger. NO `specs/backlog`.
  Owner: software-engineer. (software-architect reviews diagram fidelity.)
  - **DONE (software-engineer, 2026-07-03).** Commit: assets + drift-guard `<this commit>`
    (`docs(T-55-50)` — folds the `[-]` reservation flip). NO `specs/backlog` staged.
    **DEVIATION (necessary SPEC-implied enabler):** the repo `.gitignore` `/specs/*` privacy
    backstop ignored the new `specs/assets/` top-level subtree (every canonical subtree —
    memory/audits/bugs/backlog/releases — carries an explicit opt-in; assets had none), so the
    diagrams could not be committed. AC-5 binds them to be COMMITTED + CI-reviewable, so a
    minimal privacy-preserving opt-in was added mirroring the audits pattern (`!/specs/assets/`,
    `!/specs/assets/*/`, `/specs/assets/*/*`, `!/specs/assets/*/*.md` — *.md only; no
    `.svg`/`.mmd`/binary ever tracked, R-8). This is the privacy backstop working as designed
    (NOT a tooling bug — no bug registered), not enumerated in the literal W5 write set but
    required to deliver FR7. Verified the `/specs/*` backstop is UNIQUE to this source repo's
    `.gitignore` (no such pattern in `public/scaffold/`), so there is no consumer-scaffold
    template to keep in sync — the change is fully local to this repo.
    **Assets — three fenced-```mermaid `.md` files under `specs/assets/architecture/` (R-8:
    NO `.mmd`, NO `.svg`, NO mermaid-cli/Node; rendered natively by GitHub + the panel):**
    (a) `doctor-decomposition.md` — a `classDiagram` of the `SpecsDoctor` coordinator + the
    six validator siblings (`StructuralValidator`, `MemoryValidator`, `ReleaseValidator`,
    `ClosureAuditValidator`, `GovernanceValidator`, `CoherenceValidator`) + the two leaf
    modules (`doctor_types`, `doctor_common`), with the coordinator's "owns ORDER" delegation
    edges and NOTES pinning the two boundary imports to their sole holders (`spec_context.{lease,
    session_identity}` → `CoherenceValidator`; lazy `infrastructure.subprocess_runner` →
    `MemoryValidator`; coordinator holds neither — `pid_probe` typed against the
    `doctor_types.PidProbe` leaf); (b) `panel-views-decomposition.md` — a `classDiagram`/module
    graph of the eight per-domain `api_*` view modules + their public render functions +
    `PanelService`/`container` named-import wiring (no facade; `api.py` deleted); (c)
    `feature-packages.md` — a `flowchart` package graph of the post-merge **23** feature
    packages, with the merged `features/reports` (`next`/`retention`/`validation`) submodules,
    the `governed_catalog` cycle-break seam, and the edge-#7 repoint note. Each file carries a
    short prose header (what it shows + release origin v0.1.55) + ONE fenced ```mermaid block +
    a regeneration-law note pointing at the drift-guard.
    **Introspection drift-guard — NEW `tests/contract/test_architecture_diagrams_current.py`
    (the SPEC/TASKS-canonical name; operator prompt's `test_architecture_assets_drift.py` is a
    paraphrase — SPEC FR7 name used so the W6 gate + reviewers resolve it).** Derives EVERY
    live name by `importlib` + `pkgutil` + `inspect` introspection (a hardcoded expectation
    list is FORBIDDEN — none present): doctor coordinator = classes defined in
    `features.specs.doctor`; validators = `*Validator` classes discovered across the
    `features.specs.doctor_*` modules; api modules + render fns = discovered
    `features.panel.views.api_*` packages + their public functions; feature packages =
    `pkgutil.iter_modules(features)` ispkg set (23); reports submodules =
    `pkgutil.iter_modules(features.reports)`. Parses the sole fenced-```mermaid block per file
    and asserts, BOTH directions: **Forward** — every live name is mentioned (doctor: as a
    declared `class` node; panel/features: as a token) → catches a code rename the diagram
    missed; **Reverse** — every diagram node claiming to be a decomposed class/`api_*` module
    IS a live importable name → catches a diagram node renamed to a stale name. Also fails if a
    diagram file goes missing (`_sole_mermaid_block` asserts `is_file()` + exactly one block).
    4 tests GREEN in isolation and in the full suite.
    **AC-7(f) sabotage (diagram-side, per operator scope — the bidirectional guard also covers
    the SPEC's code-side variant via Forward):** renamed `class CoherenceValidator` →
    `class CohesionValidator` in `doctor-decomposition.md` ONLY (code untouched) ⇒
    `test_doctor_diagram_matches_live_classes` FAILED —
    `AssertionError: doctor-decomposition.md does not diagram live doctor class(es):
    ['CoherenceValidator']` (Forward caught the stranded live name; Reverse would also flag the
    stale `CohesionValidator` node). Reverted → 4 passed, zero `CohesionValidator` residue.
    **Doctor state (SPEC §FR7 anticipated the new `specs/assets/` top-level):** `dadaia specs
    doctor --specs-dir …/specs` = **exit 0, 0 errors / 10 warnings** (all pre-existing legacy:
    TREE-5 AGENTS.md drift, two SPEC-DOC-027 legacy release dirs, one SPEC-DOC-029 foreign
    stale lease, six SPEC-DOC-031 slug-mention WARNs) — **no `assets` mention; the new dir is
    NOT flagged** (memory validator scopes to `specs/memory`; `check_no_orphan_specs` rglobs
    only SPEC/PLAN/TASKS.md; no top-level allowlist exists). No doctor code change warranted —
    the SPEC's write set for W5 authorizes one ONLY "if the SPEC says so", and it does not.
    **Gates:** full unpiped `pytest` (tests/ --ignore=tests/e2e/panel) **4354 passed / 17
    skipped (exit 0)** (+4 drift-guard tests over the W4 baseline 4350); `ruff format --check`
    (768 files) exit 0; `ruff check --no-cache` exit 0; `mypy --strict dadaia_workspace` (302
    files) exit 0; `lint-imports --no-cache` **`8 kept, 0 broken`** (FR7 adds zero import edges
    — the assets are `.md`, the guard is a test importing existing modules); cap test
    (`test_import_linter_ignore_cap` + `test_module_size_ceiling`) `== 26` + per-family `9/4/13`
    + ceilings GREEN (6 passed).
    **AC-8 ledger — surviving:** the post-split architecture now has committed visual evidence
    (three canonical fenced-```mermaid `.md` diagrams of the doctor coordinator+validators, the
    panel per-domain api modules, and the 23-feature package map) + a live introspection drift
    lock that fails on any diagrammed-name/code-name divergence or a missing diagram file. The
    `architecture.md` "Visual evidence" reference (Currently-no-assets → the committed diagrams
    + regeneration law) is a CLOSURE/memory edit deferred to T-55-70 per §SPEC 8. **dead:** the
    zero-assets state — `specs/assets/` did not exist and `architecture.md` recorded "Currently
    no assets"; the post-decomposition shape had no committed UML and no drift lock.

## W6 — gates + ship (flat release: single ship gate)

- [x] T-55-60 DONE (gates + archival + QA APPROVE; security/push follows as the
  same task's push half). Archival `869e0897` (single atomic: R100 rename +
  consumed_backlog.json + candidates prune; backlog doctor clean; invariants i+ii
  verified — no W1-W5 commit staged specs/backlog). QA ship gate: **APPROVE 11/11**
  (handoff 2026-07-03T215930Z-qa-engineer-v0155-ship-gate, validated): both goldens
  real + pre-refactor-captured (W3's <WS> fix adjudicated sound); coordinator 224
  lines w/ zero _check_* bodies; doctor_* ≤516, api_* ≤429; deletions verified
  (api.py, reports_* triplet, zero old-path refs); contracts 8 kept/0 broken, cap
  26 = 9/4/13 self-counted; 6 sabotages zero-residue; FR4 staleness guard REAL
  (lock_liveness.is_stale); FR5 E2E + README complete; drift-guard genuinely
  introspective; gitignore opt-in .md-only (every binary IGNORED); frozen suite
  4/4 zero-diff; unpiped 4354 passed/17 skipped exit 0 + ruff/mypy/specs/backlog/
  public doctors all clean; 6/6 deviations adjudicated SOUND. LOW advisory →
  W7 CLOSURE: test_panel.py:204,215 stale "views/api.py" prose comments.
  Original checklist: Full gates + consumed-backlog archival at SHIP + ship:
  - **Gates (AC-6):** unpiped `pytest` + `ruff format --check` + `ruff check --no-cache` + `mypy
    --strict` + `lint-imports --no-cache` (`8 kept, 0 broken`; cap 26 = 9/4/13) + `dadaia specs
    doctor` (exit 0) + **`dadaia backlog doctor` (exit 0, zero BL-SCHEMA)** + `dadaia public
    doctor` (`[ok] public-privacy`, exit 0), locally and in CI.
  - **Consumed-backlog archival AT SHIP (single atomic commit — the release kills its own
    consuming entry's `api.py#render_api_agents_canonical` anchor):** move
    `architecture-uml-decomposition` → `specs/_archive/v0.1.55/consumed-backlog/` + write
    `consumed_backlog.json`; `dadaia backlog doctor` clean; verify NO W1-W5 commit staged
    `specs/backlog`; exactly ONE push, after this commit. (Reports package rename may strand OTHER
    entries' anchors — PM verifies `backlog doctor` clean here.)
  - **QA ship gate** (attention: the three goldens byte-identical incl. the deterministic
    normalization+clock-freeze; cap 26 = 9/4/13 + post-split edge completeness + coordinator
    zero-`spec_context`-edge; FR4 four-case incl. stale-id negative; FR5 status-gate E2E +
    public-privacy; the frozen `test_doctor_lock_gc.py` zero-diff; the api-anchor archival timing):
    APPROVE handoff.
  - **Security push gate:** APPROVE handoff `metrics.commit_sha` = pushed sha; push; CI green
    (watch until every job green); PR; merge.
  Owner: qa-engineer + security-reviewer + orchestrator.

## W7 — closure (CLOSURE phase)

- [ ] T-55-70 CLOSURE.md + memory truth updates + bug dispositions + archive. Checklist:
  - **CLOSURE.md** (Summary, Tasks, Validations, Drifts, Memory updates, Dispositions, Backlog
    returns, Archive = MOVE — SPEC-DOC-006).
  - **MEMORY edits (CLOSURE phase, §SPEC 8):** `architecture.md` — Layers → features **25 → 23**
    (reports triplet → one `reports` package); the decomposed `features/specs/doctor.py` (thin
    coordinator owning ORDER + validator classes + `doctor_types`/`doctor_common` leaves) +
    `features/panel/views/api.py` (per-domain modules; api.py deleted) module map; the
    `features/specs/doctor` contracts row; ignore-cap **unchanged 26 = 9/4/13** with the repointed
    doctor + reports edges (post-split enumeration) + the coordinator PidProbe-leaf
    zero-`spec_context`-edge note; **Visual evidence** → the committed `specs/assets/architecture/
    *.md` fenced-mermaid diagrams + the regeneration law. `agent-comms.md` — merged
    `features/reports/`. `specs-doctor.md` (if present) — coordinator + validator decomposition.
    `sdd-bug-backlog-governance.md` (if present) — the `idea`-status BL-SCHEMA gate (intents
    mandatory at `candidate`+). `quality-assurance.md` — the deterministic-golden + module-size
    ratchet precedent. `tech-stack.md` — no change (no mermaid-cli). `catalog.json` + `index.md`
    regenerated if any `tldr`/`summary`/`area` changed.
  - **Bug disposition (ADDITIVE):** append `dadaia bugs append --event resolved --release v0.1.55`
    for `bugs-append-ignores-persisted-bind` and `backlog-new-stub-readme-lag-intents-schema`.
  - **Disposition sweep:** `architecture-uml-decomposition` terminal `DELIVERED — v0.1.55`
    (archived at SHIP, T-55-60); both bugs `Closed` via the resolved events.
  - `dadaia specs doctor` clean; archive (`git mv` via devops/operator); `ACTIVE.md → next` per the
    R6→R8 mandate; candidates R7 row marked shipped. Owner: product-engineer.
