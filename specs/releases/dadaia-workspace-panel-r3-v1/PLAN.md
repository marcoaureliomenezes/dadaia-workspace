# Plan: Release — dadaia-workspace-panel-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-panel-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Companion:** SPEC.md in this directory
> **Length budget:** ≤ 300 lines (gate-enforced for releases created 2026-05-17+)

---

## 1. Strategy in one paragraph

Land the asset split FIRST so three specialists can write into separate files in parallel.
Layer everything else on top of that split: theme switcher next (small, validates the
split), then tab rename (trivial), then the two large parallel surfaces — Agents and
Workflows. SE owns all backend + the DAG renderer; FE owns all UI; QA owns the
56-test E2E suite + 21 visual evidence screenshots; PE answers questions and writes
CLOSURE. The release closes the moment all 23 tasks are `[x]` DONE and memory is updated.

---

## 2. Phase order and dependency graph

```
Phase 0 (PE)             Phase 1 (SE)               Phase 2 (FE+SE)
[prereq closures]   ──►   [asset split]      ──►    [theme switcher]
                                │                          │
                                ▼                          ▼
                          Phase 3 (SE)               Phase 4 backend (SE) ─┐
                          [tab rename]               Phase 4 UI (FE)       │  parallel
                                │                                          │  disjoint
                                ▼                                          │  write
                          Phase 5 backend (SE) ──┐                         │  sets
                          Phase 5 UI (FE)        │  parallel               │
                                                 │  disjoint               │
                                                 ▼                         │
                                          Phase 6 (SE)       ◄─────────────┘
                                          [cleanup]
                                                │
                                                ▼
                                          Phase 7 (QA + SE)
                                          [test suites + evidence]
                                                │
                                                ▼
                                          Phase 8 (PE)
                                          [CLOSURE + memory + archive]
```

Phases 4 and 5 each split into backend + frontend sub-tasks with **disjoint write sets**
(file ownership map in §4) so they run concurrently. The asset split (Phase 1) is the
foundation that makes disjoint write sets possible.

---

## 3. Phase detail

### Phase 0 — Prerequisite closures (PE)

1. **v0.1.1 closure:** verify all `T-DSR-*` tasks in
   `specs/releases/v0.1.1/TASKS.md` are `[x]` DONE; write CLOSURE.md per
   `dadaia-release-closure` template; update `specs/memory/product/server-registry.html`
   and `panel.html` per that release's memory plan; `git mv` to
   `specs/_archive/releases/v0.1.1/`.
2. **agent-monitoring-v1 closure:** verify task state; if green, write CLOSURE.md
   + memory updates + archive. If any task is open, finish it before continuing.
3. Update `ACTIVE.md` to `release: dadaia-workspace-panel-r3-v1 / phase: SPEC` and walk
   the ladder up to `IMPLEMENTATION` as each artifact reaches `**Status:** Aprovado`.

Tasks: PR3-00.

### Phase 1 — Asset split + static route (SE)

1. Create `dadaia_workspace/features/panel/views/assets/` with:
   - `css/{tokens.py, structure.py, agents.py, workflows.py}`
   - `js/{core.js, themes.js, agents.js, workflows.js}`
2. Move existing PANEL_CSS / PANEL_JS slices from `_assets.py` into the new files per
   the ownership map (§4). `_assets.py` becomes a thin re-export module during
   transition.
3. Activate `features/panel/views/static.py`: register `GET /static/<name>`; serve
   from the assets directory; enforce the Content-Type table locked in SPEC §6;
   `Cache-Control: no-cache`; 404 on unknown extension.
4. Update `index.py` to emit `<link rel="stylesheet" href="/static/tokens.css">` etc.
   instead of inlining the full PANEL_CSS. Keep CSP `'unsafe-inline'` on script-src
   for R3 (drop is deferred to first hotfix post-R3 per SPEC §8.2).
5. Unit test in `tests/features/panel/views/test_static.py` asserting Content-Type for
   each supported extension.

Tasks: PR3-01, PR3-02.

### Phase 2 — Theme switcher (FE + SE)

1. **CSS variants** (FE in `css/tokens.py` and `css/structure.py`): define the 3
   palettes (Mint, Sage, Warm) via `[data-theme="mint"]` / `[data-theme="sage"]` /
   `[data-theme="warm"]` selectors; lock the Warm focus-visible double-outline rule.
