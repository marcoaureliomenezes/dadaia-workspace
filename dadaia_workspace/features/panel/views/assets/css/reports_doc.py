"""Document-level stylesheet injected into served report HTML (operator demand 2026-06-11).

Agent-authored reports under ``.dadaia/reports/<ctx>/<agent>/*.html`` carry
arbitrary inline styles, frequently with unreadable foreground/background colour
pairs.  ``views/api_reports.py::serve_report_file`` injects this stylesheet into the
``<head>`` of every ``text/html`` report at serve time so each report inherits
the dadaia visual identity regardless of how the authoring agent styled it.

Two layers:

* ``REPORTS_DOC_BASE_CSS`` — the identity base (typography, headings, tables,
  code, links).  Injected FIRST so agent inline styles can still refine on top.
* ``REPORTS_DOC_OVERRIDE_CSS`` — a small ``!important`` readability floor for
  body text/background.  The operator explicitly wants base readability to WIN
  over agent styling, so this is injected LAST and uses ``!important`` on the
  body fg/bg only — it does not flatten the report's own layout.

All values use ``tokens.py`` custom properties with literal fallbacks so a
report is readable even if ``/static/tokens.css`` fails to load.
"""

REPORTS_DOC_BASE_CSS: str = """
body {
  font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif);
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--color-text, #222222);
  background: var(--color-bg, #fafafa);
}
h1, h2, h3, h4, h5, h6 { color: var(--color-heading, #111111); line-height: 1.25; }
h1 { color: var(--color-cost, #633d2e); border-bottom: 3px solid var(--color-accent, #9cddc8); padding-bottom: 0.3rem; }
h2 { color: var(--color-cost, #633d2e); border-bottom: 1px solid var(--color-border, #dddddd); padding-bottom: 0.2rem; }
a { color: var(--color-accent-dark, #2d7d9a); }
a:hover { color: var(--color-cost, #633d2e); }
code, pre {
  font-family: var(--font-mono, ui-monospace, monospace);
  background: var(--color-code-bg, #f0f0f0);
}
code { font-size: 0.85em; padding: 0.1em 0.35em; border-radius: var(--radius, 4px); }
pre { padding: 0.6rem 1rem; border-radius: var(--radius-card, 6px); overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; }
th {
  text-align: left;
  color: var(--color-muted, #666666);
  background: var(--color-th-bg, #eeeeee);
  border-bottom: 2px solid var(--color-border, #dddddd);
  padding: 0.5rem 0.75rem;
}
td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--color-border, #dddddd); }
"""

# Readability floor — inheritance WINS over agent styling for base text/bg.
REPORTS_DOC_OVERRIDE_CSS: str = """
body {
  color: var(--color-text, #222222) !important;
  background: var(--color-bg, #fafafa) !important;
}
"""
