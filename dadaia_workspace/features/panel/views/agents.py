"""Agents tab view. Renders cards with metrics + context breakdown + drill-down.

Consumes /api/agents JSON via PANEL_JS lazy fetch on tab activation.
SPEC § Contratos de endpoint, § Acceptance criteria #3.

Security (OWASP A03):
  This module only returns a static HTML scaffold. No agent data is serialized
  server-side into HTML — all dynamic content is rendered client-side (vanilla JS
  in PANEL_JS) after the auth handshake. This prevents any accidental injection of
  API payloads into HTML and keeps the server-side template free of user-controlled
  data.

Recovery / Secure-Delete Procedure (devops T12):
  If the telemetry database is suspected to be compromised, or if corruption is
  detected (503 on API endpoints with ``telemetry_degraded``), use the following
  secure-delete recipe to purge the sensitive local state:

      shred -u ~/.dadaia/state/telemetry/telemetry.sqlite

  After shredding, restart the panel via ``dadaia panel``.  A fresh SQLite
  database will be generated on next startup.  (The panel uses no auth token.)

  Corrupt database quarantine files (``telemetry.sqlite.corrupt.<utc_ts>``) can be
  found at ``~/.dadaia/state/telemetry/`` and should also be shredded:

      shred -u ~/.dadaia/state/telemetry/telemetry.sqlite.corrupt.*

  Note: ``shred`` is available on Linux (GNU coreutils).  On macOS, use
  ``rm -P`` instead.  On encrypted filesystems (e.g. LUKS, FileVault), ordinary
  ``rm`` is sufficient since the key protects at-rest data.
"""

from __future__ import annotations

import html


def render_agents_section() -> str:
    """Return the static HTML scaffold for the Agents tab (legacy top-level section).

    Kept for backward compatibility. Returns the sub-section HTML used inside
    the consolidated Ops tab.
    """
    return render_agents_subsection()


def render_agents_subsection() -> str:
    """Return the compact sub-section HTML for Agents inside the Ops tab.

    JS fetches dynamic data from /api/agents and /api/agents/{id}/sessions after
    the Ops tab is activated. The server never serializes agent records into this HTML.

    All dynamic content is rendered client-side via the Agents module in PANEL_JS.
    """
    return (
        '<div class="ops-subsection" id="ops-subsection-agents">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">Agents</h3>\n'
        '    <p class="section-meta" id="agents-meta" aria-live="polite"></p>\n'
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime" style="margin-left:auto;">\n'
        '      <button type="button" class="runtime-btn runtime-btn--claude" id="agents-runtime-btn-claude"\n'
        '        role="radio" aria-checked="true" data-runtime-value="claude" aria-label="Claude runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9672;</span>\n'
        '        <span class="runtime-btn-label">Claude</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--codex" id="agents-runtime-btn-codex"\n'
        '        role="radio" aria-checked="false" data-runtime-value="codex" aria-label="Codex runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9667;</span>\n'
        '        <span class="runtime-btn-label">Codex</span>\n'
        "      </button>\n"
        "    </div>\n"
        "  </div>\n"
        '  <div id="agents-staleness-banner" class="warning-banner" hidden role="status"></div>\n'
        '  <div id="agents-grid" class="card-grid agents-grid agents-grid--compact" aria-busy="false"></div>\n'
        '  <p id="agents-empty" class="empty-state" hidden>'
        + html.escape("Nenhum agente observado ainda.")
        + "</p>\n"
        '  <dialog id="agent-modal"\n'
        '          class="agent-modal"\n'
        '          aria-modal="true"\n'
        '          aria-labelledby="agent-modal-title"\n'
        '          role="dialog">\n'
        '    <div class="agent-modal__inner">\n'
        '      <div class="agent-modal__header">\n'
        '        <h3 class="agent-modal__title" id="agent-modal-title">Agent detail</h3>\n'
        '        <button type="button" class="agent-modal__close" id="agent-modal-close"\n'
        '                aria-label="Close">&#10005;</button>\n'
        "      </div>\n"
        '      <div class="agent-modal__body" id="agent-modal-body">\n'
        "        <!-- populated by JS before showModal() -->\n"
        "      </div>\n"
        "    </div>\n"
        "  </dialog>\n"
        "</div>"
    )
