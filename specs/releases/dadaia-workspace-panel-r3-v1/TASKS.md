# Tasks: Release — dadaia-workspace-panel-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-panel-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Total tasks:** 24 (PR3-00 through PR3-23)
> **Companion docs:** SPEC.md, PLAN.md

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum **one `[-]` per agent at a time**, except when the task table below marks two
tasks `parallel-safe: yes` (disjoint write sets, see PLAN §4).

---

## PR3-00 — Close prerequisite releases (v0.1.1 + agent-monitoring-v1)

- [x] **Owner:** product-engineer
- **Phase:** 0 (prerequisites)
- **SPEC acceptance:** §9 Prerequisites
- **Depends on:** none
- **Parallel-safe with:** none (must complete first)
- **Files modified:**
  - `specs/releases/v0.1.1/CLOSURE.md` (new)
  - `specs/releases/agent-monitoring-v1/CLOSURE.md` (new)
  - `specs/memory/product/server-registry.html`, `panel.html`, plus any other memory
    file touched by either closure
  - `specs/_archive/releases/v0.1.1/` (via `git mv`)
  - `specs/_archive/releases/agent-monitoring-v1/` (via `git mv`)
  - `specs/releases/ACTIVE.md`
- **Mudanças:** Set ACTIVE.md to CLOSURE phase for each prereq in turn; write
  CLOSURE.md per `dadaia-release-closure` template; render memory updates atomically;
  `git mv` to archive; finally repoint ACTIVE.md to
  `release: dadaia-workspace-panel-r3-v1 / phase: SPEC` (then walk ladder as artifacts
  approve).
- **Aceite:** Both prereq directories present under `specs/_archive/releases/`; `dadaia
  specs doctor` green; ACTIVE.md points at R3.

---

## PR3-01 — Asset split: create `views/assets/` and move CSS/JS slices

