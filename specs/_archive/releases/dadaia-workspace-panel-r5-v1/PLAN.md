# Plan: Release — dadaia-workspace-panel-r5-v1

> **Status:** Aprovado
> **Phase:** PLAN
> **Owner:** product-engineer
> **Release ID:** dadaia-workspace-panel-r5-v1
> **Created:** 2026-05-21

---

## OQ Decisions (resolved 2026-05-21, all defaults confirmed)

| OQ | Question | Decision |
|----|----------|----------|
| OQ-1 | Theme dropdown location after topbar cleanup | **Theme stays in topbar.** Only the global runtime toggle is removed from the topbar. |
| OQ-2 | Reports delete confirmation pattern | **Inline row confirmation.** "Are you sure? [Delete] [Cancel]" appears inline in the row — no modal, no toast. |
| OQ-3 | Academy HTML content security model | **`<div>` + server-side script stripping.** Academy HTML is injected into a scoped `<div>`; the backend strips `<script>` tags before serving. |
| OQ-4 | DAG Fit button scale behaviour | **Reset to `scale(1.0)` and center.** Fit does not compute a content-aware scale. |
| OQ-5 | Reports tab coverage of orphan HTML files (no sidecar) | **Sidecar-indexed only.** Reports without a `.handoff.json` sidecar are not shown. Accepted known limitation. |

---

## Strategy

The overhaul is split into 8 sequential-with-parallelism phases. Phases A and B
establish structural preconditions (dead code removal, token foundation, logo).
Phases C–H build on that stable base. Phases C and D (Projects and Agents tab)
share no file overlap and can run in parallel after Phase B. Phase H (tab nav
overhaul) must run last as it wires all new tabs into the nav bar.

All Python (backend) work is owned by `software-engineer-python`. All HTML/CSS/JS
(frontend) work is owned by `frontend-engineer`. Each phase lists the specific
files affected and the parallel-safety verdict relative to other phases.

---

## Execution Order

```
Phase A  →  Phase B  →  Phase C ┐
                         Phase D ├─ (parallel) → Phase E  →  Phase F  →  Phase G  →  Phase H
                         Phase E ┘
```

- A must complete before B (tokens must exist before CSS uses them)
- B must complete before C, D, E, F, G (logo + token definitions must be in place)
- C and D are parallel-safe (disjoint file sets)
- E (Workflows) is parallel-safe with C and D
- F (Academy) depends on A (DI wiring); parallel-safe with C, D once A is done
- G (Reports) depends on A; parallel-safe with C, D once A is done
- H (Tab nav) must be last — it wires all new tabs and removes global toggles

---

## Phase A — Architecture Cleanup

**Objective:** Remove dead code, introduce JS module registry, harden telemetry
wiring, add route-category documentation.

**Owner:** software-engineer-python (items A1–A3, A5); frontend-engineer (item A4)

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/_assets.py` | Delete `PANEL_CSS`, `PANEL_JS`, `PALETTE`; retain `LOGO_RHINO_24` path only until logo migration completes |
| `dadaia_workspace/features/panel/views/static.py` | Move SVG reads (`LOGO_RHINO_24`, `LOGO_RHINO_16`) here; remove dependency on `_assets.py` |
| `dadaia_workspace/features/panel/views/index.py` | Remove `_assets.py` import; read logo from `static.py`; add SSR-vs-client-side policy docstring |
| `dadaia_workspace/features/panel/panel.py` | Harden `_try_build_telemetry()`: replace bare `except Exception` with per-type handlers (`PermissionError`, `OSError`, `sqlite3.OperationalError`) each emitting a warning log; wire `AcademyService` via DI |
| `dadaia_workspace/features/panel/handler.py` | Add route-category comment block enumerating public / bearer-only / bearer+telemetry categories |
| `dadaia_workspace/features/panel/views/assets/js/core.js` | Introduce `window.Panel = { register, activate }` registry; promote `window.escHtml`; migrate existing `window.Agents` / `window.Workflows` to register via `window.Panel` |
| `dadaia_workspace/features/panel/views/assets/js/agents.js` | Add TODO comment on local `escHtml` copy |
| `dadaia_workspace/features/panel/views/assets/js/workflows.js` | Add TODO comment on local `escHtml` copy |
| `dadaia_workspace/features/panel/views/assets/js/sessions.js` | Add TODO comment on local `escHtml` copy |
| `dadaia_workspace/features/panel/_resolve_workspace.py` (or equivalent) | Fix `_resolve_workspace()` to walk up from cwd to find workspace root (`panel-workspace-resolver-fix`) |

**Parallel-safe with:** nothing — must run first.
**Hard deps:** none.

---

## Phase B — Visual Identity + Token Additions + Logo

**Objective:** Add all new CSS custom properties from design spec §1.2–§1.10;
update `--nav-h`; produce new rhino SVG at 36×36px.

**Owner:** frontend-engineer

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/assets/css/tokens.py` | Add all new `[NEW]` tokens: `--color-session-bg`, `--color-modal-overlay`, `--color-modal-border`, `--color-delete-icon`, `--color-delete-icon-hover`, `--color-academy-chip-bg`, `--color-report-tag-bg`, `--color-error-bg`, `--color-error-border`, `--color-chip-memory-bg`, `--color-chip-memory-border`, `--radius-modal`, `--radius-pill`, `--shadow-card`, `--shadow-modal`, `--shadow-none`, `--z-modal-overlay`, `--z-modal`, `--z-toast`, `--duration-fast`, `--duration-normal`, `--duration-slow`, `--easing-standard`, `--easing-decelerate`, `--easing-accelerate`, `--space-2xs`, `--space-3xl`, `--modal-max-w`, `--modal-max-h`; update `--nav-h: 44px` → `--nav-h: 48px` |
| `dadaia_workspace/features/panel/views/assets/css/structure.py` | Update `.nav-tab` padding from `0.65rem 1.1rem` to `0.75rem 1.1rem`; remove `.tab-memories-btn::after` responsive abbreviation |
| `dadaia_workspace/features/panel/views/assets/logo-rhino-36.svg` | New file: stroke-based rhino, viewBox `0 0 48 48`, rendered at 36×36px; per design spec §11 SVG spec |
| `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg` | Update to match new design (same anatomy, same paths scaled to 24px viewBox) |

