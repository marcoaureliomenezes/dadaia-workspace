"""Sessions tab CSS for the Dadaia Workspace Panel (aggregated-cost dashboard).

panel-plumbing v0.1.52 FR2: the Sessions tab is dashboard-only. The table,
sortable headers, detail drawer, filter toolbar, and skeleton-loading rules were
removed with the client list; only the 4-card summary grid, the cost-unknown
banner, and the last-updated badge survive here.

  - 4-card summary grid (responsive: 4 cols → 2 cols under 640px)
  - Cost-unknown banner (hidden by default via the [hidden] attribute)
  - Last-updated badge (compact muted text)
  - All colour values reference existing design tokens from tokens.py — no new
    raw hex values are introduced here. Fallbacks mirror the tokens pattern.
"""

SESSIONS_CSS: str = """
/* ── Cost-unknown banner ──────────────────────────────────────────── */
/* Shown by JS when the runtime is codex/pi; hidden by default via [hidden]. */
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

/* ── Last-updated badge ───────────────────────────────────────────── */
.sessions-last-updated {
  display: inline-block;
  margin-bottom: 0.75rem;
  font-size: 0.78rem;
  color: var(--color-muted, #666666);
  white-space: nowrap;
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
/* v0.1.59 / FR4 density pass: a calm resting shadow (--shadow-card-rest) gives the
   Sessions dashboard cards the same quiet elevation as the other card surfaces, so
   the panel reads as one designed system. These summary cards are non-interactive,
   so they carry no hover lift. */
.sessions-stat-card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  box-shadow: var(--shadow-card-rest, 0 1px 3px rgba(0,0,0,.06));
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
