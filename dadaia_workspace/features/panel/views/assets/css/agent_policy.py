"""Sub-agents tab CSS for the Dadaia Workspace Panel (v0.1.65 FR8).

Styles the L1 agent model-governance roster table (per-agent model + effort pickers),
the template selector + explicit Apply toolbar, the status banner, and the post-apply
pop-up carrying the G-2 per-harness pickup instructions. Fully token-anchored — one
control language with the existing workflow-policy pickers; all values come from
tokens.css (no ad-hoc CSS literals in control rules).
"""

AGENT_POLICY_CSS: str = """
/* ── Section-header template selector + Apply toolbar + banner ─────────────── */
.ap-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-top: var(--space-sm);
}
.ap-template-select,
.ap-model-select,
.ap-effort-select {
  font: inherit;
  font-size: var(--text-sm);
  padding: var(--space-2xs) var(--space-xs);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}
.ap-template-select:focus-visible,
.ap-model-select:focus-visible,
.ap-effort-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
.ap-apply-btn {
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  padding: var(--control-pad-y) var(--control-pad-x);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-heading);
  transition: background var(--duration-fast) var(--easing-standard),
              border-color var(--duration-fast) var(--easing-standard);
}
.ap-apply-btn:hover {
  background: var(--color-accent-secondary);
}
.ap-apply-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
.ap-banner {
  margin: var(--space-sm) 0 0 0;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  border: var(--border-width) solid var(--color-border);
}
.ap-banner--info { background: var(--color-primary-bg, #f0fbf7); color: var(--color-text); }
.ap-banner--ok { background: var(--color-badge-active-bg, #d4f5e5); color: var(--color-badge-active-text, #1f7a46); }
.ap-banner--error { background: var(--color-warning-bg, #ddd9ab); color: var(--color-cost, #633d2e); }

/* ── Roster table ──────────────────────────────────────────────────────────── */
.ap-roster-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-sm);
  font-size: var(--text-sm);
}
.ap-roster-table th {
  text-align: left;
  padding: var(--space-2xs) var(--space-sm);
  color: var(--color-muted);
  font-weight: var(--font-weight-semibold);
  border-bottom: var(--border-width) solid var(--color-border);
}
.ap-roster-table td {
  padding: var(--space-2xs) var(--space-sm);
  border-bottom: var(--border-width) solid var(--color-border);
  vertical-align: middle;
}
.ap-roster-table tr:hover td {
  background: var(--color-row-hover);
}
.ap-agent-name {
  font-family: var(--font-mono);
  color: var(--color-heading);
}
.ap-source-badge {
  display: inline-block;
  padding: 0 var(--space-xs);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  background: var(--color-chip-memory-bg, var(--color-surface));
  border: var(--border-width) solid var(--color-accent);
  color: var(--color-text);
}
.ap-source-badge--override {
  background: var(--color-accent);
  color: var(--color-heading);
  font-weight: var(--font-weight-semibold);
}

/* ── Post-apply pop-up (G-2 per-harness pickup instructions) ───────────────── */
.ap-popup {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  z-index: var(--z-modal, 100);
}
.ap-popup[hidden] { display: none; }
.ap-popup-card {
  background: var(--color-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card-hover);
  max-width: 34rem;
  width: calc(100% - 2 * var(--space-lg));
  max-height: 80vh;
  overflow: auto;
  padding: var(--space-lg);
}
.ap-popup-card h3 {
  margin-top: 0;
  color: var(--color-heading);
}
.ap-popup-instructions {
  margin: var(--space-sm) 0;
  padding-left: var(--space-lg);
}
.ap-popup-instructions li {
  margin-bottom: var(--space-xs);
}
.ap-popup-rerendered {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  background: var(--color-primary-bg, #f0fbf7);
  border-radius: var(--radius);
  padding: var(--space-xs) var(--space-sm);
  max-height: 12rem;
  overflow: auto;
  margin: var(--space-sm) 0;
}
.ap-popup-close-btn {
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  padding: var(--control-pad-y) var(--control-pad-x);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-accent);
  background: var(--color-surface);
  color: var(--color-heading);
}
.ap-popup-close-btn:hover {
  background: var(--color-card-hover);
}
.ap-popup-close-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
"""