2. **JS button + dropdown** (FE in `js/themes.js`): button, dropdown menu with
   `role="menu"`, `menuitemradio` items, Escape closes, focus management.
3. **Persistence** (FE in `js/themes.js`): write to and read from
   `localStorage["dadaia-panel-theme"]`. Inline `<script>` in `<head>` (in
   `index.py`) reads pre-paint to prevent FOUC.
4. **wrapper.py fix** (SE): replace hard-coded palette literals with
   `var(--color-*)` token references so iframe back-bars follow theme.

Tasks: PR3-03, PR3-04, PR3-05.

### Phase 3 — Tab rename + reorder (SE)

1. In `index.py`, change visible labels and order: Spec Context Projects, Agents,
   Workflows, Servers. Default-active = Spec Context Projects.
2. Internal IDs (`section-memories`, `tab-memories`, etc.) unchanged.
3. Responsive label: at `<768px` show "Spec Contexts"; full `aria-label`.
4. Update `tests/features/panel/views/test_views_index.py` assertions to match new
   labels/order (SE planned break per implementation report §6.3).

Tasks: PR3-06.

### Phase 4 — Agents backend + UI (SE + FE in parallel)

**Backend (SE):**
- PR3-07: `dadaia_workspace/features/agents/reader.py` + `infrastructure/markdown_agent_store.py`.
  Resolution order: (1) `$DADAIA_AGENTS_DIR`, (2)
  `<workspace_root>/.dadaia/agentic/agents/`, (3) `<workspace_root>/.claude/agents/`.
  Allowlist frontmatter fields; expose `AgentDTO`.
- PR3-08: rewrite `/api/agents` to merge canonical catalog + telemetry overlay, drop
  telemetry-only rows silently, return exactly 10 entries, **nest telemetry under a
  `telemetry` sub-object** per SPEC §5.1, honour `?active_window_days=N`.
- PR3-09: `GET /api/agents/<id>/prompt` with regex guard + `Path.resolve().is_relative_to`
  defence-in-depth.

**UI (FE), runs in parallel with PR3-07/08/09 (disjoint write sets — §4):**
- PR3-10: collapsed agent card in `css/agents.py` + `js/agents.js` (status badge,
  description clamp, stats, chips, chevron, left-border accent).
- PR3-11: expanded agent card (skills, cost-by-context bars, lazy prompt fetch with
  copy button, `aria-expanded`/`aria-controls`, multi-open accordion, skeleton
  loading state with `aria-busy`, `prefers-reduced-motion` cascade).

### Phase 5 — Workflows backend + UI (SE + FE in parallel)

**Backend (SE):**
- PR3-12a (conditional, pre-implementation): re-read
  `infrastructure/markdown_workflow_store.py`. If `get_by_name`,
  `expected_output_path`, or `must_include` flow-through are missing, extend the
  store with these methods FIRST. Document gaps in a one-paragraph comment under
  `## Pre-implementation findings` in TASKS.md when the task is reserved.
- PR3-12: `features/workflows/service.py` wrapping `MarkdownWorkflowStore` with DTO
  mapping + per-process `(path, mtime, size)` cache; one inline code comment
  documenting cache bound.
