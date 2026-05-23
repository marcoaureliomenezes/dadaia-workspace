"""CSS module for the Projects tab (Phase C redesign).

4-zone card anatomy:
  Zone A — project name (bold, --color-heading)
  Zone B — repo + branch rows (monospace, truncated)
  Zone C — session binding placeholder (populated by JS)
  Zone D — memory pill chips (Architecture, Tech Stack, Product)

T-P5-16: initial card redesign + chip styles + count badge
T-P5-17: Zone C styles + --color-session-bg token reference
"""

PROJECTS_CSS: str = """
/* ── Projects section header ──────────────────────────────────────────────── */

.projects-count-badge {
  background: var(--color-primary-bg);
  color: var(--color-accent-dark);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-pill);
  padding: 0.15rem 0.6rem;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}

.section-desc {
  margin: 0.4rem 0 var(--space-sm);
}

.section-desc summary {
  cursor: pointer;
  color: var(--color-muted);
  font-size: 0.85rem;
  user-select: none;
}

.section-desc p {
  color: var(--color-muted);
  font-size: 0.85rem;
  margin: 0.4rem 0 0;
}

/* ── Context card — uniform treatment (no primary special casing) ──────────── */

.context-card {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--space-md);
  border-left: 4px solid var(--color-accent);
  transition: box-shadow var(--duration-fast) var(--easing-standard);
}

.context-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* ── Zone A — project name ─────────────────────────────────────────────────── */

.card-zone-a {
  margin-bottom: var(--space-xs);
}

.card-name {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--color-heading);
}

/* ── Zone B — repo / branch rows ───────────────────────────────────────────── */

.card-zone-b {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: var(--space-sm);
}

.card-meta-row {
  font-size: 0.82rem;
  color: var(--color-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-mono {
  font-family: var(--font-mono);
  color: var(--color-text);
}

/* ── Zone C — session binding placeholder (populated by JS) ─────────────────── */

.card-zone-c {
  margin-top: var(--space-xs);
  min-height: 0;
  /* populated by JS: tinted --color-session-bg when sessions present */
}

.card-zone-c:not(:empty) {
  background: var(--color-session-bg);
  border-radius: var(--radius);
  padding: var(--space-xs) var(--space-sm);
  margin-top: var(--space-sm);
}

.session-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

/* ── Zone D — memory pill chips ────────────────────────────────────────────── */

.card-zone-d {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: var(--space-xs);
}

.memory-chip {
  background: var(--color-chip-memory-bg);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-pill);
  padding: 0.2rem 0.7rem;
  font-size: 0.75rem;
  color: var(--color-accent-dark);
  text-decoration: none;
  white-space: nowrap;
  transition: background var(--duration-fast), border-color var(--duration-fast);
}

.memory-chip:hover {
  background: var(--color-accent-secondary);
  border-color: var(--color-accent-dark);
}

.memory-chip:focus-visible {
  outline: 2px solid var(--color-accent-dark);
  outline-offset: 2px;
}
"""
