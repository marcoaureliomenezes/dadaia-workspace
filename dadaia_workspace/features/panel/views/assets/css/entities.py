"""Agentic Entities tab CSS for the Dadaia Workspace Panel.

Minimal ``<details>`` entity cards (collapsed face = name + badge), topic
headers with an inline note, and per-harness implementation rows. Shares the
card-elevation language of the other tabs; all colours reference design tokens
from tokens.py — no raw hex values except fallbacks that mirror token defaults.
Motion respects prefers-reduced-motion (transition only, no animation).
"""

ENTITIES_CSS: str = """
/* ── Topic blocks ───────────────────────────────────────────────────── */
.ent-topic {
  margin-top: var(--space-lg, 1.5rem);
}

.ent-topic h3 {
  margin: 0 0 var(--space-sm, 0.6rem);
  font-size: 1.05rem;
  color: var(--color-text, #222222);
}

.ent-topic h4 {
  margin: var(--space-md, 1rem) 0 var(--space-xs, 0.35rem);
  font-size: 0.9rem;
  color: var(--color-text-muted, #666666);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ent-topic-note {
  font-size: 0.78rem;
  font-weight: 400;
  color: var(--color-text-muted, #666666);
  margin-left: var(--space-sm, 0.6rem);
}

/* ── Entity card grid ───────────────────────────────────────────────── */
.ent-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm, 0.6rem);
}

@media (max-width: 1023px) {
  .ent-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 639px) {
  .ent-grid { grid-template-columns: 1fr; }
}

/* ── Minimal expandable entity card ─────────────────────────────────── */
.ent-card {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-card, #dddddd);
  border-radius: var(--radius-lg, 10px);
  box-shadow: var(--shadow-card-rest, 0 1px 3px rgba(0,0,0,.06));
  transition: box-shadow var(--duration-normal, 220ms) var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
  align-self: start;
}

.ent-card:hover {
  box-shadow: var(--shadow-card-hover, 0 6px 20px rgba(0,0,0,.10));
}

.ent-card > summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm, 0.6rem);
  padding: var(--space-sm, 0.6rem) var(--space-md, 1rem);
  cursor: pointer;
  list-style: none;
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--color-text, #222222);
}

.ent-card > summary::-webkit-details-marker { display: none; }

.ent-card[open] > summary {
  border-bottom: 1px solid var(--color-border-card, #dddddd);
}

.ent-card-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ent-badge {
  flex: none;
  font-size: 0.68rem;
  font-weight: 500;
  padding: 0.1rem 0.55rem;
  border-radius: var(--radius-pill, 999px);
  background: var(--color-academy-chip-bg, #eef2ec);
  color: var(--color-text-muted, #666666);
}

.ent-card-body {
  padding: var(--space-sm, 0.6rem) var(--space-md, 1rem);
  font-size: 0.82rem;
  color: var(--color-text, #222222);
}

.ent-card-body p {
  margin: 0 0 var(--space-sm, 0.6rem);
  line-height: 1.45;
}

.ent-path {
  font-size: 0.75rem;
  color: var(--color-text-muted, #666666);
  word-break: break-all;
}

/* ── Per-harness implementation rows ────────────────────────────────── */
.ent-impl {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 0.35rem);
}

.ent-impl-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm, 0.6rem);
}

.ent-impl-harness {
  flex: none;
  min-width: 5.5rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text-muted, #666666);
}

.ent-impl-row code {
  font-size: 0.74rem;
  word-break: break-all;
}

@media (prefers-reduced-motion: reduce) {
  .ent-card { transition: none; }
}
"""
