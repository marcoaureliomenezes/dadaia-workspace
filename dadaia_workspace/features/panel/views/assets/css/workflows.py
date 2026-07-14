"""Styles for the governed workflow catalog cards."""

WORKFLOWS_CSS: str = """
.section-meta {
  margin: 0;
  color: var(--color-muted);
  font-size: var(--text-sm);
  line-height: var(--line-height-snug);
}

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

.dadaia-wf-card:hover,
.dadaia-wf-card[open] {
  border-color: var(--color-accent, #9cddc8);
  box-shadow: var(--shadow-card-hover);
}

.dadaia-wf-card:hover {
  transform: translateY(var(--lift-hover));
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
  letter-spacing: 0;
  line-height: 1.25;
  color: var(--color-heading);
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dadaia-wf-step-count,
.dadaia-wf-badge {
  flex-shrink: 0;
  white-space: nowrap;
}

.dadaia-wf-step-count {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-muted);
}

.dadaia-wf-badge {
  border-radius: var(--radius-pill);
  padding: 0.15rem 0.55rem;
  font-size: var(--text-2xs);
  font-weight: 600;
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-cost, #633d2e);
  border: var(--border-width) solid var(--color-accent, #9cddc8);
}

.dadaia-wf-badge--partial {
  background: var(--color-warning-bg, #ddd9ab);
  border-color: var(--color-accent-secondary, #bfd8ad);
}

.dadaia-wf-badge--unavailable {
  background: var(--color-row-hover);
  color: var(--color-muted);
  border-color: var(--color-border);
}

.dadaia-wf-purpose,
.dadaia-wf-step-purpose,
.dadaia-wf-step-gatenote,
.dadaia-wf-empty-steps {
  margin: 0;
  color: var(--color-text);
}

.dadaia-wf-purpose {
  font-size: var(--text-base);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

.dadaia-wf-flux {
  margin: 0 0 var(--space-md);
  background: var(--color-bg);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  overflow-x: auto;
}

.dadaia-wf-flux-cap {
  margin: 0 0 var(--space-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0;
  text-transform: uppercase;
  color: var(--color-muted);
}

.dadaia-wf-diagram-svg svg {
  display: block;
  max-width: 100%;
  height: auto;
}

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
  width: 1.75rem;
  height: 1.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary-bg, #f0fbf7);
  color: var(--color-heading);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
}

.dadaia-wf-step-label {
  flex: 1 1 auto;
  min-width: 8rem;
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-heading);
}

.dadaia-wf-step-role,
.dadaia-wf-step-badge {
  font-size: var(--text-xs);
  white-space: nowrap;
}

.dadaia-wf-step-role {
  font-family: var(--font-mono);
  color: var(--color-muted);
}

.dadaia-wf-step-badge {
  border-radius: var(--radius-pill);
  padding: 0.12rem 0.45rem;
  font-weight: 600;
}

.dadaia-wf-step-badge--worker {
  color: var(--color-heading);
  background: var(--color-primary-bg, #f0fbf7);
}

.dadaia-wf-step-badge--gate {
  color: var(--color-cost, #633d2e);
  background: var(--color-warning-bg, #ddd9ab);
}

.dadaia-wf-step-purpose {
  margin-top: var(--space-sm);
  line-height: 1.45;
}

.dadaia-wf-step-model {
  display: grid;
  grid-template-columns: minmax(5rem, auto) minmax(0, 1fr);
  gap: var(--space-sm);
  align-items: center;
  margin-top: var(--space-sm);
}

.dadaia-wf-step-model-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-muted);
}

.wf-step-picker-default {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.dadaia-wf-step-gatenote,
.dadaia-wf-empty-steps {
  margin-top: var(--space-sm);
  font-size: var(--text-sm);
  color: var(--color-muted);
}

@media (max-width: 700px) {
  .dadaia-wf-catalog {
    grid-template-columns: 1fr;
  }

  .dadaia-wf-card-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .dadaia-wf-card-title {
    flex-basis: 100%;
    white-space: normal;
  }

  .dadaia-wf-step-model {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .dadaia-wf-card {
    transition: none;
  }

  .dadaia-wf-card:hover {
    transform: none;
  }
}
"""
