"""Agent card CSS for the Dadaia Workspace Panel.

PR3-10 (FE): Full collapsed card design.
  - 2-column grid at >=1024px, 1-column below
  - Collapsed card: status badge, name, description (2-line clamp), 3-stat row,
    skills chips (first 2 + "+N more")
  - Status badge variants: active (green dot) / inactive (gray)
  - Active card: 4px left-border accent
  - Loading skeleton with pulse animation (disabled under prefers-reduced-motion)
  - Hover/focus styles
  - All brand token usages include comma-separated fallbacks (test_brand_tokens_have_fallbacks)
  - Theme-responsive: Mint/Sage/Warm via tokens

P5-D (FE): Modal redesign (T-P5-18 to T-P5-21).
  - Collapsed card now opens a <dialog> modal (no inline expand/collapse)
  - Card button uses aria-haspopup="dialog" (no aria-expanded)
  - Modal CSS: .agent-modal, ::backdrop, open animation, prefers-reduced-motion fallback
  - Close button: 44×44px touch target, focus ring via --color-accent-dark
"""

AGENTS_CSS: str = """
/* ── Agents grid ──────────────────────────────────────────────────── */
.card-grid.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.5rem;
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
  border: 1px solid var(--color-border-card, #dddddd);
  border-left: 3px solid transparent;
  border-radius: var(--radius-card, 4px);
  padding: 0.45rem 0.55rem 0.4rem;
  background: var(--color-surface, #ffffff);
  cursor: pointer;
  font-family: var(--font-stack, -apple-system, sans-serif);
  font-size: 0.82rem;
  color: var(--color-text, #222222);
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.agent-card:hover {
  box-shadow: var(--shadow-card);
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

/* Active agent: 3px left-border accent (matches tier accent weight).
   Active accent is visible before JS populates data-tier (loading/skeleton phase).
   When both agent-card--active and data-tier are present, the tier selectors below
   win by CSS source order (they come after this rule), so the tier colour is always
   the authoritative left-stripe signal once tier data is available. */
.agent-card.agent-card--active {
  border-left: 3px solid var(--color-accent, #9cddc8);
}

/* ── Tier-aware left-border accent (PR4-18) ─────────────────────────────────
   Tier selectors are placed AFTER .agent-card--active so they take precedence
   when both class and attribute are present (same specificity, later wins).
   This means an active T1 card shows the red tier accent, not the mint accent.
   The active class is still visible via the status badge and overall border tint. */
.agent-card[data-tier="1"] {
  border-left: 3px solid var(--color-tier-1);
}
.agent-card[data-tier="2"] {
  border-left: 3px solid var(--color-tier-2);
}
.agent-card[data-tier="3"] {
  border-left: 3px solid var(--color-tier-3);
}

/* ── Tier label (PR4-18) ─────────────────────────────────────────────────────
   Mandatory per WCAG 1.4.1: colour must not be the sole tier differentiator.
   Text "T1 ORCHESTRATOR" / "T2 CURATOR" / "T3 LEAF" provides a redundant signal.
   Displayed as a subtitle line below .agent-card__name in the card header row. */
.agent-card__tier-label {
  display: block;
  font-size: 0.65rem;     /* ~10.4px — below 12px but still legible at card size; WCAG 1.4.1 colour+text redundancy maintained */
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-muted, #666666); /* #666666 on #fff = 5.74:1 — WCAG AA (4.5:1 min) */
  line-height: 1.1;
}

/* ── Card header ──────────────────────────────────────────────────── */
.agent-card__header {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-bottom: 0.3rem;
}

/* ── Agent name ──────────────────────────────────────────────────── */
.agent-card__name {
  flex: 1;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Status badge ────────────────────────────────────────────────── */
.agent-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.1em 0.35em;
  border-radius: 2px;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  white-space: nowrap;
  flex-shrink: 0;
}
/* Active: tinted green background, green text */
.agent-status-badge--active {
  background: var(--color-badge-active-bg, #d4f5e5); /* light tint of active-dot green */
  color: var(--color-badge-active-text, #1f7a46);    /* darker green — WCAG AA on the tinted bg */
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
  font-size: 0.72rem;
  color: var(--color-muted, #666666);
  margin: 0 0 0.35rem;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  line-height: 1.35;
}

/* ── Stat row (3 columns) ─────────────────────────────────────────── */
.agent-card__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.2rem;
  margin-bottom: 0.3rem;
}
.agent-stat {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.agent-stat__label {
  font-size: 0.6rem;
  text-transform: uppercase;
  color: var(--color-muted, #666666);
  letter-spacing: 0.02em;
}
.agent-stat__value {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text, #222222);
}

/* ── Skills chips ────────────────────────────────────────────────── */
.agent-card__skills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  margin-bottom: 0.1rem;
}
.skill-chip {
  display: inline-block;
  padding: 0.1em 0.35em;
  border-radius: 2px;
  background: var(--color-accent-secondary, #bfd8ad);
  color: var(--color-chip-text, #3a3a3a); /* WCAG AA ≥5.0:1 on all accent-secondary chip backgrounds */
  font-size: 0.62rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* ── Agent modal ─────────────────────────────────────────────────────────── */
.agent-modal {
  max-width: var(--modal-max-w, 720px);
  max-height: var(--modal-max-h, 80vh);
  width: 90vw;
  border: none;
  border-radius: var(--radius-modal, 0.75rem);
  padding: 0;
  overflow: hidden;
  box-shadow: var(--shadow-modal, 0 8px 32px rgba(0,0,0,.24), 0 2px 8px rgba(0,0,0,.12));
  animation: modal-in var(--duration-normal, 220ms) var(--easing-decelerate, cubic-bezier(0, 0, 0.2, 1)) both;
}
@keyframes modal-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .agent-modal { animation: modal-in-reduced var(--duration-normal, 220ms) both; }
  @keyframes modal-in-reduced {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
}
.agent-modal::backdrop {
  background: rgba(0,0,0,0.45);
  animation: backdrop-in var(--duration-normal, 220ms) var(--easing-decelerate, cubic-bezier(0, 0, 0.2, 1)) both;
}
@keyframes backdrop-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.agent-modal__inner {
  display: flex;
  flex-direction: column;
  max-height: var(--modal-max-h, 80vh);
  overflow: hidden;
}
.agent-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  flex-shrink: 0;
}
.agent-modal__title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  margin: 0;
}
.agent-modal__close {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius, 4px);
  background: none;
  color: var(--color-muted, #666666);
  cursor: pointer;
  font-size: 1rem;
  font-family: inherit;
}
.agent-modal__close:hover {
  background: var(--color-placeholder-bg, #f7f7f7);
  color: var(--color-text, #222222);
}
.agent-modal__close:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
}
.agent-modal__body {
  padding: 1rem 1.25rem;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border, #dddddd) transparent;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── Agent detail inner wrapper (modal body) ────────────────────── */
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

/* ── Skills list (full list in modal) ───────────────────────────── */
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
  color: var(--color-chip-text, #3a3a3a); /* WCAG AA ≥5.0:1 on all accent-secondary chip backgrounds */
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
  /* Bounded height to prevent very long prompts from dominating the modal body */
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

/* ── Context breakdown bars (modal, P5-D) ────────────────────────── */
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
