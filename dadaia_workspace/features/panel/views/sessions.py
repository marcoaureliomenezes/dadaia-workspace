"""Sessions dashboard sub-section view — aggregated-cost dashboard scaffold.

panel-plumbing v0.1.52 FR2 introduced the dashboard-only scaffold; v0.1.79
(panel agentic-layers reorg) relocated it from its own standalone primary tab
into a sub-section rendered INSIDE the "1º Agentic Layer" (``#section-subagents``)
tabpanel. ``#section-sessions`` survives as the nested mount id — ``sessions.js``
keys on it unchanged — but it is now a plain ``<div>`` sub-section (like
``.ops-subsection``), not a standalone ``role="tabpanel"``.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No session data is serialised
  server-side into this HTML — the 4-card summary dashboard and the cost-unknown
  banner are rendered client-side by ``window.Sessions`` in ``sessions.js`` from
  the ``/api/sessions`` aggregate envelope, after the auth handshake. This
  prevents any accidental injection of API payloads into HTML.

FR2 (SPEC §FR2):
  The Sessions dashboard renders ONLY the 4-card summary dashboard
  (#sessions-dashboard) plus the cost-unknown banner (#sessions-banner). The list
  table, sortable headers, filter toolbar, and skeleton machinery were removed
  with the client-computed statistics — the aggregate now lives server-side and
  is served by ``/api/sessions`` (v0.1.52 FR1). The #sessions-last-updated badge,
  extracted from the deleted toolbar, reports the last aggregate refresh time.
"""

from __future__ import annotations


def render_sessions_section() -> str:
    """Return the static HTML scaffold for the dashboard-only Sessions sub-section.

    ``sessions.js`` fetches the ``/api/sessions`` aggregate on 1º Agentic Layer
    tab load and on every ``dadaia:runtime-change`` event, renders the four stat
    cards into #sessions-dashboard, toggles #sessions-banner for cost-unknown
    runtimes (codex/pi), and updates the #sessions-last-updated badge. No
    per-session rows are rendered.

    v0.1.79: rendered as a plain ``<div id="section-sessions" class="ops-subsection">``
    — NOT a standalone ``.section``/``.panel-section`` tabpanel — so it is shown or
    hidden by its PARENT tabpanel's (#section-subagents) ``.active`` toggle, never
    independently.
    """
    return (
        '<div id="section-sessions" class="ops-subsection">\n'
        '  <header class="section-header">\n'
        "    <h2>Sessions</h2>\n"
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime">\n'
        '      <button type="button" class="runtime-btn runtime-btn--claude" id="sessions-runtime-btn-claude"\n'
        '        role="radio" aria-checked="true" data-runtime-value="claude" aria-label="Claude runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9672;</span>\n'
        '        <span class="runtime-btn-label">Claude</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--codex" id="sessions-runtime-btn-codex"\n'
        '        role="radio" aria-checked="false" data-runtime-value="codex" aria-label="Codex runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9667;</span>\n'
        '        <span class="runtime-btn-label">Codex</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--pi" id="sessions-runtime-btn-pi"\n'
        '        role="radio" aria-checked="false" data-runtime-value="pi" aria-label="PI runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9678;</span>\n'
        '        <span class="runtime-btn-label">PI</span>\n'
        "      </button>\n"
        "    </div>\n"
        "  </header>\n"
        # 4-card aggregate dashboard — populated by JS from the /api/sessions aggregate.
        '  <div id="sessions-dashboard" class="sessions-dashboard" aria-label="Sessions summary"></div>\n'
        # Last-updated badge — extracted from the deleted toolbar; JS refreshes it
        # after each aggregate fetch.
        '  <span id="sessions-last-updated" class="sessions-last-updated"\n'
        '        aria-live="polite" data-testid="sessions-last-updated">Never</span>\n'
        # Cost-unknown banner — hidden by default; JS shows it when the runtime is
        # codex or pi. aria-live="polite" so screen readers announce it when it appears.
        '  <div id="sessions-banner" class="sessions-banner"\n'
        '       role="status" aria-live="polite" hidden></div>\n'
        "</div>"
    )
