# Tasks: Release — dadaia-workspace-panel-r5-v1

> **Status:** Aprovado
> **Phase:** TASKS
> **Owner:** product-engineer
> **Release ID:** dadaia-workspace-panel-r5-v1
> **Created:** 2026-05-21

---

## Parallel-safe declarations

The following task groups may run in parallel **after their declared hard deps are
complete**. Each group has disjoint write sets.

- **Group C** (T-P5-11 to T-P5-14) and **Group D** (T-P5-15 to T-P5-18) are
  parallel-safe with each other and with **Group E** (T-P5-19 to T-P5-20).
- **Group F** (T-P5-21 to T-P5-24) and **Group G** (T-P5-25 to T-P5-30) are
  parallel-safe with Groups C, D, E (after A completes).
- **Group H** (T-P5-31 to T-P5-33) must run last — no parallelism.
- At most one `[-]` per owner at any time unless tasks are from different groups and
  their write sets are disjoint.

---

## Phase A — Architecture Cleanup

<!-- owner: software-engineer-python (A1–A3, A5, A6, A7) + frontend-engineer (A4) -->

- [x] **T-P5-01** — Remove `PANEL_CSS`, `PANEL_JS`, and `PALETTE` from `_assets.py`; retain only `LOGO_RHINO_24` and `LOGO_RHINO_16` path constants until Phase B logo migration completes
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/_assets.py -->
  <!-- done-when: `PANEL_CSS`, `PANEL_JS`, `PALETTE` are absent from `_assets.py`; existing tests pass -->

- [x] **T-P5-02** — Move SVG reads (`LOGO_RHINO_24`, `LOGO_RHINO_16`) from `_assets.py` to `static.py`; update `index.py` to remove `_assets.py` import and read logo from `static.py`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/static.py, dadaia_workspace/features/panel/views/index.py, dadaia_workspace/features/panel/views/_assets.py -->
  <!-- preconditions: T-P5-01 done -->
  <!-- done-when: `index.py` has no import of `_assets.py`; panel starts and logo renders in topbar -->

- [x] **T-P5-03** — Harden `_try_build_telemetry()` in `panel.py`: replace bare `except Exception` with per-type handlers (`PermissionError`, `OSError`, `sqlite3.OperationalError`, `ImportError`) each emitting a `logging.warning` with the root cause before returning `None`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/panel.py -->
  <!-- done-when: unit test covers each exception type; warning is emitted; `None` is returned safely -->

- [x] **T-P5-04** — Wire `AcademyService` into panel DI: add `academy` parameter to `PanelService.__init__()` (optional, default `None`); instantiate `AcademyService` in `panel.py` composition root and pass to `PanelService`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/panel.py, dadaia_workspace/features/panel/service.py -->
  <!-- done-when: `PanelService` accepts `academy=None`; panel boots without error; existing tests pass -->

- [x] **T-P5-05** — Add route-category comment block in `handler.py` enumerating public / bearer-only / bearer+telemetry routes with their current members; add note that new routes must declare their category before being added
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/handler.py -->
  <!-- done-when: comment block exists above `_RAW_ROUTES` definition; enumerates all three categories -->

