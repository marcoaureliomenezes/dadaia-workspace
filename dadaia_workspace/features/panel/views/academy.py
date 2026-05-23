"""Academy tab section scaffold.

Returns the static HTML scaffold for the Academy tab.
Content is loaded client-side by academy.js via GET /api/academy.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No academy data is serialised
  server-side into this HTML — all dynamic content is rendered client-side by
  window.Panel.activate('academy', ...) in academy.js after the auth handshake.
  This prevents any accidental injection of API payloads into HTML.
"""

from __future__ import annotations


def render_academy_section() -> str:
    """Return the static HTML scaffold for the Academy section.

    academy.js fetches /api/academy on tab activation and populates
    #academy-content with course module cards. The server never serialises
    course records into this HTML.
    """
    return (
        '<section id="section-academy" class="section" aria-label="Academy modules"\n'
        '         role="tabpanel" tabindex="0" aria-labelledby="tab-academy">\n'
        '  <div class="section-header">\n'
        "    <h2>Academy</h2>\n"
        "    <p>Course modules and learning resources for the workspace.</p>\n"
        "  </div>\n"
        '  <div id="academy-content">\n'
        '    <div class="empty-state">Loading academy modules...</div>\n'
        "  </div>\n"
        "</section>"
    )
