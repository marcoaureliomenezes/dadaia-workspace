"""Academy tab CSS for the Dadaia Workspace Panel.

T-P5-28 (FE): Academy module card grid, type chip, detail view, back button.
  - 2-column grid at >= 768px; 1-column below
  - Card left accent: 4px solid var(--color-warning-bg)
  - Type chip: --color-academy-chip-bg background, --color-cost text, --radius-pill
  - Content frame: border, padding, --color-surface background
  - All colour values reference design tokens from tokens.py — no raw hex values
    except fallbacks that mirror token defaults.
  - Motion respects prefers-reduced-motion (via transition only — no animation)
"""

ACADEMY_CSS: str = """
/* ── Academy card grid ──────────────────────────────────────────────── */
.academy-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-md, 1rem);
  margin-top: var(--space-md, 1rem);
}

@media (max-width: 767px) {
  .academy-grid {
    grid-template-columns: 1fr;
  }
}

/* ── Academy card ─────────────────────────────────────────────────── */
.academy-card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-card, #dddddd);
  border-left: 4px solid var(--color-warning-bg, #ddd9ab);
  border-radius: var(--radius-card, 6px);
  padding: var(--space-md, 1rem);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.6rem);
  box-shadow: var(--shadow-card, 0 1px 3px rgba(0,0,0,.12));
  transition: box-shadow var(--duration-fast, 120ms) var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
}

.academy-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,.16);
}

/* ── Card header ──────────────────────────────────────────────────── */
.academy-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-xs, 0.3rem);
}

/* ── Type chip ────────────────────────────────────────────────────── */
.academy-type-chip {
  display: inline-block;
  background: var(--color-academy-chip-bg, #fef9ec);
  color: var(--color-cost, #633d2e);
  border-radius: var(--radius-pill, 9999px);
  padding: 0.15em 0.65em;
  font-size: 0.72rem;
  font-weight: 600;
  font-family: var(--font-stack, -apple-system, sans-serif);
  white-space: nowrap;
}

/* ── Card title ───────────────────────────────────────────────────── */
.academy-card__title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-heading, #111111);
  margin: 0;
  line-height: 1.3;
}

/* ── Card meta ────────────────────────────────────────────────────── */
.academy-card__meta {
  font-size: 0.82rem;
  color: var(--color-muted, #666666);
  margin: 0;
  line-height: 1.4;
}

/* ── CTA button ───────────────────────────────────────────────────── */
.academy-card__cta {
  align-self: flex-start;
  margin-top: auto;
  padding: 0.35em 0.9em;
  background: transparent;
  border: 1px solid var(--color-accent, #9cddc8);
  border-radius: var(--radius, 4px);
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--duration-fast, 120ms) var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
}

.academy-card__cta:hover,
.academy-card__cta:focus-visible {
  background: var(--color-primary-bg, #f0fbf7);
}

/* ── Detail view ──────────────────────────────────────────────────── */
.academy-detail {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-card, #dddddd);
  border-radius: var(--radius-card, 6px);
  padding: var(--space-lg, 1.5rem);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.6rem);
}

/* ── Back button ──────────────────────────────────────────────────── */
.academy-back-btn {
  align-self: flex-start;
  background: transparent;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
  margin-bottom: var(--space-sm, 0.6rem);
}

.academy-back-btn:hover,
.academy-back-btn:focus-visible {
  text-decoration: underline;
}

/* ── Detail title / meta / date ───────────────────────────────────── */
.academy-detail__title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-heading, #111111);
  margin: 0;
}

.academy-detail__meta {
  font-size: 0.85rem;
  color: var(--color-muted, #666666);
  margin: 0;
}

.academy-detail__date {
  font-size: 0.78rem;
  color: var(--color-muted, #666666);
  font-family: var(--font-mono, ui-monospace, monospace);
  margin: 0;
}

/* ── Lesson list (module → lessons) ──────────────────────────────────── */
.academy-lesson-list {
  list-style: none;
  margin: var(--space-sm, 0.6rem) 0 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 0.3rem);
}

.academy-lesson-item {
  margin: 0;
}

.academy-lesson-link {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid var(--color-border-card, #dddddd);
  border-radius: var(--radius, 4px);
  padding: 0.55em 0.8em;
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--duration-fast, 120ms) var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
}

.academy-lesson-link:hover,
.academy-lesson-link:focus-visible {
  background: var(--color-primary-bg, #f0fbf7);
}

/* ── Lesson body (rendered Markdown) ─────────────────────────────────── */
.academy-lesson-body {
  margin-top: var(--space-md, 1rem);
  color: var(--color-text, #222222);
  line-height: 1.6;
}

.academy-lesson-body h1,
.academy-lesson-body h2,
.academy-lesson-body h3 {
  color: var(--color-heading, #111111);
}

.academy-lesson-body pre {
  overflow-x: auto;
  background: var(--color-code-bg, #f5f5f5);
  padding: var(--space-sm, 0.6rem);
  border-radius: var(--radius, 4px);
}

.academy-lesson-body code {
  font-family: var(--font-mono, ui-monospace, monospace);
}

/* ── Error state variant ────────────────────────────────────────────── */
.empty-state.error-state {
  color: var(--color-cost, #633d2e);
}
"""
