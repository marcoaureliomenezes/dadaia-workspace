"""Panel index view — renders the full panel HTML with all 3 sections.

Factory: ``render_index(service) -> Callable[..., tuple[int, str, bytes]]``

Security (R3-A / OWASP A03): every operator-controlled string inserted into HTML
is passed through ``html.escape()`` before interpolation. This covers server
``project``, ``url``, context ``name``, ``slug``, ``branch``, and ``group_label``.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence

from dadaia_workspace.features.panel.service import PanelContext, PanelService, ServerGroup
from dadaia_workspace.features.panel.views._assets import LOGO_RHINO_24
from dadaia_workspace.features.panel.views.agents import render_agents_section
from dadaia_workspace.features.panel.views.sessions import render_sessions_section
from dadaia_workspace.features.panel.views.workflows import render_workflows_section


def render_index(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that renders the panel index page."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        groups = service.list_servers_grouped()
        contexts = service.list_active_contexts()

        primary = next((c for c in contexts if c.is_primary), None)
        primary_badge = (
            f'<div class="topbar-badge">primary: {html.escape(primary.slug)}</div>'
            if primary
            else ""
        )

        servers_html = _render_servers(groups) if groups else _empty_state()

        # Primary context first (auto-fill grid respects DOM order)
        sorted_contexts = sorted(contexts, key=lambda c: (not c.is_primary,))
        memories_html = "".join(_render_context_card(c) for c in sorted_contexts)
        context_count = len(contexts)
        primary_count = sum(1 for c in contexts if c.is_primary)
        count_label = (
            f'<p class="context-count">'
            f"<strong>{context_count}</strong> active contexts"
            f" &mdash; {primary_count} primary"
            f"</p>"
        )

        agents_section = render_agents_section()
        workflows_section = render_workflows_section()
        sessions_section = render_sessions_section()

        body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dadaia Workspace Panel</title>
  <script>(function(){{var t=localStorage.getItem('dadaia-panel-theme');if(t&&(t==='mint'||t==='sage'||t==='warm')){{document.documentElement.dataset.theme=t;}}}})();</script>
  <link rel="stylesheet" href="/static/tokens.css">
  <link rel="stylesheet" href="/static/structure.css">
  <link rel="stylesheet" href="/static/agents.css">
  <link rel="stylesheet" href="/static/workflows.css">
  <link rel="stylesheet" href="/static/sessions.css">
</head>
<body>
  <header class="topbar" role="banner">
    <span class="topbar-logo" aria-hidden="true">{LOGO_RHINO_24}</span>
    <div class="topbar-wordmark">dadaia<span>&#183;</span>workspace</div>
    <div class="topbar-divider" aria-hidden="true"></div>
    <div class="topbar-subtitle">panel</div>
    <div class="topbar-right" style="margin-left:auto;display:flex;align-items:center;gap:0.5rem;">
    {primary_badge}
    <div class="theme-switcher" style="position:relative;">
      <button id="theme-btn" type="button" class="theme-btn"
        aria-haspopup="menu" aria-expanded="false"
        aria-label="Switch colour theme" aria-controls="theme-menu">
        <span class="theme-btn-icon" aria-hidden="true">&#9680;</span>
        <span class="theme-btn-label">Theme</span>
      </button>
      <ul id="theme-menu" role="menu" aria-label="Colour themes" hidden>
        <li role="menuitemradio" tabindex="-1" aria-checked="true" data-theme-value="mint">Mint</li>
        <li role="menuitemradio" tabindex="-1" aria-checked="false" data-theme-value="sage">Sage</li>
        <li role="menuitemradio" tabindex="-1" aria-checked="false" data-theme-value="warm">Warm</li>
      </ul>
    </div>
    </div>
  </header>
  <nav class="nav-tabs" aria-label="Panel sections" role="tablist">
    <button class="nav-tab active tab-memories-btn" data-section="memories" aria-selected="true" role="tab" id="tab-memories" aria-label="Spec Context Projects">Spec Context Projects</button>
    <button class="nav-tab" data-section="agents" aria-selected="false" role="tab" id="tab-agents">Agents</button>
    <button class="nav-tab" data-section="workflows" aria-selected="false" role="tab" id="tab-workflows">Workflows</button>
    <button class="nav-tab" data-section="servers" aria-selected="false" role="tab" id="tab-servers">Servers</button>
    <button class="nav-tab" data-section="sessions" aria-selected="false" role="tab" id="tab-sessions">Sessions</button>
  </nav>
  <main class="main" role="main">

    <section id="section-servers" class="section" aria-label="Running development servers" role="tabpanel" tabindex="0" aria-labelledby="tab-servers">
      <div class="section-header">
        <h2>Servers</h2>
        <p>Dev servers running across active contexts. Auto-refreshes every 5 seconds.</p>
      </div>
      <div class="refresh-notice">
        <span id="refresh-status" aria-hidden="true"></span>
        <span id="refresh-label">Last updated just now</span>
      </div>
      <div id="servers-content">{servers_html}</div>
    </section>

    <section id="section-memories" class="section active" aria-label="Spec Context Project memories" role="tabpanel" tabindex="0" aria-labelledby="tab-memories">
      <div class="section-header">
        <h2>Memories</h2>
        <p>Architecture, tech-stack and product memories for each active Spec Context Project.</p>
      </div>
      {count_label}
      <div class="cards-grid" role="list" aria-label="Active Spec Context Projects">
        {memories_html}
      </div>
    </section>

    {agents_section}

    {workflows_section}

    {sessions_section}

  </main>
  <script src="/static/themes.js"></script>
  <script src="/static/core.js"></script>
  <script src="/static/agents.js"></script>
  <script src="/static/workflows.js"></script>
  <script src="/static/sessions.js" defer></script>
</body>
</html>"""
        return (200, "text/html; charset=utf-8", body.encode("utf-8"))

    return _view


