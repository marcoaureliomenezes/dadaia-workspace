"""Sessions tab view. Renders a static scaffold for the Sessions table experience.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No session data is serialised
  server-side into this HTML — all dynamic content is rendered client-side by
  window.Sessions in sessions.js after the auth handshake. This prevents any
  accidental injection of API payloads into HTML.

FR4 (SPEC §FR4):
  Columns: Session (session_id[:8] with ai_title in title tooltip), Project,
  Model, AI Turns, Context (tokens), Cost (USD), Last activity (relative),
  Status (dot + label).

  Each column header <th> carries a data-sort-key attribute matching a key in
  the JSON response so the JS sort handler can use it directly.

  Filter input above the table: <input id="sessions-filter">.
  Detail drawer: <aside id="session-drawer" hidden>.
"""

from __future__ import annotations


def render_sessions_section() -> str:
    """Return the static HTML scaffold for the Sessions tab.

    sessions.js fetches /api/sessions on tab activation and populates
    #sessions-tbody with one .session-row per session. The session_id[:8]
    slug is shown in the Session column; the full ai_title (if any) is in the
    title tooltip on that cell.

    The detail drawer (<aside id="session-drawer" hidden>) starts empty and is
    populated by JS when a row is clicked.
    """
    return (
        '<section id="section-sessions" class="section panel-section" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-sessions">\n'
        '  <header class="section-header">\n'
        "    <h2>Sessions</h2>\n"
        '    <p class="section-meta" id="sessions-meta" aria-live="polite"></p>\n'
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime" style="margin-left:auto;">\n'
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
        "    </div>\n"
        "  </header>\n"
        '  <div id="sessions-dashboard" class="sessions-dashboard" aria-label="Sessions summary"></div>\n'
        # Last-updated badge — updated by JS after each auto-refresh tick
        '  <div class="sessions-toolbar">\n'
        '    <label for="sessions-filter" class="sr-only">Filter sessions</label>\n'
        '    <input id="sessions-filter" type="text" class="sessions-filter-input"\n'
        '           placeholder="filter by project or session id"\n'
        '           autocomplete="off" spellcheck="false"\n'
        '           aria-label="Filter sessions by project or session id" />\n'
        '    <span id="sessions-last-updated" class="sessions-last-updated"\n'
        '          aria-live="polite" data-testid="sessions-last-updated">Never</span>\n'
        "  </div>\n"
        # Codex cost banner — hidden by default; JS shows it when runtime === 'codex'.
        # aria-live="polite" so screen readers announce it when it appears.
        '  <div id="sessions-banner" class="sessions-banner"\n'
        '       role="status" aria-live="polite" hidden></div>\n'
        # Sessions table container — aria-busy="true" until first fetch completes
        '  <div id="sessions-table-container" class="sessions-table-container"\n'
        '       aria-busy="true">\n'
        '    <table class="sessions-table" aria-label="Sessions">\n'
        "      <colgroup>\n"
        '        <col style="width:14%">\n'
        '        <col style="width:14%">\n'
        '        <col style="width:20%">\n'
        '        <col style="width:8%">\n'
        '        <col style="width:8%">\n'
        '        <col style="width:8%">\n'
        '        <col style="width:14%">\n'
        '        <col style="width:10%">\n'
        "      </colgroup>\n"
        "      <thead>\n"
        "        <tr>\n"
        '          <th scope="col" class="cell-session" data-sort-key="session_id">Session</th>\n'
        '          <th scope="col" class="cell-project" data-sort-key="project">Project</th>\n'
        '          <th scope="col" class="cell-model" data-sort-key="model">Model</th>\n'
        '          <th scope="col" class="cell-turns" data-sort-key="message_count">AI Turns</th>\n'
        '          <th scope="col" class="cell-context" data-sort-key="context_size_tokens">Context</th>\n'
        '          <th scope="col" class="cell-cost" data-sort-key="cumulative_cost_usd"\n'
        '              data-sort="cost" data-sort-dir="none">Cost</th>\n'
        '          <th scope="col" class="cell-last-activity" data-sort-key="last_activity_at">Last activity</th>\n'
        '          <th scope="col" class="cell-status" data-sort-key="status">Status</th>\n'
        "        </tr>\n"
        "      </thead>\n"
        '      <tbody id="sessions-tbody">\n'
        # Skeleton rows injected here by JS during initial load
        "      </tbody>\n"
        "    </table>\n"
        "  </div>\n"
        # Detail drawer — hidden by default, opened by JS on row click.
        # Starts empty; JS populates from /api/sessions/<runtime>/<session_id>.
        # focus management: JS focuses the first focusable element inside on open.
        # Escape key closes the drawer (wired in sessions.js).
        '  <aside id="session-drawer" class="session-drawer" hidden\n'
        '         role="dialog" aria-modal="true"\n'
        '         aria-label="Session detail">\n'
        '    <div class="session-drawer__header">\n'
        '      <h3 class="session-drawer__title" id="session-drawer-title">'
        "Session detail</h3>\n"
        '      <button type="button" id="drawer-close"\n'
        '              class="session-drawer__close-btn"\n'
        '              aria-label="Close session detail">'
        "Close</button>\n"
        "    </div>\n"
        '    <div class="session-drawer__content">\n'
        "      <!-- Populated by JS after /api/sessions/<runtime>/<id> fetch -->\n"
        "    </div>\n"
        "  </aside>\n"
        "</section>"
    )
