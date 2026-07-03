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

- [-] T-55-30 Split `features/panel/views/api.py` (24 fns / 8 domains) into per-domain view
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

## W4 — FR4 + FR5 + FR6 bug fixes + scope docstring (independent)

- [ ] T-55-40 Fix `bugs-append-ignores-persisted-bind` (FR4), `backlog-new-stub-readme-lag-
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

## W5 — FR7 UML assets (LAST — diagram the post-split shape)

- [ ] T-55-50 Commit the canonical UML diagrams of the post-split shape. Checklist:
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

## W6 — gates + ship (flat release: single ship gate)

- [ ] T-55-60 Full gates + consumed-backlog archival at SHIP + ship. Checklist:
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
