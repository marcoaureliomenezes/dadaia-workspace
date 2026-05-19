"""Unit tests for views/index.py — T-3.1 / T-3.9.

Covers:
  - HTML contains all 3 section headers
  - Placeholder card copy "Em breve — Release-2" present verbatim
  - Primary context appears first in grid (DOM order)
  - XSS: malicious <script> in project/context fields is html.escape()'d
  - OWASP A03: no raw user-controlled string survives into HTML unescaped
"""

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

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
    """The index HTML must contain the Memories section."""
    service = _build_service()
    html = _render(service)
    assert "section-memories" in html
    assert ">Memories<" in html


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
    """Primary context must show the primary badge."""
    ctx = _make_context("My Workspace", "my-workspace", is_primary=True)
    service = _build_service(contexts=[ctx])
    html = _render(service)
    assert "card-primary-badge" in html
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
    """T-AM-01/T-AM-18/PR5-C4: there must be exactly 5 role=tabpanel elements after Sessions tab added."""
    service = _build_service()
    html = _render(service)
    assert html.count('role="tabpanel"') == 5


def test_panel_js_contains_keydown_handler() -> None:
    """T-AM-01: PANEL_JS must include keyboard navigation for ArrowRight/ArrowLeft/Home/End."""
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    assert "ArrowRight" in PANEL_JS
    assert "ArrowLeft" in PANEL_JS
    assert "Home" in PANEL_JS
    assert "End" in PANEL_JS
    assert "keydown" in PANEL_JS


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
    """T-AM-18/PR5-C4: nav-tabs must contain exactly 5 tab buttons after Sessions tab added."""
    service = _build_service()
    html = _render(service)
    # Count role="tab" occurrences (Memories, Agents, Workflows, Servers, Sessions)
    assert html.count('role="tab"') == 5


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
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    assert "panel_token" in PANEL_JS
    assert "sessionStorage" in PANEL_JS
    assert "URLSearchParams" in PANEL_JS
    assert "history.replaceState" in PANEL_JS


def test_panel_js_has_authed_fetch_wrapper() -> None:
    """panel-defects Bug 3: PANEL_JS must define authedFetch with Bearer header."""
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    assert "authedFetch" in PANEL_JS
    assert "Authorization" in PANEL_JS
    assert "Bearer" in PANEL_JS


def test_panel_js_agents_uses_authed_fetch() -> None:
    """panel-defects Bug 3: Agents.load must use authedFetch, not bare fetch."""
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    # authedFetch must be called for the agents endpoint
    assert "authedFetch('/api/agents" in PANEL_JS


def test_panel_js_workflows_uses_authed_fetch() -> None:
    """panel-defects Bug 3+4 (updated PR5-D6): Workflows.load must use authedFetch.

    PR5-D6 (runtime retrofit): URL now includes ?runtime= query param so the
    fetch reads authedFetch('/api/workflows?runtime=' + ...).
    """
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    assert "authedFetch('/api/workflows?runtime='" in PANEL_JS


def test_panel_js_sessions_uses_authed_fetch() -> None:
    """panel-defects Bug 3 (updated PR3-10 + PR5-D5): agents.js must call authedFetch for /api/agents.

    PR3-10 (collapsed card): initial list fetch via authedFetch('/api/agents').
    PR5-D5 (runtime retrofit): URL now includes ?runtime= query param so the
    fetch reads authedFetch('/api/agents?runtime=' + ...).
    The assertion checks the URL prefix which is stable regardless of the query
    string appended dynamically at runtime.
    """
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    # agents.js (in PANEL_JS) calls authedFetch with /api/agents base URL (PR5-D5 appends ?runtime=)
    assert "authedFetch('/api/agents?runtime='" in PANEL_JS


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
    in workflows.js (included in PANEL_JS).
    """
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    # The card grid renderer must reference the .workflow-card element class
    assert "workflow-card" in PANEL_JS
    # The CTA affordance must carry data-workflow-name for PR3-17 to wire
    assert "data-workflow-name" in PANEL_JS


def test_panel_js_workflows_exposes_window_workflows() -> None:
    """PR3-16: PANEL_JS must include window.Workflows from workflows.js."""
    from dadaia_workspace.features.panel.views._assets import PANEL_JS

    assert "window.Workflows" in PANEL_JS
    assert "/api/workflows" in PANEL_JS


def test_panel_css_has_workflows_pane_layout() -> None:
    """panel-defects Bug 4: PANEL_CSS must contain 2-pane grid layout."""
    from dadaia_workspace.features.panel.views._assets import PANEL_CSS

    assert ".workflows-pane" in PANEL_CSS
    assert ".workflows-list" in PANEL_CSS
    assert ".workflows-detail" in PANEL_CSS
    assert "workflow-list-item" in PANEL_CSS
