"""Unit tests for views/index.py — T-3.1 / T-3.9.

Covers:
  - HTML contains all 3 section headers
  - Placeholder card copy "Em breve — Release-2" present verbatim
  - Primary context appears first in grid (DOM order)
  - XSS: malicious <script> in project/context fields is html.escape()'d
  - OWASP A03: no raw user-controlled string survives into HTML unescaped

T-P5-01: PANEL_JS and PANEL_CSS removed from _assets.py. Tests that previously
imported them from _assets now build them inline from individual JS/CSS files.
"""

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

# ---------------------------------------------------------------------------
# JS / CSS assembly helpers (T-P5-01: PANEL_JS and PANEL_CSS moved out of _assets)
# ---------------------------------------------------------------------------
_JS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "dadaia_workspace" / "features" / "panel" / "views" / "assets" / "js"
)


def _build_panel_js() -> str:
    return (
        (_JS_DIR / "core.js").read_text(encoding="utf-8")
        + "\n"
        + (_JS_DIR / "agents.js").read_text(encoding="utf-8")
        + "\n"
        + (_JS_DIR / "workflows.js").read_text(encoding="utf-8")
    )


def _build_panel_css() -> str:
    from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
    from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
    from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
    from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS
    return TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS + WORKFLOWS_CSS + SESSIONS_CSS

# ---------------------------------------------------------------------------
# Fakes (same pattern as test_service.py)
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def __init__(self, entries: list[tuple[PortEntry, PortStatus]] | None = None) -> None:
        self._entries = entries or []

    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        if project is None:
            return list(self._entries)
        return [(e, s) for e, s in self._entries if e.project == project]


class FakeSpecContextService:
    def __init__(self, contexts: list[SpecContextProject] | None = None) -> None:
        self._contexts = contexts or []

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


def _make_context(
    name: str,
    repo_slug: str,
    is_primary: bool = False,
    state: ContextState = ContextState.ATIVO,
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=repo_slug,
        repo_url="https://github.com/org/repo",
        is_primary=is_primary,
        created_at="2026-01-01T00:00:00+00:00",
        activated_at="2026-01-01T00:00:00+00:00",
        current_branch="main",
    )


def _make_entry(port: int, project: str) -> tuple[PortEntry, PortStatus]:
    return (
        PortEntry(
            port=port,
            project=project,
            reserved_at="2026-01-01T00:00:00+00:00",
            expires_at="2026-01-01T08:00:00+00:00",
            url=f"http://localhost:{port}",
            pid=None,
            description=None,
        ),
        PortStatus.ACTIVE,
    )


def _build_service(
    entries: list[tuple[PortEntry, PortStatus]] | None = None,
    contexts: list[SpecContextProject] | None = None,
) -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(entries),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(contexts),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
    )


def _render(service: PanelService) -> str:
    view = render_index(service)
    status, content_type, body = view()
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_index_contains_servers_section() -> None:
    """The index HTML must contain the Servers section."""
    service = _build_service()
    html = _render(service)
    assert "section-servers" in html
    assert ">Servers<" in html


def test_index_contains_memories_section() -> None:
    """The index HTML must contain the Projects (section-memories) section.

    T-P5-15: section ID remains 'section-memories' for backward compat;
    the visible heading changes from 'Memories' to 'Projects'.
    """
    service = _build_service()
    html = _render(service)
    assert "section-memories" in html
    assert ">Projects<" in html


def test_index_contains_agents_section() -> None:
    """The index HTML must contain the Agents & Workflows section."""
    service = _build_service()
    html = _render(service)
    assert "section-agents" in html
    assert "Agents" in html


def test_index_agents_section_has_grid() -> None:
    """T-AM-18: agents section replaced placeholder with real grid scaffold."""
    service = _build_service()
    html = _render(service)
    assert 'id="agents-grid"' in html


