# SPEC — v0.1.55 — Architecture Decomposition

**Status:** Aprovado
**Branch:** `feature/v0.1.55` (base: `26c5089b`, v0.1.54 closure — the orchestrator branches after `Aprovado`)
**Origin:** R7 of the operator-approved 12-release plan; second release of the operator's
R6→R8 continuation mandate. Definition-time inspection verified by the orchestrator
2026-07-03 (GRILL INSPECTION DOSSIER — cited as inspection facts). Release-definition grill
(mandatory, from-bugs+backlog) run on the picked set before this SPEC.
**Dual definition review 2026-07-03 (software-architect REJECT + qa-engineer REJECT — ALL
amendments folded):** software-architect (A1 PidProbe leaf alias to keep the cap invariant;
A2 shared-leaf pure-helper allocation + no-sibling-import; A3 coordinator owns check()/fix()
ORDER, validators own LOGIC; A4 golden fixture spans all six families; A5/A6 FR4 harness-native
session-id channel + staleness guard + no-blind-fallback; A7 FR3 full move surface; OQ-1
INVERSION → `idea`-status BL-SCHEMA gate is the ROOT fix; OQ-2 fenced-mermaid `.md`, no
mermaid-cli/`.svg`; OQ-3 sibling modules; FR6 STANDS ALONE; api.py named-import wiring, no
facade) + qa-engineer (A1 golden path-normalization + clock-freeze; A2 PidProbe leak → cap 14
without the leaf alias; A3 moved-symbol production+test consumers; A4 the 14 api test importers,
no shim; A5 FR4 deterministic disjoint-`ancestry_pids` modeling; A6 FR5 E2E pinned; A7 AC-6 adds
`backlog doctor`; A8 introspection drift-guard, no byte-guarded `.svg`; A9 AC-8 covers
textual/docstring refs). QA re-verifies this Draft before `Aprovado`.
**Consumes:** backlog `architecture-uml-decomposition` (1) + open bugs
`bugs-append-ignores-persisted-bind` and `backlog-new-stub-readme-lag-intents-schema` (2).
Open bugs outrank plain backlog at pick (`release-governance`); both are FIXED here.

## 1. Problem

The import-linter layering law is now green + CI-enforced (v0.1.54), so the structural
refactors it was built to protect can land under enforcement. Two god modules and a
feature-shape noise triplet block a clean, UML-representable class diagram; two open bugs
carried forward from v0.1.54 remain undispositioned; and the architecture atom's "Visual
evidence" section records zero assets. Verified at definition (2026-07-03):

1. **`features/specs/doctor.py` — 2,830-line god module (erosion continuing).** Grew from
   the audit's 2,820 to **2,830** today. Public types `Severity` (l.301), `SpecsDoctorIssue`
   (l.307), `_MemoryMdSummary` (l.336); one `SpecsDoctor` class (l.498) with **54 methods**
   spanning five unrelated validator responsibilities. `check()` (l.566-615) runs ~35 checks
   in an order that **INTERLEAVES families** (coherence→memory→release→…→governance→
   closure→coherence). Two feature-boundary imports live inside it: `spec_context.{lease,
   session_identity}` (module-level, l.65 — used only by `_check_lease_session_coherence`,
   l.1344) and a lazy `infrastructure.subprocess_runner` (l.2657, inside
   `_check_lint1_memory_atoms`, l.2630). The `__init__` is typed `pid_probe: lease.PidProbe`
   (l.519/543) where `PidProbe = Callable[[int], bool]` (`spec_context/lease.py` l.73) —
   itself a `spec_context` type edge (see FR1). ~10 module-level helpers exist beside the
   class: `_validate_ctx_name` (l.72), `_read_active_md` (l.406 — **externally consumed** by
   `cli/commands/specs.py:15`), `_parse_memory_md`/`_iter_memory_md_files`,
   `_extract_status`/`_extract_created_date`, `_split_tier_blocks`/`_extract_tier1_names`/
   `_extract_tier2_names`/`_extract_playbook_headings`, plus the release-dir iterators
   `_is_release_dir`/`_iter_archive_release_dirs`/`_is_legacy_nested_release`/
   `_iter_all_release_dirs` (**cross-validator, used by three families**).
2. **`features/panel/views/api.py` — 1,279-line / 24-function module.** The audit's
   1,402/24 is **stale** (R4 deleted kanban/session-detail). Re-derived live: 24 functions
   spanning **eight domains** — servers, contexts, agents (`render_api_agents_canonical`,
   `render_api_agent_prompt`, `_agent_phases`, `_workflow_membership`, `_empty_telemetry_sub`,
   `_compute_30d_cost`), workflows, sessions, academy, reports, health. The module imports
   **only** `features.panel.service` — **zero** cross-feature / infra edges. Sole production
   consumer of the render fns: `container.py` (l.63 import + `build_panel_views` route table
   l.1152-1224). **14 test files** import `panel.views.api` symbols directly (§FR2).
