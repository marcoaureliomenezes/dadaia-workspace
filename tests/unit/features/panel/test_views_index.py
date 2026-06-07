"""Unit contracts for the panel index view."""

from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

# ---------------------------------------------------------------------------
# JS / CSS assembly helpers
# ---------------------------------------------------------------------------
_JS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "dadaia_workspace"
    / "features"
    / "panel"
    / "views"
    / "assets"
    / "js"
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
    state: ContextState = ContextState.ALIVE,
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=repo_slug,
        repo_url="https://github.com/org/repo",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00" if state == ContextState.ALIVE else None,
        dead_since=None if state == ContextState.ALIVE else "2026-01-01T00:00:00+00:00",
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


def _tag_fragment(html: str, marker: str, close_tag: str) -> str:
    start = html.find(marker)
    assert start >= 0, f"Missing marker: {marker}"
    end = html.find(close_tag, start)
    assert end >= 0, f"Missing close tag after marker: {marker}"
    return html[start:end]


def _section_fragment(html: str, section_id: str) -> str:
    return _tag_fragment(html, f'id="{section_id}"', "</section>")


def _button_fragment(html: str, tab_id: str) -> str:
    id_pos = html.find(f'id="{tab_id}"')
    assert id_pos >= 0, f"Missing tab: {tab_id}"
    start = html.rfind("<button", 0, id_pos)
    assert start >= 0, f"Missing button start for tab: {tab_id}"
    end = html.find("</button>", id_pos)
    assert end >= 0, f"Missing button close for tab: {tab_id}"
    return html[start:end]


@pytest.mark.parametrize(
    ("section_id", "visible_text"),
    [
        ("section-servers", ">Servers<"),
        ("section-memories", ">Projects<"),
        ("section-agents", "agents-grid"),
        ("section-workflows", "workflows-grid"),
        ("section-sessions", "sessions-tbody"),
        ("section-reports", "reports-list"),
        ("section-academy", "academy-content"),
        ("section-kanban", "kanban-board"),
    ],
)
def test_index_renders_panel_sections(section_id: str, visible_text: str) -> None:
    """The index shell must render every top-level panel section."""
    html = _render(_build_service())
    assert f'id="{section_id}"' in html
    assert visible_text in html


def test_index_tablist_contract() -> None:
    """The nav must expose the current tab order and active default tab."""
    html = _render(_build_service())
    expected = [
        ("tab-memories", "Spec Context Projects"),
        ("tab-agents", "Agents"),
        ("tab-workflows", "Workflows"),
        ("tab-sessions", "Sessions"),
        ("tab-reports", "Reports"),
        ("tab-academy", "Academy"),
        ("tab-kanban", "Kanban"),
        ("tab-servers", "Servers"),
    ]

    assert 'role="tablist"' in html
    assert html.count('role="tab"') == len(expected)
    assert [html.find(f'id="{tab_id}"') for tab_id, _ in expected] == sorted(
        html.find(f'id="{tab_id}"') for tab_id, _ in expected
    )
    for tab_id, label in expected:
        button = _button_fragment(html, tab_id)
        assert 'role="tab"' in button
        assert label in button

    memories_button = _button_fragment(html, "tab-memories")
    servers_button = _button_fragment(html, "tab-servers")
    assert "active" in memories_button
    assert 'aria-selected="true"' in memories_button
    assert 'aria-label="Spec Context Projects"' in memories_button
    assert 'aria-selected="false"' in servers_button


@pytest.mark.parametrize(
    ("section_id", "tab_id"),
    [
        ("section-memories", "tab-memories"),
        ("section-agents", "tab-agents"),
        ("section-workflows", "tab-workflows"),
        ("section-sessions", "tab-sessions"),
        ("section-reports", "tab-reports"),
        ("section-academy", "tab-academy"),
        ("section-kanban", "tab-kanban"),
        ("section-servers", "tab-servers"),
    ],
)
def test_index_tabpanel_contract(section_id: str, tab_id: str) -> None:
    """Every section must be connected to its tab for keyboard and screen-reader users."""
    html = _render(_build_service())
    section = _section_fragment(html, section_id)
    assert 'role="tabpanel"' in section
    assert 'tabindex="0"' in section
    assert f'aria-labelledby="{tab_id}"' in section
    assert html.count('role="tabpanel"') == 8


def test_panel_js_keyboard_and_auth_contract() -> None:
    """The assembled panel JS must support tab keyboard nav and authenticated API calls."""
    panel_js = _build_panel_js()
    for expected in [
        "ArrowRight",
        "ArrowLeft",
        "Home",
        "End",
        "keydown",
        "panel_token",
        "localStorage",
        "URLSearchParams",
        "history.replaceState",
        "authedFetch",
        "Authorization",
        "Bearer",
        "authedFetch('/api/agents?runtime='",
        "authedFetch('/api/workflows?runtime='",
    ]:
        assert expected in panel_js


