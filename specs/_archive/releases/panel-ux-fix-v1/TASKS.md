# TASKS — panel-ux-fix-v1

**Status:** Aprovado

## T-PUX-01 — Fix Sessions table column widths [frontend-engineer]
[x] Re-opened 2026-05-30: prior fix used col% under table-layout:fixed (ineffective — min-width on `<col>` is ignored by the fixed-layout algorithm per MDN).
    Correct approach: set `min-width` on each `<th>`/`<td>` pair via CSS class selectors.
    Required per-cell min-widths (design-spec values):
      - `.cell-session` (SESSION): min-width 120px
      - `.cell-project` (PROJECT): min-width 96px
      - `.cell-model` (MODEL): min-width 160px
      - `.cell-turns` (AI TURNS): min-width 72px
      - `.cell-context` (CONTEXT): min-width 80px
      - `.cell-cost` (COST): min-width 72px
      - `.cell-activity` (LAST ACTIVITY): min-width 112px
      - `.cell-status` (STATUS): min-width 80px
    Container `.sessions-table-container` must have `overflow-x: auto` (may already exist; verify).
    `<colgroup>` percentage widths (14/14/20/8/8/8/14/10%) remain for proportional allocation on wide viewports.
    Codex rows: PROJECT cell must render `<span class="cell-placeholder" title="Project context not applicable for Codex sessions">&mdash;</span>`.
    `.cell-placeholder`: `color: var(--color-muted); font-style: italic;` (contrast #666 on white = 5.52:1 AA pass).
    Verified correct when Codex runtime is selected — all 8 columns visible, PROJECT='—' not blank, no collapse, h-scroll below 792px.
    Files: `dadaia_workspace/features/panel/views/sessions.py`,
           `dadaia_workspace/features/panel/views/assets/css/sessions.css`

## T-PUX-02 — Fix Claude↔Codex toggle on all tabs [frontend-engineer]
[x] Change `document.querySelector('.runtime-switcher')` to `document.querySelectorAll('.runtime-switcher')` in `_wireRuntimeSwitcher()`.
    Wire click+keyboard handlers for EVERY `.runtime-switcher` instance in the DOM.
    File: `dadaia_workspace/features/panel/views/assets/js/runtime.js`

## T-PUX-03 — Memory pages visual identity [design-specialist → frontend-engineer]
[x] design-specialist: define visual identity spec for memory pages (typography, colors, spacing tokens matching panel brand).
[x] frontend-engineer: implement — create `/assets/css/memory.css` served by the panel's static route; inject `<link>` via a new `/memory-view/` wrapper route that wraps raw memory HTML in a styled shell, OR update the panel's Projects tab to serve memory through an iframe with panel CSS injected.

## T-PUX-04 — Agent cards visual identity [design-specialist → frontend-engineer]
[x] design-specialist: audit agent cards against brand tokens; emit spec.
[x] frontend-engineer: update `agents.py` (CSS) to use brand palette, correct font sizes, WCAG AA status badge contrast.

## T-PUX-06 — Loopback no-token auth bypass [software-engineer-python]
[x] Implement `loopback_bypass` flag in `make_handler_class()`:
    1. `dadaia_workspace/cli/commands/panel.py` (~L123): pass `loopback_bypass=(bind == "127.0.0.1")` to `make_handler_class()`.
    2. `dadaia_workspace/features/panel/handler.py` (~L210): add `loopback_bypass: bool = False` parameter to `make_handler_class()`; close over it as `_loopback_bypass`.
    3. `dadaia_workspace/features/panel/handler.py` (~L283): wrap the existing 401 branch: `if not _loopback_bypass and (_token is None or not _validate_bearer(...)): respond 401`.
    Detection is from the server bind address (the `_LOOPBACK_ONLY` set in `panel.py`), NOT the client TCP peer address (`self.client_address[0]`).
    `core.js` / `authedFetch` is unchanged — server ignores absent/empty Authorization header on loopback.
    Log a one-line startup warning: `[PANEL] Auth disabled for loopback (127.0.0.1) connections.`
    Security boundary note (must appear in PR description and SPEC F5 AC): any local process can read panel data without a token — deliberate trade-off for a dev-local tool.
    Reference: QA auth test catalogue in `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T143000Z-test-strategy-panel-hardening-kanban.html` §1.1.

## T-PUX-05 — QA validation [qa-engineer]
[x] Capture Playwright screenshots for all 4 fixes at 1280px + 768px.
[x] Verify Sessions table shows all columns readable.
[x] Verify toggle works on Sessions tab after loading from Agents tab.
[x] Verify memory pages render with panel visual identity.
[x] Verify agent cards contrast ratios pass WCAG AA.
[x] Re-verify T-PUX-03 and T-PUX-04 are still passing (check not regressed by column-width rework).
    Mandatory Playwright Codex gate (added 2026-05-30):
    Launch panel with a Codex SQLite fixture (see fixture helper `tests/fixtures/telemetry/seed_codex_fixture.py`),
    select Codex runtime, then assert ALL of the following using deterministic `waitForSelector` — NO `time.sleep`:
      - All 8 column headers visible: SESSION, PROJECT, MODEL, AI TURNS, CONTEXT, COST, LAST ACTIVITY, STATUS.
      - Every `tr.session-row` has exactly 8 `<td>` children.
      - PROJECT column cells contain '—' (em-dash), not an empty string, not 'None', not blank.
      - No column has computed width below its declared min-width at 900px viewport.
      - Table container overflows-x at 600px viewport (does not collapse below 792px total width).
    Loopback-auth assertions (added 2026-05-30, validates T-PUX-06):
      - `GET /api/sessions` with no Authorization header returns 200 on a 127.0.0.1-bound panel (loopback_bypass=True).
      - `GET /api/sessions` with no Authorization header returns 401 on a handler configured with loopback_bypass=False.
    Evidence folder: `.dadaia/tmp/qa-engineer/panel-ux-fix-v1/`.
