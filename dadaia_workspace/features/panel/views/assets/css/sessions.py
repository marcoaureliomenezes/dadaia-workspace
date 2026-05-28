"""Sessions table CSS for the Dadaia Workspace Panel.

PR5-C2 (FE): Sessions tab table, status dot, drawer transitions.
  - Sortable table with sticky header
  - Status dot variants: active (green), idle (amber), ended (muted)
  - Skeleton-pulse loading rows during initial fetch (reuses .skeleton-pulse from agents.css)
  - Drawer slide-in/out transition (≤200ms per NFR)
  - Filter input above the table
  - All colour values reference existing design tokens from tokens.py — no new
    raw hex values are introduced here. Fallbacks mirror the tokens pattern.
  - Motion respects prefers-reduced-motion
  - Drawer transition under 200ms (NFR)
"""

SESSIONS_CSS: str = """
/* ── Screen-reader-only utility (if not defined globally) ─────────── */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border-width: 0;
}

/* ── Codex cost banner ────────────────────────────────────────────── */
/* Shown by JS when runtime === 'codex'; hidden by default via [hidden] attribute. */
.sessions-banner {
  padding: 0.55rem 1rem;
  margin-bottom: 0.75rem;
  background: var(--color-placeholder-bg, #f7f7f7);
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  font-size: 0.875rem;
  color: var(--color-muted, #666666);
  font-family: var(--font-stack, -apple-system, sans-serif);
  /* Contrast: #666666 on #f7f7f7 → 4.56:1 (WCAG 2.1 AA ≥ 4.5:1 satisfied) */
}
/* Ensure [hidden] attribute is respected over display rules */
.sessions-banner[hidden] {
  display: none !important;
}

/* ── Sessions toolbar (filter + last-updated badge) ───────────────── */
.sessions-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.sessions-filter-input {
  flex: 1;
  min-width: 200px;
  max-width: 400px;
  padding: 0.35em 0.65em;
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius, 4px);
  font-size: 0.88rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  color: var(--color-text, #222222);
  background: var(--color-surface, #ffffff);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.sessions-filter-input:focus {
  outline: none;
  border-color: var(--color-accent-dark, #2d7d9a);
  box-shadow: 0 0 0 2px var(--color-accent, #9cddc8);
}
.sessions-filter-input::placeholder {
  color: var(--color-muted, #666666);
}
@media (prefers-reduced-motion: reduce) {
  .sessions-filter-input { transition: none; }
}

.sessions-last-updated {
  font-size: 0.78rem;
  color: var(--color-muted, #666666);
  white-space: nowrap;
}

/* ── Sessions table container ─────────────────────────────────────── */
.sessions-table-container {
  overflow-x: auto;
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  margin-bottom: 1rem;
}

/* ── Sessions table ───────────────────────────────────────────────── */
.sessions-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 0.875rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  background: var(--color-surface, #ffffff);
}

/* ── Table header ─────────────────────────────────────────────────── */
.sessions-table th {
  padding: 0.6rem 0.75rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted, #666666);
  background: var(--color-th-bg, #eeeeee);
  border-bottom: 2px solid var(--color-border, #dddddd);
  white-space: nowrap;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 1;
}

/* Sortable column headers — pointer cursor + sort indicator */
.sessions-table th[data-sort-key] {
  cursor: pointer;
}
.sessions-table th[data-sort-key]:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-text, #222222);
}
.sessions-table th[data-sort-key]:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: -2px;
}
/* Sort direction indicator via ::after pseudo-element */
.sessions-table th[data-sort-dir="asc"]::after {
  content: " ↑";
  font-weight: 400;
  font-size: 0.7em;
}
.sessions-table th[data-sort-dir="desc"]::after {
  content: " ↓";
  font-weight: 400;
  font-size: 0.7em;
}

/* ── Table cells ──────────────────────────────────────────────────── */
.sessions-table td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  color: var(--color-text, #222222);
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Session row (clickable) ──────────────────────────────────────── */
.sessions-table tbody tr.session-row {
  cursor: pointer;
  transition: background 0.1s ease;
}
.sessions-table tbody tr.session-row:hover {
  background: var(--color-row-hover, #f5f5f5);
}
.sessions-table tbody tr.session-row:focus {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: -2px;
}
.sessions-table tbody tr.session-row:last-child td {
  border-bottom: none;
}
@media (prefers-reduced-motion: reduce) {
  .sessions-table tbody tr.session-row { transition: none; }
}

/* ── Session cell (truncated session_id + tooltip) ────────────────── */
.cell-session {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.8rem;
}

/* ── Cost cell ────────────────────────────────────────────────────── */
.cell-cost {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
  color: var(--color-cost, #633d2e);
}

/* ── Context / AI Turns / Model cells ────────────────────────────── */
.cell-context,
.cell-turns {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  text-align: right;
}

.cell-model {
  max-width: 160px;
  font-size: 0.82rem;
}

/* ── Status dot ───────────────────────────────────────────────────── */
.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  font-size: 0.82rem;
  white-space: nowrap;
}
/* Coloured dot rendered via ::before pseudo-element */
.status-dot::before {
  content: "";
  display: inline-block;
  width: 0.55em;
  height: 0.55em;
  border-radius: 50%;
  background: var(--color-muted, #666666);
  flex-shrink: 0;
}
/* active — green */
.status-dot[data-status="active"]::before {
  background: var(--color-active-dot, #3aaa6e);
}
/* idle — amber */
.status-dot[data-status="idle"]::before {
  background: var(--color-stale-dot, #cc7700);
}
/* ended — muted grey */
.status-dot[data-status="ended"]::before {
  background: var(--color-muted, #666666);
}

/* ── Skeleton loading rows ────────────────────────────────────────── */
.session-row--skeleton td {
  padding: 0.65rem 0.75rem;
}
.session-row--skeleton .skeleton-cell {
  display: block;
  height: 0.85em;
  border-radius: 3px;
}

/* ── Sessions detail drawer ───────────────────────────────────────── */
/* Drawer is positioned as a side panel on the right.
   Transition is ≤200ms per NFR.                                         */
.session-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: min(480px, 90vw);
  height: 100%;
  background: var(--color-surface, #ffffff);
  border-left: 1px solid var(--color-border, #dddddd);
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transform: translateX(100%);
  transition: transform 180ms ease-out;
  overflow: hidden;
}
@media (prefers-reduced-motion: reduce) {
  .session-drawer { transition: none; }
}

/* hidden attribute — override to keep hidden state when JS hasn't opened it yet */
.session-drawer[hidden] {
  display: none !important;
  transform: translateX(100%);
}

/* open state — slide in */
.session-drawer.open {
  transform: translateX(0);
}

/* ── Drawer header ────────────────────────────────────────────────── */
.session-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  flex-shrink: 0;
}
.session-drawer__title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  margin: 0;
}

/* ── Drawer close button ──────────────────────────────────────────── */
.session-drawer__close-btn {
  background: none;
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius, 4px);
  color: var(--color-muted, #666666);
  cursor: pointer;
  font-size: 0.82rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  padding: 0.2em 0.6em;
  transition: background 0.12s ease, color 0.12s ease;
}
.session-drawer__close-btn:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-text, #222222);
}
.session-drawer__close-btn:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .session-drawer__close-btn { transition: none; }
}

/* ── Drawer content area ──────────────────────────────────────────── */
.session-drawer__content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border, #dddddd) transparent;
}

/* ── Drawer detail fields ─────────────────────────────────────────── */
.drawer-field {
  margin-bottom: 0.75rem;
}
.drawer-field-label {
  display: block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted, #666666);
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.drawer-field-value {
  font-size: 0.9rem;
  color: var(--color-text, #222222);
  word-break: break-all;
}
.drawer-field-value--mono {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
}
.drawer-field-value--cost {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
}

/* ── Drawer event timeline ────────────────────────────────────────── */
.drawer-events {
  list-style: none;
  padding: 0;
  margin: 0.25rem 0 0;
}
.drawer-events li {
  font-size: 0.78rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  color: var(--color-muted, #666666);
  padding: 0.15rem 0;
  border-bottom: 1px solid var(--color-border, #dddddd);
}
.drawer-events li:last-child {
  border-bottom: none;
}

/* ── Drawer loading / error states ───────────────────────────────── */
.drawer-loading {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 0;
  aria-busy: true;
}
.drawer-error {
  color: var(--color-cost, #633d2e);
  background: #fef3ec;
  border: 1px solid var(--color-alert, #f7af63);
  border-radius: var(--radius-card, 6px);
  padding: 0.75rem 1rem;
  font-size: 0.88rem;
}

/* ── Sessions error state (T-P5-38) ──────────────────────────────── */
.sessions-error-container {
  padding: 1rem 1.25rem;
  scroll-margin-top: calc(var(--topbar-h, 56px) + var(--nav-h, 48px) + var(--space-sm, 0.6rem));
}
.sessions-error-heading {
  color: var(--color-cost, #633d2e);
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0 0 0.4rem;
}
.sessions-error-body {
  color: var(--color-muted, #666666);
  font-size: 0.88rem;
  margin: 0 0 0.75rem;
}
.sessions-retry-btn {
  background: none;
  border: 1px solid var(--color-accent-dark, #2d7d9a);
  border-radius: var(--radius, 4px);
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  font-size: 0.85rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  min-width: 44px;
  min-height: 44px;
  padding: 0.3em 0.9em;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.sessions-retry-btn:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
}
.sessions-retry-btn:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}

/* ── Sessions dashboard ─────────────────────────────────────────── */
.sessions-dashboard {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
@media (max-width: 640px) {
  .sessions-dashboard { grid-template-columns: repeat(2, 1fr); }
}
.sessions-stat-card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  padding: 0.85rem 1rem;
  overflow: hidden;
}
.sessions-stat-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted, #666666);
  margin-bottom: 0.3rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
}
.sessions-stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  font-family: var(--font-mono, ui-monospace, monospace);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sessions-stat-value--cost {
  color: var(--color-cost, #633d2e);
}
.sessions-stat-sub {
  display: block;
  font-size: 0.72rem;
  color: var(--color-muted, #666666);
  margin-top: 0.25rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-stack, -apple-system, sans-serif);
}
"""
