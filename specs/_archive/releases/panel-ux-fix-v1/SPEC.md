# SPEC — panel-ux-fix-v1

**Status:** Aprovado
**Revised:** 2026-05-30 — corrected F2 (column fix was technically wrong: col% under table-layout:fixed); added F5 (panel auth UX).
**Release ID:** panel-ux-fix-v1
**Owner:** frontend-engineer + design-specialist + qa-engineer + software-engineer-python

## Objective

Fix 4 reported UX/visual bugs in the dadaia-workspace panel and establish consistent visual identity across memory pages, reports, and agent cards.

## Findings (operator screenshots 2026-05-26)

| # | Surface | Issue | Severity |
|---|---------|-------|----------|
| F1 | Memory pages (Projects tab) | No visual identity — raw HTML served without panel CSS or brand styling | HIGH |
| F2 | Sessions tab | Table columns collapse — `<col>` percentage widths under `table-layout:fixed` do not respect `min-width` on `<col>` elements; Codex rows (which return `project='—'`, no sub-slug) trigger catastrophic collapse where SESSION shows ~4 chars and all other cols render empty | HIGH |
| F3 | Sessions/Workflows tabs | Claude↔Codex toggle locked — `_wireRuntimeSwitcher()` only wires the first `.runtime-switcher` in DOM; Sessions tab switcher never receives click handlers | HIGH |
| F4 | Agents tab | Agent cards not following visual identity — generic styling, inconsistent token usage | MEDIUM |
| F5 | Panel auth | Bearer-token wall on every `/api/*` request blocks local humans and AI-agent (bot) clients — produces a "a required part couldn't load" failure (a 401, mis-attributed to ad blockers). Bots use the workspace too. | HIGH |

## Acceptance criteria

- F1: Memory pages render with panel CSS variables (typography, colors, spacing) whether accessed from Projects tab link or direct URL
- F2: Sessions table shows all 8 columns with readable widths using per-cell `min-width` applied via CSS class selectors (`.cell-session`, `.cell-project`, etc.) on `<th>`/`<td>` pairs — NOT on `<col>` elements (which are ignored under `table-layout:fixed`). Required minimums: SESSION 120px, PROJECT 96px, MODEL 160px, AI TURNS 72px, CONTEXT 80px, COST 72px, LAST ACTIVITY 112px, STATUS 80px (total floor ≈ 792px). Container has `overflow-x:auto` so the table scrolls horizontally below 792px instead of collapsing. Verified correct when Codex runtime is selected — all 8 columns visible and populated, PROJECT shows '—' not blank, no column collapse, horizontal scroll below 792px. Codex '—' placeholder rendered with `.cell-placeholder` class, muted `#666` (5.52:1 AA contrast ratio), italic.
- F3: Claude↔Codex toggle works on Sessions tab independently of which tab was loaded first; toggling on any tab reflects across all tabs
- F4: Agent cards use brand palette (mint/sage/warm), correct font sizes (≥ 0.75rem), WCAG AA contrast on status badges
- F5: `GET /api/*` from a 127.0.0.1-bound panel with NO `Authorization` header returns 200; from a non-loopback bind, still 401 without a valid token. A bot using plain `fetch()` against a local panel never receives 401. Detection is at the server bind level via a `loopback_bypass` flag in `make_handler_class()` — not from the client peer address. Log a one-line startup warning `[PANEL] Auth disabled for loopback (127.0.0.1) connections.`

## Out of scope

- New features or tabs
- Data model changes
- CI pipeline changes
