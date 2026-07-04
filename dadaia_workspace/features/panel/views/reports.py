"""Reports tab section scaffold.

Returns the static HTML scaffold for the Reports tab.
Content is loaded client-side by reports.js via GET /api/reports.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No report data is serialised
  server-side into this HTML — all dynamic content is rendered client-side by
  window.Panel.activate('reports', ...) in reports.js after the auth handshake.
  This prevents any accidental injection of API payloads into HTML.
"""

from __future__ import annotations


def render_reports_section() -> str:
    """Return the static HTML scaffold for the Reports section.

    reports.js fetches /api/reports on tab activation and populates
    #reports-list with handoff report rows. The server never serialises
    report records into this HTML.
    """
    return (
        '<section id="section-reports" class="section" aria-label="Reports"\n'
        '         role="tabpanel" tabindex="0" aria-labelledby="tab-reports">\n'
        '  <header class="section-header">\n'
        "    <h2>Reports</h2>\n"
        "    <p>Agent handoff reports and findings.</p>\n"
        "  </header>\n"
        '  <div id="reports-list">\n'
        '    <div class="empty-state">Loading reports…</div>\n'
        "  </div>\n"
        '  <div id="reports-content" hidden>\n'
        "  </div>\n"
        "</section>"
    )