def test_index_primary_context_badge() -> None:
    """Primary context topbar badge must still show; card-level badge removed in T-P5-16."""
    ctx = _make_context("My Workspace", "my-workspace", is_primary=True)
    service = _build_service(contexts=[ctx])
    html = _render(service)
    # T-P5-16: card-primary-badge removed — all cards are uniform
    assert "card-primary-badge" not in html
    # Topbar badge remains for primary context identification
    assert "topbar-badge" in html


def test_index_primary_context_first_in_dom() -> None:
    """Primary context card must appear before non-primary cards in DOM order."""
    primary = _make_context("Primary", "primary-slug", is_primary=True)
    other = _make_context("Other", "other-slug", is_primary=False)
    service = _build_service(contexts=[other, primary])  # other listed first
    html = _render(service)

    # Primary's slug should appear before other's slug in the HTML
    pos_primary = html.find("primary-slug")
    pos_other = html.find("other-slug")
    assert pos_primary < pos_other, "Primary context card must come first in DOM"


def test_index_xss_project_name_escaped() -> None:
    """R3-A: <script> in project name must be HTML-escaped, never raw."""
    malicious_project = "<script>alert(1)</script>"
    entry = _make_entry(port=3000, project=malicious_project)
    service = _build_service(entries=[entry])
    html = _render(service)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_index_xss_context_name_escaped() -> None:
    """R3-A: <script> in context name must be HTML-escaped."""
    ctx = _make_context(
        name='<script>alert("xss")</script>',
        repo_slug="safe-slug",
    )
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert '<script>alert("xss")</script>' not in html
    assert "&lt;script&gt;" in html


def test_index_xss_branch_escaped() -> None:
    """R3-A: <script> in branch name must be HTML-escaped."""
    ctx = SpecContextProject(
        name="safe-name",
        state=ContextState.ATIVO,
        repo_slug="safe-slug",
        repo_url="https://github.com/org/repo",
        is_primary=False,
        created_at="2026-01-01T00:00:00+00:00",
        activated_at="2026-01-01T00:00:00+00:00",
        current_branch="<script>alert(1)</script>",
    )
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_index_empty_servers_shows_empty_state() -> None:
    """When registry is empty, empty-state hint must be present."""
    service = _build_service(entries=[], contexts=[])
    html = _render(service)
    assert "Nenhum servidor rodando" in html


def test_index_returns_bytes() -> None:
    """View must return (int, str, bytes) tuple."""
    service = _build_service()
    view = render_index(service)
    result = view()
    assert isinstance(result, tuple)
    assert len(result) == 3
    status, ct, body = result
    assert isinstance(status, int)
    assert isinstance(ct, str)
    assert isinstance(body, bytes)


# ---------------------------------------------------------------------------
# T-AM-01: A11y role snapshot tests
# ---------------------------------------------------------------------------


def test_nav_has_role_tablist() -> None:
    """T-AM-01: <nav class="nav-tabs"> must carry role="tablist"."""
    service = _build_service()
    html = _render(service)
    assert 'role="tablist"' in html


def test_tab_servers_has_id() -> None:
    """T-AM-01: Servers tab button must have id="tab-servers"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-servers"' in html


def test_tab_memories_has_id() -> None:
    """T-AM-01: Memories tab button must have id="tab-memories"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-memories"' in html


def test_tab_agents_has_id() -> None:
    """T-AM-01: Agents tab button must have id="tab-agents"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-agents"' in html


def test_section_servers_has_tabpanel_role() -> None:
    """T-AM-01: section#section-servers must have role="tabpanel"."""
    service = _build_service()
    html = _render(service)
    assert 'id="section-servers"' in html
    # Verify role=tabpanel appears somewhere before closing of the section
    assert 'role="tabpanel"' in html


def test_section_servers_has_aria_labelledby() -> None:
    """T-AM-01: section#section-servers must have aria-labelledby="tab-servers"."""
    service = _build_service()
    html = _render(service)
    assert 'aria-labelledby="tab-servers"' in html


def test_section_memories_has_aria_labelledby() -> None:
    """T-AM-01: section#section-memories must have aria-labelledby="tab-memories"."""
    service = _build_service()
    html = _render(service)
    assert 'aria-labelledby="tab-memories"' in html


