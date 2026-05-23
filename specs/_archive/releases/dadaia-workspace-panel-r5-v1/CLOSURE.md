# Closure: Release — dadaia-workspace-panel-r5-v1

> **Status:** Aprovado
> **Release ID:** dadaia-workspace-panel-r5-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-21

## Summary

Major panel overhaul across all seven tabs. The release delivered 8 phases of work in a
single-day blitz: architecture cleanup (Phase A), visual identity + CSS tokens + logo redesign
(Phase B), Projects tab redesign with 4-zone card anatomy and local/remote terminology (Phase C),
Agents tab with native dialog modal and per-tab runtime toggle (Phase D), Workflows tab with
in-panel DAG zoom controls (Phase E), Academy tab infrastructure wired to AcademyService (Phase F),
Reports tab with sidecar-indexed report viewer + inline delete (Phase G), and canonical 7-tab nav
overhaul (Phase H). All 38 tasks (T-P5-01 through T-P5-38) completed and verified with 630 tests
passing (614 pre-existing + 16 new).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-P5-01 | Remove PANEL_CSS, PANEL_JS, PALETTE from _assets.py | — |
| T-P5-02 | Move SVG reads to static.py; remove _assets.py import from index.py | — |
| T-P5-03 | Harden _try_build_telemetry() with per-type exception handlers | — |
| T-P5-04 | Wire AcademyService into PanelService DI | — |
| T-P5-05 | Add route-category comment block in handler.py | — |
| T-P5-06 | Fix _resolve_workspace() walk-up from cwd | — |
| T-P5-07 | Introduce window.Panel registry in core.js; promote window.escHtml | — |
| T-P5-08 | Add TODO comments on local escHtml copies in agents.js, workflows.js, sessions.js | — |
| T-P5-09 | Add SSR-vs-client-side policy docstring to views/index.py | — |
| T-P5-10 | Add all new CSS custom properties to tokens.py; update --nav-h to 48px | — |
| T-P5-11 | Update .nav-tab padding in structure.py; remove tab-memories-btn::after rule | — |
| T-P5-12 | Create logo-rhino-36.svg (stroke-based, viewBox 0 0 48 48, no hardcoded hex) | — |
| T-P5-13 | Update logo-rhino-24.svg to match new stroke-based design | — |
| T-P5-14 | Rename API status labels active→local, inactive→remote in contexts endpoint | — |
| T-P5-15 | Update Projects tab section header (heading, count badge, description block) | — |
| T-P5-16 | Redesign Projects card HTML + CSS (4-zone anatomy, mint left accent, no PRIMARY badge) | — |
| T-P5-17 | Add session binding zone (Zone C) to Projects card | — |
| T-P5-18 | Add native dialog modal + focus trap + ARIA to Agents tab | — |
| T-P5-19 | Add modal CSS (animation, prefers-reduced-motion, 44px close button) | — |
| T-P5-20 | Redesign collapsed agent card anatomy (Zones A–D; remove expand chevron) | — |
| T-P5-21 | Add runtime toggle to Agents tab section header | — |
| T-P5-22 | Add DAG zoom controls to workflows.js (toolbar, applyZoom, keyboard bindings) | — |
| T-P5-23 | Add DAG zoom CSS to workflows.py (.workflow-dag-viewport, .dag-toolbar) | — |
| T-P5-24 | Add runtime toggle to Workflows tab section header | — |
| T-P5-25 | Add GET /api/academy route (bearer-only) + render_api_academy() | — |
| T-P5-26 | Create views/academy.py HTML scaffold | — |
| T-P5-27 | Create academy.js (module cards, detail view, back nav, window.Panel.register) | — |
| T-P5-28 | Create academy.py CSS module; wire into index.py | — |
| T-P5-29 | Add GET /api/reports route + render_api_reports() (sidecar traversal) | — |
| T-P5-30 | Add GET /reports/<path> with path-traversal guard | — |
| T-P5-31 | Add DELETE /api/reports/<path> + delete_report_file() + do_DELETE handler | — |
| T-P5-32 | Create views/reports.py HTML scaffold | — |
| T-P5-33 | Create reports.js (grouped list, inline delete confirm, content view, window.Panel.register) | — |
| T-P5-34 | Create reports.py CSS module; wire into index.py | — |
| T-P5-35 | Reorder nav tabs to canonical 7-tab sequence; add Reports and Academy nav buttons | — |
| T-P5-36 | Remove global runtime switcher from topbar; upgrade logo to 36px | — |
| T-P5-37 | Add Sessions runtime toggle; wire window.Panel.activate for all 7 tabs | — |
| T-P5-38 | Redesign Sessions error state (role=alert, Retry button, scroll-margin-top) | — |

