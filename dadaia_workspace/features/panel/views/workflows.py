"""Workflows tab view. Renders a static scaffold for the Workflows grid.

Consumes /api/workflows JSON via PANEL_JS lazy fetch on tab activation.
SPEC § Contratos de endpoint, § Acceptance criteria #4.

Security (OWASP A03):
  Same pattern as agents.py — scaffold only, no server-side data serialization.
  All workflow cards are rendered client-side by the Workflows module in PANEL_JS.
"""

from __future__ import annotations

import html


def render_workflows_section() -> str:
    """Return the static HTML scaffold for the Workflows tab.

    JS fetches dynamic data from /api/workflows after tab activation.
    The server never serializes workflow records into this HTML.

    Card layout uses CSS grid (added to PANEL_CSS in _assets.py).
    """
    return (
        '<section id="section-workflows" class="section panel-section" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-workflows">\n'
        '  <header class="section-header">\n'
        "    <h2>Workflows</h2>\n"
        '    <p class="section-meta" id="workflows-meta" aria-live="polite"></p>\n'
        "  </header>\n"
        '  <div id="workflows-grid" class="card-grid workflows-grid" aria-busy="false"></div>\n'
        '  <p id="workflows-empty" class="empty-state" hidden>'
        + html.escape("Nenhum workflow descoberto.")
        + "</p>\n"
        "</section>"
    )