**Parallel-safe with:** nothing after A — must run after A.
**Hard deps:** Phase A complete.

---

## Phase C — Projects Tab Redesign

**Objective:** Redesign Projects tab cards; fix section heading; add session
binding indicator; update terminology.

**Owner:** frontend-engineer (CSS/HTML/JS); software-engineer-python (API changes
if `local`/`remote` status needs backend support)

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/assets/css/projects.py` (or equivalent) | New CSS for 4-zone card anatomy, memory pill chips, session binding zone, `.card-local` / `.card-remote` classes |
| `dadaia_workspace/features/panel/views/index.py` | Update context card HTML template: remove PRIMARY badge, separate repo/branch rows, add session zone, add memory chip footer, update section heading |
| `dadaia_workspace/features/panel/views/api.py` or context view | Rename `active`/`inactive` status labels to `local`/`remote` in the API response for `GET /api/contexts` |

**Parallel-safe with:** Phase D, Phase E.
**Hard deps:** Phase B complete.

---

## Phase D — Agents Tab Redesign

**Objective:** Replace inline expand with modal; redesign collapsed card anatomy;
move runtime toggle into tab.

**Owner:** frontend-engineer

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/agents.py` | Add `<dialog id="agent-modal">` scaffold to HTML; remove `.agent-card__detail` region from collapsed card |
| `dadaia_workspace/features/panel/views/assets/css/agents.py` | Add modal CSS (`.agent-modal`, `.agent-modal::backdrop`, overlay, animation, focus ring); update card anatomy CSS (Zones A–D); remove expand chevron styles |
| `dadaia_workspace/features/panel/views/assets/js/agents.js` | Replace inline expand with `showModal()` / `close()` on `<dialog>`; add focus trap (Escape key handler, return-focus tracking); implement `window.Panel.register('agents', ...)` |

**Parallel-safe with:** Phase C, Phase E.
**Hard deps:** Phase B complete.

---

## Phase E — Workflows Tab DAG Zoom

**Objective:** Add in-panel zoom controls to DAG viewer; move runtime toggle into
tab.

**Owner:** frontend-engineer

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/assets/css/workflows.py` | Add `.workflow-dag-viewport` container CSS; add `.dag-toolbar` styles |
| `dadaia_workspace/features/panel/views/assets/js/workflows.js` | Wrap injected SVG in `.workflow-dag-viewport`; add zoom toolbar HTML; implement `applyZoom(level)` function; add keyboard bindings |

**Parallel-safe with:** Phase C, Phase D.
**Hard deps:** Phase B complete.

**Technical note:** verify that SVGs generated by the workflow diagram generator
include a `viewBox` attribute. If absent, the CSS `transform: scale()` approach will
distort proportions. If SVGs lack `viewBox`, the server-side generator must be
patched to add it (add a sub-task in T-P5 if discovered during implementation).

---

## Phase F — Academy Tab (Infrastructure Only)

**Objective:** Wire `AcademyService` into panel; add `GET /api/academy` endpoint;
build Academy tab scaffold and JS module.

**Owner:** software-engineer-python (API + DI); frontend-engineer (HTML/CSS/JS)

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/panel.py` | Accept `AcademyService` in DI (already started in Phase A); pass to views |
| `dadaia_workspace/features/panel/handler.py` | Add `GET /api/academy` route to `_RAW_ROUTES` as bearer-only; add route to `_BEARER_ONLY_ROUTES` |
| `dadaia_workspace/features/panel/views/api.py` | Add `render_api_academy()` function calling `service.academy.list_all()` + JSON serialization |
| `dadaia_workspace/features/panel/views/academy.py` | New file: HTML scaffold for Academy tab (module list + content view) |
| `dadaia_workspace/features/panel/views/assets/css/academy.py` | New file: CSS for module card grid, type chips, content frame |
| `dadaia_workspace/features/panel/views/assets/js/academy.js` | New file: fetches `GET /api/academy`; renders module cards; handles click → content view; `window.Panel.register('academy', ...)` |
| `dadaia_workspace/features/panel/views/index.py` | Add `<link>` for academy CSS and `<script>` for academy JS |

