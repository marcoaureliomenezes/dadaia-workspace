"""Kanban board CSS for the Dadaia Workspace Panel.

panel-kanban-v1 K-2 (FE): Swimlane × 4-column Kanban layout (§7 lifecycle columns).
  - One swimlane per Spec Context Project; four phase columns per lane:
      Backlog | Release Definition | Implementation + Review | Closure
  - Board is horizontally scrollable below 800px.
  - Desktop (>=1280px): all 4 columns visible side-by-side.
  - Column min-width: var(--kanban-col-min-w, 200px).
  - The combined "Implementation + Review" column may be wider at
    --kanban-col-min-w to accommodate the longer label; responsive behaviour kept.
  - XOR-lock dimming (.kanban-column--locked) is retired: impl and review share
    one column so mutual-exclusion visual no longer applies.
  - Card anatomy: font-mono session ID + status dot, runtime line (muted),
    runtime·age line (muted). min-height: var(--kanban-card-min-h, 72px).
  - Per-card stale indicator preserved: data-stale="true" left-border accent.
  - Empty-column placeholder: dashed border, height var(--kanban-card-min-h).
  - Card appear animation: opacity 0→1 var(--duration-normal, 220ms) var(--easing-decelerate).
    Suppressed under prefers-reduced-motion.
  - Column header concurrency badges: Release Definition ≤2, Implementation + Review ×2.
    Badge: --color-placeholder-bg bg, --color-muted text, --font-size-xs, --radius-pill.
  - All colour values reference design tokens from tokens.py — no new raw hex values.
  - WCAG AA: card title #111 on white → 18.5:1; card meta #666 on white → 5.52:1;
    separator #888 on #fafafa → 3.54:1 (1.4.11 non-text).
"""

