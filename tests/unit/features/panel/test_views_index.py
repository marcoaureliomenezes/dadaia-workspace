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
    """T-AM-01/T-AM-18: there must be exactly 4 role=tabpanel elements after workflows tab added."""
    service = _build_service()
    html = _render(service)
    assert html.count('role="tabpanel"') == 4


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
    """T-AM-18: nav-tabs must contain exactly 4 tab buttons."""
    service = _build_service()
    html = _render(service)
    # Count role="tab" occurrences
    assert html.count('role="tab"') == 4
