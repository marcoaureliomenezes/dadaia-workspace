"""Unit contracts for the panel index view — real decisions only.

Tablist/tabpanel/section/static-link/card structural presence is owned by
``test_index_dom_contract.py`` (the e2e-selector presence lock). The
panel-JS credential-free contract is owned by ``test_no_auth_contract.py``/
``test_no_bearer_in_url.py``. The empty-state and CSS-registration smoke
checks were deleted as low-value duplicates of the DOM-contract fixture.

Two survivors:
  1. Operator-controlled field escaping (project/context_name/branch) — XSS.
  2. Card contract: chip href always ``.md`` (never ``.html``) + 5-chip order +
     context render order, merged into one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

pytestmark = pytest.mark.unit


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
    current_branch: str | None = "main",
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=repo_slug,
        repo_url="https://github.com/org/repo",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00" if state == ContextState.ALIVE else None,
        dead_since=None if state == ContextState.ALIVE else "2026-01-01T00:00:00+00:00",
        current_branch=current_branch,
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


def _tag_fragment(html: str, marker: str, close_tag: str) -> str:
    start = html.find(marker)
    assert start >= 0, f"Missing marker: {marker}"
    end = html.find(close_tag, start)
    assert end >= 0, f"Missing close tag after marker: {marker}"
    return html[start:end]


# ---------------------------------------------------------------------------
# 1. Operator-controlled field escaping (XSS)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 2. Card contract: chip href .md-never-.html + 5-chip order + context order
# ---------------------------------------------------------------------------


def test_card_contract_chip_hrefs_order_and_context_order() -> None:
    first = _make_context("First", "first-slug")
    second = _make_context("Second", "second-slug")
    html = _render(_build_service(contexts=[first, second]))

    # Contexts with the same primary status render in service order.
    assert html.find("first-slug") < html.find("second-slug")

    card = _tag_fragment(html, 'class="context-card"', "</article>")
    for expected in [
        'data-slug="first-slug"',
        'class="memory-chip"',
        'href="/memory-view/first-slug/constitution.md"',
        'href="/memory-view/first-slug/architecture.md"',
        'href="/memory-view/first-slug/tech-stack.md"',
        'href="/memory-view/first-slug/quality-assurance.md"',
        'href="/memory-view/first-slug/product/index.md"',
        ">Constitution<",
        ">Architecture<",
        ">Tech Stack<",
        ">Quality<",
        ">Product<",
    ]:
        assert expected in card

    # Five-chip contract (operator demand 2026-06-11): Constitution leads, then
    # Architecture / Tech Stack / Quality / Product.
    order = [
        card.find(">Constitution<"),
        card.find(">Architecture<"),
        card.find(">Tech Stack<"),
        card.find(">Quality<"),
        card.find(">Product<"),
    ]
    assert order == sorted(order) and -1 not in order

    # T-016-P03 regression guard: chip hrefs must use .md, never .html.
    assert 'href="/memory-view/first-slug/architecture.html"' not in card
    assert 'href="/memory-view/first-slug/tech-stack.html"' not in card
    assert 'href="/memory-view/first-slug/product/index.html"' not in card
