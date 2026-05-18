"""Agent card CSS for the Dadaia Workspace Panel.

PR3-10 (FE): Full collapsed card design.
  - 2-column grid at >=1024px, 1-column below
  - Collapsed card: status badge, name, description (2-line clamp), 3-stat row,
    skills chips (first 2 + "+N more"), expand chevron
  - Status badge variants: active (green dot) / inactive (gray)
  - Active card: 3px left-border accent
  - Loading skeleton with pulse animation (disabled under prefers-reduced-motion)
  - Hover/focus styles
  - All brand token usages include comma-separated fallbacks (test_brand_tokens_have_fallbacks)
  - Theme-responsive: Mint/Sage/Warm via tokens

PR3-11 (FE): Expanded card panel.
  - Expanded detail region: full skills, cost-by-context bars, scrollable system prompt
  - System prompt: <pre><code> block with max-height + overflow-y: auto
  - Copy-to-clipboard button for system prompt
  - Total cost label with prominent styling
  - Detail loading state (skeleton lines while prompt fetches)
  - Error state for failed prompt fetch
  - Expand/collapse transition respects prefers-reduced-motion
"""

AGENTS_CSS: str = """
/* ── Agents grid ──────────────────────────────────────────────────── */
.card-grid.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 1rem;
  align-items: start;
}
@media (max-width: 767px) {
  .card-grid.agents-grid {
    grid-template-columns: 1fr;
  }
}

/* ── Agent card (collapsed) ────────────────────────────────────────── */
.agent-card {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid var(--color-border, #dddddd);
  border-left: 3px solid transparent;
  border-radius: var(--radius-card, 6px);
  padding: 1rem 1rem 0.875rem;
  background: var(--color-surface, #ffffff);
  cursor: pointer;
  font-family: var(--font-stack, -apple-system, sans-serif);
  font-size: 1rem;
  color: var(--color-text, #222222);
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.agent-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border-color: var(--color-accent, #9cddc8);
  border-left-color: var(--color-accent, #9cddc8);
}
.agent-card:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
/* Warm theme: double focus outline per SPEC §7.7 WCAG constraint */
[data-theme="warm"] .agent-card:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  box-shadow: 0 0 0 4px var(--color-accent, #9cddc8);
}

/* Active agent: 3px left-border accent */
.agent-card.agent-card--active {
  border-left: 3px solid var(--color-accent, #9cddc8);
}

/* ── Card header ──────────────────────────────────────────────────── */
.agent-card__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

/* ── Agent name ──────────────────────────────────────────────────── */
.agent-card__name {
  flex: 1;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Expand chevron ──────────────────────────────────────────────── */
.agent-card__chevron {
  font-size: 0.85rem;
  color: var(--color-muted, #666666);
  flex-shrink: 0;
  transition: transform 0.2s ease;
}
@media (prefers-reduced-motion: reduce) {
  .agent-card__chevron {
    transition: none;
  }
}

/* ── Status badge ────────────────────────────────────────────────── */
.agent-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15em 0.55em;
  border-radius: 3px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
  flex-shrink: 0;
}
/* Active: tinted green background, green text */
.agent-status-badge--active {
  background: #d4f5e5; /* light tint of active-dot green */
  color: #1f7a46;      /* darker green — WCAG AA on the tinted bg */
}
/* Inactive: neutral */
.agent-status-badge--inactive {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-muted, #666666);
}
.agent-status-badge__dot {
  display: inline-block;
  width: 0.5em;
  height: 0.5em;
  border-radius: 50%;
  background: currentColor;
}

/* ── Description (2-line clamp) ──────────────────────────────────── */
.agent-card__description {
  font-size: 0.88rem;
  color: var(--color-muted, #666666);
  margin: 0 0 0.75rem;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  line-height: 1.5;
}

/* ── Stat row (3 columns) ─────────────────────────────────────────── */
.agent-card__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.agent-stat {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.agent-stat__label {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--color-muted, #666666);
  letter-spacing: 0.03em;
}
.agent-stat__value {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text, #222222);
}

/* ── Skills chips ────────────────────────────────────────────────── */
.agent-card__skills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.25rem;
}
.skill-chip {
  display: inline-block;
  padding: 0.2em 0.55em;
  border-radius: 3px;
  background: var(--color-accent-secondary, #bfd8ad);
  color: var(--color-text, #222222);
  font-size: 0.72rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  white-space: nowrap;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.7;
}
.skill-chip--more {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-muted, #666666);
  font-family: var(--font-stack, -apple-system, sans-serif);
  opacity: 1;
}
.skill-chip--none {
  background: none;
  color: var(--color-muted, #666666);
  font-style: italic;
  font-family: var(--font-stack, -apple-system, sans-serif);
  opacity: 1;
}

/* ── Expanded detail region ──────────────────────────────────────── */
.agent-card__detail {
  margin-top: 0.75rem;
  border-top: 1px solid var(--color-border, #dddddd);
  padding-top: 0.75rem;
}
.agent-card__detail[hidden] { display: none; }

/* ── Agent detail inner wrapper ──────────────────────────────────── */
.agent-detail {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── Section label (Skills / Cost by context / System prompt) ────── */
.agent-detail__section-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted, #666666);
  font-weight: 700;
  margin-bottom: 0.4rem;
  display: block;
}

/* ── Skills list (expanded — full list, not truncated) ───────────── */
.agent-detail__section {
  display: flex;
  flex-direction: column;
}
.agent-detail__skills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.skill-chip--expanded {
  background: var(--color-accent-secondary, #bfd8ad);
  color: var(--color-text, #222222);
  opacity: 0.85;
}
.agent-detail__no-skills {
  font-size: 0.82rem;
  color: var(--color-muted, #666666);
  font-style: italic;
}

/* ── Total cost row ──────────────────────────────────────────────── */
.agent-detail__cost-row {
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
}
.agent-detail__cost-value {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
}

/* ── System prompt header (label + copy button) ───────────────────── */
.agent-detail__prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.4rem;
}

/* ── Copy-to-clipboard button ─────────────────────────────────────── */
.agent-detail__copy-btn {
  background: none;
  border: 1px solid var(--color-border, #dddddd);
  border-radius: 3px;
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  font-size: 0.72rem;
  font-family: var(--font-stack, -apple-system, sans-serif);
  padding: 0.15em 0.5em;
  transition: background 0.1s ease, color 0.1s ease;
  white-space: nowrap;
}
.agent-detail__copy-btn:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-cost, #633d2e);
}
.agent-detail__copy-btn:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .agent-detail__copy-btn { transition: none; }
}

/* ── System prompt block ─────────────────────────────────────────── */
.agent-prompt {
  margin: 0;
  padding: 0.6rem 0.75rem;
  background: var(--color-placeholder-bg, #f7f7f7);
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.78rem;
  line-height: 1.55;
  color: var(--color-text, #222222);
  white-space: pre-wrap;
  word-break: break-word;
  /* Bounded height to prevent very long prompts from dominating the page */
  max-height: 320px;
  overflow-y: auto;
  /* Custom scrollbar (subtle) */
  scrollbar-width: thin;
  scrollbar-color: var(--color-border, #dddddd) transparent;
}
.agent-prompt code {
  font-family: inherit;
  font-size: inherit;
}

/* ── Expand transition ───────────────────────────────────────────── */
/* Chevron rotation is driven by inline style via JS;
   the CSS transition on .agent-card__chevron handles the animation. */
@media (prefers-reduced-motion: reduce) {
  .agent-card__detail {
    transition: none;
  }
}

/* ── Detail loading state ────────────────────────────────────────── */
.agent-detail--loading {
  padding: 0.25rem 0;
}
.agent-detail__loading-row {
  margin: 0.3rem 0;
}

/* ── Detail error state ──────────────────────────────────────────── */
.agent-detail--error {
  font-size: 0.85rem;
  color: var(--color-cost, #633d2e);
  background: #fef3ec;
  border: 1px solid var(--color-alert, #f7af63);
  border-radius: var(--radius-card, 6px);
  padding: 0.6rem 0.75rem;
}

/* ── Loading skeleton ────────────────────────────────────────────── */
.agent-card--skeleton {
  pointer-events: none;
  cursor: default;
}
.skeleton-pulse {
  background: linear-gradient(
    90deg,
    var(--color-placeholder-bg, #f7f7f7) 25%,
    var(--color-border, #dddddd) 37%,
    var(--color-placeholder-bg, #f7f7f7) 63%
  );
  background-size: 400px 100%;
  animation: skeleton-shimmer 1.4s ease infinite;
  border-radius: 3px;
  display: inline-block;
  height: 1em;
}
@keyframes skeleton-shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-pulse {
    animation: none;
    background: var(--color-placeholder-bg, #f7f7f7);
  }
}
.skeleton-badge  { width: 64px;  height: 1.3em; }
.skeleton-name   { flex: 1; height: 1em; }
.skeleton-chevron { width: 16px; height: 1em; }
.skeleton-line   { display: block; height: 0.85em; margin: 0.4rem 0; }

/* ── Error / empty states ────────────────────────────────────────── */
.error-state {
  color: var(--color-cost, #633d2e);
  background: #fef3ec; /* light amber tint */
  border: 1px solid var(--color-alert, #f7af63);
  border-radius: var(--radius-card, 6px);
  padding: 1rem 1.25rem;
  font-size: 0.9rem;
}
.retry-link {
  background: none;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  font-size: inherit;
  font-family: inherit;
  text-decoration: underline;
  padding: 0;
}
.retry-link:hover { color: var(--color-cost, #633d2e); }
.retry-link:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}

/* ── Warning / staleness banner ──────────────────────────────────── */
.warning-banner {
  padding: 0.75rem 1rem;
  background: var(--color-warning-bg, #ddd9ab);
  color: var(--color-cost, #633d2e);
  border-radius: var(--radius-card, 6px);
  margin-bottom: 1rem;
  font-size: 0.88rem;
}

/* ── Context breakdown bars (expanded, PR3-11) ───────────────────── */
.context-breakdown { margin: 0.5rem 0; }
.context-breakdown-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  margin: 0.25rem 0;
}
.context-bar {
  flex: 1;
  height: 0.5rem;
  background: var(--color-placeholder-bg, #f7f7f7);
  border-radius: 4px;
  overflow: hidden;
}
.context-bar-fill {
  height: 100%;
  background: var(--color-accent, #9cddc8);
  border-radius: 4px;
}

/* ── Placeholder card (legacy — kept for compat until fully removed) */
.placeholder-card {
  background: var(--color-placeholder-bg, #f7f7f7);
  border: 1px dashed var(--color-border, #dddddd);
  border-radius: var(--radius-card, 6px);
  padding: var(--space-xl, 2rem);
  text-align: center;
  color: var(--color-muted, #666666);
  max-width: 480px;
}
.placeholder-card .placeholder-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-muted, #666666);
  margin-bottom: var(--space-sm, 0.6rem);
}
.placeholder-card .placeholder-body { font-size: 0.88rem; }

/* ── Legacy agent-card styles (sessions drilldown, PR3-11 will clean up) */
.agent-cost-unknown { color: #999; font-style: italic; }
.agent-suspect-badge {
  background: var(--color-alert, #f7af63);
  color: #3d2a00;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
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
"""
