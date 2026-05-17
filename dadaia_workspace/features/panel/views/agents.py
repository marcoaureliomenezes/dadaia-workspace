"""Agents tab view. Renders cards with metrics + context breakdown + drill-down.

Consumes /api/agents JSON via PANEL_JS lazy fetch on tab activation.
SPEC § Contratos de endpoint, § Acceptance criteria #3.

Security (OWASP A03):
  This module only returns a static HTML scaffold. No agent data is serialized
  server-side into HTML — all dynamic content is rendered client-side (vanilla JS
  in PANEL_JS) after the auth handshake. This prevents any accidental injection of
  API payloads into HTML and keeps the server-side template free of user-controlled
  data.
"""

from __future__ import annotations

import html


def render_agents_section() -> str:
    """Return the static HTML scaffold for the Agents tab.

    JS fetches dynamic data from /api/agents and /api/agents/{id}/sessions after
    tab activation. The server never serializes agent records into this HTML.

    Card layout uses CSS grid (added to PANEL_CSS in _assets.py).
    All dynamic content is rendered client-side via the Agents module in PANEL_JS.
    """
    return (
        '<section id="section-agents" class="section panel-section" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-agents">\n'
        '  <header class="section-header">\n'
        "    <h2>Agents</h2>\n"
        '    <p class="section-meta" id="agents-meta" aria-live="polite"></p>\n'
        "  </header>\n"
        '  <div id="agents-staleness-banner" class="warning-banner" hidden role="status"></div>\n'
        '  <div id="agents-grid" class="card-grid agents-grid" aria-busy="false"></div>\n'
        '  <p id="agents-empty" class="empty-state" hidden>'
        + html.escape("Nenhum agente observado ainda.")
        + "</p>\n"
        "</section>"
    )
