"""§3-FR1 structural DOM-contract lock for the panel index (v0.1.59 W1 / T-59-10, AC-1).

This is the **index-HTML behavior lock** for the v0.1.59 Panel UX Overhaul. The
``api_golden_v0155.json`` byte-invariant captures only ``render_api_*`` JSON bodies —
it does NOT cover the index page. This module fills that gap: it renders the REAL index
via ``render_index`` over fixed, POPULATED fakes and asserts the presence of the full
e2e selector contract (the same selectors the GH-only Playwright suite keys on), so that
a dropped selector fails loudly in unit CI *before* the SSR-HTML restyle (W2–W6) touches
anything.

Contract character (Q5 — NEVER re-baselined this release):
  This is a **presence-invariant** contract test, not a byte-golden. It survives an
  intentional restyle because it asserts *selector presence*, not markup bytes. It is
  **NEVER re-baselined in v0.1.59** (symmetric with Ruling C for the api-golden): any
  wave that must change one of the asserted selectors is a STOP-and-rescope declared on
  that wave's AC-11 ledger line — never a silent edit here. By design FR2–FR6 rename
  none of the asserted selectors, so this lock should never move.

Fixture (A3 — the fakes MUST render the data-dependent selectors):
  ``.memory-chip`` / ``.context-card`` / ``.card-zone-*`` / ``.card-name`` are emitted
  ONLY by ``_render_context_card``, run once per context. The fixed fakes therefore
  include **≥1 SpecContextProject** (+ ≥1 server row), modelled on
  ``test_views_index._make_context`` / ``_build_service`` — NOT the empty
  ``test_security_headers._render_index_html`` fake (whose ``list_all()`` returns ``[]``,
  rendering zero cards, so ``.memory-chip`` would never render and the lock would
  silently drop that assertion). We reuse only the render *mechanics*, never an empty
  fixture. The unconditional selectors (6 tabs/sections, ``.nav-tab``, theme + runtime
  switchers) render with any fake; only the card selectors need the populated context.

Relation to test_views_index.py (A4/Q6 — CONSOLIDATES, does not replace):
  ``test_views_index.py`` already partially locks the index HTML (tab ids + labels + the
  active default; the 6 tabpanels; the section marker strings; the 5 memory chips + card
  zones; the ``/static/*`` links). This module CONSOLIDATES those into one e2e-selector
  presence invariant — it does NOT replace ``test_views_index.py``, which SURVIVES
  unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes + populated fixture (modelled on test_views_index._make_context /
# _build_service — A3; NEVER the empty test_security_headers fake).
# ---------------------------------------------------------------------------


class _FakeServerRegistryService:
    def __init__(self, entries: list[tuple[PortEntry, PortStatus]]) -> None:
        self._entries = entries

    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        if project is None:
            return list(self._entries)
        return [(e, s) for e, s in self._entries if e.project == project]


class _FakeSpecContextService:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


def _make_context(name: str, repo_slug: str) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=repo_slug,
        repo_url="https://github.com/org/repo",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00",
        dead_since=None,
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


def _render_populated_index() -> str:
    """Render the real index over ≥1 SpecContextProject + ≥1 server row.

    ``workspace_root`` is a fixed literal path (NOT resolved from cwd) so the render
    never reads host state — v0.1.58 golden law.
    """
    service = PanelService(
        registry=_FakeServerRegistryService([_make_entry(3000, "dadaia-workspace")]),  # type: ignore[arg-type]
        spec_context=_FakeSpecContextService(  # type: ignore[arg-type]
            [_make_context("Dadaia Workspace", "dadaia-workspace")]
        ),
        workspace_root=Path("/workspace"),
    )
    status, content_type, body = render_index(service)()
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


def _topbar_fragment(html: str) -> str:
    start = html.find('class="topbar"')
    assert start >= 0, "missing .topbar"
    end = html.find("</header>", start)
    assert end >= 0, "missing </header> after .topbar"
    return html[start:end]


def _theme_switcher_fragment(html: str) -> str:
    start = html.find('class="theme-switcher"')
    assert start >= 0, "missing .theme-switcher"
    end = html.find("</div>", html.find("</ul>", start))
    assert end >= 0, "missing theme-switcher close"
    return html[start:end]


# ---------------------------------------------------------------------------
# The 6-tab / 6-section nav contract (Ruling A — the nav set is pinned).
# ---------------------------------------------------------------------------

_SECTIONS = ["memories", "workflows", "subagents", "sessions", "reports", "academy", "servers"]


@pytest.fixture(scope="module")
def index_html() -> str:
    return _render_populated_index()


@pytest.mark.parametrize("section", _SECTIONS)
def test_tab_id_and_data_section_present(index_html: str, section: str) -> None:
    """Every one of the 6 nav tabs is present with its id AND its data-section attr."""
    assert f'id="tab-{section}"' in index_html, f"missing tab id tab-{section}"
    assert f'data-section="{section}"' in index_html, f"missing data-section={section}"


@pytest.mark.parametrize("section", _SECTIONS)
def test_section_panel_present(index_html: str, section: str) -> None:
    """Every one of the 6 #section-* tabpanels is present in the rendered index."""
    assert f'id="section-{section}"' in index_html, f"missing #section-{section}"