def test_section_agents_has_aria_labelledby() -> None:
    """T-AM-01: section#section-agents must have aria-labelledby="tab-agents"."""
    service = _build_service()
    html = _render(service)
    assert 'aria-labelledby="tab-agents"' in html


def test_sections_have_tabindex_zero() -> None:
    """T-AM-01: all tabpanel sections must have tabindex="0"."""
    service = _build_service()
    html = _render(service)
    assert html.count('tabindex="0"') >= 3


def test_tabpanel_count_is_three() -> None:
    """T-AM-01/T-AM-18/PR5-C4/T-P5-26/T-P5-34: 7 role=tabpanel elements after Reports section added.

    Count history: 3 → 5 (Sessions added in PR5-C4) → 6 (Academy added in T-P5-26)
                     → 7 (Reports added in T-P5-34).
    """
    service = _build_service()
    html = _render(service)
    assert html.count('role="tabpanel"') == 7


def test_panel_js_contains_keydown_handler() -> None:
    """T-AM-01: PANEL_JS must include keyboard navigation for ArrowRight/ArrowLeft/Home/End."""
    panel_js = _build_panel_js()
    assert "ArrowRight" in panel_js
    assert "ArrowLeft" in panel_js
    assert "Home" in panel_js
    assert "End" in panel_js
    assert "keydown" in panel_js


# ---------------------------------------------------------------------------
# T-AM-18: 4th nav-tab (Workflows) wired into index
# ---------------------------------------------------------------------------


def test_has_workflows_tab() -> None:
    """T-AM-18: nav must contain a tab with id="tab-workflows"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-workflows"' in html


def test_has_workflows_section() -> None:
    """T-AM-18: rendered HTML must contain id="section-workflows"."""
    service = _build_service()
    html = _render(service)
    assert 'id="section-workflows"' in html


def test_aria_pairs_workflows() -> None:
    """T-AM-18: section has aria-labelledby="tab-workflows" and tab has id="tab-workflows"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-workflows"' in html
    assert 'aria-labelledby="tab-workflows"' in html


def test_nav_has_4_tabs() -> None:
    """T-AM-18/PR5-C4/T-P5-35: nav-tabs must contain exactly 7 tab buttons after Reports and Academy tabs added."""
    service = _build_service()
    html = _render(service)
    # Count role="tab" occurrences (Memories, Agents, Workflows, Sessions, Reports, Academy, Servers)
    assert html.count('role="tab"') == 7


# ---------------------------------------------------------------------------
# PR5-C4 — Sessions tab wired into index
# ---------------------------------------------------------------------------


def test_has_sessions_tab() -> None:
    """PR5-C4: nav must contain a tab with id="tab-sessions"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-sessions"' in html


def test_has_sessions_section() -> None:
    """PR5-C4: rendered HTML must contain id="section-sessions"."""
    service = _build_service()
    html = _render(service)
    assert 'id="section-sessions"' in html


def test_aria_pairs_sessions() -> None:
    """PR5-C4: section has aria-labelledby="tab-sessions" and tab has id="tab-sessions"."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-sessions"' in html
    assert 'aria-labelledby="tab-sessions"' in html


def test_sessions_css_link_present() -> None:
    """PR5-C4: rendered HTML must include sessions.css link."""
    service = _build_service()
    html = _render(service)
    assert "/static/sessions.css" in html


def test_sessions_js_script_present() -> None:
    """PR5-C4: rendered HTML must include sessions.js script tag."""
    service = _build_service()
    html = _render(service)
    assert "/static/sessions.js" in html


# ---------------------------------------------------------------------------
# Bug 2 — memory link labels (panel-defects hotfix)
# ---------------------------------------------------------------------------


def test_memory_link_label_architecture() -> None:
    """panel-defects Bug 2: architecture link must show 'Architecture', not filename."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert ">Architecture<" in html
    assert ">architecture.html<" not in html


def test_memory_link_label_tech_stack() -> None:
    """panel-defects Bug 2: tech-stack link must show 'Tech Stack', not filename."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert ">Tech Stack<" in html
    assert ">tech-stack.html<" not in html