**Parallel-safe with:** Phase C, Phase D (after Phase A DI wiring complete).
**Hard deps:** Phase A (DI wiring) and Phase B complete.

---

## Phase G — Reports Tab

**Objective:** Add `GET /api/reports` and `/reports/<path>` endpoints; build
Reports tab scaffold and JS module.

**Owner:** software-engineer-python (API + path guard); frontend-engineer (HTML/CSS/JS)

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/handler.py` | Add `GET /api/reports` as bearer-only route; add `GET /reports/<path>` with path-traversal guard; add `DELETE /api/reports/<path>` |
| `dadaia_workspace/features/panel/views/api.py` | Add `render_api_reports()`: traverse `.dadaia/reports/`, find `.handoff.json` sidecars, parse, return sorted list; add `render_report_file()`: resolve path, traversal guard (`os.path.realpath`), serve HTML with `Content-Type: text/html`; add `delete_report_file()` |
| `dadaia_workspace/features/panel/views/reports.py` | New file: HTML scaffold for Reports tab (list + content view) |
| `dadaia_workspace/features/panel/views/assets/css/reports.py` | New file: CSS for report list rows, group labels, agent tag chips, delete button, content frame |
| `dadaia_workspace/features/panel/views/assets/js/reports.js` | New file: fetches `GET /api/reports`; renders grouped list; handles title click → content view; handles trash → inline confirm → `DELETE`; `window.Panel.register('reports', ...)` |
| `dadaia_workspace/features/panel/views/index.py` | Add `<link>` for reports CSS and `<script>` for reports JS |

**Parallel-safe with:** Phase C, Phase D (after Phase A complete).
**Hard deps:** Phase A and Phase B complete.

---

## Phase H — Tab Nav Overhaul

**Objective:** Reorder tabs to canonical sequence; add "Reports" and "Academy" tabs
to nav; remove global runtime toggle from topbar; wire all new tab activations in
`core.js`.

**Owner:** frontend-engineer

**Files touched:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/views/index.py` | Reorder `<button class="nav-tab">` elements to `Projects | Agents | Workflows | Sessions | Reports | Academy | Servers`; remove global runtime switcher HTML from topbar; update logo element to 36px |
| `dadaia_workspace/features/panel/views/assets/css/structure.py` | Update `.topbar` CSS to remove primary badge and runtime switcher areas; update `.topbar-logo svg` size |
| `dadaia_workspace/features/panel/views/assets/js/core.js` | Add tab activation cases for `reports` and `academy` (using `window.Panel.activate`); remove direct `window.Agents.load()` / `window.Workflows.load()` calls in favour of `window.Panel.activate` |

**Parallel-safe with:** nothing — must be last phase.
**Hard deps:** Phases A–G all complete.

---

## Technical Risks

| Risk | Mitigation |
|---|---|
| SVG `viewBox` absent from workflow diagrams | Verify in Phase E; add sub-task for server-side fix if needed |
| `<dialog>` native browser support gap | Use native `<dialog>` with polyfill for focus trap; `inert` attribute fallback for very old browsers |
| `AcademyService` DI wiring breaks existing panel boot | Unit-test the boot path after Phase A; keep `academy` as optional in `PanelService.__init__` with `academy=None` default |
| Path traversal in Reports `DELETE` endpoint | Use `os.path.realpath()` to resolve symlinks before prefix check; return 403 if resolved path escapes boundary |
| Token additions in `tokens.py` conflict with brand-identity-v1 tokens | Review brand-identity-v1 SPEC token table before writing; only add tokens marked `[NEW]` in design spec |

---

## Validation Plan

After all phases complete:

1. **Smoke test:** `python -m dadaia_workspace.features.panel.panel` starts without error; panel loads at `127.0.0.1:4999`.
2. **Tab navigation:** all 7 tabs appear in canonical order; each tab loads its content.
3. **Sessions:** `GET /api/sessions` returns data (not 503) on a clean workspace.
4. **Academy:** `GET /api/academy` returns `[]` (empty knowledge basis); tab shows empty state.
5. **Reports:** `GET /api/reports` returns list of reports indexed by sidecars; list loads grouped by context.
6. **Agent modal:** clicking any agent card opens modal; Escape closes; focus returns to card.
7. **DAG zoom:** clicking `+` scales the workflow SVG; `[Fit]` resets.
8. **Logo:** topbar shows 36px rhino; no hardcoded hex in SVG source.
9. **Dead code gone:** `python -c "from dadaia_workspace.features.panel.views._assets import PANEL_CSS"` raises `ImportError`.
10. **`dadaia doctor`** passes (no ruff/mypy errors from changes).
