"""Panel index view — renders the full panel HTML with all 3 sections.

Factory: ``render_index(service) -> Callable[..., tuple[int, str, bytes]]``

Security (R3-A / OWASP A03): every operator-controlled string inserted into HTML
is passed through ``html.escape()`` before interpolation. This covers server
``project``, ``url``, context ``name``, ``slug``, ``branch``, and ``group_label``.

SSR-vs-client-side policy
--------------------------
SSR (data inlined into the initial HTML response, no auth required):
  - Contexts (active Spec Context Projects) — small payload, public
  - Servers (server registry grouped by context) — small payload, public
  - Academy initial scaffold — public empty shell; content fetched client-side

Client-side (fetched via XHR/fetch after Bearer auth):
  - Agents    — auth-gated; telemetry-enriched; dynamic
  - Sessions  — auth-gated; large/dynamic; runtime-dependent; rendered as a
                sub-section INSIDE the 1º Agentic Layer (subagents) tabpanel
                (v0.1.79 — the standalone Sessions tab was removed)
  - Workflows — auth-gated; file-system backed
  - Reports   — auth-gated; file-system backed; sidecar-indexed

Primary tabs (v0.1.79 panel agentic-layers reorg — 7 -> 6 tabs):
  Projects | 1º Agentic Layer (id ``tab-subagents``) |
  2º Agentic Layer (id ``tab-workflows``) | Reports | Academy | Servers.
  The 1º Agentic Layer governs Layer-1 Claude sub-agent model+effort
  (v0.1.65 L1 governance) and now also hosts the Sessions cost/telemetry
  dashboard as a sub-section (``render_sessions_section``, appended inside
  ``_render_subagents_section``); the 2º Agentic Layer governs Layer-2
  pi/codex workflow model policy. Tab/section
  ids are unchanged (``tab-subagents``/``section-subagents``,
  ``tab-workflows``/``section-workflows``) — label-only rename plus the
  Sessions relocation. The nav-button order AND the tabpanel body order both
  place 1º Agentic Layer before 2º Agentic Layer (ratified SPEC order); the
  ``.active`` class toggle in core.js is position-independent, but body order
  is kept aligned with button order for visual/reading-order sanity.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence

from dadaia_workspace.features.panel.service import PanelContext, PanelService, ServerGroup
from dadaia_workspace.features.panel.views._md_render import memory_view_url
from dadaia_workspace.features.panel.views.academy import render_academy_section
from dadaia_workspace.features.panel.views.reports import render_reports_section
from dadaia_workspace.features.panel.views.sessions import render_sessions_section
from dadaia_workspace.features.panel.views.static import LOGO_RHINO_36
from dadaia_workspace.features.panel.views.workflows import (
    render_workflows_first_class_section,
)


def render_index(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that renders the panel index page."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        groups = service.list_servers_grouped()
        contexts = service.list_active_contexts()

        servers_html = _render_servers(groups) if groups else _empty_state()

        sorted_contexts = sorted(contexts, key=lambda c: c.slug)
        memories_html = "".join(_render_context_card(c) for c in sorted_contexts)
        context_count = len(contexts)

        academy_section = render_academy_section()
        reports_section = render_reports_section()
        workflows_section = render_workflows_first_class_section()

        body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dadaia Workspace Panel</title>
  <script>(function(){{var t=localStorage.getItem('dadaia-panel-theme');if(t&&(t==='mint'||t==='sage'||t==='warm')){{document.documentElement.dataset.theme=t;}}}})();</script>
  <script>(function(){{var r=localStorage.getItem('dadaia-panel-runtime');if(r&&(r==='claude'||r==='codex'||r==='pi')){{document.documentElement.dataset.runtime=r;}}}})();</script>
  <link rel="stylesheet" href="/static/tokens.css">
  <link rel="stylesheet" href="/static/structure.css">
  <link rel="stylesheet" href="/static/projects.css">
  <link rel="stylesheet" href="/static/workflows.css">
  <link rel="stylesheet" href="/static/workflow-policy.css">
  <link rel="stylesheet" href="/static/agent-policy.css">
  <link rel="stylesheet" href="/static/sessions.css">
  <link rel="stylesheet" href="/static/academy.css">
  <link rel="stylesheet" href="/static/reports.css">
</head>
<body>
  <header class="topbar" role="banner">
    <span class="topbar-logo" aria-hidden="true">{LOGO_RHINO_36}</span>
    <div class="topbar-wordmark">dadaia<span>&#183;</span>workspace</div>
    <div class="topbar-divider" aria-hidden="true"></div>
    <div class="topbar-subtitle">panel</div>
    <div class="topbar-right">
    <div class="theme-switcher">
      <button id="theme-btn" type="button" class="theme-btn"
        aria-haspopup="menu" aria-expanded="false"
        aria-label="Switch colour theme" aria-controls="theme-menu">
        <span class="theme-btn-icon" aria-hidden="true">&#9680;</span>
        <span class="theme-btn-label">Theme</span>
        <span class="theme-btn-caret" aria-hidden="true">&#9660;</span>
      </button>
      <ul id="theme-menu" role="menu" aria-label="Colour themes" hidden>
        <li role="menuitemradio" tabindex="-1" aria-checked="true" data-theme-value="mint">
          <span class="theme-swatch-dot theme-swatch-dot--mint" aria-hidden="true"></span>
          <span class="theme-label">Mint</span>
        </li>
        <li role="menuitemradio" tabindex="-1" aria-checked="false" data-theme-value="sage">
          <span class="theme-swatch-dot theme-swatch-dot--sage" aria-hidden="true"></span>
          <span class="theme-label">Sage</span>
        </li>
        <li role="menuitemradio" tabindex="-1" aria-checked="false" data-theme-value="warm">
          <span class="theme-swatch-dot theme-swatch-dot--warm" aria-hidden="true"></span>
          <span class="theme-label">Warm</span>
        </li>
      </ul>
    </div>
    </div>
  </header>
  <nav class="nav-tabs" aria-label="Panel sections" role="tablist">
    <button class="nav-tab active tab-memories-btn" data-section="memories" aria-selected="true" role="tab" id="tab-memories" aria-label="Projects">Projects</button>
    <button class="nav-tab" data-section="subagents" aria-selected="false" role="tab" id="tab-subagents" aria-label="1º Agentic Layer">1&#186; Agentic Layer</button>
    <button class="nav-tab" data-section="workflows" aria-selected="false" role="tab" id="tab-workflows" aria-label="2º Agentic Layer">2&#186; Agentic Layer</button>
    <button class="nav-tab" data-section="reports" aria-selected="false" role="tab" id="tab-reports">Reports</button>
    <button class="nav-tab" data-section="academy" aria-selected="false" role="tab" id="tab-academy">Academy</button>
    <button class="nav-tab" data-section="servers" aria-selected="false" role="tab" id="tab-servers">Servers</button>
  </nav>
  <main class="main" role="main">

    <section id="section-servers" class="section" aria-label="Running development servers" role="tabpanel" tabindex="0" aria-labelledby="tab-servers">
      <header class="section-header">
        <h2>Servers</h2>
        <p>Dev servers running across active contexts. Auto-refreshes every 5 seconds.</p>
      </header>
      <div class="refresh-notice">
        <span id="refresh-status" aria-hidden="true"></span>
        <span id="refresh-label">Last updated just now</span>
      </div>
      <div id="servers-content">{servers_html}</div>
    </section>

    <section id="section-memories" class="section active" aria-label="Spec Context Project memories" role="tabpanel" tabindex="0" aria-labelledby="tab-memories">
      <header class="section-header">
        <h2>Projects</h2>
        <span class="projects-count-badge">{context_count} projects</span>
      </header>
      <details class="section-desc">
        <summary>About this section</summary>
        <p>Active Spec Context Projects — architecture, tech-stack and product memories for each repo.</p>
      </details>
      <div class="cards-grid" role="list" aria-label="Active Spec Context Projects">
        {memories_html}
      </div>
    </section>

    {_render_subagents_section()}

    {workflows_section}

    {academy_section}

    {reports_section}

  </main>
  <script src="/static/runtime.js"></script>
  <script src="/static/themes.js"></script>
  <script src="/static/core.js"></script>
  <script src="/static/agent-policy.js"></script>
  <script src="/static/workflow-policy.js"></script>
  <script src="/static/sessions.js" defer></script>
  <script src="/static/academy.js"></script>
  <script src="/static/reports.js"></script>
  <!--
    The dadaia-workflow catalog renders each step-sequence diagram as a
    server-rendered SVG DAG (.dadaia-wf-diagram-svg) plus the raw mermaid source
    in a <pre class="mermaid"> block (same convention as memory atoms). No
    client-side mermaid hydration is attempted: the panel is loopback with a
    strict CSP whose script-src is 'self' + hashed inline snippets only — it does
    not allow an external CDN origin, so a CDN mermaid import can never execute.
    The server-rendered SVG is the canonical, offline diagram.
  -->
</body>
</html>"""
        return (200, "text/html; charset=utf-8", body.encode("utf-8"))

    return _view


