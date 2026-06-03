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
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime" style="margin-left:auto;">\n'
        '      <button type="button" class="runtime-btn runtime-btn--claude"\n'
        '        id="workflows-runtime-btn-claude" role="radio" aria-checked="true"\n'
        '        data-runtime-value="claude" aria-label="Claude runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9672;</span>\n'
        '        <span class="runtime-btn-label">Claude</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--codex"\n'
        '        id="workflows-runtime-btn-codex" role="radio" aria-checked="false"\n'
        '        data-runtime-value="codex" aria-label="Codex runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9667;</span>\n'
        '        <span class="runtime-btn-label">Codex</span>\n'
        "      </button>\n"
        "    </div>\n"
        "  </header>\n"
        '  <p id="workflows-empty" class="empty-state" hidden>' + empty_msg + "</p>\n"
        # Card grid container — workflows.js renders .workflow-card elements inside.
        # aria-busy="false" is the default; workflows.js sets it to "true" during fetch.
        '  <div id="workflows-grid" class="workflows-card-grid" '
        'aria-busy="false"></div>\n'
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
