# Closure: Release — dadaia-workspace-panel-r3-v1

> **Status:** Aprovado
> **Release ID:** dadaia-workspace-panel-r3-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-18

## Summary

Release **R3** transforms `dadaia panel` from a single-tab utility into a **control
surface**. The "Memories" tab is renamed **Spec Context Projects** and moved to the
left-most position, declaring the operator-facing identity of the panel. Three further
tabs ship with full functional depth: **Agents** renders exactly 10 canonical agent
cards (collapsed by default, multi-open accordion on expand) with status badge, 3-stat
row (sessions / total cost / last activity), cost-by-context breakdown, skills chips and
**lazy fetch of the system prompt** via the new `GET /api/agents/<id>/prompt` endpoint.
**Workflows** renders 12 canonical workflow cards backed by the new `WorkflowsService`
wrapping `MarkdownWorkflowStore`; clicking a card opens a hash-routed detail view
(`#workflows?detail=<name>`) that fetches `GET /api/workflows/<name>` and displays a
**server-side rendered DAG SVG** with `role="img"` + `<title>` + per-node `aria-label`.
**Servers** keeps its prior payload minus the dead `unregistered` field.

A **theme switcher** lands in the topbar with three palettes (Mint default, Sage, Warm)
persisted in `localStorage["dadaia-panel-theme"]`, pre-paint script applied to avoid
FOUC, and a WCAG double-outline `focus-visible` rule scoped to Warm. The legacy
single-file `_assets.py` is split into `features/panel/views/assets/{css,js}/` modules
served via `/static/<name>` with a locked Content-Type table. The dead
`features/telemetry/reader/workflows.py` is deleted; SQLite `workflows` and
`workflow_agents` tables stay (deferred) but receive literal `# DEAD:` markers in
`schema.py`. New endpoints carry **regex + `Path.resolve().is_relative_to(base)`
defence-in-depth** against path traversal.

The acceptance suite is closed: **480 unit tests + 45 integration tests + 56 Playwright
E2E tests + 21 visual screenshots + 6 axe-core PASS audits** (3 themes × 2 tabs), with
zero serious/critical accessibility violations. Five mid-release regressions were
caught and patched **before** PR3-21 closed, all attributable to earlier R3 PRs (CSP,
IIFE scope, factory cleanup, hash-activation guard, WCAG contrast). The release ships
the post-R3 control surface as `dadaia-workspace-panel-r3-v1`.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| PR3-00 | Close prerequisite releases (v0.1.1 + agent-monitoring-v1) | `96733ff` |
| PR3-01 | Asset split: `views/assets/` + thin `_assets.py` shim | `a34fe27` |
| PR3-02 | `/static/<name>` route + Content-Type table + traversal guard | `91df088` |
| PR3-03 | 3 theme palettes (Mint/Sage/Warm) + Warm focus fix | `1e426a2` |
| PR3-04 | Theme switcher button + dropdown + persistence + pre-paint script | `7ec814b` |
| PR3-05 | `wrapper.py` consumes `var(--color-*)` tokens via `/static/tokens.css` | `1aaaf6f` |
| PR3-06 | Rename Memories → Spec Context Projects + tab reorder + responsive label | `68c2911` |
| PR3-07 | Canonical agent reader (`features/agents/` + `MarkdownAgentStore`) | `0175294` |
| PR3-08 | `/api/agents` canonical overlay + telemetry sub-object + `active_window_days` query | `343ec9e` |
| PR3-09 | `GET /api/agents/<id>/prompt` + regex + defence-in-depth path check | `bec030c` |
| PR3-10 | Agent card UI (collapsed) — FE | `f04ece0` |
| PR3-11 | Agent card UI (expanded + lazy prompt fetch + multi-open accordion) — FE | `c6a0cea` |
| PR3-12a | Pre-implementation gap check on `MarkdownWorkflowStore` (no gaps — folded into PR3-12) | `5725cf4` |
| PR3-12 | `WorkflowsService` wrapping `MarkdownWorkflowStore` + mtime cache | `5725cf4` |
| PR3-13 | DAG layout + server-side SVG renderer (`features/workflows/dag.py`) | `6ae1a71` |
| PR3-14 | `/api/workflows` LIST endpoint (lean — summaries only) | `fb4abe1` |
| PR3-15 | `GET /api/workflows/<name>` DETAIL endpoint (folded into PR3-14 commit) | `fb4abe1` |
| PR3-16 | Workflow card grid UI + `workflows.js` IIFE — FE | `5cc0e2e` |
| PR3-17 | Workflow detail view + hash routing + DAG skeleton — FE | `626be00` |
| PR3-18 | Drop dead workflow reader + dead field + `# DEAD:` markers in schema.py | `404c7fb` |
| PR3-19 | SE unit test suite (~62 new tests) | `8e1ebb7` |
| PR3-20 | SE integration test suite (45 new tests) | `5d4d15e` |
| PR3-21 | QA Playwright E2E suite (56 tests) | `e34be15` + `a0109c4` |
| PR3-22 | Visual evidence (21 screenshots) + axe-core ×3 themes | `c171c8d` |