def _empty_state() -> str:
    return (
        '<div class="empty-state">'
        "Nenhum servidor rodando. "
        "Rode <code>dadaia server register --port X --project Y</code>."
        "</div>"
    )


def _render_servers(groups: Sequence[ServerGroup]) -> str:
    parts: list[str] = []
    for group in groups:
        label = html.escape(group.group_label)
        parts.append(f'<div class="group-label">{label}</div>')
        parts.append('<table class="servers-table"><thead><tr>')
        parts.append(
            "<th>Port</th><th>Project</th><th>URL</th>"
            "<th>Status</th><th>TTL restante</th><th>PID</th>"
        )
        parts.append("</tr></thead><tbody>")
        for row in group.rows:
            status_class = "status-active" if row.status == "active" else "status-stale"
            symbol = "&#9679;" if row.status == "active" else "&#9675;"
            url_cell = (
                f'<a href="{html.escape(row.url)}" target="_blank" rel="noopener noreferrer">'
                f"{html.escape(row.url)}</a>"
                if row.url
                else "&mdash;"
            )
            pid_cell = f"<code>{html.escape(str(row.pid))}</code>" if row.pid else "&mdash;"
            parts.append(
                f"<tr>"
                f'<td><span class="port-badge">{html.escape(str(row.port))}</span></td>'
                f"<td>{html.escape(row.project)}</td>"
                f"<td>{url_cell}</td>"
                f'<td><span class="{status_class}">{symbol} {html.escape(str(row.status))}</span></td>'
                f"<td>{html.escape(row.expires_at)}</td>"
                f"<td>{pid_cell}</td>"
                f"</tr>"
            )
        parts.append("</tbody></table>")
    return "".join(parts)


def _render_context_card(ctx: PanelContext) -> str:
    primary_class = " primary" if ctx.is_primary else ""
    badge = (
        '<div class="card-primary-badge" aria-label="Primary context">primary</div>'
        if ctx.is_primary
        else ""
    )
    branch = html.escape(ctx.branch or "(unknown)")
    name = html.escape(ctx.name)
    slug = html.escape(ctx.slug)
    return (
        f'<article class="context-card{primary_class}" role="listitem">'
        f'<div class="card-header">'
        f'<div class="card-name">{name}</div>'
        f"{badge}"
        f"</div>"
        f'<div class="card-meta">'
        f"<span>repo: <code>{slug}</code></span>"
        f"<span>branch: <code>{branch}</code></span>"
        f"</div>"
        f'<nav class="card-links">'
        f'<a class="memory-link" href="/memory-view/{slug}/architecture.html">'
        f'<span class="memory-link-icon" aria-hidden="true">&#9632;</span>'
        f'<span class="memory-link-label">Architecture</span>'
        f'<span class="memory-link-arrow" aria-hidden="true">&#8594;</span>'
        f"</a>"
        f'<a class="memory-link" href="/memory-view/{slug}/tech-stack.html">'
        f'<span class="memory-link-icon" aria-hidden="true">&#9632;</span>'
        f'<span class="memory-link-label">Tech Stack</span>'
        f'<span class="memory-link-arrow" aria-hidden="true">&#8594;</span>'
        f"</a>"
        f'<a class="memory-link" href="/memory-view/{slug}/product/index.html">'
        f'<span class="memory-link-icon" aria-hidden="true">&#9632;</span>'
        f'<span class="memory-link-label">Product</span>'
        f'<span class="memory-link-arrow" aria-hidden="true">&#8594;</span>'
        f"</a>"
        f"</nav>"
        f"</article>"
    )
