"""Workflow model-governance CSS for the Dadaia Workspace Panel (v0.1.45 redesign).

Styles the inline per-step model picker that now lives inside each workflow diagram
card's expand — the segmented codex/pi harness control, the harness-filtered profile
dropdown, the concrete-model readout, the default-vs-effective diff + reset — plus the
single section-header Validate / Save toolbar and its banner. Fully token-anchored (no
ad-hoc CSS literals in control rules); all values come from tokens.css.
"""

WORKFLOW_POLICY_CSS: str = """
/* ── Section-header Validate / Save toolbar + banner ──────────────────────── */
.wfp-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-top: var(--space-sm);
}
.wfp-validate-btn,
.wfp-save-btn {
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  padding: var(--control-pad-y) var(--control-pad-x);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-accent);
  background: var(--color-surface);
  color: var(--color-heading);
  transition: background var(--duration-fast) var(--easing-standard),
              border-color var(--duration-fast) var(--easing-standard);
}
.wfp-save-btn {
  background: var(--color-accent);
}
.wfp-validate-btn:hover,
.wfp-save-btn:hover {
  background: var(--color-card-hover);
}
.wfp-save-btn:hover {
  background: var(--color-accent-secondary);
}
.wfp-validate-btn:focus-visible,
.wfp-save-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
.wfp-banner {
  flex: 1 1 100%;
  margin: var(--space-2xs) 0 0 0;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  border: var(--border-width) solid var(--color-border);
}
.wfp-banner--info { background: var(--color-primary-bg, #f0fbf7); color: var(--color-text); }
.wfp-banner--ok { background: var(--color-badge-active-bg, #d4f5e5); color: var(--color-badge-active-text, #1f7a46); }
.wfp-banner--error { background: var(--color-warning-bg, #ddd9ab); color: var(--color-cost, #633d2e); }

/* ── Inline per-step model picker (hydrated by workflow-policy.js) ─────────── */
.wfp-picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  width: 100%;
}
.wfp-picker-controls {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.wfp-picker-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  font-size: var(--text-xs);
}
.wfp-picker-model {
  font-family: var(--font-mono);
  color: var(--color-heading);
}
.wfp-effort { color: var(--color-muted); }
.wfp-diff { font-size: var(--text-xs); color: var(--color-accent-dark, #2d7d9a); }
.wfp-diff--none { color: var(--color-muted); }
.wfp-diff-harness { font-size: var(--text-xs); color: var(--color-accent-dark, #2d7d9a); }

.wfp-seg {
  display: inline-flex;
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
.wfp-seg-btn {
  border: 0;
  background: var(--color-surface);
  padding: var(--space-2xs) var(--space-sm);
  cursor: pointer;
  font: inherit;
  font-size: var(--text-xs);
  color: var(--color-text);
  transition: background var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard);
}
.wfp-seg-btn:hover {
  background: var(--color-row-hover);
}
.wfp-seg-btn--active {
  background: var(--color-accent);
  color: var(--color-heading);
  font-weight: var(--font-weight-bold);
}
.wfp-seg-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: calc(-1 * var(--focus-ring-offset));
}
.wfp-profile-select {
  max-width: 18rem;
  font: inherit;
  font-size: var(--text-sm);
  padding: var(--space-2xs) var(--space-xs);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}
.wfp-profile-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
.wfp-reset-btn {
  font: inherit;
  font-size: var(--text-2xs);
  cursor: pointer;
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--control-radius);
  border: var(--border-width) solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-muted);
  transition: background var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard);
}
.wfp-reset-btn:hover:not([disabled]) {
  background: var(--color-row-hover);
  color: var(--color-text);
}
.wfp-reset-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}
.wfp-reset-btn[disabled] { opacity: 0.4; cursor: default; }
"""