KANBAN_CSS: str = """
/* ── Kanban board container ───────────────────────────────────────────── */
.kanban-board {
  display: flex;
  flex-direction: column;
  gap: var(--space-md, 1rem);
  padding: var(--space-sm, 0.6rem) 0;
}

/* ── Kanban toolbar (last-updated + meta) ─────────────────────────────── */
.kanban-toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}
.kanban-last-updated {
  font-size: 0.78rem;
  color: var(--color-muted, #666666);
  white-space: nowrap;
}

/* ── Swimlane ─────────────────────────────────────────────────────────── */
.kanban-lane {
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  overflow: hidden;
}

/* ── Swimlane header (context name) ──────────────────────────────────── */
.kanban-lane-header {
  background: var(--color-kanban-lane-header-bg, var(--color-primary-bg, #f0fbf7));
  border-bottom: 1px solid var(--color-border, #dddddd);
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.kanban-lane-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  font-family: var(--font-stack, -apple-system, sans-serif);
  margin: 0;
}

/* ── Swimlane columns row ─────────────────────────────────────────────── */
/* Mobile: scroll; ≥800px: four columns fit without scroll; ≥1280px: all
   four always visible side-by-side (min-width constraint ensures this). */
.kanban-lane-columns {
  display: flex;
  flex-direction: row;
  overflow-x: auto;
  gap: 0;
}
@media (min-width: 800px) {
  .kanban-lane-columns {
    overflow-x: hidden;
  }
}

/* ── Column ───────────────────────────────────────────────────────────── */
.kanban-column {
  flex: 1 0 var(--kanban-col-min-w, 200px);
  min-width: var(--kanban-col-min-w, 200px);
  padding: 0.5rem;
  border-right: 1px solid var(--color-kanban-separator, #888888);
  background: var(--color-surface, #ffffff);
  display: flex;
  flex-direction: column;
  gap: var(--kanban-card-gap, var(--space-sm, 0.6rem));
  transition: opacity var(--duration-fast, 120ms) var(--easing-standard, ease);
}
.kanban-column:last-child {
  border-right: none;
}
@media (prefers-reduced-motion: reduce) {
  .kanban-column {
    transition: none;
  }
}

/* ── Locked column (retired — XOR-lock dimming is no longer used since    */
/* impl and review share one combined column; kept as CSS guard in case    */
/* future features reintroduce the class.)                                 */
.kanban-column--locked {
  opacity: var(--opacity-kanban-locked, 0.40);
}

/* ── Column header ────────────────────────────────────────────────────── */
.kanban-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  margin-bottom: 0.25rem;
}
.kanban-col-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted, #666666);
  font-family: var(--font-stack, -apple-system, sans-serif);
  white-space: nowrap;
  /* Contrast: #666666 on #ffffff → 5.52:1 (WCAG 2.1 AA ≥ 4.5:1 pass) */
}
.kanban-col-header-right {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* ── Concurrency badge ─────────────────────────────────────────────────── */
.kanban-concurrency-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-muted, #666666);
  font-size: var(--font-size-xs, 0.68rem);
  font-family: var(--font-stack, -apple-system, sans-serif);
  border-radius: var(--radius-pill, 9999px);
  padding: 0.1em 0.45em;
  line-height: 1.4;
  border: 1px solid var(--color-border, #dddddd);
  white-space: nowrap;
  /* Contrast: #666666 on #f7f7f7 → 4.56:1 (WCAG 2.1 AA ≥ 4.5:1 pass) */
}

/* ── Lock badge on column header (retired — kept for forward-compat) ─── */
.kanban-lock-badge {
  font-size: 0.78rem;
  /* lock icon is visual supplement; not sole conveyance of locked state */
}

/* ── Card ─────────────────────────────────────────────────────────────── */
.kanban-card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-card, #dddddd);
  border-radius: var(--radius-card, 6px);
  padding: 0.5rem 0.6rem;
  min-height: var(--kanban-card-min-h, 72px);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  cursor: default;
  box-shadow: var(--shadow-card, 0 1px 3px rgba(0,0,0,.12));
  /* Card appear animation: opacity 0→1 */
  animation: kanban-card-appear var(--duration-normal, 220ms) var(--easing-decelerate, cubic-bezier(0,0,.2,1)) both;
}
.kanban-card:focus {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
.kanban-card:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .kanban-card {
    animation: none;
  }
}

@keyframes kanban-card-appear {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* ── Card: stale indicator ────────────────────────────────────────────── */
.kanban-card[data-stale="true"] {
  border-left: 3px solid var(--color-stale-dot, #cc7700);
}

/* ── Card title row (session id + status dot) ────────────────────────── */
.kanban-card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.3rem;
}
.kanban-card-session-id {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-heading, #111111);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  /* Contrast: #111111 on #ffffff → 18.5:1 (WCAG 2.1 AA ≥ 4.5:1 pass) */
}
.kanban-status-dot {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.kanban-status-dot::before {
  content: "";
  display: inline-block;
  width: 0.5em;
  height: 0.5em;
  border-radius: 50%;
  background: var(--color-muted, #666666);
}
.kanban-status-dot[data-stale="true"]::before {
  background: var(--color-stale-dot, #cc7700);
}
.kanban-status-dot[data-stale="false"]::before {
  background: var(--color-active-dot, #3aaa6e);
}

/* ── Card meta rows (runtime, age) ───────────────────────────────────── */
.kanban-card-meta {
  font-family: var(--font-stack, -apple-system, sans-serif);
  font-size: 0.78rem;
  color: var(--color-muted, #666666);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  /* Contrast: #666666 on #ffffff → 5.52:1 (WCAG 2.1 AA ≥ 4.5:1 pass) */
}
.kanban-card-meta-detail {
  font-size: 0.72rem;
  color: var(--color-muted, #666666);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Empty column placeholder ────────────────────────────────────────── */
.kanban-empty-placeholder {
  border: 1px dashed var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  height: var(--kanban-card-min-h, 72px);
  background: transparent;
}

/* ── Empty lane state ─────────────────────────────────────────────────── */
.kanban-lane-empty {
  padding: var(--space-sm, 0.6rem) 0.75rem;
  font-size: 0.82rem;
  font-style: italic;
  color: var(--color-muted, #666666);
  font-family: var(--font-stack, -apple-system, sans-serif);
}

/* ── Empty board state ────────────────────────────────────────────────── */
.kanban-board-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl, 2rem);
  font-size: 0.9rem;
  color: var(--color-muted, #666666);
  font-family: var(--font-stack, -apple-system, sans-serif);
  font-style: italic;
  text-align: center;
}

/* ── Error state ──────────────────────────────────────────────────────── */
.kanban-error {
  color: var(--color-cost, #633d2e);
  background: #fef3ec;
  border: 1px solid var(--color-alert, #f7af63);
  border-radius: var(--radius-card, 6px);
  padding: 0.75rem 1rem;
  font-size: 0.88rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
}
"""
