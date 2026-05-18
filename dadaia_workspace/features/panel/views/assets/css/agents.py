"""Agent card CSS for the Dadaia Workspace Panel.

Phase 1 (SE): placeholder card, agents-grid, agent-card, and related styles
extracted from _assets.py PANEL_CSS. FE will replace / extend this with the
full collapsed + expanded card design in Phase 4.
"""

AGENTS_CSS: str = """
/* ── Agents placeholder card ─────────────────────── */
.placeholder-card {
  background: var(--color-placeholder-bg);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-xl);
  text-align: center;
  color: var(--color-muted);
  max-width: 480px;
}
.placeholder-card .placeholder-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-muted);
  margin-bottom: var(--space-sm);
}
.placeholder-card .placeholder-body { font-size: 0.88rem; }

/* ── agents-grid ─────────────────────────────────── */
.card-grid.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
}
.agent-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  background: var(--color-surface);
}
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
}
.agent-card-header h3 { margin: 0; font-size: 1rem; color: var(--color-cost, #633d2e); }
.agent-model { font-size: 0.85rem; color: #666; font-family: ui-monospace, monospace; }
.agent-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin: 0.75rem 0;
  font-size: 0.9rem;
}
.agent-metric .label { display: block; font-size: 0.7rem; text-transform: uppercase; color: #666; }
.agent-metric .value { display: block; font-weight: 600; }
.agent-cost-unknown { color: #999; font-style: italic; }
.agent-suspect-badge {
  background: var(--color-alert, #f7af63);
  color: #3d2a00; /* dark on amber — WCAG AA contrast ~6.3:1 */
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}
.context-breakdown { margin: 0.5rem 0; }
.context-breakdown-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  margin: 0.25rem 0;
}
.context-bar { flex: 1; height: 0.5rem; background: #eee; border-radius: 4px; overflow: hidden; }
.context-bar-fill { height: 100%; background: var(--color-accent, #9cddc8); }
.warning-banner {
  padding: 0.75rem 1rem;
  background: var(--color-warning-bg, #ddd9ab);
  color: #3d3600;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.sessions-drilldown { margin-top: 0.5rem; }
.sessions-drilldown table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.sessions-drilldown th,
.sessions-drilldown td { padding: 0.25rem 0.5rem; text-align: left; border-bottom: 1px solid #eee; }
.sessions-drilldown button[aria-expanded] {
  background: none;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0.25rem 0;
  font-family: inherit;
  text-decoration: underline;
}
.sessions-drilldown button[aria-expanded]:hover { color: var(--color-cost, #633d2e); }
.sessions-drilldown button[aria-expanded]:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
}
.error-state { color: #c0392b; font-size: 0.9rem; }
"""