Mid-release hotfixes (regressions from earlier PRs, landed before PR3-21 closed):

| SHA | Slug | Root-cause PR |
|-----|------|---------------|
| `35e96ce` | CSP: allow `style-src 'self'` for external stylesheets | PR3-01 regression |
| `296ffcc` | Expose `authedFetch` on `window` so IIFE modules can reach it | PR3-10 / PR3-16 regression |
| `a802e44` | Drop `workflows_reader` from `TelemetryService` factory | PR3-18 cleanup gap |
| `f074a0a` | `workflows.js` falls back to `load()` when no `#workflows` hash | PR3-17 regression |
| `b859d3f` | WCAG AA contrast on workflow-name button + skill-chip text | PR3-03 / PR3-16 regression |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Surface A — Tab rename + reorder + reflow (A1–A7) | `npx playwright test e2e/tab-rename.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z/screenshots/tab-bar-initial.png` |
| Surface B — Spec Context Projects smoke + `#memories` back-compat (B1, B2) | `npx playwright test e2e/spec-context.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z/screenshots/spec-context-tab.png` |
| Surface C — Agents tab (C1–C12, includes `active_window_days` and lazy prompt fetch) | `npx playwright test e2e/agents.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z/screenshots/{agent-card-collapsed-frontend-engineer,agent-card-expanded-frontend-engineer,agents-two-expanded,agent-card-inactive-zero-telemetry,agents-grid-zero-telemetry}.png` |
| Surface D — Workflows tab + DAG (D1–D14, includes hash routing + DAG accessibility) | `npx playwright test e2e/workflows.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z/screenshots/{workflows-grid,workflow-card-tdd-cycle,workflow-card-cross-cutting-feature,workflow-dag-tdd-cycle,workflow-dag-cross-cutting-feature,workflow-dag-spec-refinement,workflow-detail-tdd-cycle-full,workflows-grid-after-back}.png` |
| Surface E — Theme switcher (E1–E9, includes Warm focus rule + 3-theme axe-core PASS) | `npx playwright test e2e/theme.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z/screenshots/{topbar-with-theme-switcher,theme-switcher-dropdown-open,theme-mint-applied,theme-sage-applied,theme-warm-applied}.png` |
| Surface F — Servers tab smoke + no `unregistered` field (F1) | `npx playwright test e2e/servers.spec.ts` | commit `404c7fb` (`feat(panel): drop dead workflow reader + add DEAD markers (PR3-18)`) |
| Surface G — API security (G1–G12, includes 401, path traversal on both new endpoints) | `npx playwright test e2e/api-security.spec.ts` | commits `bec030c` + `fb4abe1` (new endpoints with defence-in-depth) |
| Surface H — 21 visual screenshots + 6/6 axe-core PASS (3 themes × 2 tabs) | `npx playwright test e2e/visual.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z-pr3-22-evidence.html` + `2026-05-18T160000Z-pr3-22-evidence.handoff.json` |
| 480 unit tests green | `pytest tests/unit -q` | `8e1ebb7` (PR3-19 SE unit suite landing commit) |
| 45 integration tests green | `pytest tests/integration -q` | `5d4d15e` (PR3-20 SE integration suite landing commit) |
| 56 Playwright E2E tests green | `npx playwright test --reporter=line` | `e34be15` + `a0109c4` (PR3-21 final landing commits) |
| 6/6 axe-core audits PASS (Mint/Sage/Warm × Agents/Workflows) | `npx playwright test e2e/axe.spec.ts` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T160000Z-pr3-22-evidence.html` |
| Operator smoke (DoD #8) — open panel, switch themes, expand 2 agents, open cross-cutting-feature DAG | manual | operator confirmation on PR3-22 review |
| `dadaia specs doctor` `[ok]` (DoD #3) | `.dadaia/.venv/bin/dadaia specs doctor` | run inline during CLOSURE (PR3-23) — see commit `chore(release): CLOSURE panel-r3-v1 + archive + memory atoms (PR3-23)` |
| `dadaia public doctor` `[ok]` (DoD #4) | `.dadaia/.venv/bin/dadaia public doctor` | run inline during CLOSURE (PR3-23) |

## Drifts

### csp-style-src-regression

**Description:** PR3-01 asset split moved `tokens.css` and `structure.css` out of inline
`<style>` blocks and into `/static/*.css` routes. The pre-existing CSP header `style-src
'unsafe-inline'` lacked `'self'`, so the new external stylesheet links were blocked by
the browser. Manifested as unstyled tabs on first manual smoke.

**Resolution:** `35e96ce fix(panel): allow style-src 'self' in CSP to load external
stylesheets (PR3-01 regression)` — added `'self'` to `style-src` while keeping
`'unsafe-inline'` for token bootstrap. Note: the planned post-R3 hotfix is dropping
`'unsafe-inline'` from `script-src` entirely (filed in `candidates.md` per SPEC §8.2 as
"first hotfix release after R3, named target P2"); the `style-src 'self'` addition here
is an in-release CSP relaxation, not the script-src hardening.

**Memory updates:** none — CSP composition is implementation detail, not in
`memory/architecture.html`.

### authedfetch-iife-scope

**Description:** PR3-10 (agents.js) and PR3-16 (workflows.js) extracted their logic into
IIFE modules. The shared helper `authedFetch` was defined in the page's main
script but **not exposed on `window`**, so the IIFEs couldn't reference it — manifested
as `ReferenceError: authedFetch is not defined` on tab activation.

**Resolution:** `296ffcc fix(panel): expose authedFetch on window so agents.js/workflows.js
IIFEs can call it (PR3-10/PR3-16 regression)` — assigned `window.authedFetch =
authedFetch` after the helper's definition in the main script.

**Memory updates:** none — internal JS module wiring, not load-bearing for memory.

### telemetryservice-factory-cleanup

**Description:** PR3-18 deleted `features/telemetry/reader/workflows.py` but the
`TelemetryService.from_workspace_paths()` factory still passed `workflows_reader=...`
into the constructor, breaking service boot at `dadaia panel` start-up with
`TypeError: __init__() got an unexpected keyword argument`.

**Resolution:** `a802e44 fix(panel): drop workflows_reader from TelemetryService factory
(PR3-18 cleanup gap)` — removed the kwarg from the factory and updated unit tests.

**Memory updates:** none — already captured by "Remove any prior reference to
telemetry-fed workflow tables" in `architecture.html`, applied in this CLOSURE.

### workflows-hash-activation-guard

**Description:** PR3-17 added hash routing for the workflow detail view
(`#workflows?detail=<name>`). On a clean tab switch (no hash present yet), the IIFE
short-circuited on hash absence and never called `load()`, leaving the grid blank.

**Resolution:** `f074a0a fix(panel): workflows.js falls back to load() when no #workflows
hash (PR3-17 regression)` — `handleHashOnActivation` falls through to `load()` when
neither `detail=` nor a bare `#workflows` is present.

**Memory updates:** none — hash grammar in `memory/product/panel.html` updated by this
CLOSURE (catalog entry now mentions hash routing); the bug is internal to JS.

### wcag-contrast-workflow-button-skill-chip

**Description:** The Mint palette tokens chosen in PR3-03 produced
**4.31:1 contrast on the workflow-name button** (the clickable card title) and
**3.94:1 on skill-chip text** — both fail WCAG AA 4.5:1 for normal text. Caught by
axe-core in PR3-22 evidence run.

**Resolution:** `b859d3f fix(panel): WCAG AA contrast on workflow-name button +
skill-chip text` — darkened the two affected tokens (`--color-link-strong`,
`--color-chip-text`) while staying within the Mint palette's hue band. axe-core re-run
showed 0 violations across all 3 themes.

**Memory updates:** none — palette tokens are an implementation detail; the WCAG
guarantee is stated in `memory/product/panel.html` (axe-clean across 3 themes) via this
CLOSURE.

## Memory updates

- `specs/memory/product/index.html` — catalog entry for "panel" updated: new description
  reflects the 4-tab control surface (Spec Context Projects / Agents / Workflows /
  Servers), theme switcher with 3 palettes, server-side DAG SVG, and axe-clean across 3
  themes. Tab order in the catalog text is corrected to the post-R3 order. Last-update
  date bumped to 2026-05-18; closure reference set to
  `dadaia-workspace-panel-r3-v1`.
- `specs/memory/product/panel.html` — rewrite of Propósito (control surface framing, 4
  tabs, 10 canonical agents, 12 canonical workflows, theme switcher, hash grammar),
  Fluxo de uso (tab boot order with Spec Context Projects as default + theme persistence
  pre-paint + hash routing for workflow detail + lazy prompt/DAG fetch), Trigger típico
  (operator wants control-surface visibility), Diferencial (canonical sources + axe-clean
  3-theme palette + server-side DAG vs Mermaid), Estado runtime tocado (new endpoints
  `/api/agents/<id>/prompt`, `/api/workflows/<name>`, `/static/<name>` content-type
  table, asset modules path), Dependências (agent-monitoring continues; brand-identity
  tokens + 3-palette extension; no new runtime deps; pyyaml already declared).
- `specs/memory/architecture.html` — note new modules `features/agents/`
  (`MarkdownAgentStore`), `features/workflows/` (`WorkflowsService` wrapping
  `MarkdownWorkflowStore` + `dag.py` SVG renderer), and the new
  `features/panel/views/assets/{css,js}/` split + `features/panel/views/static.py` route.
  Remove the prior reference to telemetry-fed workflow tables (SQLite
  `workflows`/`workflow_agents` are marked `# DEAD:` and stay until the deferred
  cleanup release).
- `specs/memory/tech-stack.html` — **no change: pyyaml already declared** (already at
  `^6.0` for `infrastructure/ + features/`, sufficient for canonical agent/workflow
  reading); no other tech-stack additions in R3.

## Backlog returns

Files added to `specs/backlog/candidates.md` (formal candidates with named owner +
context, per SPEC §8.2):

- `backlog/candidates.md` ← Drop SQLite `workflows` / `workflow_agents` tables (migration 6) — future cleanup release
- `backlog/candidates.md` ← "Run this workflow" invocation (Claude Code dispatcher integration) — future release
- `backlog/candidates.md` ← Dark mode (light-mode-only palette permutations in R3) — future release
- `backlog/candidates.md` ← **Drop `'unsafe-inline'` from script CSP** — explicit target: first hotfix release after R3 (P2, named target)

Files added to `specs/backlog/ideas.md`: **none in this CLOSURE** — per operator policy
(working memory file, do not touch). The remaining 5 DEFERRED items per SPEC §8.2
(4th theme variant "brown-forward"; render `input_contract` in expanded agent card;
manifest-drift banner; ETag header on detail endpoints; run-aware DAG state) are
recorded here in CLOSURE for traceability but NOT filed in `ideas.md` to avoid
clobbering operator notes. They remain available for the operator to file directly when
prioritising next post-R3 work; the SPEC §8.2 table is the durable record.

## Archive decision

**MOVE** — release directory moved to
`specs/_archive/releases/dadaia-workspace-panel-r3-v1/` via `git mv`. ACTIVE.md
repointed to `release: none / phase: none`.
