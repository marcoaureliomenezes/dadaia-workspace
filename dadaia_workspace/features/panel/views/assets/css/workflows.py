"""Workflow card grid CSS for the Dadaia Workspace Panel.

PR3-16 (FE): Replaces the 2-pane layout CSS with a full-width card grid.
PR3-17 (FE): Will extend this module with detail-view, DAG skeleton,
             and placeholder agent node styles.

Design (per design report, SPEC §7.5, Surface D3):
  - Full-width card grid, 2-col >=768px, 1-col below
  - Cards: name heading, description clamped, agent chips, stage_count badge
  - "View DAG ->" CTA per card
  - Token-only colour values (var(--color-*)) for full theme support
  - Hover/focus-visible affordances for keyboard accessibility (WCAG 2.1 AA)
"""

WORKFLOWS_CSS: str = """
/* ── Workflows card grid ──────────────────────────────────────────── */
#workflows-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 767px) {
  #workflows-grid { grid-template-columns: 1fr; }
}

/* Workflow card */
.workflow-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  transition: box-shadow 0.15s, border-color 0.15s;
}
.workflow-card:hover {
  border-color: var(--color-accent, #9cddc8);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}
.workflow-card:focus-within {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
}

/* Card header: name + stage badge on same row */
.workflow-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
}
.workflow-card__name {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-heading);
  margin: 0;
  line-height: 1.3;
}

/* Stage count badge */
.workflow-stage-badge {
  flex-shrink: 0;
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-cost, #633d2e);
  border: 1px solid var(--color-accent, #9cddc8);
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.15rem 0.55rem;
  white-space: nowrap;
  font-family: var(--font-mono);
}

/* Description: clamp to 2 lines */
.workflow-card__description {
  font-size: 0.88rem;
  color: var(--color-text);
  line-height: 1.45;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.workflow-card__description--empty {
  color: var(--color-muted);
  font-style: italic;
}

/* Agent chips row */
.workflow-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.workflow-agent-chip {
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  border: none;
  padding: 0.18rem 0.55rem;
  border-radius: 10px;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  font-weight: 500;
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.workflow-agent-chip--none {
  background: var(--color-row-hover);
  color: var(--color-muted);
  font-style: italic;
}

/* Card footer: CTA button */
.workflow-card__footer {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
}

/* "View DAG ->" CTA */
.workflow-dag-cta {
  background: none;
  border: none;
  color: var(--color-accent-secondary, #bfd8ad);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 0.2rem 0;
  transition: color 0.1s;
}
.workflow-dag-cta:hover {
  color: var(--color-cost, #633d2e);
  text-decoration: underline;
}
.workflow-dag-cta:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
  border-radius: 2px;
}

/* ── Skeleton card state ─────────────────────────────────────────── */
.workflow-card--skeleton {
  pointer-events: none;
}

/* ── Error / empty states ────────────────────────────────────────── */
.workflows-error {
  grid-column: 1 / -1;
  padding: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-text);
}

/* ── Legacy 2-pane classes (kept for PR3-17 detail view; will be removed post-PR3-17) */
.workflows-pane {
  display: contents;
}
.workflows-list {
  display: none;
}
.workflows-detail {
  display: none;
}
.workflow-list-item { display: none; }
.workflow-item-name { display: none; }
.workflow-item-source { display: none; }
.workflows-detail-empty { display: none; }
.workflow-detail-name { display: none; }
.workflow-detail-source { display: none; }
.workflow-detail-description { display: none; }
.workflow-diagram { display: none; }
.workflow-agent-chips { display: none; }
"""
