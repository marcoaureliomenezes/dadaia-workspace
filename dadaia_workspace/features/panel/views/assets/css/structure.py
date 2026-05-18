"""Structural CSS for the Dadaia Workspace Panel.

Phase 1 (SE): reset, body, links, code, topbar, nav-tabs, main content area,
section visibility, section-header, servers section, memory cards grid, and
shared utility classes.
Phase 2 (FE / PR3-03): adds the Warm theme focus-visible override (E2E-THM-07).
"""

STRUCTURE_CSS: str = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-stack);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.55;
  min-height: 100vh;
}

a { color: var(--color-accent-dark); text-decoration: none; }
a:hover, a:focus { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: 2px; border-radius: 2px; }

code {
  font-family: var(--font-mono);
  background: var(--color-code-bg);
  padding: 0.1em 0.3em;
  border-radius: var(--radius);
  font-size: 0.88em;
}

/* ── Top bar ─────────────────────────────────────── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--topbar-h);
  background: var(--color-surface);
  border-bottom: 2px solid var(--color-border-strong);
  display: flex;
  align-items: center;
  padding: 0 var(--space-lg);
  gap: var(--space-md);
}

.topbar-logo { color: var(--color-cost, #633d2e); display: inline-flex; align-items: center; margin-right: 0.5rem; }
.topbar-logo svg { width: 24px; height: 24px; display: block; }

.topbar-wordmark {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e); /* brand-identity-v1 T-BR-07: high-contrast brown (AAA on white) */
  letter-spacing: -0.01em;
}
.topbar-wordmark span { color: var(--color-accent-dark); }
.topbar-divider { width: 1px; height: 24px; background: var(--color-border); }
.topbar-subtitle { color: var(--color-muted); font-size: 0.9rem; }
.topbar-badge {
  margin-left: auto;
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  white-space: nowrap;
}

/* ── Navigation tabs ─────────────────────────────── */
.nav-tabs {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  padding: 0 var(--space-lg);
  gap: 0;
}

.nav-tab {
  display: inline-block;
  padding: 0.65rem 1.1rem;
  font-size: 0.92rem;
  color: var(--color-muted);
  border-bottom: 3px solid transparent;
  cursor: pointer;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  font-family: inherit;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.nav-tab:hover { color: var(--color-text); }
.nav-tab:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: -2px; }
.nav-tab.active {
  color: var(--color-heading);
  font-weight: 600;
  border-bottom-color: var(--color-accent, #9cddc8);
}

/* ── Main content ───────────────────────────────── */
.main {
  max-width: 1024px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}

.section { display: none; }
.section.active { display: block; }

.section-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}
.section-header h2 { font-size: 1.15rem; color: var(--color-heading); }
.section-header p { font-size: 0.88rem; color: var(--color-muted); margin-top: 0.25rem; }

/* ── Servers section ─────────────────────────────── */
.refresh-notice {
  font-size: 0.8rem;
  color: var(--color-muted);
  text-align: right;
  margin-bottom: var(--space-sm);
}

#refresh-status {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-active-dot);
  margin-right: 4px;
  vertical-align: middle;
  transition: opacity 0.3s;
}
#refresh-status.updating { opacity: 0.3; }

.group-label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted);
  margin: var(--space-lg) 0 var(--space-xs) 0;
}
.group-label:first-of-type { margin-top: 0; }

table.servers-table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  font-size: 0.92rem;
}
table.servers-table th,
table.servers-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: middle;
}
table.servers-table th {
  background: var(--color-th-bg);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
}
table.servers-table tr:last-child td { border-bottom: none; }
table.servers-table tbody tr:hover { background: var(--color-row-hover); }

.status-active { color: var(--color-active-dot); font-weight: 600; }
.status-stale  { color: var(--color-stale-dot); }

.port-badge {
  font-family: var(--font-mono);
  font-size: 0.88em;
  background: var(--color-code-bg);
  padding: 0.15em 0.4em;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}

.empty-state {
  padding: var(--space-xl);
  text-align: center;
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-muted);
}
.empty-state code { display: inline-block; margin-top: var(--space-sm); font-size: 0.85em; }

/* ── Memory cards grid ───────────────────────────── */
.context-count {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-bottom: var(--space-md);
}
.context-count strong { color: var(--color-text); }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.context-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: box-shadow 0.15s;
}
.context-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.context-card.primary {
  border-left: 4px solid var(--color-primary-ring, #9cddc8);
  background: var(--color-primary-bg, #f0fbf7);
}

.card-header {
  padding: var(--space-md) var(--space-md) var(--space-sm);
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
}
.card-name { font-size: 0.97rem; font-weight: 700; color: var(--color-heading); flex: 1; }
.card-primary-badge {
  flex-shrink: 0;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  padding: 0.2em 0.5em;
  border-radius: 20px;
}
.card-meta {
  padding: 0 var(--space-md) var(--space-sm);
  font-size: 0.83rem;
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.card-links { border-top: 1px solid var(--color-border); }
.memory-link {
  display: flex;
  align-items: center;
  padding: 0.5rem var(--space-md);
  font-size: 0.87rem;
  color: var(--color-accent-dark);
  border-bottom: 1px solid var(--color-border);
  gap: var(--space-sm);
  transition: background 0.1s;
}
.memory-link:last-child { border-bottom: none; }
.memory-link:hover, .memory-link:focus { background: var(--color-card-hover); text-decoration: none; }
.memory-link:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: -2px; }
.memory-link-icon { font-size: 0.9em; color: var(--color-muted); flex-shrink: 0; width: 1.2em; text-align: center; }
.memory-link-label { flex: 1; }
.memory-link-arrow { color: var(--color-border); font-size: 0.9em; flex-shrink: 0; }

/* ── panel-section base ──────────────────────────── */
.panel-section { display: none; }
.panel-section.active { display: block; }

/* ── Warm theme focus-visible override (E2E-THM-07) ─────────────────────────
   Amber alone fails the WCAG 3:1 UI-component contrast threshold on white.
   In the Warm theme the focus ring uses --color-accent-dark (brown) as the
   primary outline so the focus indicator meets WCAG AA. A secondary amber
   outline is added as a visual accent that does not carry the contrast burden.
   See tokens.py for the amber hex value definition.
   ─────────────────────────────────────────────────────────────────────────── */
html[data-theme="warm"] a:focus-visible,
html[data-theme="warm"] .nav-tab:focus-visible,
html[data-theme="warm"] .memory-link:focus-visible,
html[data-theme="warm"] button:focus-visible,
html[data-theme="warm"] [role="button"]:focus-visible,
html[data-theme="warm"] [role="menuitem"]:focus-visible,
html[data-theme="warm"] [role="menuitemradio"]:focus-visible {
  outline: 2px solid var(--color-accent-dark, #633d2e),
           1px solid var(--color-accent, #f7af63);
  outline-offset: 2px;
}
"""