def test_nav_tab_class_present(index_html: str) -> None:
    """The .nav-tab selector (the styled control the e2e keys on) is present."""
    assert 'class="nav-tab' in index_html


# ---------------------------------------------------------------------------
# Data-dependent card selectors — require the POPULATED context fixture (A3).
# ---------------------------------------------------------------------------


def test_memory_chip_present_with_populated_context(index_html: str) -> None:
    """.memory-chip renders ONLY when ≥1 context card renders (A3 fixture guard)."""
    assert 'class="memory-chip"' in index_html, (
        ".memory-chip absent — the fixture must carry ≥1 SpecContextProject so "
        "_render_context_card runs (do NOT use the empty test_security_headers fake)"
    )


def test_context_card_and_zones_present(index_html: str) -> None:
    """The context card anatomy (.context-card + .card-zone-* + .card-name) renders."""
    assert 'class="context-card"' in index_html
    assert 'class="card-name"' in index_html
    for zone in ("card-zone-a", "card-zone-b", "card-zone-c", "card-zone-d"):
        assert zone in index_html, f"missing .{zone}"


# ---------------------------------------------------------------------------
# Theme switcher cluster (theme-switcher.spec.ts contract).
# ---------------------------------------------------------------------------


def test_theme_button_in_topbar_with_haspopup(index_html: str) -> None:
    """#theme-btn lives in the .topbar and advertises aria-haspopup="menu"."""
    topbar = _topbar_fragment(index_html)
    assert 'id="theme-btn"' in topbar, "#theme-btn must render inside .topbar"
    assert 'aria-haspopup="menu"' in topbar, "#theme-btn must carry aria-haspopup=menu"


def test_theme_menu_is_role_menu(index_html: str) -> None:
    """#theme-menu is present and carries role="menu"."""
    fragment = _theme_switcher_fragment(index_html)
    assert 'id="theme-menu"' in fragment
    assert 'role="menu"' in fragment


@pytest.mark.parametrize("value", ["mint", "sage", "warm"])
def test_three_theme_values_present(index_html: str, value: str) -> None:
    """The three [data-theme-value] menu items (mint/sage/warm) are present."""
    assert f'data-theme-value="{value}"' in index_html, f"missing data-theme-value={value}"


def test_theme_swatch_dot_present(index_html: str) -> None:
    """The .theme-swatch-dot swatch (per menu item) renders."""
    assert 'class="theme-swatch-dot' in index_html


# ---------------------------------------------------------------------------
# Runtime switcher (rendered inside the Sessions section — sessions.py).
# ---------------------------------------------------------------------------


def test_runtime_switcher_present(index_html: str) -> None:
    """The .runtime-switcher radiogroup renders in the Sessions section."""
    assert 'class="runtime-switcher"' in index_html


def test_runtime_buttons_present(index_html: str) -> None:
    """The .runtime-btn controls render."""
    assert 'class="runtime-btn' in index_html


@pytest.mark.parametrize("value", ["claude", "codex", "pi"])
def test_runtime_values_present(index_html: str, value: str) -> None:
    """Each [data-runtime-value] (claude/codex/pi) is present."""
    assert f'data-runtime-value="{value}"' in index_html, f"missing data-runtime-value={value}"