@pytest.mark.parametrize(
    "asset",
    [
        "tokens.css",
        "structure.css",
        "projects.css",
        "agents.css",
        "workflows.css",
        "sessions.css",
        "academy.css",
        "reports.css",
        "kanban.css",
        "runtime.js",
        "themes.js",
        "core.js",
        "agents.js",
        "workflows.js",
        "sessions.js",
        "academy.js",
        "reports.js",
        "kanban.js",
    ],
)
def test_index_links_registered_static_assets(asset: str) -> None:
    """The HTML shell must load the static assets required by the panel."""
    html = _render(_build_service())
    assert f"/static/{asset}" in html


def test_index_context_order_preserved() -> None:
    """Contexts with the same primary status render in service order."""
    first = _make_context("First", "first-slug")
    second = _make_context("Second", "second-slug")
    html = _render(_build_service(contexts=[first, second]))

    assert html.find("first-slug") < html.find("second-slug")


@pytest.mark.parametrize("field", ["project", "context_name", "branch"])
def test_index_escapes_operator_controlled_fields(field: str) -> None:
    """Operator-controlled strings must be HTML-escaped before rendering."""
    raw = "<script>alert(1)</script>"
    if field == "project":
        html = _render(_build_service(entries=[_make_entry(port=3000, project=raw)]))
    elif field == "context_name":
        html = _render(_build_service(contexts=[_make_context(raw, "safe-slug")]))
    else:
        ctx = SpecContextProject(
            name="safe-name",
            state=ContextState.ALIVE,
            repo_slug="safe-slug",
            repo_url="https://github.com/org/repo",
            created_at="2026-01-01T00:00:00+00:00",
            alive_since="2026-01-01T00:00:00+00:00",
            dead_since=None,
            current_branch=raw,
        )
        html = _render(_build_service(contexts=[ctx]))

    assert raw not in html
    assert "&lt;script&gt;" in html


def test_index_empty_servers_shows_empty_state() -> None:
    """When registry is empty, empty-state hint must be present."""
    html = _render(_build_service(entries=[], contexts=[]))
    assert "Nenhum servidor rodando" in html


def test_projects_section_contract() -> None:
    """The projects section must expose count, description, cards, and memory chips."""
    ctx1 = _make_context("Workspace 1", "ws-1")
    ctx2 = _make_context("Workspace 2", "ws-2")
    html = _render(_build_service(contexts=[ctx1, ctx2]))
    section = _section_fragment(html, "section-memories")

    assert "<h2>Projects</h2>" in section
    assert 'class="projects-count-badge"' in section
    assert "2 projects" in section
    assert 'class="section-desc"' in section
    assert "<summary>About this section</summary>" in section
    assert "Active Spec Context Projects" in section
    assert "card-primary-badge" not in section
    assert 'class="context-card primary"' not in section


def test_project_card_contract() -> None:
    """A project card must render stable zones, metadata, session slot, and memory links."""
    html = _render(_build_service(contexts=[_make_context("My Workspace", "my-workspace")]))
    card = _tag_fragment(html, 'class="context-card"', "</article>")

    for expected in [
        'class="card-zone-a"',
        'class="card-name"',
        'class="card-zone-b"',
        'class="card-meta-row"',
        "repo:",
        "branch:",
        'class="card-zone-c"',
        'data-slug="my-workspace"',
        'aria-live="polite"',
        'class="card-zone-d card-chips"',
        'class="memory-chip"',
        'href="/memory-view/my-workspace/architecture.md"',
        'href="/memory-view/my-workspace/tech-stack.md"',
        'href="/memory-view/my-workspace/product/index.md"',
        ">Architecture<",
        ">Tech Stack<",
        ">Product<",
    ]:
        assert expected in card

    assert card.find('class="card-zone-b"') < card.find('class="card-zone-c"')
    assert card.find('class="card-zone-c"') < card.find('class="card-zone-d')
    # T-016-P03 regression guard: chip hrefs must use .md, never .html
    assert 'href="/memory-view/my-workspace/architecture.html"' not in card
    assert 'href="/memory-view/my-workspace/tech-stack.html"' not in card
    assert 'href="/memory-view/my-workspace/product/index.html"' not in card


def test_projects_css_contract() -> None:
    """Project card CSS and tokens must stay registered for static serving."""
    from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
    from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
    from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
    from dadaia_workspace.features.panel.views.static import render_static

    for expected in [
        ".context-card",
        "border-left",
        ".memory-chip",
        ".card-zone-a",
        ".card-zone-b",
        ".card-zone-c",
        ".card-zone-d",
        ".card-name",
        ".card-meta-row",
        ".session-row",
        "--color-chip-memory-bg",
        "--color-session-bg",
        "--color-accent",
    ]:
        assert expected in PROJECTS_CSS or expected in TOKENS_CSS

    assert "@media" in STRUCTURE_CSS
    assert "768px" in STRUCTURE_CSS
    assert "Spec Contexts" in STRUCTURE_CSS

    status, ct, body = render_static()(name="projects.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"
    assert len(body) > 0
