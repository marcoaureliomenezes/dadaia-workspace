"""CSS for memory page styling in the Dadaia Workspace Panel.

T-PUX-03 (FE): Memory page shell CSS — applied by wrapper.py when serving
memory HTML files via /memory-view/. The /memory/ route remains byte-identical.

All values use CSS custom properties from tokens.py; never raw hex.
Design spec: design-specialist report panel-ux-fix-v1.
"""

MEMORY_CSS: str = """
/* ── Memory page shell ─────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif);
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--color-text, #222222);
  background: var(--color-bg, #fafafa);
  padding: 0;
}

/* ── Skip link (WCAG 2.4.1) ──────────────────────────────────────── */
.skip-link {
  position: absolute;
  top: -9999px;
  left: var(--space-sm, 0.6rem);
  background: var(--color-surface, #ffffff);
  color: var(--color-accent-dark, #2d7d9a);
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius, 4px);
  font-size: 0.875rem;
  text-decoration: none;
  z-index: 9999;
}
.skip-link:focus { top: var(--space-sm, 0.6rem); }

/* ── Main content area ───────────────────────────────────────────── */
#main {
  max-width: 840px;
  margin: 0 auto;
  padding: var(--space-xl, 2rem) var(--space-lg, 1.5rem);
}

/* ── Headings ────────────────────────────────────────────────────── */
h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  border-bottom: 3px solid var(--color-accent, #9cddc8);
  padding-bottom: var(--space-xs, 0.4rem);
  margin-bottom: var(--space-md, 1rem);
}
h2 {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-cost, #633d2e);
  border-bottom: 1px solid var(--color-border, #dddddd);
  padding-bottom: 0.25rem;
  margin-top: var(--space-xl, 2rem);
  margin-bottom: var(--space-sm, 0.6rem);
}
h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading, #111111);
  margin-top: var(--space-lg, 1.5rem);
  margin-bottom: var(--space-xs, 0.4rem);
}
h4, h5, h6 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-muted, #666666);
  margin-top: var(--space-md, 1rem);
  margin-bottom: var(--space-xs, 0.4rem);
}

/* ── Paragraphs & lists ──────────────────────────────────────────── */
p { margin-bottom: var(--space-sm, 0.6rem); }
ul, ol { margin-bottom: var(--space-sm, 0.6rem); padding-left: 1.5em; }
li { margin-bottom: 0.25rem; }

/* ── Links (WCAG AA: 4.53:1 on #fafafa) ─────────────────────────── */
a { color: var(--color-accent-dark, #2d7d9a); text-decoration: underline; }
a:hover { color: var(--color-cost, #633d2e); }
a:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
  border-radius: 2px;
}

/* ── Code & pre ──────────────────────────────────────────────────── */
code {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85em;
  background: var(--color-code-bg, #f0f0f0);
  padding: 0.1em 0.35em;
  border-radius: var(--radius, 4px);
}
pre {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  background: var(--color-code-bg, #f0f0f0);
  padding: var(--space-sm, 0.6rem) var(--space-md, 1rem);
  border-radius: var(--radius-card, 6px);
  overflow-x: auto;
  margin-bottom: var(--space-sm, 0.6rem);
  line-height: 1.5;
}
pre code { background: none; padding: 0; font-size: inherit; }

/* ── Tables ──────────────────────────────────────────────────────── */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  margin-bottom: var(--space-md, 1rem);
}
th {
  text-align: left;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted, #666666);
  background: var(--color-th-bg, #eeeeee);
  padding: 0.5rem 0.75rem;
  border-bottom: 2px solid var(--color-border, #dddddd);
}
td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  vertical-align: top;
}
tr:hover td { background: var(--color-row-hover, #f5f5f5); }
tr:last-child td { border-bottom: none; }

/* ── Horizontal rule ─────────────────────────────────────────────── */
hr {
  border: none;
  border-top: 1px solid var(--color-border, #dddddd);
  margin: var(--space-xl, 2rem) 0;
}

/* ── Blockquote ──────────────────────────────────────────────────── */
blockquote {
  border-left: 3px solid var(--color-accent, #9cddc8);
  padding-left: var(--space-md, 1rem);
  color: var(--color-muted, #666666);
  font-style: italic;
  margin: var(--space-sm, 0.6rem) 0;
}
"""
