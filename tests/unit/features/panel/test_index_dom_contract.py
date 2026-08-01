"""§3-FR1 structural DOM-contract lock for the panel index (v0.1.59 W1 / T-59-10, AC-1).

This is the **index-HTML behavior lock** for the v0.1.59 Panel UX Overhaul. The
``api_golden_v0155.json`` byte-invariant captures only ``render_api_*`` JSON bodies —
it does NOT cover the index page. This module fills that gap: it renders the REAL index
via ``render_index`` over fixed, POPULATED fakes and asserts the presence of the full
e2e selector contract (the same selectors the GH-only Playwright suite keys on), so that
a dropped selector fails loudly in unit CI *before* an SSR-HTML restyle touches anything.

Contract character (Q5 — NEVER re-baselined this release):
  This is a **presence-invariant** contract test, not a byte-golden. It survives an
  intentional restyle because it asserts *selector presence*, not markup bytes. Any
  wave that must change one of the asserted selectors is a STOP-and-rescope declared on
  that wave's AC-11 ledger line — never a silent edit here.

FR4 (v0.1.75): the primary tab list is single-sourced in
``conftest.PANEL_PRIMARY_TABS`` — this module consumes it instead of a private
hardcoded list, so a v0.1.77 tab change edits ONE list.

Three survivors, the sole selector-presence lock for the index page:
  1. tabs + sections + nav-tab param (walks conftest.PANEL_PRIMARY_TABS).
  2. Populated-context card selectors (.memory-chip / .context-card / zones).
  3. Theme cluster + runtime switcher values (mint/sage/warm; claude/codex/pi).
"""

from __future__ import annotations

import html as html_lib
from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

from .conftest import PANEL_PRIMARY_TAB_SLUGS, PANEL_PRIMARY_TABS

pytestmark = pytest.mark.unit


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
    """Render the real index over >=1 SpecContextProject + >=1 server row.

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


@pytest.fixture(scope="module")
def index_html() -> str:
    return _render_populated_index()


# ---------------------------------------------------------------------------
# 1. tabs + sections + nav-tab param (single-sourced via conftest)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section", PANEL_PRIMARY_TAB_SLUGS)
def test_tab_and_section_present(index_html: str, section: str) -> None:
    """Every primary tab renders its nav id, data-section attr, and #section-* tabpanel;
    the .nav-tab selector (the styled control the e2e keys on) is present."""
    assert f'id="tab-{section}"' in index_html, f"missing tab id tab-{section}"
    assert f'data-section="{section}"' in index_html, f"missing data-section={section}"
    assert f'id="section-{section}"' in index_html, f"missing #section-{section}"
    assert 'class="nav-tab' in index_html


def test_exactly_five_primary_tabs_in_order(index_html: str) -> None:
    """v0.1.79: exactly 6 primary tabs render, in the exact PANEL_PRIMARY_TABS order,
    with the operator's exact label strings (masculine ordinal º)."""
    assert len(PANEL_PRIMARY_TABS) == 5

    positions = []
    for slug, label in PANEL_PRIMARY_TABS:
        tab_marker = f'id="tab-{slug}"'
        pos = index_html.find(tab_marker)
        assert pos >= 0, f"missing tab id tab-{slug}"
        positions.append(pos)

        # The label renders as the visible button text (between the opening tag's
        # closing '>' and the '</button>' close). The masculine ordinal "º" is
        # served as a numeric HTML entity (&#186;, same convention as &#183; / &mdash;
        # elsewhere in this module) — decode before comparing operator-visible text.
        open_end = index_html.find(">", pos) + 1
        close = index_html.find("</button>", open_end)
        assert close >= 0, f"missing </button> for tab-{slug}"
        button_text = html_lib.unescape(index_html[open_end:close])
        assert label in button_text, (
            f"tab-{slug} label mismatch: expected {label!r} in {button_text!r}"
        )

    assert positions == sorted(positions), "primary tabs do not render in PANEL_PRIMARY_TABS order"


def test_no_sessions_tab_or_section_remnants(index_html: str) -> None:
    """v0.1.79 FR1: the standalone Sessions tab/section is fully removed — no
    #tab-sessions button and no top-level #section-sessions tabpanel remain."""
    assert 'id="tab-sessions"' not in index_html
    assert 'data-section="sessions"' not in index_html
    assert 'aria-labelledby="tab-sessions"' not in index_html