def test_memory_link_label_product() -> None:
    """panel-defects Bug 2: product link must show 'Product', not filename."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert ">Product<" in html
    assert ">product/index.html<" not in html


def test_memory_link_hrefs_unchanged() -> None:
    """panel-defects Bug 2: hrefs must remain unchanged after label fix."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert 'href="/memory-view/my-workspace/architecture.html"' in html
    assert 'href="/memory-view/my-workspace/tech-stack.html"' in html
    assert 'href="/memory-view/my-workspace/product/index.html"' in html


# ---------------------------------------------------------------------------
# Bug 3 — token management (panel-defects hotfix)
# ---------------------------------------------------------------------------


def test_panel_js_has_token_bootstrap() -> None:
    """panel-defects Bug 3: PANEL_JS must include token bootstrap from URLSearchParams."""
    panel_js = _build_panel_js()
    assert "panel_token" in panel_js
    assert "sessionStorage" in panel_js
    assert "URLSearchParams" in panel_js
    assert "history.replaceState" in panel_js


def test_panel_js_has_authed_fetch_wrapper() -> None:
    """panel-defects Bug 3: PANEL_JS must define authedFetch with Bearer header."""
    panel_js = _build_panel_js()
    assert "authedFetch" in panel_js
    assert "Authorization" in panel_js
    assert "Bearer" in panel_js


def test_panel_js_agents_uses_authed_fetch() -> None:
    """panel-defects Bug 3: Agents.load must use authedFetch, not bare fetch."""
    panel_js = _build_panel_js()
    assert "authedFetch('/api/agents" in panel_js


def test_panel_js_workflows_uses_authed_fetch() -> None:
    """panel-defects Bug 3+4 (updated PR5-D6): Workflows.load must use authedFetch.

    PR5-D6 (runtime retrofit): URL now includes ?runtime= query param so the
    fetch reads authedFetch('/api/workflows?runtime=' + ...).
    """
    panel_js = _build_panel_js()
    assert "authedFetch('/api/workflows?runtime='" in panel_js


def test_panel_js_sessions_uses_authed_fetch() -> None:
    """panel-defects Bug 3 (updated PR3-10 + PR5-D5): agents.js must call authedFetch for /api/agents.

    PR3-10 (collapsed card): initial list fetch via authedFetch('/api/agents').
    PR5-D5 (runtime retrofit): URL now includes ?runtime= query param so the
    fetch reads authedFetch('/api/agents?runtime=' + ...).
    The assertion checks the URL prefix which is stable regardless of the query
    string appended dynamically at runtime.
    """
    panel_js = _build_panel_js()
    assert "authedFetch('/api/agents?runtime='" in panel_js


# ---------------------------------------------------------------------------
# PR3-06 — Tab rename + reorder + responsive label
# ---------------------------------------------------------------------------


def test_tab_memories_visible_label_is_spec_context_projects() -> None:
    """PR3-06: The visible label on #tab-memories must be 'Spec Context Projects'."""
    service = _build_service()
    html = _render(service)
    # The button text must show the new label
    assert "Spec Context Projects" in html
    # The tab button must NOT use the old "Memories" label as its text
    # (the word may still appear in the section <h2>, but the nav button must say
    # "Spec Context Projects"). Check the button content specifically.
    assert ">Spec Context Projects<" in html
    # The tab-memories button must not still read ">Memories<" as its own label.
    # Note: <h2>Memories</h2> is allowed inside the section — only the button label matters.
    idx = html.find('id="tab-memories"')
    # Grab the button tag up to the closing </button>
    close_tag = html.find("</button>", idx)
    button_fragment = html[idx:close_tag]
    assert "Memories" not in button_fragment, (
        "tab-memories button text must be 'Spec Context Projects', not 'Memories'"
    )