- [x] **T-P5-06** — Fix `_resolve_workspace()` (workspace resolver) to walk up from cwd to find the workspace root (containing `.dadaia/`) rather than assuming cwd is workspace root; ensure `dadaia panel` works from any subdirectory within the workspace
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/*.py (whichever file contains _resolve_workspace) -->
  <!-- done-when: `dadaia panel` invoked from `repos/dadaia-workspace/` (a subdirectory) resolves workspace root correctly; unit test covers the walk-up logic -->

- [x] **T-P5-07** — Introduce `window.Panel` registry in `core.js`: add `window.Panel = { register(name, mod), activate(name, opts) }` object before tab loading logic; migrate `window.Agents` and `window.Workflows` to also call `window.Panel.register()`; promote `escHtml` to `window.escHtml`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/core.js -->
  <!-- done-when: `window.Panel` object exists at runtime; `window.Panel.register('agents', window.Agents)` is called; `window.escHtml` is defined and callable -->

- [x] **T-P5-08** — Add `// TODO: replace with window.escHtml when touching this file` comment to local `escHtml` copies in `agents.js`, `workflows.js`, and `sessions.js`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/agents.js, workflows.js, sessions.js -->
  <!-- done-when: TODO comment present above each local `escHtml` function -->

- [x] **T-P5-09** — Add SSR-vs-client-side policy docstring to `views/index.py` module: SSR for public small-payload data (contexts, servers, academy); client-side for auth-gated or large/dynamic data (agents, sessions, workflows, reports)
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/index.py -->
  <!-- done-when: module docstring or comment block documents the policy -->

---

## Phase B — Visual Identity + Tokens + Logo

<!-- owner: frontend-engineer -->

- [x] **T-P5-10** — Add all new CSS custom properties to `tokens.py` per design spec §1.2–§1.10: new color tokens, spacing tokens (`--space-2xs`, `--space-3xl`), border-radius tokens (`--radius-modal`, `--radius-pill`), shadow tokens (`--shadow-card`, `--shadow-modal`, `--shadow-none`), z-index tokens (`--z-modal-overlay`, `--z-modal`, `--z-toast`), motion tokens (`--duration-fast`, `--duration-normal`, `--duration-slow`, `--easing-standard`, `--easing-decelerate`, `--easing-accelerate`), dimension tokens (`--modal-max-w`, `--modal-max-h`); update `--nav-h` from `44px` to `48px`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/tokens.py -->
  <!-- preconditions: T-P5-01 done (no conflict with _assets.py PANEL_CSS) -->
  <!-- done-when: all tokens listed in design spec §1.2–§1.10 as [NEW] are present; no raw hex values in new CSS rules outside tokens.py; panel compiles without error -->

- [x] **T-P5-11** — Update `structure.py`: change `.nav-tab` padding from `0.65rem 1.1rem` to `0.75rem 1.1rem`; remove `.tab-memories-btn::after` responsive abbreviation rule
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/structure.py -->
  <!-- preconditions: T-P5-10 done -->
  <!-- done-when: nav tab height is ~48px; no `::after` abbreviation rule exists for memories tab -->

- [x] **T-P5-12** — Create `logo-rhino-36.svg`: minimalist stroke-based rhino, viewBox `0 0 48 48`, rendered at 36×36px; anatomy includes body, head, horn (filled triangle), ear (small triangle), eye (circle r=1.5), 4 legs, tail (open stroke); all paths use `stroke="currentColor"`, body/head use `fill-opacity="0.12"`, horn/ear use opaque fill; no hardcoded hex
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/logo-rhino-36.svg -->
  <!-- done-when: SVG file exists; passes `xml.etree.ElementTree` parse; no hex colors; visually recognizable as rhino with horn at 36×36px -->

- [x] **T-P5-13** — Update `logo-rhino-24.svg` to match new stroke-based design (scaled to 24px viewBox); retain `logo-rhino-16.svg` unchanged
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg -->
  <!-- done-when: logo-rhino-24.svg uses same anatomy as logo-rhino-36.svg; passes SVG parse; no hardcoded hex -->

---

## Phase C — Projects Tab Redesign

<!-- owner: frontend-engineer (CSS/JS/HTML); software-engineer-python (API status rename) -->
<!-- parallel-safe with: Phase D, Phase E -->

- [x] **T-P5-14** — Update `GET /api/contexts` (or equivalent) API response to rename status labels `active` → `local` and `inactive` → `remote`; update any frontend references to these status strings
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/api.py (contexts endpoint) -->
  <!-- preconditions: Phase A complete -->
  <!-- done-when: API returns `local`/`remote`; existing tests updated; panel displays "local"/"remote" terminology -->

- [x] **T-P5-15** — Update Projects tab section header in `index.py`: change heading from "Memories" to "Projects"; remove "N active contexts — 1 primary" counter; add "N projects" plain count badge; add collapsible description block with expand toggle
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/index.py -->
  <!-- preconditions: Phase B complete -->
  <!-- done-when: heading reads "Projects"; counter is gone; description block present with collapse/expand -->

- [x] **T-P5-16** — Redesign Projects card HTML + CSS (4-zone anatomy): Zone A (name bold); Zone B (repo on own row, branch on own row, monospace, truncated with `text-overflow: ellipsis`); Zone D (three horizontal memory pill chips — Architecture, Tech Stack, Product — with `--color-chip-memory-bg` background, `--color-accent` border, `--radius-pill`); remove PRIMARY badge and primary left-border treatment; set uniform `4px solid var(--color-accent)` left accent on all cards
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/index.py (card template), dadaia_workspace/features/panel/views/assets/css/ (projects CSS module) -->
  <!-- preconditions: Phase B complete, T-P5-14 done -->
  <!-- done-when: no card shows PRIMARY badge; repo/branch on separate rows with truncation; memory chips are horizontal pills; all cards have mint left accent -->

- [x] **T-P5-17** — Add session binding zone (Zone C) to Projects card: conditional zone shown only when project has >= 1 active session bound; tinted `--color-session-bg`; each session is one row with provider icon + truncated name (max 200px); max 3 rows, "+N more" for overflow
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/index.py, relevant CSS module -->
  <!-- preconditions: T-P5-16 done -->
  <!-- done-when: projects with active sessions show session zone; projects without sessions hide zone completely -->

---

## Phase D — Agents Tab Redesign

<!-- owner: frontend-engineer -->
<!-- parallel-safe with: Phase C, Phase E -->

- [x] **T-P5-18** — Add `<dialog id="agent-modal">` scaffold to `agents.py` HTML; implement modal open/close in `agents.js` using native `<dialog>.showModal()` / `.close()`; implement focus trap (Tab cycles inside; Escape closes; focus returns to triggering card); add ARIA attributes (`role="dialog"`, `aria-modal="true"`, `aria-labelledby="agent-modal-title"`, close button `aria-label="Close"`)
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/agents.py, dadaia_workspace/features/panel/views/assets/js/agents.js -->
  <!-- preconditions: Phase B complete -->
  <!-- done-when: clicking agent card opens modal; Escape closes; focus trapped inside modal; ARIA attributes correct; screen reader sees dialog role -->

- [x] **T-P5-19** — Add modal CSS to `agents.py` CSS module: `.agent-modal`, `.agent-modal::backdrop`, overlay animation (opacity 0→1, translateY 12px→0, 250ms, `--easing-decelerate`), `prefers-reduced-motion` no-transform fallback, close button (44×44px, `--radius`, `--color-accent-dark` focus ring)
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/agents.py -->
  <!-- preconditions: T-P5-18 done -->
  <!-- done-when: modal animates open/close; `prefers-reduced-motion` respected; close button meets 44px touch target -->

- [x] **T-P5-20** — Redesign collapsed agent card anatomy (Zones A–D): Zone A (status badge + agent name + tier label); Zone B (description, 2-line clamp); Zone C (3-column stats row: Sessions, Cost Life, Last Seen); Zone D (skill chips + "+N more"); remove inline expand chevron and `.agent-card__detail` region; make entire card a `<button>` with `aria-haspopup="dialog"` and `aria-label="View details for [name]"`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/agents.py, dadaia_workspace/features/panel/views/assets/css/agents.py, dadaia_workspace/features/panel/views/assets/js/agents.js -->
  <!-- preconditions: T-P5-18, T-P5-19 done -->
  <!-- done-when: no expand chevron; card grid does not reflow when modal opens; card has button semantics -->

- [x] **T-P5-21** — Add runtime toggle (`.runtime-switcher`) to Agents tab section header: right-aligned via `margin-left: auto` in the `.section-header` flex row; uses existing `.runtime-switcher` + `.runtime-btn` CSS classes
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/agents.py -->
  <!-- preconditions: T-P5-18 done -->
  <!-- done-when: runtime toggle appears in Agents tab section header; does not appear in topbar -->

---

## Phase E — Workflows Tab DAG Zoom

<!-- owner: frontend-engineer -->
<!-- parallel-safe with: Phase C, Phase D -->

- [x] **T-P5-22** — Add DAG zoom controls to workflow detail view in `workflows.js`: wrap injected SVG in `div.workflow-dag-viewport` (`overflow: hidden`); add toolbar HTML `[−] [zoom%] [+] [Fit]` (right-aligned); implement `applyZoom(level)` function; zoom range 50%–300%, step 25%; keyboard bindings `+` / `−` / `0` when focus is within DAG section; `[Fit]` resets to `scale(1.0)`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/workflows.js -->
  <!-- preconditions: Phase B complete -->
  <!-- done-when: workflow detail view shows toolbar; + zooms in; − zooms out; Fit resets; keyboard bindings functional; zoom% display updates -->

- [x] **T-P5-23** — Add DAG zoom CSS to `workflows.py` CSS module: `.workflow-dag-viewport` (overflow hidden, min-height 280px, cursor grab when zoomed); `.dag-toolbar` (flex, justify-content flex-end, `--color-th-bg` background, padding); zoom buttons (32×32px, `--color-border` border, `--radius`); zoom% display (52px width, monospace, `--color-muted`)
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/workflows.py -->
  <!-- preconditions: T-P5-22 done -->
  <!-- done-when: DAG toolbar renders with correct styling; buttons are 32×32px; zoom display is monospace -->

- [x] **T-P5-24** — Add runtime toggle to Workflows tab section header (same pattern as T-P5-21 for Agents)
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/workflows.py (or index.py workflows section) -->
  <!-- preconditions: Phase B complete -->
  <!-- done-when: runtime toggle appears in Workflows tab section header -->

- [x] **T-P5-38** — Redesign Sessions tab error state per FR-6 design spec §8.2: replace single-cell error with a full-table-body-span container (`colspan` or block replacement); add `role="alert"` on the error container; add `[Retry]` button (`<button>` with explicit text, re-triggers `GET /api/sessions`); heading uses `var(--color-cost)` (#633d2e); body text uses `var(--color-muted)`; apply `scroll-margin-top: calc(var(--topbar-h) + var(--nav-h) + var(--space-sm))` to Sessions error container and to Projects/Agents card/modal triggers (FR-12)
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/sessions.js, dadaia_workspace/features/panel/views/assets/css/sessions.py (or equivalent) -->
  <!-- preconditions: T-P5-03 done (telemetry fix), Phase B complete (tokens) -->
  <!-- done-when: Sessions error container spans full table body; role="alert" present; Retry button is a <button> with text; heading is --color-cost; scroll-margin-top applied to cards and modal triggers -->

---

## Phase F — Academy Tab Infrastructure

<!-- owner: software-engineer-python (API/DI) + frontend-engineer (HTML/CSS/JS) -->

- [x] **T-P5-25** — Add `GET /api/academy` route to `handler.py` as bearer-only; add `render_api_academy()` to `api.py` calling `service.academy.list_all()` when `service.academy is not None`, returning JSON list; return empty list with 200 if `service.academy is None`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/handler.py, dadaia_workspace/features/panel/views/api.py -->
  <!-- preconditions: T-P5-04 done (DI wiring) -->
  <!-- done-when: `GET /api/academy` returns 200 with `[]` when no courses exist; bearer token required -->

- [x] **T-P5-26** — Create `views/academy.py`: HTML scaffold for Academy tab with module list section and content section (hidden by default); follows same static-scaffold pattern as `agents.py` and `sessions.py`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/academy.py -->
  <!-- preconditions: T-P5-25 done -->
  <!-- done-when: file exists; HTML scaffold renders empty state when no modules -->

- [x] **T-P5-27** — Create `academy.js`: fetch `GET /api/academy`; render module cards (type chip, title, 2-line description, "Open →" CTA); handle click → content view with `[← Back to Academy]` breadcrumb; show empty state "No academy modules available" when list is empty; register via `window.Panel.register('academy', ...)`; use `window.escHtml`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/academy.js -->
  <!-- preconditions: T-P5-26 done, T-P5-07 done (window.Panel registry) -->
  <!-- done-when: Academy tab loads list of courses; empty state shows when none; click opens content view; back button returns to list -->

- [x] **T-P5-28** — Create `academy.py` CSS module: module card grid (2-col >= 768px, 1-col below); type chip (`--color-academy-chip-bg`, `--color-cost` text, `--radius-pill`); left accent `4px solid var(--color-warning-bg)`; content frame (border, padding, `--color-surface` background); add `<link>` and `<script>` tags to `index.py` for academy
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/academy.py, dadaia_workspace/features/panel/views/index.py -->
  <!-- preconditions: T-P5-27 done, Phase B complete -->
  <!-- done-when: Academy cards render with warm olive left accent; type chip visible; grid responsive -->

---

## Phase G — Reports Tab

<!-- owner: software-engineer-python (API) + frontend-engineer (HTML/CSS/JS) -->

- [x] **T-P5-29** — Add `GET /api/reports` bearer-only route in `handler.py`; add `render_api_reports()` in `api.py`: traverse `.dadaia/reports/` recursively for `.handoff.json` sidecars, parse each, return sorted list by `produced_at` descending; fields: `title` (from `artifact.path` stem), `agent`, `context`, `created_at`, `path`, `findings_summary` (severity counts)
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/handler.py, dadaia_workspace/features/panel/views/api.py -->
  <!-- preconditions: Phase A complete -->
  <!-- done-when: `GET /api/reports` returns 200 with list of sidecars; sorted by date descending; malformed sidecars are skipped with a warning log -->

- [x] **T-P5-30** — Add `GET /reports/<path>` route in `handler.py`: serve HTML report file with path-traversal guard using `os.path.realpath()` to verify path is under `<workspace_root>/.dadaia/reports/`; return 403 if path escapes; set `Content-Type: text/html`
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/handler.py, dadaia_workspace/features/panel/views/api.py -->
  <!-- preconditions: T-P5-29 done -->
  <!-- done-when: valid path serves HTML; path outside boundary returns 403; symlinks are resolved before check -->

- [x] **T-P5-31** — Add `DELETE /api/reports/<path>` route in `handler.py` with same traversal guard; `delete_report_file()` in `api.py` deletes the `.html` file and its `.handoff.json` sidecar if present; return 404 if file not found; return 403 if path escapes boundary
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/handler.py, dadaia_workspace/features/panel/views/api.py -->
  <!-- preconditions: T-P5-30 done -->
  <!-- done-when: DELETE removes both HTML and sidecar; 404 for missing; 403 for boundary escape -->

- [x] **T-P5-32** — Create `views/reports.py`: HTML scaffold for Reports tab with list section and content section (hidden by default); follows static-scaffold pattern
  <!-- owner: software-engineer-python -->
  <!-- files: dadaia_workspace/features/panel/views/reports.py -->
  <!-- preconditions: T-P5-29 done -->
  <!-- done-when: file exists; scaffold renders -->

- [x] **T-P5-33** — Create `reports.js`: fetch `GET /api/reports`; render list grouped by context using `<details>/<summary>` per group; each row: agent tag chip, title button, date, trash icon; trash click: show inline "Are you sure? [Delete] [Cancel]"; Delete: call `DELETE /api/reports/<path>`, remove row on success; title click: fetch and render HTML content inline; breadcrumb `[← Back to Reports]`; register via `window.Panel.register('reports', ...)`; use `window.escHtml`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/js/reports.js -->
  <!-- preconditions: T-P5-32 done, T-P5-07 done (window.Panel registry) -->
  <!-- done-when: list loads grouped by context; trash shows inline confirm; delete removes row; click renders HTML inline; back returns to list; delete button 44px touch target; aria-labels dynamic -->

- [ ] **T-P5-34** — Create `reports.py` CSS module: list rows (flex, gap, padding); agent tag chip (`--color-report-tag-bg`, `--radius-pill`, 0.72rem); delete icon button (44px touch target, `--color-delete-icon`, hover `--color-delete-icon-hover`); group label (uppercase, `--color-muted`, `.group-label` class); content frame; add `<link>` and `<script>` to `index.py`
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/assets/css/reports.py, dadaia_workspace/features/panel/views/index.py -->
  <!-- preconditions: T-P5-33 done, Phase B complete -->
  <!-- done-when: report rows render with agent chip and 44px delete button; group labels are uppercase muted; content frame styled -->

---

## Phase H — Tab Nav Overhaul

<!-- owner: frontend-engineer -->
<!-- must be last — no parallelism -->

- [ ] **T-P5-35** — Reorder nav tabs in `index.py` to canonical sequence: `Projects | Agents | Workflows | Sessions | Reports | Academy | Servers`; add nav tab buttons for "Reports" and "Academy" (currently missing); move "Servers" tab button to last position
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/index.py -->
  <!-- preconditions: All phases A–G complete -->
  <!-- done-when: 7 tab buttons present in correct order; Reports and Academy tabs activate their respective content sections -->

- [ ] **T-P5-36** — Remove global runtime switcher (`div.runtime-switcher`) from topbar HTML in `index.py`; update topbar CSS in `structure.py` to remove primary badge area and runtime switcher area; update `.topbar-logo svg` size to 36×36px; wire new logo-rhino-36.svg reference
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/index.py, dadaia_workspace/features/panel/views/assets/css/structure.py -->
  <!-- preconditions: T-P5-12 done (new SVG exists), T-P5-35 done -->
  <!-- done-when: no PRIMARY badge in topbar; no runtime switcher in topbar; logo is 36px; Theme dropdown is still present -->

- [ ] **T-P5-37** — Add runtime toggle to Sessions tab section header (same pattern as T-P5-21 for Agents); update `core.js` tab activation to use `window.Panel.activate` for all tabs; wire Academy and Reports tab activations
  <!-- owner: frontend-engineer -->
  <!-- files: dadaia_workspace/features/panel/views/sessions.py (or equivalent), dadaia_workspace/features/panel/views/assets/js/core.js -->
  <!-- preconditions: T-P5-35, T-P5-36 done -->
  <!-- done-when: runtime toggle appears in Sessions tab; core.js activates Academy and Reports modules via window.Panel; all 7 tabs load their content correctly -->
