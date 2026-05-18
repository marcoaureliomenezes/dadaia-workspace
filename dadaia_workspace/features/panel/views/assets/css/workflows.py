"""Workflow card and DAG CSS for the Dadaia Workspace Panel.

Phase 1 (SE): 2-pane layout, workflow list, workflow detail, and SVG diagram
styles extracted from _assets.py PANEL_CSS. FE will replace / extend this with
the card grid, detail view, DAG skeleton, and placeholder node styles in Phase 5.
"""

WORKFLOWS_CSS: str = """
/* ── Workflows 2-pane layout ─────────────────────── */
.workflows-pane {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 640px) {
  .workflows-pane { grid-template-columns: 1fr; }
  .workflows-detail { display: none; }
  .workflows-detail.visible { display: block; }
}

/* Left list */
.workflows-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  overflow: hidden;
}
.workflow-list-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.65rem var(--space-md);
  font-size: 0.9rem;
  font-family: inherit;
  background: none;
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.1s;
}
.workflow-list-item:last-child { border-bottom: none; }
.workflow-list-item:hover { background: var(--color-row-hover); }
.workflow-list-item.selected {
  background: var(--color-primary-bg, #f0fbf7);
  border-left: 3px solid var(--color-accent, #9cddc8);
  color: var(--color-heading);
  font-weight: 600;
}
.workflow-list-item:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: -2px;
}
.workflow-item-name { display: block; font-size: 0.88rem; font-weight: 600; }
.workflow-item-source { display: block; font-size: 0.75rem; color: var(--color-muted); font-family: var(--font-mono); margin-top: 0.1rem; }

/* Right detail panel */
.workflows-detail {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  padding: var(--space-md);
  min-height: 240px;
}
.workflows-detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--color-muted);
  font-size: 0.9rem;
  text-align: center;
}
.workflow-detail-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
  margin-bottom: var(--space-xs);
}
.workflow-detail-source {
  font-size: 0.78rem;
  color: var(--color-muted);
  font-family: var(--font-mono);
  margin-bottom: var(--space-sm);
}
.workflow-detail-description {
  font-size: 0.9rem;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}
.workflow-detail-description.no-desc { color: var(--color-muted); font-style: italic; }

/* SVG stepper diagram */
.workflow-diagram {
  margin-top: var(--space-md);
  overflow-x: auto;
}
.workflow-diagram svg { display: block; }

/* Agent chips (detail pane) */
.workflow-agent-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: var(--space-sm); }
.workflow-agent-chip {
  background: var(--color-accent, #9cddc8);
  color: #222;
  border: none;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  cursor: pointer;
  font-family: inherit;
}
.workflow-agent-chip:hover { background: var(--color-accent-secondary, #bfd8ad); }
.workflow-agent-chip:focus { outline: 2px solid var(--color-cost, #633d2e); outline-offset: 2px; }
"""