*Note: individual commit SHAs were not captured per-task in the session log. All tasks are [x] in TASKS.md.*

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite passes (630 tests) | `cd repos/dadaia-workspace && poetry run pytest` | 630 passed (614 pre-existing + 16 new) |
| Dead code removed from _assets.py | `python -c "from dadaia_workspace.features.panel.views._assets import PANEL_CSS"` | raises ImportError |
| window.Panel registry present | grep in core.js for `window.Panel` | `window.Panel = { register, activate }` defined |
| GET /api/academy returns 200 | `curl -H "Authorization: Bearer <token>" http://127.0.0.1:4999/api/academy` | 200 with `[]` when no courses exist |
| GET /api/reports returns 200 | `curl -H "Authorization: Bearer <token>" http://127.0.0.1:4999/api/reports` | 200 with sorted sidecar list |
| do_DELETE handler present | `grep -n "do_DELETE" dadaia_workspace/features/panel/handler.py` | handler method exists |
| Path traversal guard for reports | test_handler_delete.py (5 tests) | all 5 pass |
| Reports scaffold test | test_views_reports.py (11 tests) | all 11 pass |
| logo-rhino-36.svg no hardcoded hex | `grep -i "#" dadaia_workspace/features/panel/views/assets/logo-rhino-36.svg` | no matches |
| mypy + ruff clean on changed files | `poetry run mypy dadaia_workspace/features/panel/ --strict && poetry run ruff check` | no errors |

## Drifts

### T-P5-38-out-of-phase

**Description:** T-P5-38 (Sessions error state redesign) was filed under Phase E in TASKS.md
rather than under Phase C or a standalone phase, since it touched different files than the other
E tasks (workflows.js / workflows.py). Tracking ID was added late during the TASKS authoring
session.

**Resolution:** Task was grouped into Phase E in TASKS.md for tracking convenience. The
implementation was independent and correct — sessions.js and sessions.py CSS were touched as
declared. No merge conflict with other Phase E tasks. The dependency note "T-P5-03 done
(telemetry fix)" was respected.

**Memory updates:** No memory update required — this was a tracking/grouping drift, not a
functional drift.

### container-wiring-route-categories

**Description:** The PLAN listed `container.py` as the authoritative location for
`build_panel_views()` wiring of the new reports routes. During implementation, `handler.py`
route registration also received the new routes (api_reports, reports_serve, api_report_delete)
directly. Both `container.py` and `handler.py` were updated per the route-category pattern.

**Resolution:** Both files were updated consistently. The PLAN's description was accurate at the
level of "wired in container.py via build_panel_views()" — the actual wiring also required
handler.py route registration, which was implicit in the PLAN's Phase G route listing.

**Memory updates:** `specs/memory/architecture.html` — panel HTTP server + route architecture
section updated to reflect do_DELETE addition and three new routes.

## Memory updates

- `specs/memory/product/panel.html` — Major update: 7-tab canonical state, window.Panel registry,
  runtime toggle per-tab, Projects card 4-zone anatomy + local/remote terminology, Agents modal,
  Workflows DAG zoom, Sessions error state, Reports tab (sidecar-indexed, DELETE with guard),
  Academy tab (AcademyService DI), logo 36px stroke-based, CSS token additions (all new tokens
  listed), HTTP route table extended with /api/academy, /api/reports, /reports/<path>,
  DELETE /api/reports/<path>, _assets.py dead code removed, do_DELETE handler.
- `specs/memory/product/academy.html` — Updated to reflect Academy integration as panel tab:
  AcademyService wired via DI in PanelService; GET /api/academy is the canonical API endpoint
  (bearer-only); academy.js registers via window.Panel.register('academy', Academy); primary
  access is now via the panel at /academy tab, not a standalone route.
- `specs/memory/architecture.html` — Panel HTTP server section updated: route categories
  (public / bearer-only / telemetry) documented in handler.py; do_DELETE handler added;
  static asset registry in static.py (SVG reads moved from _assets.py); view composition in
  container.py via build_panel_views(); window.Panel registry pattern (core.js) for lazy tab
  module loading.
- `specs/memory/tech-stack.html` — No change: release did not add new runtime dependencies.
- `specs/memory/product/index.html` — No change: panel and academy catalog entries and their
  order did not change in this release.

## Backlog returns

- `backlog/candidates.md` ← Drop `'unsafe-inline'` from CSP script-src (carry-over from R3;
  still pending post-R5)
- `backlog/candidates.md` ← Drop SQLite workflows / workflow_agents tables (migration 6;
  carry-over, marked DEAD in schema.py)
- `backlog/candidates.md` ← "Run this workflow" invocation dispatcher from panel
- `backlog/candidates.md` ← Academy content modules (01–06) knowledge basis — explicitly
  out-of-scope in R5, deferred to next release
- `backlog/candidates.md` ← Reports tab for HTML files without .handoff.json sidecar
  (accepted known limitation in R5; pagination also deferred when count > 500)
- `backlog/candidates.md` ← Dual route dispatch consolidation in handler.py (deferred to
  handler overhaul release)
- `backlog/candidates.md` ← E2E tests for new tabs (Reports, Academy) — deferred to qa-engineer
- `backlog/ideas.md` ← Index on sessions.provider for list_sessions() performance at 10k+ rows
- `backlog/ideas.md` ← Synthetic Codex cost estimation (compute_cost_codex in pricing.py)

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/dadaia-workspace-panel-r5-v1/`
via `git mv`. ACTIVE.md will be updated to `release: none` after memory updates are confirmed.

Command for devops-engineer or operator:
```
git mv repos/dadaia-workspace/specs/releases/dadaia-workspace-panel-r5-v1 repos/dadaia-workspace/specs/_archive/releases/dadaia-workspace-panel-r5-v1
```
