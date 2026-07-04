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
/* The grid container is a vertical stack of lifecycle-phase groups; the
   2-column card layout lives inside each group's .workflow-phase-cards. */
#workflows-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg, 1.5rem);
  align-items: stretch;
}

/* ── Lifecycle-phase group ────────────────────────────────────────── */
.workflow-phase-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.workflow-phase-heading {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
  margin: 0;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-heading);
}
.workflow-phase-count {
  font-size: 0.72rem;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  color: var(--color-muted);
  font-family: var(--font-mono);
}
.workflow-phase-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 767px) {
  .workflow-phase-cards { grid-template-columns: 1fr; }
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

/* ── Subsection meta description (v0.1.59 / FR4) ─────────────────────────────
   The dadaia-workflows subsection header emits <p class="section-meta"> (the
   "Every dadaia-workflow: purpose, step sequence …" line) which previously had no
   rule and rendered as unstyled body text. Give it the same muted-description
   treatment as a .section-header <p> so the workflows subsection reads with the
   consistent title→description hierarchy of the other tabs. Token-anchored. */
.section-meta {
  margin: 0;
  color: var(--color-muted);
  font-size: var(--text-sm);
  line-height: var(--line-height-snug);
}

/* ── dadaia-workflow catalog cards (v0.1.45 / T-45-03) ───────────────── */
/* Big, scannable, expandable diagram cards in a responsive grid. Each card is a
   native <details> disclosure: server-rendered, CSP-clean, no client script, not a
   <dialog>. The collapsed <summary> face carries the header, purpose, the enhanced
   server-SVG fluxogram, and a compact step-chain; the expanded body carries the full
   per-step detail. Token-anchored (no ad-hoc literals). */
.dadaia-wf-catalog {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--grid-card-min-w), 1fr));
  gap: var(--space-md);
  align-items: start;
}
.dadaia-wf-card {
  background: var(--color-surface);
  border: var(--border-width) solid var(--color-border-card);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  overflow: hidden;
  box-shadow: var(--shadow-card-rest);
  transition: box-shadow var(--duration-normal) var(--easing-standard),
              border-color var(--duration-normal) var(--easing-standard),
              transform var(--duration-normal) var(--easing-decelerate);
}
.dadaia-wf-card:hover {
  border-color: var(--color-accent, #9cddc8);
  box-shadow: var(--shadow-card-hover);
  transform: translateY(var(--lift-hover));
}
.dadaia-wf-card[open] {
  border-color: var(--color-accent, #9cddc8);
  box-shadow: var(--shadow-card-hover);
}
@media (prefers-reduced-motion: reduce) {
  .dadaia-wf-card { transition: box-shadow var(--duration-normal) var(--easing-standard),
                                border-color var(--duration-normal) var(--easing-standard); }
  .dadaia-wf-card:hover { transform: none; }
}
.dadaia-wf-card[aria-disabled="true"] {
  opacity: 0.6;
}
.dadaia-wf-card-summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.dadaia-wf-card-summary::-webkit-details-marker {
  display: none;
}
.dadaia-wf-card-summary:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
  border-radius: var(--radius);
}
.dadaia-wf-card-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: nowrap;
}
.dadaia-wf-card-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
  color: var(--color-heading);
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dadaia-wf-step-count {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-muted);
  white-space: nowrap;
}
.dadaia-wf-badge {
  flex-shrink: 0;
  border-radius: var(--radius-pill);
  padding: 0.15rem 0.55rem;
  font-size: var(--text-2xs);
  font-weight: 600;
  white-space: nowrap;
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-cost, #633d2e);
  border: var(--border-width) solid var(--color-accent, #9cddc8);
}
.dadaia-wf-badge--partial {
  background: var(--color-warning-bg, #ddd9ab);
  color: var(--color-cost, #633d2e);
  border-color: var(--color-accent-secondary, #bfd8ad);
}
.dadaia-wf-badge--unavailable {
  background: var(--color-row-hover);
  color: var(--color-muted);
  border-color: var(--color-border);
}
.dadaia-wf-purpose {
  margin: 0;
  font-size: var(--text-base);
  line-height: 1.45;
  color: var(--color-text);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dadaia-wf-flux {
  margin: 0 0 var(--space-md) 0;
  background: var(--color-bg);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  overflow-x: auto;
}
.dadaia-wf-flux-cap {
  margin: 0 0 var(--space-sm) 0;
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--color-muted);
}
.dadaia-wf-diagram-svg svg {
  display: block;
  max-width: 100%;
  height: auto;
}
.dadaia-wf-step-chain {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dadaia-wf-expand-hint {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-accent-dark);
}
.dadaia-wf-card[open] .dadaia-wf-expand-hint {
  color: var(--color-cost, #633d2e);
}
.dadaia-wf-detail {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: var(--border-width) solid var(--color-border);
}
/* One formatted CARD per step — clean typographic hierarchy, no monospace comma-dump. */
.dadaia-wf-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
.dadaia-wf-step {
  background: var(--color-bg);
  border: var(--border-width) solid var(--color-border);
  border-left: var(--border-width-accent) solid var(--color-accent, #9cddc8);
  border-radius: var(--radius-card);
  padding: var(--space-sm) var(--space-md);
}
.dadaia-wf-step--gate {
  border-left-color: var(--color-alert, #f7af63);
}
.dadaia-wf-step-head {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.dadaia-wf-step-order {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.5rem;
  height: 1.5rem;
  padding: 0 0.35rem;
  border-radius: var(--radius-pill);
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
}
.dadaia-wf-step-label {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--color-heading);
}
.dadaia-wf-step-role {
  font-size: var(--text-xs);
  color: var(--color-muted);
}
.dadaia-wf-step-badge {
  margin-left: auto;
  flex-shrink: 0;
  border-radius: var(--radius-pill);
  padding: 0.1rem 0.55rem;
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.dadaia-wf-step-badge--worker {
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-accent-dark);
  border: var(--border-width) solid var(--color-accent, #9cddc8);
}
.dadaia-wf-step-badge--gate {
  background: var(--color-warning-bg, #ddd9ab);
  color: var(--color-cost, #633d2e);
  border: var(--border-width) solid var(--color-alert, #f7af63);
}
.dadaia-wf-step-purpose {
  margin: var(--space-xs) 0 0 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.5;
}
.dadaia-wf-step-gatenote {
  margin: var(--space-sm) 0 0 0;
  font-size: var(--text-xs);
  font-style: italic;
  color: var(--color-muted);
}
/* Inline per-step model picker — a labelled control, hydrated by workflow-policy.js. */
.dadaia-wf-step-model {
  margin-top: var(--space-sm);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.dadaia-wf-step-model-label {
  flex-shrink: 0;
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-muted);
}
.wf-step-picker {
  flex: 1 1 auto;
  min-width: 0;
}
.wf-step-picker-default {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text);
}
.dadaia-wf-empty-steps {
  margin: 0;
  font-style: italic;
  color: var(--color-muted);
  font-size: var(--text-md);
}
@media (max-width: 640px) {
  .dadaia-wf-catalog { grid-template-columns: 1fr; }
}
"""