def _render_subagents_section() -> str:
    """The "1º Agentic Layer" tab scaffold (v0.1.65 FR8; relabeled + Sessions-merged
    v0.1.79) — hydrated by agent_policy.js (roster) and sessions.js (dashboard).

    Static server-rendered shell: section header with the template selector + explicit
    Apply button, the status banner, the roster mount, and the (hidden) post-apply
    pop-up that agent_policy.js fills with the G-2 per-harness pickup instructions.

    v0.1.79 (panel agentic-layers reorg): the standalone Sessions tab was removed —
    its cost/telemetry dashboard (``render_sessions_section``) is now appended as a
    sub-section INSIDE this tabpanel body, after the agent-model-governance roster.
    The ``/api/sessions`` endpoint contract and ``sessions.js`` are unchanged; only
    the DOM placement moved (``#section-sessions`` is now a nested mount, not its
    own tabpanel — see ``sessions.py``).
    """
    return (
        '<section id="section-subagents" class="section" '
        'aria-label="Layer-1 sub-agent model governance" role="tabpanel" tabindex="0" '
        'aria-labelledby="tab-subagents">\n'
        '      <header class="section-header">\n'
        "        <h2>1&#186; Agentic Layer</h2>\n"
        '        <div class="ap-toolbar">\n'
        '          <select id="ap-template-select" class="ap-template-select" '
        'aria-label="Agent model template"></select>\n'
        '          <button id="ap-apply-btn" type="button" class="ap-apply-btn">Apply</button>\n'
        "        </div>\n"
        "      </header>\n"
        '      <details class="section-desc">\n'
        "        <summary>About this section</summary>\n"
        "        <p>Layer-1 agent model governance — pick a template or set per-agent "
        "model/effort overrides, then Apply to re-render both harness projections.</p>\n"
        "      </details>\n"
        '      <div id="ap-banner" class="ap-banner" hidden></div>\n'
        '      <div id="ap-roster" aria-live="polite"></div>\n'
        '      <div id="ap-popup" class="ap-popup" role="dialog" aria-modal="true" '
        'aria-labelledby="ap-popup-title" hidden>\n'
        '        <div class="ap-popup-card">\n'
        '          <h3 id="ap-popup-title">Policy applied</h3>\n'
        '          <div id="ap-popup-body"></div>\n'
        '          <button id="ap-popup-close" type="button" class="ap-popup-close-btn">'
        "Close</button>\n"
        "        </div>\n"
        "      </div>\n"
        f"      {render_sessions_section()}\n"
        "    </section>"
    )


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
    branch = html.escape(ctx.branch or "(unknown)")
    name = html.escape(ctx.name)
    slug = html.escape(ctx.slug)
    zone_c = f'<div class="card-zone-c" data-slug="{slug}" aria-live="polite"></div>'
    return (
        f'<article class="context-card" role="listitem">'
        f'<div class="card-zone-a"><span class="card-name">{name}</span></div>'
        f'<div class="card-zone-b">'
        f'<span class="card-meta-row">repo: <code class="card-mono">{slug}</code></span>'
        f'<span class="card-meta-row">branch: <code class="card-mono">{branch}</code></span>'
        f"</div>"
        f"{zone_c}"
        f'<nav class="card-zone-d card-chips" aria-label="Memory links">'
        f'<a class="memory-chip" href="{memory_view_url(slug, "constitution.md")}">Constitution</a>'
        f'<a class="memory-chip" href="{memory_view_url(slug, "architecture.md")}">Architecture</a>'
        f'<a class="memory-chip" href="{memory_view_url(slug, "tech-stack.md")}">Tech Stack</a>'
        f'<a class="memory-chip" href="{memory_view_url(slug, "quality-assurance.md")}">Quality</a>'
        f'<a class="memory-chip" href="{memory_view_url(slug, "product/index.md")}">Product</a>'
        f"</nav>"
        f"</article>"
    )