def test_sessions_dashboard_relocated_inside_agentic_layer_one(index_html: str) -> None:
    """v0.1.79 FR1: the Sessions cost/telemetry dashboard renders as a sub-section
    INSIDE the 1º Agentic Layer (#section-subagents) tabpanel — #section-sessions
    survives as a nested mount (sessions.js keys on this id), #sessions-dashboard
    and #sessions-banner render after #section-subagents opens and before it closes."""
    subagents_start = index_html.find('id="section-subagents"')
    assert subagents_start >= 0, "missing #section-subagents"
    # Find the matching </section> close for the subagents tabpanel — it is the
    # first </section> after the subagents section opens (no nested <section> tags
    # are used for sub-sections, only <div>).
    subagents_close = index_html.find("</section>", subagents_start)
    assert subagents_close >= 0, "missing </section> close for #section-subagents"

    sessions_pos = index_html.find('id="section-sessions"')
    assert sessions_pos >= 0, "missing #section-sessions (relocated dashboard mount)"
    assert subagents_start < sessions_pos < subagents_close, (
        "#section-sessions must render INSIDE the #section-subagents tabpanel body"
    )

    dashboard_pos = index_html.find('id="sessions-dashboard"')
    banner_pos = index_html.find('id="sessions-banner"')
    assert subagents_start < dashboard_pos < subagents_close
    assert subagents_start < banner_pos < subagents_close

    # The relocated sub-section must NOT carry the top-level .section/.panel-section
    # class that would let CSS hide it independently of the parent tabpanel's
    # .active toggle (that class pair is display:none until .active is applied).
    sessions_tag_start = index_html.rfind("<", 0, sessions_pos + 1)
    # crude-but-sufficient: look at the opening tag text up to its '>' close.
    tag_close = index_html.find(">", sessions_pos)
    opening_tag = index_html[sessions_tag_start:tag_close]
    assert 'class="section' not in opening_tag, (
        f"#section-sessions must not carry the standalone .section class after "
        f"relocation: {opening_tag!r}"
    )
    assert 'class="panel-section' not in opening_tag, (
        f"#section-sessions must not carry the standalone .panel-section class "
        f"after relocation: {opening_tag!r}"
    )


# ---------------------------------------------------------------------------
# 2. Populated-context card selectors
# ---------------------------------------------------------------------------


def test_populated_context_card_selectors(index_html: str) -> None:
    """.memory-chip and the .context-card anatomy render only with >=1 populated context
    (A3 fixture guard — do NOT use an empty fixture here)."""
    assert 'class="memory-chip"' in index_html, (
        ".memory-chip absent — the fixture must carry >=1 SpecContextProject so "
        "_render_context_card runs"
    )
    assert 'class="context-card"' in index_html
    assert 'class="card-name"' in index_html
    for zone in ("card-zone-a", "card-zone-b", "card-zone-c", "card-zone-d"):
        assert zone in index_html, f"missing .{zone}"


# ---------------------------------------------------------------------------
# 3. Theme cluster + runtime switcher values
# ---------------------------------------------------------------------------


def test_theme_and_runtime_clusters(index_html: str) -> None:
    topbar = _topbar_fragment(index_html)
    assert 'id="theme-btn"' in topbar, "#theme-btn must render inside .topbar"
    assert 'aria-haspopup="menu"' in topbar, "#theme-btn must carry aria-haspopup=menu"

    theme_fragment = _theme_switcher_fragment(index_html)
    assert 'id="theme-menu"' in theme_fragment
    assert 'role="menu"' in theme_fragment
    assert 'class="theme-swatch-dot' in index_html

    for value in ("mint", "sage", "warm"):
        assert f'data-theme-value="{value}"' in index_html, f"missing data-theme-value={value}"

    assert 'class="runtime-switcher"' in index_html
    assert 'class="runtime-btn' in index_html
    for value in ("claude", "codex", "pi"):
        assert f'data-runtime-value="{value}"' in index_html, f"missing data-runtime-value={value}"
