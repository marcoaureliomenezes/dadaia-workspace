"""Workflow card grid + detail view CSS for the Dadaia Workspace Panel.

PR3-16 (FE): Replaces the 2-pane layout CSS with a full-width card grid.
PR3-17 (FE): Extends with detail-view, DAG container, DAG loading skeleton,
             placeholder agent node styles, back-button, error inline, and
             forward-compatible data-status rules for all 4 node states.

Design (per design report, SPEC §7.5, Surface D3):
  - Full-width card grid, 2-col >=768px, 1-col below
  - Cards: name heading, description clamped, agent chips, stage_count badge
  - "View DAG ->" CTA per card
  - Detail view: full-width, replaces grid in place; back button; DAG container
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
  color: var(--color-accent-dark, #2d7d9a);
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

/* ── Legacy 2-pane classes (zeroed out; detail view uses .workflow-detail-view) */
.workflows-pane { display: contents; }
.workflows-list { display: none; }
.workflows-detail { display: none; }
.workflow-list-item { display: none; }
.workflow-item-name { display: none; }
.workflow-item-source { display: none; }
.workflows-detail-empty { display: none; }
.workflow-detail-name { display: none; }
.workflow-detail-source { display: none; }
.workflow-detail-description { display: none; }
.workflow-diagram { display: none; }
.workflow-agent-chips { display: none; }

/* ── Detail view (full-width, replaces grid in place) ─────────────── */
.workflow-detail-view {
  width: 100%;
}

/* ── Back button ─────────────────────────────────────────────────── */
.workflow-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 0.3rem 0;
  margin-bottom: var(--space-md);
  transition: color 0.1s;
}
.workflow-back-btn:hover {
  color: var(--color-cost, #633d2e);
  text-decoration: underline;
}
.workflow-back-btn:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
  border-radius: 2px;
}

/* ── Detail header ───────────────────────────────────────────────── */
.workflow-detail-header {
  margin-bottom: var(--space-md);
}
.workflow-detail-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-heading);
  margin: 0 0 0.25rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.workflow-detail-version {
  font-size: 0.72rem;
  font-weight: 600;
  font-family: var(--font-mono);
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-cost, #633d2e);
  border: 1px solid var(--color-accent, #9cddc8);
  border-radius: 10px;
  padding: 0.15rem 0.55rem;
  white-space: nowrap;
}
.workflow-detail-description {
  font-size: 0.88rem;
  color: var(--color-text);
  margin: 0;
  line-height: 1.5;
}

/* ── Detail chips section ────────────────────────────────────────── */
.workflow-detail-agents {
  margin-bottom: var(--space-md);
}
.workflow-detail-agents-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.4rem;
}
.workflow-detail-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.workflow-detail-chip {
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  border: none;
  padding: 0.22rem 0.65rem;
  border-radius: 10px;
  font-size: 0.78rem;
  font-family: var(--font-mono);
  font-weight: 500;
  white-space: nowrap;
}

/* ── Stages table ────────────────────────────────────────────────── */
.workflow-stages-section {
  margin-bottom: var(--space-md);
}
.workflow-stages-toggle {
  background: none;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 0.2rem 0;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.workflow-stages-toggle:hover {
  color: var(--color-cost, #633d2e);
  text-decoration: underline;
}
.workflow-stages-toggle:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
  border-radius: 2px;
}
.workflow-stages-table-wrap {
  margin-top: 0.5rem;
  overflow-x: auto;
}
.workflow-stages-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  color: var(--color-text);
}
.workflow-stages-table th {
  text-align: left;
  font-weight: 600;
  color: var(--color-muted);
  padding: 0.3rem 0.6rem;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.workflow-stages-table td {
  padding: 0.3rem 0.6rem;
  border-bottom: 1px solid var(--color-border);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  vertical-align: top;
}
.workflow-stages-table tr:last-child td {
  border-bottom: none;
}

/* ── DAG container ───────────────────────────────────────────────── */
.workflow-dag-section {
  margin-bottom: var(--space-md);
}
.workflow-dag-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.5rem;
}
.workflow-dag {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-md);
  overflow-x: auto;
  line-height: 1;
}
.workflow-dag svg {
  display: block;
  max-width: 100%;
  height: auto;
}

/* ── DAG loading skeleton ────────────────────────────────────────── */
.workflow-detail-skeleton {
  width: 100%;
}
.workflow-dag-skeleton {
  display: flex;
  gap: var(--space-md);
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-md);
  overflow: hidden;
}
.dag-node-placeholder {
  flex-shrink: 0;
  width: 140px;
  height: 40px;
  background: var(--color-border, #d4e6de);
  border-radius: 6px;
}
.dag-edge-placeholder {
  flex: 1;
  height: 2px;
  background: var(--color-border, #d4e6de);
  border-radius: 1px;
}

/* ── Skeleton pulse animation ────────────────────────────────────── */
@keyframes skeleton-pulse {
  0%   { opacity: 1; }
  50%  { opacity: 0.45; }
  100% { opacity: 1; }
}
.skeleton-pulse {
  animation: skeleton-pulse 1.4s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-pulse { animation: none; }
}

/* ── Detail skeleton header ──────────────────────────────────────── */
.workflow-detail-skeleton .skeleton-line {
  display: block;
  height: 1em;
  background: var(--color-border, #d4e6de);
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

/* ── Inline error state ──────────────────────────────────────────── */
.workflow-detail-error {
  padding: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-text);
}
.workflow-detail-error strong {
  color: var(--color-cost, #633d2e);
}

/* ── DAG node states (forward-compatible data-status hooks) ──────── */
/*
 * These CSS rules target the data-status attribute on .dag-node elements
 * rendered by dag.py. They are intentionally forward-compatible so future PRs
 * can light up live workflow run states without additional CSS work.
 *
 * States defined by dag.py (emitted as data-status="pending" on every node):
 *   pending  — default, node has not run yet
 *   running  — node is currently executing (future: ws/SSE push)
 *   done     — node completed successfully (future: run-aware overlay)
 *   failed   — node completed with failure (future: run-aware overlay)
 */
.dag-node[data-status="pending"] rect {
  /* Subtle treatment: inherit base node style; opacity dial */
  opacity: 0.85;
}
.dag-node[data-status="running"] rect {
  fill: var(--color-primary-bg, #e6f4ff);
  stroke: var(--color-accent, #9cddc8);
  stroke-width: 2.5;
}
.dag-node[data-status="running"] text.stage-id {
  fill: var(--color-heading);
  font-weight: 700;
}
.dag-node[data-status="done"] rect {
  fill: var(--color-primary-bg, #f0fbf7);
  stroke: var(--color-accent-secondary, #bfd8ad);
  stroke-width: 2;
}
.dag-node[data-status="done"] text.stage-id {
  fill: var(--color-heading);
}
.dag-node[data-status="failed"] rect {
  fill: #fff0f0;
  stroke: var(--color-cost, #633d2e);
  stroke-width: 2;
}
.dag-node[data-status="failed"] text.stage-id {
  fill: var(--color-cost, #633d2e);
  font-weight: 700;
}

/* ── DAG viewport + toolbar ──────────────────────────────────────────── */
.workflow-dag-viewport {
  overflow: hidden;
  min-height: 280px;
  position: relative;
  border: 1px solid var(--color-border, #d4e6de);
  border-radius: 0 0 var(--radius-card, 6px) var(--radius-card, 6px);
  background: var(--color-surface, #ffffff);
}
.workflow-dag-viewport.dag-zoomed {
  cursor: grab;
}
.workflow-dag-viewport.dag-zoomed:active {
  cursor: grabbing;
}
.workflow-dag-viewport .workflow-dag {
  transform-origin: top left;
  transition: transform var(--duration-fast, 120ms) var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
  padding: var(--space-md, 1rem);
  overflow: visible;
  border: none;
  border-radius: 0;
  background: transparent;
}
@media (prefers-reduced-motion: reduce) {
  .workflow-dag-viewport .workflow-dag { transition: none; }
}
.dag-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.35rem;
  background: var(--color-th-bg, #eeeeee);
  border: 1px solid var(--color-border, #d4e6de);
  border-bottom: none;
  border-radius: var(--radius-card, 6px) var(--radius-card, 6px) 0 0;
  padding: 0.35rem 0.75rem;
}
.dag-zoom-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border, #d4e6de);
  border-radius: var(--radius, 4px);
  background: var(--color-surface, #ffffff);
  color: var(--color-text, #222222);
  font-size: 1rem;
  cursor: pointer;
  font-family: var(--font-mono, ui-monospace, monospace);
  padding: 0;
  line-height: 1;
}
.dag-zoom-btn:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
  border-color: var(--color-accent-dark, #2d7d9a);
}
.dag-zoom-btn:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
.dag-zoom-fit {
  font-family: var(--font-stack, -apple-system, sans-serif);
  font-size: 0.78rem;
  width: auto;
  padding: 0 0.5rem;
}
.dag-zoom-display {
  width: 52px;
  text-align: center;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  color: var(--color-muted, #666666);
  user-select: none;
}

/* ── Workflow Run button + status badges (T-WH-17) ─────────────────────── */
.workflow-run-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.75rem;
  border: 1px solid var(--color-accent-dark, #2d7d9a);
  border-radius: var(--radius, 4px);
  background: var(--color-surface, #ffffff);
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.82rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.workflow-run-btn:hover {
  background: var(--color-accent-dark, #2d7d9a);
  color: #ffffff;
}
.workflow-run-btn:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
.workflow-run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.workflow-run-badge {
  display: inline-block;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius, 4px);
  font-family: var(--font-mono, ui-monospace, monospace);
}
.workflow-run-badge--started {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}
.workflow-run-badge--running {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}
.workflow-run-badge--error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
"""