3. **`reports_*` triplet — three top-level feature packages, 845 lines.**
   `features/reports_next/` + `features/reports_retention/` + `features/reports_validation/`
   for one concern (agent-comms reports). Only one cross-feature edge touches them:
   `features.lifecycle.report_workflow -> features.reports_validation.service` (edge #7).
   Consumers: `container.py` (l.97-99, 465/484/514/835), `cli/commands/reports.py`
   (l.22/26/57/316/643), `lifecycle/report_workflow.py` (l.17), plus a stale docstring in
   `core/protocols/handoff_validator.py:4`.
4. **`bugs-append-ignores-persisted-bind` (MEDIUM, codex).** `cli/commands/bugs.py:23` routes
   through `cli/_specs_resolution.resolve_specs_dir_for_cli` (flag → bound context via
   `current_ancestry_pids()` → cwd/specs), so the defect is **deeper**. Root cause CONFIRMED
   at review: a codex `dadaia bugs append` is **not a process-descendant** of the `dadaia
   context bind` session → its ancestry chain is disjoint from the bind-epoch marker's chain
   → `_persisted_bind_context` (`core/specs_resolver.py`) misses (membership fails) →
   fall-through at `resolve_specs_dir` l.191 → `typer.BadParameter("Could not resolve
   specs_dir …")`. The resolution order (`resolve_bound_context_name` l.138-150) is
   explicit → `DADAIA_CONTEXT` → `_session_context` (needs `DADAIA_SESSION_ID` +
   `.dadaia/sessions/<id>.json` carrying `context`) → `_persisted_bind_context`. `bind` keys
   its session record by a random `sess_<uuid>` (`cli/commands/context.py:377`), so
   `_session_context` (reads only `DADAIA_SESSION_ID`, `specs_resolver.py:25`) cannot find it
   for a codex session that never exported `DADAIA_SESSION_ID`.
5. **`backlog-new-stub-readme-lag-intents-schema` (MEDIUM, claude-layer1).** The
   `_BACKLOG_STUB` (`features/spec_artifacts/new_artifacts.py` l.103) emits `title/status/
   opened` frontmatter with `status: idea` (l.106) and **no `intents[]`** (v0.1.25 BL-SCHEMA)
   and no `description` field. `dadaia backlog doctor` `_check_schema` (`features/backlog/
   doctor.py` l.127) hard-errors "no intents[] declared" on the fresh stub — even though
   `idea` is an unbound brainstorm (`idea ∈ _KNOWN_STATUSES`, doctor.py l.50). The projected
   PUBLIC asset `public/scaffold/backlog/README.md` documents `title/status/opened/description`
   only; the typed `intents[]` requirement, the five subject kinds, and the non-Python-repo
   anchor factor (the registry derives **code** anchors from Python only) are undocumented.
6. **`features/workspace_clean` scope is undocumented** — no one-line module scope docstring.
7. **Zero UML assets.** `specs/memory/architecture.md` "Visual evidence" (l.305-307) records
   "Currently no assets"; `specs/assets/` does not exist.

**Inspection contradictions found (recorded, corrected in this SPEC):**
- **(a) Frozen-suite misattribution (dossier #6).** The named `tests/unit/features/specs/
  test_doctor_lock_gc.py` is actually at `tests/unit/features/spec_context/
  test_doctor_lock_gc.py` and imports `spec_context.doctor.DoctorService` — a **different
  subsystem** from `features/specs/doctor.py#SpecsDoctor` being split. **FR1 does not touch
  `spec_context`, so this frozen file is naturally zero-diff.** The real FR1 preservation net
  is the SpecsDoctor issue-code golden (AC-2).
- **(b) api.py size (dossier #2).** Live is **1,279/24**, not the audit's 1,402/24 — the
  per-domain split targets the live shape.

## 2. Goals

1. `features/specs/doctor.py` is a **thin `SpecsDoctor` coordinator** that **owns check()/fix()
   ORDER** and delegates LOGIC to focused single-responsibility validator classes — behavior
   byte-identical (golden), the public `SpecsDoctor` surface + issue codes + issue ORDER
   preserved, `doctor.py#SpecsDoctor` anchor alive.
2. `features/panel/views/api.py` is decomposed into per-domain view modules; `api.py` is
   **deleted** (no facade/shim); route responses byte-identical (golden).
3. `reports_next / reports_retention / reports_validation` merge into one `features/reports/`
   package (`next`/`retention`/`validation` submodules) — behavior-preserving relocation.
4. **No new suppressed import edge**: the three moves repoint existing ignore edges 1:1; the
   ignore-cap stays **26 = 9/4/13**; `lint-imports` stays `8 kept, 0 broken`.
5. The two open bugs are **fixed** with regression tests: a codex session resolves its bound
   context for `dadaia bugs append` via a **per-session-deterministic** channel (never a blind
   fallback) without weakening concurrent multi-session safety; a freshly-scaffolded
   `dadaia backlog new` stub is `dadaia backlog doctor`-clean via the **`idea`-status
   BL-SCHEMA gate** (the root-cause fix).
6. `features/workspace_clean` STANDS ALONE with a one-line scope docstring.
7. The canonical UML diagrams of the post-split shape are committed as **fenced ```mermaid
   blocks in `.md` files** under `specs/assets/architecture/`, referenced from
   `architecture.md` "Visual evidence", with an **introspection drift-guard**.

## 3. Functional requirements

### FR1 — `SpecsDoctor` decomposition (coordinator owns ORDER; validators own LOGIC)

- **OQ-3 (BINDING): sibling modules, not a subpackage.** `features/specs/doctor.py` stays a
  FILE holding the `SpecsDoctor` **coordinator** (anchor `doctor.py#SpecsDoctor` SURVIVES);
  the validators are sibling modules `features/specs/doctor_*.py`; the shared surface lives in
  sibling leaf modules.
- **Shared leaf modules (imports only stdlib + `core`; NO sibling-validator import):**
  - `doctor_types.py` — `Severity`, `SpecsDoctorIssue`, `_MemoryMdSummary`, **and the leaf
    alias `PidProbe = Callable[[int], bool]`** (imports only `collections.abc.Callable`). Per
    R-1, `doctor_types.PidProbe` IS `lease.PidProbe` (identical bare-callable type), so
    re-homing the alias is runtime byte-identical — only the import source moves off
    `spec_context`.
  - `doctor_common.py` — the **cross-validator PURE free functions** used by three families:
    `read_active_md`, `is_release_dir`, `iter_archive_release_dirs`, `is_legacy_nested_release`,
    `iter_all_release_dirs`.
- **Coordinator `doctor.py`:** `SpecsDoctor.__init__` preserves its public signature but is
  **typed against the leaf** — `pid_probe: doctor_types.PidProbe | None = None`,
  `self.pid_probe: doctor_types.PidProbe`. The coordinator imports **NO `spec_context` and NO
  `subprocess_runner` module**; it imports only the leaves + the sibling validators.
- **Coordinator owns ORDER (R-3):** `check()` invokes the validators' individual PUBLIC check
  methods in the **EXACT original interleaved sequence** (the ~35-check order at l.566-615) —
  the coordinator owns ORDER, validators own LOGIC. `fix()` dispatches by issue code:
  `TREE-4 → structural.fix_tree4`, `SPEC-DOC-034 → closure_audit.fix_archive_dir`.
- **Six validator classes, one per module, each independently testable:**
  - `doctor_structural.py` — tree1-7, required dirs, agents.md; `fix_tree4`.
  - `doctor_memory.py` — memory files/atomicity/image-links/mermaid, LINT-1, CAT-1; **holds the
    lazy `infrastructure.subprocess_runner` import** (LINT-1 shell-out) + the family-local
    `_parse_memory_md`/`_iter_memory_md_files`.
  - `doctor_release.py` — active.md, active-release artifacts, plan-line-limit, phase-marker
    coherence, unique/naming/semver checks; family-local `_extract_status`/`_extract_created_date`.
  - `doctor_closure_audit.py` — archive closures, archive-dirs-exist (`fix_archive_dir`), audit
    disposition, loose-undisposed-audits, audits-naming-canon, no-orphan-specs.
  - `doctor_governance.py` — bug status canon, bugs-jsonl invariant, backlog schema,
    consumed-backlog disposition, unarchived-terminal-backlog.
  - `doctor_coherence.py` — constitution + file-refs + no-runtime-enum, orchestration-registry,
    specs-pattern-version, **lease/session coherence**. **Holds the `spec_context.{lease,
    session_identity}` import** (moved from l.65) + the family-local `_validate_ctx_name`
    (single caller at l.1394, verified), `_split_tier_blocks`/`_extract_tier1_names`/
    `_extract_tier2_names`/`_extract_playbook_headings`.
- **External-surface repoint — NO new re-export shims (R-2):**
  - `features/specs/__init__.py` — repoint the `Severity`/`SpecsDoctorIssue` re-export SOURCE
    to `doctor_types` (`SpecsDoctor` stays re-exported from `doctor`).
  - `cli/commands/specs.py:15` — repoint `_read_active_md` to the shared-leaf public name
    `doctor_common.read_active_md`.
  - The 3 test importers (`test_active_md_schema_v2.py` [`_read_active_md`],
    `test_specs_evolution.py` [`Severity`], `test_scaffolder_doctor.py` [`Severity`]) repoint
    to the new homes. All named in the W1 write set + AC-8 greps (imports AND textual refs).
  - `tests/unit/features/specs/test_doctor_lint.py` (QA re-verify R10) — RE-HOME to
    `doctor_memory`: repoint the 5 `SpecsDoctor(specs)._check_lint1_memory_atoms()` call
    sites (l.54/64/79/91/106) to the `doctor_memory` validator's public LINT-1 method, and
    the `doctor._LINT_SCRIPT` monkeypatch (l.104) to `doctor_memory._LINT_SCRIPT` (both
    move in FR1; R-3 removes every `_check_*` body from the coordinator).
  - `tests/unit/features/specs/test_doctor_ledger_invariants.py` l.677-684
    (`inspect.signature`/`getsource` over the doctor module) — re-widen the
    `process_probe_adapter`-avoidance assertion to cover the validator modules (it would
    otherwise silently narrow to coordinator-only).
- **Cap invariant (dossier #5 + R-1):** each ignored import lives in EXACTLY ONE submodule —
  `spec_context.{lease,session_identity}` only in `doctor_coherence`; `subprocess_runner` only
  in `doctor_memory`; the coordinator imports neither. **`setup.cfg` SAME-commit edge repoints**
  (see the enumeration below). No edge splits → cap stays 26 = 9/4/13.
- **Golden (AC-2):** see AC-2 for the deterministic capture (path normalization + clock freeze
  + all-six-families fixture).

### FR2 — `panel/views/api.py` per-domain decomposition (delete api.py; no facade)

- Split the 24 functions into per-domain view modules under `features/panel/views/`
  (`api_servers`, `api_contexts`, `api_agents`, `api_workflows`, `api_sessions`, `api_academy`,
  `api_reports`, `api_health`), one responsibility per module; domain-private helpers move with
  their domain. `render_api_agents_canonical` moves into `api_agents` → the anchor
  `api.py#render_api_agents_canonical` **DIES** (§6 archival-at-SHIP).
- **api.py wiring (BINDING, R-5): NO facade, NO re-export shim/barrel; `api.py` is DELETED.**
  `container.py` imports each `render_api_*` from its per-domain module via explicit **named
  imports** (extending the incumbent l.63-91 named-import pattern; matches the
  `panel.views.workflow_policy` precedent).
- **No `setup.cfg` change** — api had zero cross-feature/infra edges; each new module imports
  only `features.panel.service`. AC-3 re-verifies the cross-feature/cap set is untouched by FR2.
- **Repoint the 14 test importers (verbatim, W3 write set + AC-8 ledger):**
  `tests/integration/panel/test_api_workflows.py`, `tests/integration/panel/test_api_agents.py`,
  `tests/integration/panel/test_workflows_api.py`, `tests/integration/panel/test_academy_route.py`,
  `tests/integration/test_panel_sessions_endpoint.py`,
  `tests/unit/features/panel/test_api_agents.py`, `tests/unit/features/panel/test_api_agent_prompt.py`,
  `tests/unit/features/panel/test_api_academy.py`, `tests/unit/features/panel/test_api_workflows_list.py`,
  `tests/unit/features/panel/test_api_workflows_detail.py`, `tests/unit/features/panel/test_api_contract.py`,
  `tests/unit/features/panel/test_views_api_sessions.py`, `tests/unit/features/panel/test_build_panel_views.py`,
  `tests/unit/features/panel/test_serve_report_identity.py`. Plus the stale docstring textual
  ref `features/panel/views/assets/css/reports_doc.py:5` (`views/api.py::serve_report_file`).
- **Golden (AC-2, R6 pattern):** capture each route's `(status, content_type, body)` on a
  fixture panel state PRE-split → golden; assert POST-split byte-identical.

### FR3 — `reports_*` triplet → one `features/reports/` package

- Merge into `features/reports/` with flat submodules `next.py` / `retention.py` /
  `validation.py`; delete the three `reports_*` packages.
- **Full move surface (A7, enumerated so W2's ledger is complete):**
  - Production: `container.py` (l.97-99 imports; l.465/484/514/835 factories),
    `cli/commands/reports.py` (l.22/26), `features/lifecycle/report_workflow.py` (l.17 — edge #7),
    the stale docstring `core/protocols/handoff_validator.py:4` (`reports_validation` →
    `reports.validation`).
  - Tests: rename `tests/unit/features/reports_{next,retention,validation}/` →
    `tests/unit/features/reports/`; `tests/unit/test_reports_validation_service.py`,
    `tests/contract/test_reports_retention_cleanup.py`,
    `tests/integration/test_lifecycle_push_preflight.py`,
    `tests/unit/features/panel/test_api_contract.py` (+ the AC-8 grep sweeps the rest).
- **`setup.cfg` SAME-commit:** `features-no-cross-feature` `modules =` remove the three
  `reports_{next,retention,validation}`, add `features.reports`; edge #7 target repoint
  `...report_workflow -> ...features.reports.validation` (was `reports_validation.service`).
- **Regression:** the reports consumers' existing suites are the net (relocation-only).

### Expected post-split ignore-edge enumeration (SPEC-pinned; cap stays 26 = 9/4/13)

`features-no-cross-feature` (13 — 3 repoint):
```
7  lifecycle.report_workflow  -> reports.validation              (FR3 target repoint)
12 specs.doctor_coherence     -> spec_context.lease              (FR1 source repoint)
13 specs.doctor_coherence     -> spec_context.session_identity   (FR1 source repoint)
   (#1-6, #8-11 unchanged)
```
`features-no-infrastructure` (9 — 1 repoints) & `features-no-subprocess` (4 — 1 repoints):
`specs.doctor_memory -> infrastructure.subprocess_runner` (was `specs.doctor -> …`). All full
`dadaia_workspace.` prefixes; every repoint is 1:1 → cap **26 = 9/4/13** INVARIANT. The
coordinator holds **no** `spec_context` edge (R-1 PidProbe leaf), so cross-feature stays 13
(a naive `pid_probe: lease.PidProbe` annotation would leak a 14th edge → cap 27 → FAIL).

### FR4 — Fix `bugs-append-ignores-persisted-bind` (codex bound-context resolution)

- **Fix channel DECIDED (R-6, BINDING):** at `bind`, **persist the harness-native session id**
  (`CODEX_SESSION_ID` / `CLAUDE_CODE_SESSION_ID`, resolved via `hooks/_common.resolve_session_id`
  l.132-138) into the session record (or a harness-id → context index). Extend `_session_context`
  (`core/specs_resolver.py:25`) to resolve via the harness-native ids **when `DADAIA_SESSION_ID`
  is absent** — so a codex session (whose CLI calls are non-descendants of the bind) resolves its
  bound context deterministically, ahead of the ancestry-membership path.
- **Staleness guard (NON-NEGOTIABLE):** a harness-id match resolves **ONLY when its session
  record is live** (heartbeat-fresh / pid-alive) — the harness-native id "may be inherited from
  a parent shell and stale" (the audit F-1 rotated-sid self-block source); a stale/inherited id
  must NOT resolve to a foreign bound context.
- **No blind fallback (ADDITIVE calculus, R-6):** `specs/bugs/` is ADDITIVE, so a misfile's blast
  radius is lower (misfile vs corruption) but the **correctness bar is identical** — a blind
  first-ALIVE / single-marker fallback stays FORBIDDEN. **Contingency:** if no stable per-session
  channel exists for codex's default flow, the fix is an **actionable error message only** (direct
  the caller to `--specs-dir` or the `--print-env` eval), never a guess. State this branch so W4
  cannot stall.
- **Regression modeling (R-6 / QA A5 — deterministic, no spawned processes):** model the
  non-descendant case by seeding a bind-epoch marker with chain `[A1,A2]` and resolving with a
  **disjoint `ancestry_pids` frozenset `{B1,B2}`**. AC-4: (i) RED = `BadParameter` pre-fix; GREEN
  drives the SAME channel the fix wires (the harness-id session record — a slope test that
  doesn't exercise the channel is rejected); (ii) two bind-epoch markers → never cross-attribute
  (concurrent multi-session safety); (iii) the descendant/same-shell case still resolves; (iv) **a
  resolving process with a STALE/inherited harness-id must NOT resolve to a foreign bound
  context** (the new negative case). AC-7 sabotage = revert the fix line.

### FR5 — Fix `backlog-new-stub-readme-lag-intents-schema` (idea-status gate — ROOT fix)

- **OQ-1 INVERSION (BINDING, R-7): the ROOT fix is the idea-lifecycle status gate — NOT a
  self-resolving subject.** The self-referential-subject path is REJECTED as checker-gaming
  (verified mechanically unsound: `_derive_doc_anchors` scans only `specs/memory/**/*.md`, so a
  backlog entry's own file is never a doc anchor; `_derive_catalog_anchors` reads `catalog.json`
  slugs, empty in a fresh scaffold — neither a self `doc` nor `catalog` ref resolves).
- **Doctor change (`features/backlog/doctor.py` `_check_schema`):** status-gate the resolvable-
  typed-intents requirement — an entry at `status: idea` is **EXEMPT** from the "no intents[]
  declared" (l.127) AND the unresolved-subject (l.145-149) BL-SCHEMA errors; those become
  mandatory when the item matures to `candidate` and beyond. This is a **status-gated** gate,
  **not a blanket exemption** (a malformed-`intents:` frontmatter error still fires at any
  status).
- **Stub (`features/spec_artifacts/new_artifacts.py`):** `_BACKLOG_STUB` keeps `status: idea`,
  gains a `description:` frontmatter field and a **commented `intents[]` template** in the body
  (a teaching template, NOT a live dummy subject) — no scaffold-content coupling, no placeholder
  subject.
- **README (`public/scaffold/backlog/README.md`, lib-originated PUBLIC asset):** document
  idea-stage freedom (intents optional at `idea`), the typed `intents[]` requirement at
  `candidate` and beyond, the five subject kinds (code/cli/catalog/doc/invariant), the
  `dadaia backlog subjects` pointer, and the non-Python-repo anchor note (code anchors are
  Python-derived only → JS-only repos bind catalog/doc anchors). Follow `stage → install
  --target all → doctor` (`[ok] public-privacy`).
- **E2E (AC-4, pinned):** in a fresh scaffold **without `catalog.json`**, `dadaia backlog new
  <slug>` then `dadaia backlog doctor` → exit 0, zero BL-SCHEMA. AC-7 sabotage: flip the fresh
  stub's `status` to `candidate` ⇒ `backlog doctor` BL-SCHEMA FIRES (proves the status-gate).

### FR6 — `features/workspace_clean` scope docstring (STANDS ALONE — BINDING)

- Add a one-line module scope docstring: `workspace_clean` (`WorkspaceCleanService` = TTL
  reclaim of ephemeral `.dadaia/` zones behind `dadaia clean`) **STANDS ALONE** — the opposite
  lifecycle end from `workspace` (`WorkspaceService` = bootstrap/init); the docstring records
  the create-vs-reclaim rationale. No behavior change.

### FR7 — Canonical UML assets (LAND LAST; fenced mermaid in Markdown — BINDING)

- **OQ-2 (BINDING, R-8): NO mermaid-cli/Node, NO `.svg` artifacts.** No in-repo mermaid renderer
  exists (`render_dag_svg` is a bespoke DAG→SVG, not mermaid; the panel's mermaid is
  client-side). Commit the diagrams as **fenced ```mermaid blocks inside Markdown files** at
  `specs/assets/architecture/<name>.md` (rendered natively by GitHub + the panel) — single-
  sourced, diffable, no binary: (a) a `classDiagram` of the `SpecsDoctor` coordinator + the six
  validator classes; (b) a `classDiagram`/module graph of the panel per-domain view modules;
  (c) a package graph of the post-merge feature map (**23 features**).
- **Introspection drift-guard (R-8):** `tests/contract/test_architecture_diagrams_current.py`
  derives the live class/module names by **IMPORTING** `doctor_*`, the per-domain api modules,
  and `features.reports` (introspection — a hardcoded expectation list is FORBIDDEN, else the
  AC-7(f) sabotage stays GREEN) and asserts each diagram `.md` mentions them.
- Referenced from `architecture.md` "Visual evidence" at CLOSURE; the regeneration law recorded
  there.

## 4. Non-goals

- **No behavior change anywhere EXCEPT the deliberate FR5 root-cause fix.** The three structural
  moves + reports merge are behavior-preserving (golden / existing suites). The **FR5
  `idea`-status BL-SCHEMA gate is a scoped, principled semantics refinement** of `backlog
  doctor` (an unbound brainstorm carries no bound intents) — the root-cause fix, not incidental
  drift; it is the ONLY intentional behavior change.
- **No new features.** The bug fixes restore contracts the tools already promise.
- **No new import-linter contract and no cap change.** Cap stays **26 = 9/4/13** (repoints only).
  Durability is guarded by a **test-side module-size ratchet** (AC-1) + the diagram drift-guard
  (FR7), not a new import contract.
- **No facade / re-export barrel for the api split; no re-export shims for the doctor split** —
  consumers are repointed (R-2, R-5). `api.py` is deleted.
- **No `mermaid-cli`/Node and no `.svg`** (R-8); no full AST→mermaid auto-generator.
- **The `workflows ↔ lifecycle` cycle break, `features-no-cross-feature`, and CI wiring are
  ALREADY DONE (v0.1.54)** — not re-touched. Fixing (vs documenting) the surviving 13
  cross-feature edges remains R8/R9 work (this release repoints, does not eliminate them).
- **Constitution unchanged; no new deprecations; no memory changes outside the §8 CLOSURE list.**

## 5. Acceptance criteria

- **AC-1 (decomposition responsibility + anti-erosion size ratchet):** (a) the `SpecsDoctor`
  coordinator delegates only — a structural probe asserts its class body defines **no `_check_*`
  method** (only `__init__`, `check`, `fix`, and code-keyed fix dispatch); (b) each validator /
  api-domain module is single-responsibility and imports **no sibling validator** (leaf-only);
  (c) `tests/contract/test_module_size_ceiling.py` asserts no `features/specs/doctor*.py` module
  exceeds **700 lines** and no `features/panel/views/api*.py` module exceeds **450 lines**
  (recorded ratchet ceilings; lowering welcome, raising needs same-commit justification). With
  `api.py` deleted, the api ceiling is trivially met.
- **AC-2 (golden behavior-preservation, DETERMINISTIC — R-4):** the FR1 golden is captured
  **in-process on a fixed committed fixture root**, **normalizing every absolute path** (the CLI
  `--json` top-level `specs_dir` AND each issue `path`) to the token `<SPECS>`, and **freezing the
  clock** by monkeypatching `date.today` + `datetime.now(tz=UTC)` to **2026-07-15** (so the
  release-semver and candidates-hotfix date-gated checks are deterministic); the fixture triggers
  **≥1 issue from EACH of the six validator families** and preserves the interleaved `check()`
  order; byte-identical pre/post FR1. The FR2 route-response golden is byte-identical pre/post;
  the reports consumers' suites are green after FR3.
- **AC-3 (contract/cap tracking + post-split enumeration):** `lint-imports --no-cache` reports
  **`8 kept, 0 broken`** with the §3 post-split edge set; the doctor edges + edge #7 are repointed
  in the SAME commit as their module move (no "No matches for ignored import"); the cap test
  verifies the total (`== 26`) AND the per-family split (`9/4/13`); `modules =` lists
  `features.reports` and no `reports_*`; **the coordinator holds no `spec_context` edge (PidProbe
  leaf)** so cross-feature stays **13**; FR2 changes zero ignore edges.
- **AC-4 (bug regression tests):** FR4 — the four cases in §FR4 (RED-pre-fix non-descendant
  resolve via the harness-id channel; concurrent two-marker never-cross-attribute; descendant
  still resolves; **stale/inherited harness-id must NOT resolve to a foreign context**), modeled
  with a disjoint `ancestry_pids` frozenset (no spawned processes). FR5 — a freshly-scaffolded
  `dadaia backlog new` stub (no `catalog.json`) is `dadaia backlog doctor`-clean (exit 0, zero
  BL-SCHEMA); the projected README documents idea-stage freedom + `intents[]` at candidate+ +
  subject kinds + `dadaia backlog subjects`.
- **AC-5 (UML assets exist + referenced + guarded):** `specs/assets/architecture/*.md` committed
  with fenced ```mermaid blocks (class diagrams for the doctor + api decompositions; a package
  graph for the 23 features); the **introspection** drift-guard passes; referenced from
  `architecture.md` "Visual evidence" at CLOSURE; the regeneration law recorded. **No `.svg` is
  committed or byte-guarded.**
- **AC-6 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the
  full unpiped `pytest` (real exit), `lint-imports --no-cache` (`8 kept, 0 broken`),
  `dadaia specs doctor` (exit 0), **`dadaia backlog doctor` (exit 0 / zero BL-SCHEMA)**, and
  `dadaia public doctor` (`[ok] public-privacy`, exit 0) are green locally and in CI.
- **AC-7 (mutation-sanity per new test — sabotage → FAIL → revert):** (a) mutate one issue
  description in a doctor validator ⇒ the FR1 golden FAILS; (b) mutate one route body ⇒ the FR2
  golden FAILS; (c) add a stub module over the ceiling ⇒ `test_module_size_ceiling` FAILS; (d)
  revert the FR4 fix line ⇒ the non-descendant regression FAILS; (e) flip the fresh FR5 stub's
  `status` to `candidate` ⇒ `backlog doctor` BL-SCHEMA FIRES; (f) rename a decomposed class
  without updating its diagram `.md` ⇒ the **introspection** drift-guard FAILS. Each captured on
  its task line, then reverted.
- **AC-8 (surviving/dead behavior ledger, per wave):** each wave records a two-column ledger on
  its task line. Every move/rename/repoint grep **includes `tests/` AND non-import textual
  references** (docstrings/comments/README) — specifically `core/protocols/handoff_validator.py:4`
  (FR3) and `features/panel/views/assets/css/reports_doc.py:5` (FR2).

## 6. Consumed bugs & backlog

| Item | Kind | Priority | Consumed → FR | Note |
|---|---|---|---|---|
| `bugs-append-ignores-persisted-bind` | bug (open) | MEDIUM | codex bound-context resolution → FR4 | Picked; FIXED. Terminal `resolved --release v0.1.55` at CLOSURE. |
| `backlog-new-stub-readme-lag-intents-schema` | bug (open) | MEDIUM | idea-status gate + stub + README → FR5 | Picked; FIXED. Terminal `resolved --release v0.1.55` at CLOSURE. |
| `architecture-uml-decomposition` | backlog (candidate) | HIGH | doctor split → FR1; api split → FR2; reports merge → FR3; workspace_clean → FR6; UML → FR7 | Anchor `doctor.py#SpecsDoctor` (intent #1) SURVIVES; `agent-comms` catalog (#3) + `architecture.md#Visual evidence` doc (#4) SURVIVE; **`api.py#render_api_agents_canonical` (#2) is KILLED** by FR2. |

**Archival-at-SHIP (R4/R5 process law — applies because this release kills its own consuming
entry's anchor).** FR2 relocates `render_api_agents_canonical` (and deletes `api.py`), so the
`api.py#render_api_agents_canonical` anchor dies and the live entry would fail BL-SCHEMA
subject-resolution mid-branch. Therefore **no implementation-wave commit stages any
`specs/backlog/**`**; the consumed entry is moved to `specs/_archive/v0.1.55/consumed-backlog/`
with `consumed_backlog.json` in **one atomic commit at SHIP**, after all anchor-killing waves,
before the single push — so `dadaia backlog doctor` in the pushed/CI state never sees a live
entry referencing a dead anchor.

**Frozen-suite callout (dossier #6, corrected).** `tests/unit/features/spec_context/
test_doctor_lock_gc.py` exercises `spec_context.doctor.DoctorService` — a DIFFERENT subsystem
from the `features/specs/doctor.py#SpecsDoctor` split; it stays **zero-diff naturally** (FR1 does
not touch `spec_context`). Any diff to it is a red flag requiring adjudication.

## 7. Risks

- **Doctor cap-invariant slip (FR1) — RESOLVED by design.** A naive `pid_probe: lease.PidProbe`
  annotation would leak a 14th cross-feature edge (cap 27 → `lint-imports` + per-family test
  FAIL). Mitigation: the `doctor_types.PidProbe` leaf alias (R-1); each ignored import in exactly
  one submodule; per-family cap assertion.
- **Golden non-determinism (FR1) — RESOLVED.** Absolute issue paths + `specs_dir` + two
  date-gated checks would break a raw byte-golden on `tmp_path`. Mitigation: `<SPECS>` path
  normalization + clock freeze to 2026-07-15 (AC-2).
- **Interleaved-order regression (FR1).** Concatenating per-validator issue lists by family
  changes ORDER → golden FAILS. Mitigation: the coordinator owns the exact interleaved sequence
  (R-3); the all-six-families fixture (AC-2).
- **Moved-symbol blast radius (FR1/FR2/FR3).** Production + test consumers of moved symbols
  (`_read_active_md`, `Severity`, the 14 api test importers, the reports test dirs, the two
  stale docstrings) must all repoint. Mitigation: enumerated write sets + AC-8 textual-ref greps.
- **Stale-ignore lint error.** A module move without the same-commit `setup.cfg` edge repoint →
  `lint-imports` "No matches for ignored import". Mitigation: move + repoint + cap re-verify are
  one commit per wave.
- **FR4 over-correction / stall.** A blind fallback re-opens cross-attribution; a missing channel
  could stall W4. Mitigation: the harness-id channel + live-record staleness guard + the
  actionable-error contingency (R-6); the four-case AC-4 incl. the stale-id negative.
- **FR5 behavior-change scope.** The status-gate is an intentional semantics change; scoped and
  carved out of the non-goal (§4). Mitigation: status-gated (not blanket); AC-7(e) proves
  `candidate` still fires.
- **Reports rename stranding foreign anchors (FR3).** Deleting `reports_*` may strand code
  anchors in OTHER live backlog entries (PM curation). Mitigation: PM verifies `backlog doctor`
  clean at SHIP; flagged here, not owned here.

## 8. Memory files affected at CLOSURE

- `specs/memory/architecture.md` — Layers → features **25 → 23** (reports triplet → one
  `reports` package); the decomposed `features/specs/doctor.py` (thin coordinator owning ORDER +
  validator classes + the `doctor_types`/`doctor_common` leaves) and `features/panel/views/api.py`
  (per-domain modules; `api.py` deleted) module map; the `features/specs/doctor` contracts row;
  ignore-cap **unchanged 26 = 9/4/13** with the repointed doctor + reports edges (post-split
  enumeration) and the coordinator's PidProbe-leaf zero-`spec_context`-edge note; **Visual
  evidence** → the committed `specs/assets/architecture/*.md` fenced-mermaid diagrams + the
  regeneration law. Atomic.
- `specs/memory/product/**/agent-comms.md` (intent #3) — merged `features/reports/`.
  `specs/memory/product/**/specs-doctor.md` (if present) — coordinator + validator decomposition.
  `specs/memory/product/**/sdd-bug-backlog-governance.md` (if present) — the `idea`-status
  BL-SCHEMA gate (intents mandatory at `candidate`+). `catalog.json` + `index.md` regenerated if
  any `tldr`/`summary`/`area` changed.
- `specs/memory/quality-assurance.md` — the golden behavior-preservation precedent (in-process
  capture + path normalization + clock freeze + all-families fixture) and the module-size ratchet
  as an anti-erosion guard.
- `specs/memory/tech-stack.md` — **no change** (no dependency added; mermaid rendered natively,
  no mermaid-cli). Confirmed at CLOSURE.
- Bug telemetry (`specs/bugs/`) — the two `resolved --release v0.1.55` events are ADDITIVE.

## 9. Resolved definition decisions (dual review — binding)

- **OQ-1 → FR5:** REJECT self-resolving-subject; ADOPT the `idea`-status BL-SCHEMA gate (root
  fix); stub keeps `status: idea` + `description` + a commented `intents[]` template.
- **OQ-2 → FR7:** NO mermaid-cli/Node, NO `.svg`; fenced ```mermaid in `.md` under
  `specs/assets/architecture/`; introspection drift-guard.
- **OQ-3 → FR1:** sibling modules `features/specs/doctor_*.py` + shared leaves
  (`doctor_types.py` types+`PidProbe`, `doctor_common.py` pure helpers); `doctor.py` stays a file.
- **FR6:** `workspace_clean` STANDS ALONE.
- **api.py wiring:** `container.py` named imports per-domain; no facade/barrel; `api.py` deleted.
- **FR4 ADDITIVE calculus:** ADDITIVE lowers blast radius, not the correctness bar — no blind
  fallback; the fix is per-session-deterministic (harness-id channel) or an actionable error.
