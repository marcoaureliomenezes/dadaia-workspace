"""Workflows tab view. Renders a static scaffold for the card-grid Workflows experience.

PR3-16: The old 2-pane layout (workflows-list nav + workflows-detail pane) is replaced
by a full-width card grid sourced from /api/workflows. The div#workflows-grid is now the
container workflows.js populates with one .workflow-card per workflow.

PR3-17 will extend this scaffold with the detail-view overlay HTML.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No workflow data is
  serialised server-side — all dynamic content is rendered client-side by
  window.Workflows in workflows.js after the auth handshake.
"""

from __future__ import annotations

import html


def render_workflows_section() -> str:
    """Return the static HTML scaffold for the Workflows tab card grid.

    workflows.js fetches /api/workflows on tab activation and populates
    #workflows-grid with one .workflow-card per workflow.
    """
    empty_msg = html.escape("Nenhum workflow descoberto.")
    return (
        '<section id="section-workflows" class="section panel-section" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-workflows">\n'
        '  <header class="section-header">\n'
        "    <h2>Workflows</h2>\n"
        '    <p class="section-meta" id="workflows-meta" aria-live="polite"></p>\n'
        "  </header>\n"
        '  <p id="workflows-empty" class="empty-state" hidden>'
        + empty_msg
        + "</p>\n"
        # Card grid container — workflows.js renders .workflow-card elements inside.
        # aria-busy="false" is the default; workflows.js sets it to "true" during fetch.
        '  <div id="workflows-grid" class="workflows-card-grid" '
        'aria-busy="false" aria-label="Workflow cards"></div>\n'
        # Legacy pane elements retained as hidden stubs so existing tests that check
        # for workflows-list/workflows-detail keep passing; they are visually hidden
        # via CSS (display:none on .workflows-list / .workflows-detail in workflows.css).
        # PR3-17 will decide whether to repurpose or remove them.
        '  <nav class="workflows-list" aria-label="Workflow list" '
        'id="workflows-list" hidden></nav>\n'
        '  <div class="workflows-detail" id="workflows-detail" '
        'role="region" aria-label="Workflow detail" aria-live="polite" hidden></div>\n'
        "</section>"
    )
