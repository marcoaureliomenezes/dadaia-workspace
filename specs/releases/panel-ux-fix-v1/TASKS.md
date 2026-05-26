# TASKS — panel-ux-fix-v1

**Status:** Aprovado

## T-PUX-01 — Fix Sessions table column widths [frontend-engineer]
[x] Add `table-layout: fixed` to `.sessions-table` in `sessions.py` (CSS).
    Add `<colgroup>` with proportional `width` on each `<col>` in `sessions.py` (HTML).
    File: `dadaia_workspace/features/panel/views/sessions.py`
    File: `dadaia_workspace/features/panel/views/assets/css/sessions.py`

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

## T-PUX-05 — QA validation [qa-engineer]
[ ] Capture Playwright screenshots for all 4 fixes at 1280px + 768px.
[ ] Verify Sessions table shows all columns readable.
[ ] Verify toggle works on Sessions tab after loading from Agents tab.
[ ] Verify memory pages render with panel visual identity.
[ ] Verify agent cards contrast ratios pass WCAG AA.
[ ] Screenshots go to `.dadaia/tmp/qa-engineer/panel-ux-fix-v1/`.