- [x] **Owner:** software-engineer
- **Phase:** 1 (asset split)
- **SPEC acceptance:** §3 D-foundation + §6 Static asset Content-Type table
- **Depends on:** PR3-00
- **Parallel-safe with:** none
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/{tokens,structure,agents,workflows}.py` (new)
  - `dadaia_workspace/features/panel/views/assets/js/{core.js,themes.js,agents.js,workflows.js}` (new)
  - `dadaia_workspace/features/panel/views/_assets.py` (becomes a thin re-export)
  - `dadaia_workspace/features/panel/views/index.py` (link/script tags switch to `/static/<name>`)
- **Mudanças:** Move PANEL_CSS / PANEL_JS slices into 8 new files per PLAN §4
  ownership map. Each JS file starts as a stub for SE-only territory; FE will fill
  in their owned files in later phases.
- **Aceite:** `pytest tests/features/panel/views/` green; manual smoke: panel loads,
  no 404 on any `/static/*` asset; `_assets.py` no longer contains string literals
  for moved CSS/JS.

---

## PR3-02 — Activate `/static/<name>` route + Content-Type table + unit test

- [x] **Owner:** software-engineer
- **Phase:** 1
- **SPEC acceptance:** §6 Static asset Content-Type table
- **Depends on:** PR3-01
- **Parallel-safe with:** none
- **Files modified:**
  - `dadaia_workspace/features/panel/views/static.py` (activate)
  - `dadaia_workspace/features/panel/views/handler.py` (route wiring)
  - `tests/features/panel/views/test_static.py` (new)
- **Mudanças:** Implement extension-to-MIME mapping per SPEC §6; `Cache-Control:
  no-cache`; 404 on unknown extension; unit test asserts Content-Type per extension.
- **Aceite:** `GET /static/tokens.css` returns `text/css; charset=utf-8`;
  `GET /static/missing.png` returns 404; unit test green.

---

## PR3-03 — Theme palettes (3 variants) in `css/tokens.py` + `css/structure.py`

- [x] **Owner:** frontend-engineer
- **Phase:** 2 (theme switcher)
- **SPEC acceptance:** Surface E (E2E-THM-01..04, E2E-THM-07)
- **Depends on:** PR3-02
- **Parallel-safe with:** none
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/tokens.py`
  - `dadaia_workspace/features/panel/views/assets/css/structure.py` (Warm focus-visible rule)
- **Mudanças:** Three palettes via `[data-theme="mint"|"sage"|"warm"]` selectors.
  Warm `focus-visible` includes secondary dark outline using `--color-accent-dark`.
- **Aceite:** Visual inspection of three themes; axe-core green on each; WCAG 4.5:1
  contrast for text in all three.

---

## PR3-04 — Theme switcher JS (button + dropdown + persistence + pre-paint script)

- [x] **Owner:** frontend-engineer
- **Phase:** 2
- **SPEC acceptance:** §7.7 + Surface E (E2E-THM-01, 02, 05, 06, 08, 09)
- **Depends on:** PR3-03
- **Parallel-safe with:** none
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/js/themes.js`
  - `dadaia_workspace/features/panel/views/index.py` (inline pre-paint `<script>` in `<head>`)
- **Mudanças:** Topbar button with `aria-haspopup="menu"` / `aria-expanded`; dropdown
  with `role="menu"`, `menuitemradio` items; Escape closes + focus returns to trigger;
  persist to `localStorage["dadaia-panel-theme"]`; pre-paint inline `<script>` reads
  storage and sets `data-theme` before first contentful paint.
- **Aceite:** E2E-THM-01..09 pass; no FOUC observed on hard reload.

---

## PR3-05 — `wrapper.py` token consumption fix

- [x] **Owner:** software-engineer
- **Phase:** 2
- **SPEC acceptance:** §4 wrapper.py FIX + §7.7
- **Depends on:** PR3-03
- **Parallel-safe with:** PR3-04 (different files)
- **Files modified:**
  - `dadaia_workspace/features/panel/views/wrapper.py`
- **Mudanças:** Replace hard-coded palette literals (`#7ec8e3` and similar) with
  `var(--color-*)` token references so iframe back-bars follow the active theme.
- **Aceite:** `/memory-view/<slug>/<path>` iframe back-bar visibly changes when
  theme changes; ~15 LOC delta.

---

## PR3-06 — Tab rename + reorder + responsive label

- [ ] **Owner:** software-engineer
- **Phase:** 3 (tab rename)
- **SPEC acceptance:** Surface A (E2E-TAB-01..06)
- **Depends on:** PR3-02
- **Parallel-safe with:** PR3-03/04/05 (different concerns, but conservative: run
  after Phase 2 to keep DOM diffs reviewable)
- **Files modified:**
  - `dadaia_workspace/features/panel/views/index.py`
  - `tests/features/panel/views/test_views_index.py` (assertion updates per SE
    implementation plan §6.3)
- **Mudanças:** Visible labels and order: Spec Context Projects, Agents, Workflows,
  Servers. Default-active = Spec Context Projects. Internal IDs unchanged.
  `<768px` abbreviation "Spec Contexts" via CSS-only rule in `css/structure.py`;
  `aria-label` keeps full string.
- **Aceite:** E2E-TAB-01..06 pass; existing `#memories` hash still activates the tab.

---

## PR3-07 — Canonical agent reader (`features/agents/` + `markdown_agent_store.py`)

- [ ] **Owner:** software-engineer
- **Phase:** 4 backend (agents)
- **SPEC acceptance:** §4 agents module + §5.1 shape
- **Depends on:** PR3-06
- **Parallel-safe with:** PR3-10, PR3-11 (FE territory, disjoint files)
- **Files modified:**
  - `dadaia_workspace/features/agents/reader.py` (new)
  - `dadaia_workspace/features/agents/__init__.py` (new)
  - `dadaia_workspace/infrastructure/markdown_agent_store.py` (new)
  - `tests/features/agents/test_reader.py` (new)
- **Mudanças:** Resolution order: `$DADAIA_AGENTS_DIR` → `.dadaia/agentic/agents/`
  → `.claude/agents/`. Allowlist frontmatter fields. Expose `AgentDTO` with
  description, skills, tools, model, opencode_model, max_turns, input_contract.
- **Aceite:** Unit tests cover all 3 resolution branches + allowlist enforcement +
  malformed-frontmatter resilience.

---

## PR3-08 — `/api/agents` rewrite: canonical overlay + telemetry sub-object + window query

- [ ] **Owner:** software-engineer
- **Phase:** 4 backend
- **SPEC acceptance:** §5.1 + Surface C (C1, C9, C12) + Surface G (G1, G8)
- **Depends on:** PR3-07
- **Parallel-safe with:** PR3-10, PR3-11
- **Files modified:**
  - `dadaia_workspace/features/panel/views/api.py`
  - `dadaia_workspace/features/panel/service.py`
  - `tests/features/panel/test_api_agents.py`
- **Mudanças:** Merge canonical catalog + telemetry overlay; drop telemetry-only
  rows silently; exactly 10 entries; **nest telemetry under `telemetry` sub-object**;
  honour `?active_window_days=N` (default 30, range 1–365); include `status_window_days`
  in response.
- **Aceite:** E2E-AGT-01, E2E-AGT-09, E2E-AGT-10, E2E-AGT-12, E2E-API-01, E2E-API-08
  pass; payload conforms exactly to SPEC §5.1 shape (top-level `agents[].telemetry.*`).

---

## PR3-09 — `GET /api/agents/<id>/prompt` + regex + defence-in-depth path check

- [ ] **Owner:** software-engineer
- **Phase:** 4 backend
- **SPEC acceptance:** §5.2 + Surface G (G2, G3, G10, G11)
- **Depends on:** PR3-07
- **Parallel-safe with:** PR3-08, PR3-10, PR3-11
- **Files modified:**
  - `dadaia_workspace/features/panel/views/api.py`
  - `dadaia_workspace/features/agents/reader.py` (`get_prompt`)
  - `tests/features/panel/test_api_agent_prompt.py`
- **Mudanças:** Validate `id` against `^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$`;
  resolve candidate path and assert `Path(resolved).resolve().is_relative_to(base.resolve())`
  before opening; 404 if file absent; 400 if regex or path-resolve check fails.
  Auth: Bearer required.
- **Aceite:** E2E-API-02, E2E-API-03, E2E-API-10, E2E-API-11 pass; defence-in-depth
  unit test exercises a symlink that escapes `base_dir` and asserts 400.

---

## PR3-10 — Agent card UI (collapsed) — FE

- [ ] **Owner:** frontend-engineer
- **Phase:** 4 UI (agents)
- **SPEC acceptance:** §7.4 + Surface C (C1, C2, C3)
- **Depends on:** PR3-04 (themes), PR3-06 (tab rename)
- **Parallel-safe with:** PR3-07, PR3-08, PR3-09 (SE backend, disjoint files)
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/agents.py`
  - `dadaia_workspace/features/panel/views/assets/js/agents.js`
- **Mudanças:** Collapsed card layout (status badge, name, description clamp,
  3-stat row, skills chips first 2 + "+N more", chevron, 3px left-border accent for
  active). Skeleton placeholder with `aria-busy`. Empty-state graceful (`Never`,
  `—`, `0`).
  - Extract Agents IIFE block from `assets/js/core.js` into `assets/js/agents.js`
    (placeholder landed in PR3-01); update `_assets.py` so `PANEL_JS` reads from
    `agents.js`.
- **Aceite:** E2E-AGT-01..03 pass; layout works at ≥1024px (2-col) and below (1-col).
  - `assets/js/core.js` no longer contains the Agents IIFE block; `pytest
    tests/features/panel/views/test_assets.py` confirms PANEL_JS still produces a
    syntactically valid script.

---

## PR3-11 — Agent card UI (expanded + lazy prompt fetch + multi-open accordion) — FE

- [ ] **Owner:** frontend-engineer
- **Phase:** 4 UI
- **SPEC acceptance:** §7.4 + Surface C (C4..C8, C11)
- **Depends on:** PR3-10, PR3-09 (endpoint for lazy fetch)
- **Parallel-safe with:** Phase 5 UI tasks (PR3-16, PR3-17)
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/agents.py`
  - `dadaia_workspace/features/panel/views/assets/js/agents.js`
- **Mudanças:** Expanded card with full skills, cost-by-context bars, scrollable
  `<pre>` system prompt (lazy fetch via `authedFetch('/api/agents/<id>/prompt')` on
  first expand), copy-to-clipboard button. `aria-expanded` on chevron, `aria-controls`
  on detail. Enter/Space toggles. Multi-open accordion (no single-open enforcement).
  `prefers-reduced-motion` disables expand transition.
- **Aceite:** E2E-AGT-04..08, E2E-AGT-11 pass; axe-core clean on Agents tab in all
  three themes.

---

## PR3-12a — Pre-implementation: extend `MarkdownWorkflowStore` if gaps

- [ ] **Owner:** software-engineer
- **Phase:** 5 backend (workflows) — pre-implementation gate
- **SPEC acceptance:** §4 wrap directive + Risk #3
- **Depends on:** PR3-06
- **Parallel-safe with:** none (must complete before PR3-12)
- **Files modified:**
  - `dadaia_workspace/infrastructure/markdown_workflow_store.py` (only if gaps confirmed)
  - `tests/infrastructure/test_markdown_workflow_store.py`
- **Mudanças:** Re-read the store. Document `## Pre-implementation findings` in
  this task's commit message: presence of `get_by_name`, behaviour for
  `expected_output_path`, behaviour for `must_include` flow-through. Add missing
  methods only if absent. If no gaps, mark this task `[x]` with a one-line message
  "no gaps — store passes through all required fields" and proceed.
- **Aceite:** All four pieces (`get_by_name`, `expected_output_path`,
  `must_include`, full DTO flow-through) confirmed accessible from the wrapping
  service.

---

## PR3-12 — `WorkflowsService` wrapping `MarkdownWorkflowStore` + mtime cache

- [ ] **Owner:** software-engineer
- **Phase:** 5 backend
- **SPEC acceptance:** §4 workflows module + §5.6 cache
- **Depends on:** PR3-12a
- **Parallel-safe with:** PR3-16, PR3-17 (FE territory)
- **Files modified:**
  - `dadaia_workspace/features/workflows/service.py` (new)
  - `dadaia_workspace/features/workflows/__init__.py` (new)
  - `tests/features/workflows/test_service.py` (new)
- **Mudanças:** Service wraps `MarkdownWorkflowStore`; DTO mapping for list +
  detail responses; per-process dict cache keyed by `(path, mtime, size)`; one
  inline comment documenting "cache size bounded by file count in source dir".
- **Aceite:** Unit tests cover cache hit, mtime invalidation, file deletion
  (cache eviction), DTO field shape.

---

## PR3-13 — DAG layout + SVG renderer (`features/workflows/dag.py`)

- [ ] **Owner:** software-engineer
- **Phase:** 5 backend
- **SPEC acceptance:** §4 dag.py + §7.5 DAG visual + Surface D (D5, D6, D7, D14)
- **Depends on:** PR3-12
- **Parallel-safe with:** PR3-16, PR3-17 (FE territory)
- **Files modified:**
  - `dadaia_workspace/features/workflows/dag.py` (new)
  - `tests/features/workflows/test_dag.py` (new)
- **Mudanças:** Longest-path layered layout; stdlib only; rounded-rect nodes
  (140×40); parallel-group dashed bands; gate ⊙ marker; edge arrow polygons;
  `role="img"` + `<title>` + per-node `aria-label`; HTML-escape at every embed
  point. **Deliver SVG prototype for `cross-cutting-feature` and `spec-refinement`
  before committing renderer constants** (paste prototype as comment in the task's
  intermediate commit; FE reviews before final tuning).
- **Aceite:** E2E-WF-05, E2E-WF-06, E2E-WF-07, E2E-WF-14 pass; manual inspection of
  the two hardest workflows shows no node overlap.

---

## PR3-14 — `/api/workflows` rewrite: LIST card summaries only

- [ ] **Owner:** software-engineer
- **Phase:** 5 backend
- **SPEC acceptance:** §5.3 + Surface D (D11, D12) + Surface G (G4, G5, G9)
- **Depends on:** PR3-12
- **Parallel-safe with:** PR3-16
- **Files modified:**
  - `dadaia_workspace/features/panel/views/api.py`
  - `tests/features/panel/test_api_workflows.py`
- **Mudanças:** Replace existing workflow endpoint to return card summaries only:
  `name`, `display_name`, `description`, `version`, `schema_version`, `stage_count`
  (integer), `agent_ids`, `has_parallel`, `has_gates`, `source_path`. No
  `diagram_svg`, no `stages[]`. Bearer required.
- **Aceite:** E2E-WF-11 passes (12 entries, `stage_count: 5` for tdd-cycle, no
  `stages` key, no `diagram_svg` key); E2E-API-04, E2E-API-05, E2E-API-09 pass.

---

## PR3-15 — `GET /api/workflows/<name>` (detail) + regex + defence-in-depth

- [ ] **Owner:** software-engineer
- **Phase:** 5 backend
- **SPEC acceptance:** §5.4 + Surface D (D8a/b, D12 companion) + Surface G (G6, G7, G12)
- **Depends on:** PR3-12, PR3-13, PR3-14
- **Parallel-safe with:** PR3-16, PR3-17
- **Files modified:**
  - `dadaia_workspace/features/panel/views/api.py`
  - `dadaia_workspace/features/workflows/service.py` (detail DTO with `stages[]`)
  - `tests/features/panel/test_api_workflow_detail.py`
- **Mudanças:** Validate `name` against the SPEC §5.4 regex; `Path.resolve().is_relative_to(base)`
  defence-in-depth; Bearer required. Response includes full `stages[]` +
  `diagram_svg` from `dag.py`.
- **Aceite:** E2E-WF-08 (both parts), E2E-API-06, E2E-API-07 (split), E2E-API-12
  pass.

---

## PR3-16 — Workflow card grid UI — FE

- [ ] **Owner:** frontend-engineer
- **Phase:** 5 UI
- **SPEC acceptance:** §7.5 + Surface D (D1, D2, D3)
- **Depends on:** PR3-04 (themes), PR3-14 (endpoint shape)
- **Parallel-safe with:** PR3-07/08/09/11/12/13/15
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/workflows.py`
  - `dadaia_workspace/features/panel/views/assets/js/workflows.js`
- **Mudanças:** 12-card grid (2-col ≥768px, 1-col below). Card layout: name,
  version pill, description clamp, agent chips, stats footer, "View DAG →" CTA.
  - Extract Workflows IIFE block from `assets/js/core.js` into
    `assets/js/workflows.js` (placeholder landed in PR3-01); update `_assets.py` so
    `PANEL_JS` reads from `workflows.js`.
- **Aceite:** E2E-WF-01, E2E-WF-02, E2E-WF-03 pass.
  - `assets/js/core.js` no longer contains the Workflows IIFE block; `pytest
    tests/features/panel/views/test_assets.py` confirms PANEL_JS still produces a
    syntactically valid script.

---

## PR3-17 — Workflow detail view + hash routing + DAG skeleton — FE

- [ ] **Owner:** frontend-engineer
- **Phase:** 5 UI
- **SPEC acceptance:** §7.1 hash grammar + §7.5 detail view + DAG skeleton + Surface D (D4, D8, D10, D13, D14)
- **Depends on:** PR3-16, PR3-15
- **Parallel-safe with:** PR3-11
- **Files modified:**
  - `dadaia_workspace/features/panel/views/assets/css/workflows.py` (detail view +
    DAG skeleton + placeholder agent node style)
  - `dadaia_workspace/features/panel/views/assets/js/workflows.js` (renderDetail,
    fetchDetail, loadDAG, hashchange handler)
  - `dadaia_workspace/features/panel/views/assets/js/core.js` (hash grammar parser
    accepts `#workflows?detail=` and `#agents?filter=`; module-level comment
    documents grammar)
- **Mudanças:** Hash routing per SPEC §7.1; in-section detail replacement; back
  link; DAG container hosts the server-rendered SVG; **DAG loading skeleton**
  (3 placeholder rounded-rects, pulse animation, `aria-busy`, `prefers-reduced-motion`
  cascade); error retry text; placeholder agent node style (italic + dashed border).
- **Aceite:** E2E-WF-04 (updated — asserts detail-endpoint network call on click),
  E2E-WF-08 (two-part), E2E-WF-10, E2E-WF-13, E2E-WF-14 pass.

---

## PR3-18 — Cleanup: drop dead field, dead method, dead reader, `# DEAD:` comment

- [ ] **Owner:** software-engineer
- **Phase:** 6 (cleanup)
- **SPEC acceptance:** §4 SHRINK rows + §8.1
- **Depends on:** PR3-08 (so `/api/servers` shrink does not break agents work)
- **Parallel-safe with:** none (touches multiple files)
- **Files modified:**
  - `dadaia_workspace/features/panel/views/api.py` (`/api/servers` drops `unregistered`)
  - `dadaia_workspace/features/panel/service.py` (delete `list_unregistered_listeners`)
  - `dadaia_workspace/features/telemetry/schema.py` (literal `# DEAD: replaced by
    canonical workflow reader in panel-r3; do not extend; see backlog/candidates.md`
    next to `workflows` and `workflow_agents` table CREATE statements)
  - `dadaia_workspace/features/telemetry/reader/workflows.py` (delete)
  - `dadaia_workspace/features/telemetry/aggregator.py` (remove workflow query path)
  - `tests/features/telemetry/test_reader_workflows.py` (delete)
  - `tests/features/telemetry/test_aggregator.py` (empty-telemetry assertion update)
- **Aceite:** `pytest -q` green after deletion + updates; `/api/servers` payload
  no longer contains `unregistered` key; grep on the `# DEAD:` literal in
  `schema.py` finds 2 occurrences (one per table).

---

## PR3-19 — SE unit test suite (~38 new tests)

- [ ] **Owner:** software-engineer
- **Phase:** 7 (tests + evidence)
- **SPEC acceptance:** §13 Definition of Done #2
- **Depends on:** PR3-07..PR3-18
- **Parallel-safe with:** PR3-20, PR3-21
- **Files modified:**
  - `tests/features/agents/`
  - `tests/features/workflows/`
  - `tests/features/panel/views/test_static.py`
  - `tests/infrastructure/test_markdown_agent_store.py`
- **Mudanças:** Unit tests for canonical agent reader, workflow service + DAG
  renderer, static-route Content-Type, defence-in-depth path checks (symlink
  escape, traversal, regex rejection).
- **Aceite:** `pytest -q tests/features/agents tests/features/workflows
  tests/features/panel/views tests/infrastructure` green; coverage ≥ 90% for the
  new modules.

---

## PR3-20 — SE integration tests (~12 new)

- [ ] **Owner:** software-engineer
- **Phase:** 7
- **SPEC acceptance:** §13 Definition of Done #2
- **Depends on:** PR3-19
- **Parallel-safe with:** PR3-21
- **Files modified:**
  - `tests/integration/panel/test_api_agents.py`
  - `tests/integration/panel/test_api_workflows.py`
  - `tests/integration/panel/test_static_route.py`
- **Mudanças:** End-to-end HTTP integration tests (no browser) covering: telemetry
  overlay merge, `?active_window_days` honoured, cache invalidation on mtime
  change, Bearer enforcement, defence-in-depth on traversal.
- **Aceite:** `pytest -q tests/integration/panel` green.

---

## PR3-21 — QA E2E Playwright suite (56 tests)

- [ ] **Owner:** qa-engineer
- **Phase:** 7
- **SPEC acceptance:** §10 Surfaces A–H + §13 Definition of Done #5
- **Depends on:** PR3-19, PR3-20 (so unit/integration are green before E2E
  authoring; reduces churn)
- **Parallel-safe with:** PR3-22
- **Files modified:**
  - `tests/e2e/tab-navigation.spec.ts` (6 tests)
  - `tests/e2e/spec-context-tab.spec.ts` (2)
  - `tests/e2e/agents-tab.spec.ts` (11)
  - `tests/e2e/workflows-tab.spec.ts` (14)
  - `tests/e2e/theme-switcher.spec.ts` (9)
  - `tests/e2e/servers-tab.spec.ts` (1)
  - `tests/e2e/api-contracts.spec.ts` (13: E2E-API-01..12 + E2E-AGT-12)
- **Mudanças:** All 56 tests authored against **real files**, real
  `.dadaia/agentic/agents/` and `.dadaia/agentic/workflows/`. Zero-telemetry fixture
  uses `DADAIA_TELEMETRY_DB=/tmp/test_telemetry_empty.sqlite`. E2E-AGT-12 uses
  pre-check skip guard for telemetry state. Test IDs E2E-WF-04, E2E-WF-08,
  E2E-WF-11, E2E-API-07 carry the updated assertions per QA review §2 + §4.
  E2E-API-12 + E2E-AGT-12 are NEW per QA review §3 + §5.
- **Aceite:** `npx playwright test` returns 56/56 green.

---

## PR3-22 — Visual evidence (21 screenshots) + axe-core ×3 themes

- [ ] **Owner:** qa-engineer
- **Phase:** 7
- **SPEC acceptance:** Surface H + §13 Definition of Done #6, #7
- **Depends on:** PR3-21
- **Parallel-safe with:** none (consumes final UI)
- **Files modified:**
  - `.dadaia/reports/dadaia-workspace/qa-engineer/<run>/screenshots/*.png` (21
    files per QA test plan §4)
  - `.dadaia/reports/dadaia-workspace/qa-engineer/<run>-evidence.html` (with
    `dadaia-handoff-emitter` sidecar)
- **Mudanças:** Capture all 21 screenshots; run axe-core on Mint/Sage/Warm against
  Agents and Workflows surfaces; emit one consolidated evidence HTML + handoff
  sidecar.
- **Aceite:** All 21 screenshots present; axe-core reports zero
  serious/critical violations; handoff sidecar VALID.

---

## PR3-23 — CLOSURE.md + memory update + backlog returns + archive

- [ ] **Owner:** product-engineer
- **Phase:** 8 (closure)
- **SPEC acceptance:** §11 Memory + §13 Definition of Done #9, #10
- **Depends on:** PR3-22
- **Parallel-safe with:** none
- **Files modified:**
  - `specs/releases/ACTIVE.md` (phase → CLOSURE, then ARCHIVED)
  - `specs/releases/dadaia-workspace-panel-r3-v1/CLOSURE.md` (new)
  - `specs/memory/product/index.html` (catalog entry order + description for "panel")
  - `specs/memory/product/panel.html` (rewrite per SPEC §11)
  - `specs/memory/architecture.html` (note new modules)
  - `specs/memory/tech-stack.html` (verify pyyaml; document as "no change" if unchanged)
  - `specs/backlog/candidates.md`, `specs/backlog/ideas.md` (file 9 DEFERRED items
    per SPEC §8.2)
  - `git mv specs/releases/dadaia-workspace-panel-r3-v1 specs/_archive/releases/dadaia-workspace-panel-r3-v1`
- **Mudanças:** Set ACTIVE.md phase to CLOSURE; write CLOSURE.md per
  `dadaia-release-closure` template (Summary, Tasks completed PR3-00..PR3-22 with
  final SHAs, Validations as triples per template, Drifts per `### <slug>` blocks
  if any, Memory updates list, Backlog returns list, Archive decision = MOVE);
  render memory HTML from canonical templates; run
  `.dadaia/.venv/bin/dadaia specs doctor` and confirm `[ok]`; `git mv` to archive;
  repoint ACTIVE.md to next release or `release: none`.
- **Aceite:** `dadaia specs doctor` `[ok]`; `dadaia public doctor` `[ok]`; release
  directory present under `specs/_archive/releases/`; ACTIVE.md repointed; CLOSURE
  Validations cite all evidence per SPEC §13.

---

## Approval

Operator transitions this TASKS.md `**Status:** Draft → Em revisão → Aprovado`. Once
Aprovado, update ACTIVE.md phase to `IMPLEMENTATION` to unblock implementer agents.
