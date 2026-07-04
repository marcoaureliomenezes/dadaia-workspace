"""Reports tab CSS for the Dadaia Workspace Panel.

T-P5-34 (FE): Report list rows, agent tag chip, delete icon button, group labels,
content frame, and back button.
  - Group label: uppercase, letter-spacing, --color-muted
  - Agent tag chip: --color-report-tag-bg background, --radius-pill, 0.72rem font
  - Delete icon button: 44px touch target, --color-delete-icon, hover --color-delete-icon-hover
  - Content frame: border, padding, --color-surface background, overflow-x auto
  - All colour values reference design tokens from tokens.py — no raw hex values
    except fallbacks that mirror token defaults.
  - Motion respects prefers-reduced-motion (via transition only — no animation)
"""

REPORTS_CSS: str = """
/* ── Reports group (context group) ────────────────────────────────── */
.reports-group {
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  margin-bottom: var(--space-sm, 0.6rem);
  overflow: hidden;
}

.reports-group-summary {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 0.6rem);
  padding: 0.55rem var(--space-md, 1rem);
  cursor: pointer;
  background: var(--color-th-bg, #eeeeee);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-heading, #111111);
  user-select: none;
  list-style: none;
}

.reports-group-summary::-webkit-details-marker {
  display: none;
}

.reports-group-label {
  flex: 1;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.75rem;
  color: var(--color-muted, #666666);
}

.reports-count-badge {
  background: var(--color-accent, #9cddc8);
  border-radius: var(--radius-pill, 9999px);
  padding: 0.1em 0.55em;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
}

/* ── Report rows ──────────────────────────────────────────────────── */
.reports-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.reports-row {
  border-top: 1px solid var(--color-border, #dddddd);
  padding: 0.45rem var(--space-md, 1rem);
}

.reports-row__actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 0.6rem);
  flex-wrap: wrap;
}

/* ── Agent tag chip ───────────────────────────────────────────────── */
.report-tag-chip {
  display: inline-block;
  background: var(--color-report-tag-bg, #f0f4f7);
  border-radius: var(--radius-pill, 9999px);
  padding: 0.12em 0.6em;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text, #222222);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── Title button ─────────────────────────────────────────────────── */
.reports-row__title {
  flex: 1;
  background: transparent;
  border: none;
  text-align: left;
  padding: 0;
  font-size: 0.85rem;
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 340px;
}

.reports-row__title:hover,
.reports-row__title:focus-visible {
  text-decoration: underline;
}

/* ── Date ─────────────────────────────────────────────────────────── */
.reports-row__date {
  font-size: 0.75rem;
  color: var(--color-muted, #666666);
  font-family: var(--font-mono, ui-monospace, monospace);
  white-space: nowrap;
  flex-shrink: 0;
}

.reports-row__retention {
  font-size: 0.75rem;
  color: var(--color-muted, #666666);
  white-space: nowrap;
  flex-shrink: 0;
}

.reports-row__important {
  min-height: 44px;
  padding: 0 0.75rem;
  background: transparent;
  border: 1px solid var(--color-border, #dddddd);
  color: var(--color-text, #222222);
  border-radius: var(--radius, 4px);
  font-size: 0.78rem;
  cursor: pointer;
  flex-shrink: 0;
}

.reports-row__important[aria-pressed="true"] {
  border-color: var(--color-accent-dark, #2d7d9a);
  color: var(--color-accent-dark, #2d7d9a);
  font-weight: 600;
}

/* ── Trash button (44px touch target) ────────────────────────────── */
.reports-row__trash {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-delete-icon);
  border-radius: var(--control-radius);
  flex-shrink: 0;
  font-size: var(--text-xl);
  transition: color var(--duration-fast) var(--easing-standard),
              background var(--duration-fast) var(--easing-standard);
}

.reports-row__trash:hover,
.reports-row__trash:focus-visible {
  color: var(--color-delete-icon-hover);
  background: var(--color-row-hover);
}

/* ── Inline confirm strip ─────────────────────────────────────────── */
.reports-row__confirm {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 0.6rem);
  padding: 0.35rem 0;
}

.reports-confirm-text {
  font-size: 0.82rem;
  color: var(--color-muted, #666666);
}

.reports-confirm-delete {
  padding: 0.25em 0.75em;
  background: transparent;
  border: var(--border-width) solid var(--color-delete-icon-hover);
  color: var(--color-delete-icon-hover);
  border-radius: var(--control-radius);
  font-size: var(--text-sm);
  cursor: pointer;
}

.reports-confirm-delete:hover {
  background: var(--color-delete-icon-hover);
  color: var(--color-surface);
}

.reports-confirm-cancel {
  padding: 0.25em 0.75em;
  background: transparent;
  border: var(--border-width) solid var(--color-border);
  color: var(--color-text);
  border-radius: var(--control-radius);
  font-size: var(--text-sm);
  cursor: pointer;
}

.reports-confirm-cancel:hover {
  background: var(--color-row-hover);
  color: var(--color-heading);
}

/* ── Content frame ────────────────────────────────────────────────── */
.reports-content-frame {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-card, #dddddd);
  border-radius: var(--radius-card, 6px);
  padding: var(--space-lg, 1.5rem);
  margin-top: var(--space-sm, 0.6rem);
  overflow-x: auto;
}

/* ── Back button ──────────────────────────────────────────────────── */
.reports-back-btn {
  background: transparent;
  border: none;
  color: var(--color-accent-dark);
  font-size: var(--text-base);
  cursor: pointer;
  padding: 0;
  margin-bottom: var(--space-sm);
  display: block;
}

.reports-back-btn:hover,
.reports-back-btn:focus-visible {
  color: var(--color-cost);
  text-decoration: underline;
}
"""