def test_tab_memories_aria_label_is_spec_context_projects() -> None:
    """PR3-06: aria-label on tab-memories must be 'Spec Context Projects'."""
    service = _build_service()
    html = _render(service)
    assert 'aria-label="Spec Context Projects"' in html


def test_tab_memories_id_unchanged() -> None:
    """PR3-06: Internal ID tab-memories must remain so #memories hash still works."""
    service = _build_service()
    html = _render(service)
    assert 'id="tab-memories"' in html


def test_tab_spec_context_projects_is_active_default() -> None:
    """PR3-06: Default-active tab must be Spec Context Projects (tab-memories)."""
    service = _build_service()
    html = _render(service)
    # The tab-memories button must carry the 'active' class
    assert 'id="tab-memories"' in html
    # Verify active class and aria-selected=true are on tab-memories
    # The active tab button must have aria-selected="true"
    assert 'id="tab-memories"' in html
    # Find the substring containing tab-memories and verify active class is present
    idx = html.find('id="tab-memories"')
    # Look for 'active' in the surrounding tag (within 200 chars before the id)
    surrounding = html[max(0, idx - 200) : idx + 100]
    assert "active" in surrounding, "tab-memories button must have active class"
    assert 'aria-selected="true"' in surrounding


def test_tab_order_spec_context_first_before_agents() -> None:
    """PR3-06: Spec Context Projects tab must appear before Agents tab in DOM."""
    service = _build_service()
    html = _render(service)
    pos_memories = html.find('id="tab-memories"')
    pos_agents = html.find('id="tab-agents"')
    assert pos_memories < pos_agents, "tab-memories must come before tab-agents"


def test_tab_order_agents_before_workflows() -> None:
    """PR3-06: Agents tab must appear before Workflows tab in DOM."""
    service = _build_service()
    html = _render(service)
    pos_agents = html.find('id="tab-agents"')
    pos_workflows = html.find('id="tab-workflows"')
    assert pos_agents < pos_workflows, "tab-agents must come before tab-workflows"


def test_tab_order_workflows_before_servers() -> None:
    """PR3-06: Workflows tab must appear before Servers tab in DOM."""
    service = _build_service()
    html = _render(service)
    pos_workflows = html.find('id="tab-workflows"')
    pos_servers = html.find('id="tab-servers"')
    assert pos_workflows < pos_servers, "tab-workflows must come before tab-servers"


def test_servers_tab_not_active_by_default() -> None:
    """PR3-06: Servers tab must NOT be the default-active tab."""
    service = _build_service()
    html = _render(service)
    idx = html.find('id="tab-servers"')
    surrounding = html[max(0, idx - 200) : idx + 100]
    assert 'aria-selected="false"' in surrounding, "tab-servers must not be active"


def test_responsive_css_abbreviation_rule_present() -> None:
    """PR3-06: structure.py must contain a <768px CSS rule abbreviating the tab label."""
    from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS

    assert "@media" in STRUCTURE_CSS
    assert "768px" in STRUCTURE_CSS
    assert "Spec Contexts" in STRUCTURE_CSS


# ---------------------------------------------------------------------------
# Bug 4 — Workflows 2-pane redesign (panel-defects hotfix)
# ---------------------------------------------------------------------------


def test_panel_js_workflows_has_card_grid() -> None:
    """PR3-16: PANEL_JS must render workflow-card elements in a card grid.

    The old 2-pane stepper (buildStepperSVG) was replaced by the card-grid
    layout in PR3-16. This test verifies the new card-grid JS is present
    in workflows.js (included in assembled JS).
    """
    panel_js = _build_panel_js()
    assert "workflow-card" in panel_js
    assert "data-workflow-name" in panel_js


def test_panel_js_workflows_exposes_window_workflows() -> None:
    """PR3-16: PANEL_JS must include window.Workflows from workflows.js."""
    panel_js = _build_panel_js()
    assert "window.Workflows" in panel_js
    assert "/api/workflows" in panel_js


