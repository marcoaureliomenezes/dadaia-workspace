"""Workflows tab view. Renders a 2-pane scaffold for the Workflows experience.

Left pane: scrollable list of workflow items (populated by PANEL_JS).
Right pane: detail panel showing name, source, description, and an inline SVG
step diagram derived from agent_ids (rendered client-side — no CDN, no Mermaid,
CSP-safe vanilla SVG).

Consumes /api/workflows JSON via PANEL_JS lazy fetch on tab activation.
SPEC § Contratos de endpoint, § Acceptance criteria #4.

API gap note (panel-defects hotfix):
  /api/workflows does NOT return status, duration, or last-run timestamps.
  These fields are absent from the SPEC contract for this endpoint.
  The detail panel shows placeholders where those fields would appear;
  a backend follow-up is required to surface run metadata per workflow.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No workflow data is
  serialised server-side — all dynamic content is rendered client-side by
  the Workflows module in PANEL_JS after the auth handshake.
"""

from __future__ import annotations

import html


def render_workflows_section() -> str:
    """Return the static HTML scaffold for the Workflows tab.

    JS fetches dynamic data from /api/workflows after tab activation and
    populates the left list and right detail pane.
    """
    select_hint = html.escape("Select a workflow to view details.")
    return (
        '<section id="section-workflows" class="section panel-section" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-workflows">\n'
        '  <header class="section-header">\n'
        "    <h2>Workflows</h2>\n"
        '    <p class="section-meta" id="workflows-meta" aria-live="polite"></p>\n'
        "  </header>\n"
        '  <p id="workflows-empty" class="empty-state" hidden>'
        + html.escape("Nenhum workflow descoberto.")
        + "</p>\n"
        '  <div id="workflows-grid" class="workflows-pane" aria-busy="false">\n'
        '    <nav class="workflows-list" aria-label="Workflow list" id="workflows-list"></nav>\n'
        '    <div class="workflows-detail" id="workflows-detail" role="region" aria-label="Workflow detail" aria-live="polite">\n'
        '      <div class="workflows-detail-empty">' + select_hint + "</div>\n"
        "    </div>\n"
        "  </div>\n"
        "</section>"
    )