- PR3-13: `features/workflows/dag.py` — longest-path layered layout + SVG serialisation,
  stdlib only, rounded-rect nodes, parallel-group dashed bands, gate ⊙ marker, edge
  arrow polygons, `role="img"` + per-node `aria-label`, HTML-escape at every embed
  point. **SE delivers SVG prototype for `cross-cutting-feature` and `spec-refinement`
  before committing renderer constants** (risk #1).
- PR3-14: rewrite `/api/workflows` to return card summaries only (no `diagram_svg`,
  no `stages[]`).
- PR3-15: `GET /api/workflows/<name>` returning full `stages[]` + `diagram_svg` +
  regex guard + `Path.resolve().is_relative_to` defence-in-depth.

**UI (FE), runs in parallel with backend tasks:**
- PR3-16: workflow card grid in `css/workflows.py` + `js/workflows.js` (name, version
  pill, description clamp, agent chips, stats footer, "View DAG →" CTA).
- PR3-17: detail view with hash routing (`#workflows?detail=<name>`), in-section
  replacement, back link, DAG container, **DAG loading skeleton** (3 placeholder
  rounded-rects, pulse animation, `aria-busy`, `prefers-reduced-motion` cascade per
  SPEC §7.5), error retry text. Hash grammar parser in `js/core.js` accepts both
  `#workflows?detail=` and `#agents?filter=`; module-level comment documents grammar.

### Phase 6 — Cleanup (SE)

- PR3-18: drop `unregistered` field from `/api/servers`; delete
  `list_unregistered_listeners()`; add literal `# DEAD: replaced by canonical workflow
  reader in panel-r3; do not extend; see backlog/candidates.md` next to `workflows`
  and `workflow_agents` table definitions in `schema.py`; delete
  `features/telemetry/reader/workflows.py`; remove its tests
  (`test_reader_workflows.py`).

### Phase 7 — Test suites + evidence (QA + SE)

- PR3-19: SE unit tests for `features/agents/`, `features/workflows/`, `dag.py`,
  `markdown_agent_store.py`, static-route Content-Type, path-traversal guards
  (regex + `Path.resolve` defence-in-depth). Estimate ~38 unit tests.
- PR3-20: SE integration tests covering the new endpoints + telemetry overlay +
  cache mtime invalidation. Estimate ~12 integration tests.
- PR3-21: QA Playwright suite — **56 E2E tests** per SPEC §10 + QA test plan §3 +
  QA review §6. Updated test IDs: E2E-WF-04 (asserts detail-endpoint network call),
  E2E-WF-08 (two-part LIST vs detail), E2E-WF-11 (no `stages[]` in LIST), E2E-API-07
  (split absence + presence), plus NEW E2E-API-12 + NEW E2E-AGT-12. Existing 54
  carry forward.
- PR3-22: capture the 21 visual evidence screenshots per QA test plan §4; run
  axe-core on Mint/Sage/Warm; place artefacts under
  `.dadaia/reports/dadaia-workspace/qa-engineer/<run>/screenshots/` and reference in
  CLOSURE Validations.

### Phase 8 — CLOSURE (PE)

- PR3-23: set `ACTIVE.md` phase to `CLOSURE`; write `CLOSURE.md` per
  `dadaia-release-closure` template (Summary, Tasks completed, Validations, Drifts,
  Memory updates, Backlog returns, Archive decision = MOVE); render
  `specs/memory/product/panel.html` + `index.html` + `architecture.html` updates
  per SPEC §11 (tech-stack.html only if pyyaml note needs adjusting); file the 9
  DEFERRED items into `backlog/candidates.md` or `backlog/ideas.md` per SPEC §8.2;
  run `dadaia specs doctor` (`.dadaia/.venv/bin/dadaia specs doctor`) and confirm
  `[ok]`; `git mv specs/releases/dadaia-workspace-panel-r3-v1
  specs/_archive/releases/dadaia-workspace-panel-r3-v1`; repoint ACTIVE.md.

---

## 4. File ownership map for `views/assets/` (8 files, 3 writers)

This map prevents merge conflicts during Phase 2/4/5 parallel work. Each file has a
**single authoritative writer** per phase. Cross-phase reads are allowed; cross-phase
writes require explicit handoff via task completion.

| File | Phase 1 (split) | Phase 2 (theme) | Phase 4 (agents) | Phase 5 (workflows) |
|---|---|---|---|---|
| `css/tokens.py` | SE writes (move tokens block) | **FE writes** (3 palettes) | — | — |
| `css/structure.py` | SE writes (move reset/body/topbar/tab-bar/skeleton-pulse) | FE writes (Warm focus-visible rule) | — | — |
| `css/agents.py` | SE writes (move agent card slices) | — | **FE writes** (collapsed + expanded + skeleton) | — |
| `css/workflows.py` | SE writes (move workflow + DAG slices) | — | — | **FE writes** (grid + detail + DAG skeleton + placeholder node style) |
| `js/core.js` | SE writes (move tab + hash router + authedFetch + DOM-ready) | FE writes (hash grammar comment) | — | FE writes (hash router accepts `#workflows?detail=`) |
| `js/themes.js` | SE writes (stub) | **FE writes** (button, dropdown, persistence) | — | — |
| `js/agents.js` | SE writes (stub) | — | **FE writes** (renderAgentCard, expand, lazy prompt fetch) | — |
| `js/workflows.js` | SE writes (stub) | — | — | **FE writes** (renderWorkflowCard, renderDetail, fetchDetail, loadDAG, hashchange handler) |

**Rule of thumb:** in any given phase, the column with "FE writes" is the only writer.
SE retains read-only access for cross-cutting fixes; if SE must edit an FE-owned file
during their phase, that fix is logged as a drift in CLOSURE.md.

---

## 5. Effort budget

| Layer | Estimate | Source |
|---|---|---|
| Backend (Phases 1, 3, 4-be, 5-be, 6) | **22–32h** | SE review §3 (revised up from 16–24h after re-scoping under decisions #1, #2, #5, #21, #22; further `MarkdownWorkflowStore` extension work may add 1–3h if gaps confirmed by PR3-12a). |
| Frontend (Phases 2, 4-ui, 5-ui) | **20–28h** | FE design report. Includes 3-palette token table, hash router, DAG skeleton, multi-open accordion, lazy prompt fetch, axe-core fixes. |
| QA (Phase 7 — E2E + visual evidence + axe-core) | **14–18h** | QA test plan §6 — 56 tests authored against real files, 21 screenshots, axe-core×3 themes. |
| SE unit + integration tests (PR3-19, PR3-20) | **6–9h** | SE implementation plan (38 unit + 12 integration). Tracked inside the SE budget above for some teams; broken out here for accounting. |
| Prereq closures + CLOSURE + memory + archive (PE) | **3–5h** | Three closures (v0.1.1, agent-monitoring-v1, R3 itself) + memory rendering. |
| **Total release effort** | **~65–92h** | Roughly 1.5–2.5 engineer-weeks at normal cadence. |

Effort is informative; the gate is task completion (all `[x]`), not hours logged.

---

## 6. Validation plan

| Validation | Command | Expected |
|---|---|---|
| Doctor (specs) | `.dadaia/.venv/bin/dadaia specs doctor` | `[ok] 0 errors` |
| Doctor (workspace) | `.dadaia/.venv/bin/dadaia doctor` | green |
| Doctor (public) | `.dadaia/.venv/bin/dadaia public doctor` | all `[ok]` |
| Lint + format | `ruff format --check && ruff check && mypy --strict` | green |
| Unit + integration | `pytest -q` | green; no regressions; +~50 new tests |
| E2E | `npx playwright test` | 56 green |
| Accessibility | axe-core per theme on Agents + Workflows + Themes surfaces | zero violations on serious/critical |
| Visual evidence | 21 screenshots captured + DAG renders inspected | committed under qa-engineer report dir |
| Manual smoke | open panel, switch themes, expand 2 agents, open cross-cutting-feature DAG | operator confirms "control surface" feel |

---

## 7. Parallelism contract

- **At most one `[-]` per agent at any time**, except across Phases 4 and 5 where the
  ownership map (§4) declares disjoint write sets. The TASKS.md document marks the
  safe-parallel boundaries explicitly per the `dadaia-task-manager` skill.
- Any task that needs to violate the ownership map must be re-negotiated by amending
  TASKS.md (status flip from `[x]` back to `[ ]` is forbidden; raise to PE instead).

---

## 8. Risk-driven sequencing

The phase order above is risk-driven, not just dependency-driven:

- **Phase 1 first** because the asset split is the highest-risk infra change in R3.
  Catching its issues before any new feature code means rollback is cheap.
- **Phase 2 (theme)** validates that the split works end-to-end and exercises
  `/static/<name>` early; the rest of R3 then benefits from theme tokens.
- **Phase 5 (workflows)** lands after Phase 4 (agents) because the DAG renderer is
  the only new visual primitive in R3; agents are familiar territory. Stacking the
  novel work later lets the team build confidence first.

---

## 9. Done criteria recap

PLAN is DONE when all 8 phases have ended cleanly, every PR3-* task in TASKS.md is
`[x]`, and SPEC §13 Definition of Done is satisfied in CLOSURE Validations.