def test_panel_css_has_workflows_pane_layout() -> None:
    """panel-defects Bug 4: PANEL_CSS must contain 2-pane grid layout."""
    panel_css = _build_panel_css()
    assert ".workflows-pane" in panel_css
    assert ".workflows-list" in panel_css
    assert ".workflows-detail" in panel_css
    assert "workflow-list-item" in panel_css


# ---------------------------------------------------------------------------
# T-P5-15 — Projects tab section header redesign
# ---------------------------------------------------------------------------


def test_projects_section_heading_is_projects() -> None:
    """T-P5-15: section-memories <h2> must read 'Projects', not 'Memories'."""
    service = _build_service()
    rendered = _render(service)
    # Find the section-memories block and check h2 inside it
    idx = rendered.find('id="section-memories"')
    end = rendered.find('</section>', idx)
    section_frag = rendered[idx:end]
    assert "<h2>Projects</h2>" in section_frag, "h2 inside section-memories must read 'Projects'"


def test_projects_section_no_old_count_label() -> None:
    """T-P5-15: 'N active contexts — 1 primary' count label must be removed from section-memories."""
    ctx = _make_context("My Workspace", "my-workspace", is_primary=True)
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    # Find only the memories section fragment
    idx = rendered.find('id="section-memories"')
    end = rendered.find('</section>', idx)
    section_frag = rendered[idx:end]
    assert "context-count" not in section_frag, "Old context-count CSS class must be removed"
    # The old count label format was "N active contexts — 1 primary" as a <p class="context-count">
    # After redesign it should be a badge with "N projects" only
    assert "primary" not in section_frag or "projects-count-badge" in section_frag, (
        "Old primary count text must be removed from section header"
    )


def test_projects_section_has_count_badge() -> None:
    """T-P5-15: section-header must contain a projects-count-badge span with N projects text."""
    ctx1 = _make_context("Workspace 1", "ws-1")
    ctx2 = _make_context("Workspace 2", "ws-2")
    service = _build_service(contexts=[ctx1, ctx2])
    rendered = _render(service)
    assert 'class="projects-count-badge"' in rendered
    assert "2 projects" in rendered


def test_projects_section_has_collapsible_description() -> None:
    """T-P5-15: A <details class='section-desc'> block must follow section-header."""
    service = _build_service()
    rendered = _render(service)
    assert 'class="section-desc"' in rendered
    assert "<summary>About this section</summary>" in rendered
    assert "Active Spec Context Projects" in rendered


# ---------------------------------------------------------------------------
# T-P5-16 — Projects card redesign
# ---------------------------------------------------------------------------


def test_projects_card_has_zone_a() -> None:
    """T-P5-16: Card must have card-zone-a with card-name span."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert 'class="card-zone-a"' in rendered
    assert 'class="card-name"' in rendered


def test_projects_card_zone_b_has_repo_and_branch_rows() -> None:
    """T-P5-16: Zone B must have two card-meta-row spans — repo and branch."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert 'class="card-zone-b"' in rendered
    assert "repo:" in rendered
    assert "branch:" in rendered
    assert 'class="card-meta-row"' in rendered


def test_projects_card_zone_d_has_memory_chips() -> None:
    """T-P5-16: Zone D must have three memory-chip links — Architecture, Tech Stack, Product."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert 'class="card-zone-d card-chips"' in rendered
    assert 'class="memory-chip"' in rendered
    # All three chip labels present
    assert ">Architecture<" in rendered
    assert ">Tech Stack<" in rendered
    assert ">Product<" in rendered


def test_projects_card_no_primary_badge() -> None:
    """T-P5-16: PRIMARY badge must be removed — no card-primary-badge class."""
    ctx = _make_context("My Workspace", "my-workspace", is_primary=True)
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert "card-primary-badge" not in rendered, "PRIMARY badge must be removed in redesign"


def test_projects_card_no_primary_class() -> None:
    """T-P5-16: No 'primary' CSS class on article — uniform card treatment."""
    ctx = _make_context("My Workspace", "my-workspace", is_primary=True)
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    # The article should not have class="context-card primary"
    assert 'class="context-card primary"' not in rendered, (
        "Primary context must not get special 'primary' CSS class"
    )


def test_projects_card_memory_chip_hrefs() -> None:
    """T-P5-16: Memory chip hrefs must point to correct memory URLs."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert 'href="/memory-view/my-workspace/architecture.html"' in rendered
    assert 'href="/memory-view/my-workspace/tech-stack.html"' in rendered
    assert 'href="/memory-view/my-workspace/product/index.html"' in rendered


