"""Document-level stylesheet for rendered memory atoms (operator demand 2026-06-11).

The existing ``memory.py`` (``MEMORY_CSS`` / ``/static/memory.css``) styles the
*iframe shell* applied by ``wrapper.py``.  This module is the stylesheet linked
DIRECTLY into the rendered memory document served at ``/memory/<slug>/<file>``
(``views/memory.py``) so the document carries the dadaia visual identity on its
own — typography, heading hierarchy, table/code styling, link colours, spacing —
regardless of whether it is viewed standalone or inside the wrapper iframe.

It also styles the compact frontmatter meta header (``.memory-meta``) that
``views/memory.py`` emits in place of the raw YAML ``key: value`` soup.

All values use CSS custom properties from ``tokens.py`` (respecting the active
``data-theme``); literal fallbacks are provided so the document is still
readable if ``tokens.css`` fails to load.  Never raw hex without a token.
"""

MEMORY_DOC_CSS: str = """
/* ── Memory document — dadaia visual identity ────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { background: var(--color-bg, #fafafa); }

body {
  font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif);
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--color-text, #222222);
  background: var(--color-bg, #fafafa);
  padding: 0;
}

.memory-doc {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--space-xl, 2rem) var(--space-lg, 1.5rem);
}

/* ── Frontmatter meta header (replaces raw YAML soup) ─────────────────── */
.memory-meta {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #dddddd);
  border-left: 4px solid var(--color-accent, #9cddc8);
  border-radius: var(--radius-card, 6px);
  padding: var(--space-md, 1rem) var(--space-lg, 1.5rem);
  margin-bottom: var(--space-xl, 2rem);
}
.memory-meta__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
  margin: 0 0 var(--space-2xs, 0.25rem);
  border: none;
  padding: 0;
}
.memory-meta__tldr {
  font-size: 0.95rem;
  color: var(--color-text, #222222);
  margin: 0 0 var(--space-sm, 0.6rem);
}
.memory-meta__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs, 0.25rem);
  margin: var(--space-xs, 0.3rem) 0 0;
  padding: 0;
  list-style: none;
}
.memory-meta__chip {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--color-chip-text, #3a3a3a);
  background: var(--color-chip-memory-bg, #f0fbf7);
  border: 1px solid var(--color-border, #dddddd);
  border-radius: var(--radius-pill, 9999px);
  padding: 0.15rem 0.55rem;
}
.memory-meta__footer {
  margin-top: var(--space-sm, 0.6rem);
  font-size: 0.75rem;
  color: var(--color-muted, #666666);
}

/* ── Headings ─────────────────────────────────────────────────────────── */
.memory-doc h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-heading, #111111);
  border-bottom: 3px solid var(--color-accent, #9cddc8);
  padding-bottom: var(--space-xs, 0.4rem);
  margin-bottom: var(--space-md, 1rem);
}
.memory-doc h2 {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-cost, #633d2e);
  border-bottom: 1px solid var(--color-border, #dddddd);
  padding-bottom: 0.25rem;
  margin-top: var(--space-xl, 2rem);
  margin-bottom: var(--space-sm, 0.6rem);
}
.memory-doc h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading, #111111);
  margin-top: var(--space-lg, 1.5rem);
  margin-bottom: var(--space-xs, 0.4rem);
}
.memory-doc h4, .memory-doc h5, .memory-doc h6 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-muted, #666666);
  margin-top: var(--space-md, 1rem);
  margin-bottom: var(--space-xs, 0.4rem);
}

/* ── Paragraphs & lists ──────────────────────────────────────────────── */
.memory-doc p { margin-bottom: var(--space-sm, 0.6rem); }
.memory-doc ul, .memory-doc ol { margin-bottom: var(--space-sm, 0.6rem); padding-left: 1.5em; }
.memory-doc li { margin-bottom: 0.25rem; }

/* ── Links (WCAG AA on #fafafa) ──────────────────────────────────────── */
.memory-doc a { color: var(--color-accent-dark, #2d7d9a); text-decoration: underline; }
.memory-doc a:hover { color: var(--color-cost, #633d2e); }
.memory-doc a:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: 2px;
  border-radius: 2px;
}

/* ── Code & pre ──────────────────────────────────────────────────────── */
.memory-doc code {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85em;
  background: var(--color-code-bg, #f0f0f0);
  padding: 0.1em 0.35em;
  border-radius: var(--radius, 4px);
}
.memory-doc pre {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  background: var(--color-code-bg, #f0f0f0);
  padding: var(--space-sm, 0.6rem) var(--space-md, 1rem);
  border-radius: var(--radius-card, 6px);
  overflow-x: auto;
  margin-bottom: var(--space-sm, 0.6rem);
  line-height: 1.5;
}
.memory-doc pre code { background: none; padding: 0; font-size: inherit; }

/* ── Tables ──────────────────────────────────────────────────────────── */
.memory-doc table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  margin-bottom: var(--space-md, 1rem);
}
.memory-doc th {
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
.memory-doc td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border, #dddddd);
  vertical-align: top;
}
.memory-doc tr:hover td { background: var(--color-row-hover, #f5f5f5); }
.memory-doc tr:last-child td { border-bottom: none; }

/* ── Horizontal rule ─────────────────────────────────────────────────── */
.memory-doc hr {
  border: none;
  border-top: 1px solid var(--color-border, #dddddd);
  margin: var(--space-xl, 2rem) 0;
}

/* ── Blockquote ──────────────────────────────────────────────────────── */
.memory-doc blockquote {
  border-left: 3px solid var(--color-accent, #9cddc8);
  padding-left: var(--space-md, 1rem);
  color: var(--color-muted, #666666);
  font-style: italic;
  margin: var(--space-sm, 0.6rem) 0;
}
"""