def test_projects_css_link_present() -> None:
    """T-P5-16: rendered HTML must include projects.css link."""
    service = _build_service()
    rendered = _render(service)
    assert "/static/projects.css" in rendered


# ---------------------------------------------------------------------------
# T-P5-16 — projects.py CSS module (tokens + static serving)
# ---------------------------------------------------------------------------


def test_projects_css_has_color_chip_memory_bg_token() -> None:
    """T-P5-16: tokens.py must define --color-chip-memory-bg custom property."""
    from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
    assert "--color-chip-memory-bg" in TOKENS_CSS


def test_projects_css_module_exists_and_nonempty() -> None:
    """T-P5-16: projects.py CSS module must exist and export non-empty PROJECTS_CSS."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    assert isinstance(PROJECTS_CSS, str)
    assert len(PROJECTS_CSS) > 0


def test_projects_css_registered_in_static() -> None:
    """T-P5-16: projects.css must be registered and served from /static/."""
    from dadaia_workspace.features.panel.views.static import render_static
    view = render_static()
    status, ct, body = view(name="projects.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"
    assert len(body) > 0


def test_projects_css_has_memory_chip_styles() -> None:
    """T-P5-16: PROJECTS_CSS must contain .memory-chip styles."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    assert ".memory-chip" in PROJECTS_CSS
    assert "--color-chip-memory-bg" in PROJECTS_CSS
    assert "--color-accent" in PROJECTS_CSS


def test_projects_css_has_card_zones() -> None:
    """T-P5-16: PROJECTS_CSS must contain card zone styles."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    assert ".card-zone-a" in PROJECTS_CSS
    assert ".card-zone-b" in PROJECTS_CSS
    assert ".card-zone-d" in PROJECTS_CSS
    assert ".card-name" in PROJECTS_CSS
    assert ".card-meta-row" in PROJECTS_CSS


def test_projects_css_has_context_card_accent() -> None:
    """T-P5-16: .context-card must have 4px solid var(--color-accent) left border."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    assert ".context-card" in PROJECTS_CSS
    assert "border-left" in PROJECTS_CSS


# ---------------------------------------------------------------------------
# T-P5-17 — Zone C (session binding placeholder)
# ---------------------------------------------------------------------------


def test_projects_card_has_zone_c() -> None:
    """T-P5-17: Card must have card-zone-c div with data-slug attribute."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    assert 'class="card-zone-c"' in rendered
    assert 'data-slug="my-workspace"' in rendered
    assert 'aria-live="polite"' in rendered


def test_projects_card_zone_c_between_b_and_d() -> None:
    """T-P5-17: Zone C must appear between Zone B and Zone D in card HTML."""
    ctx = _make_context("My Workspace", "my-workspace")
    service = _build_service(contexts=[ctx])
    rendered = _render(service)
    pos_b = rendered.find('class="card-zone-b"')
    pos_c = rendered.find('class="card-zone-c"')
    pos_d = rendered.find('class="card-zone-d')
    assert pos_b < pos_c < pos_d, "Zone C must appear between Zone B and Zone D"


def test_projects_css_has_zone_c_styles() -> None:
    """T-P5-17: PROJECTS_CSS must contain .card-zone-c and .session-row styles."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    assert ".card-zone-c" in PROJECTS_CSS
    assert ".session-row" in PROJECTS_CSS
    assert "--color-session-bg" in PROJECTS_CSS


def test_tokens_css_has_color_session_bg() -> None:
    """T-P5-17: tokens.py must define --color-session-bg custom property."""
    from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
    assert "--color-session-bg" in TOKENS_CSS
