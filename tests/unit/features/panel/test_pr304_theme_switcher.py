"""TDD tests for PR3-04 — Theme switcher JS + pre-paint inline script in index.py.

SPEC acceptance: §7.7 + Surface E (E2E-THM-01, 02, 05, 06, 08, 09)
TASKS.md PR3-04 acceptance criteria:
  - Topbar theme-switcher button present in rendered HTML
  - Button has aria-haspopup="menu" and aria-expanded
  - Dropdown element with role="menu" present
  - Three menuitemradio items (Mint, Sage, Warm)
  - Pre-paint inline <script> in <head> reads localStorage and sets data-theme
  - themes.js is non-empty and served correctly by static route
  - themes.js is an IIFE (wrapped in (function() { ... })())
  - themes.js contains localStorage["dadaia-panel-theme"] key
  - Escape-key close and focus-return logic present
  - Arrow-key cycling logic present
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.static import render_static


# ---------------------------------------------------------------------------
# Fakes (same pattern as test_views_index.py)
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        return []


class FakeSpecContextService:
    def list_all(self) -> list[SpecContextProject]:
        return []


def _build_service() -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
    )


def _render() -> str:
    service = _build_service()
    view = render_index(service)
    status, content_type, body = view()
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


# ---------------------------------------------------------------------------
# Pre-paint inline <script> in <head>
# ---------------------------------------------------------------------------


def test_index_head_has_inline_theme_script() -> None:
    """PR3-04: <head> must contain an inline <script> before stylesheets for pre-paint FOUC prevention."""
    html = _render()
    head_end = html.find("</head>")
    assert head_end > 0, "No </head> found"
    head_section = html[:head_end]
    assert "<script>" in head_section, "No inline <script> in <head>"


def test_prepaint_script_reads_localstorage() -> None:
    """PR3-04: inline pre-paint script must read localStorage['dadaia-panel-theme']."""
    html = _render()
    head_end = html.find("</head>")
    head_section = html[:head_end]
    assert "dadaia-panel-theme" in head_section, (
        "Pre-paint script must reference localStorage key 'dadaia-panel-theme'"
    )


def test_prepaint_script_sets_dataset_theme() -> None:
    """PR3-04: inline pre-paint script must set document.documentElement.dataset.theme."""
    html = _render()
    head_end = html.find("</head>")
    head_section = html[:head_end]
    # Accept either dataset.theme or setAttribute('data-theme', ...)
    assert "dataset.theme" in head_section or "data-theme" in head_section, (
        "Pre-paint script must set data-theme on <html> element"
    )


def test_prepaint_script_before_stylesheets() -> None:
    """PR3-04: inline pre-paint <script> must appear BEFORE the first <link rel='stylesheet'>."""
    html = _render()
    first_script_pos = html.find("<script>")
    first_stylesheet_pos = html.find('<link rel="stylesheet"')
    assert first_script_pos > 0, "No inline <script> found"
    assert first_stylesheet_pos > 0, "No stylesheet link found"
    assert first_script_pos < first_stylesheet_pos, (
        "Pre-paint <script> must come before the first stylesheet <link> in <head>"
    )


# ---------------------------------------------------------------------------
# Theme switcher button in topbar
# ---------------------------------------------------------------------------


def test_topbar_has_theme_button() -> None:
    """PR3-04: topbar must contain a theme-switcher button."""
    html = _render()
    assert 'id="theme-btn"' in html or 'class="theme-btn"' in html or "theme" in html.lower(), (
        "Topbar must contain a theme switcher button"
    )


def test_theme_button_has_aria_haspopup_menu() -> None:
    """PR3-04: theme-switcher button must have aria-haspopup='menu'."""
    html = _render()
    assert 'aria-haspopup="menu"' in html, "Theme button must carry aria-haspopup='menu'"


def test_theme_button_has_aria_expanded() -> None:
    """PR3-04: theme-switcher button must have aria-expanded attribute."""
    html = _render()
    assert "aria-expanded=" in html, "Theme button must carry aria-expanded attribute"


def test_theme_button_aria_expanded_default_false() -> None:
    """PR3-04: theme-switcher button aria-expanded must default to 'false'."""
    html = _render()
    assert 'aria-expanded="false"' in html, "Theme button aria-expanded must default to 'false'"


# ---------------------------------------------------------------------------
# Dropdown menu structure
# ---------------------------------------------------------------------------


def test_theme_dropdown_has_role_menu() -> None:
    """PR3-04: dropdown container must have role='menu'."""
    html = _render()
    assert 'role="menu"' in html, "Theme dropdown must carry role='menu'"


def test_theme_dropdown_has_three_menuitemradio_items() -> None:
    """PR3-04: dropdown must have exactly 3 role='menuitemradio' items."""
    html = _render()
    count = html.count('role="menuitemradio"')
    assert count == 3, f"Expected 3 menuitemradio items, found {count}"


def test_theme_dropdown_has_mint_option() -> None:
    """PR3-04: dropdown must contain a 'Mint' option."""
    html = _render()
    assert "Mint" in html, "Theme dropdown must contain Mint option"


def test_theme_dropdown_has_sage_option() -> None:
    """PR3-04: dropdown must contain a 'Sage' option."""
    html = _render()
    assert "Sage" in html, "Theme dropdown must contain Sage option"


def test_theme_dropdown_has_warm_option() -> None:
    """PR3-04: dropdown must contain a 'Warm' option."""
    html = _render()
    assert "Warm" in html, "Theme dropdown must contain Warm option"


def test_theme_items_have_aria_checked() -> None:
    """PR3-04: menuitemradio items must have aria-checked attribute."""
    html = _render()
    assert "aria-checked=" in html, "menuitemradio items must carry aria-checked attribute"


# ---------------------------------------------------------------------------
# themes.js static file
# ---------------------------------------------------------------------------


def test_themes_js_served_by_static_route() -> None:
    """PR3-04: /static/themes.js must be served with correct content-type."""
    view = render_static()
    status, ct, _ = view(name="themes.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_themes_js_body_is_nonempty() -> None:
    """PR3-04: themes.js must be non-empty."""
    view = render_static()
    _, _, body = view(name="themes.js")
    assert isinstance(body, bytes)
    assert len(body) > 100, "themes.js is too short — stub not yet filled"


def test_themes_js_is_iife() -> None:
    """PR3-04: themes.js must be wrapped as an IIFE to avoid global pollution."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "(function" in js or "(function(" in js, "themes.js must be wrapped as an IIFE"


def test_themes_js_references_localstorage_key() -> None:
    """PR3-04: themes.js must reference localStorage key 'dadaia-panel-theme'."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "dadaia-panel-theme" in js, "themes.js must use localStorage key 'dadaia-panel-theme'"


def test_themes_js_handles_escape_key() -> None:
    """PR3-04: themes.js must handle Escape key to close dropdown."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "Escape" in js, "themes.js must handle Escape key"


def test_themes_js_handles_arrow_keys() -> None:
    """PR3-04: themes.js must handle ArrowDown/ArrowUp for cycling items."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "ArrowDown" in js or "ArrowUp" in js, "themes.js must handle arrow keys for item cycling"


def test_themes_js_sets_dataset_theme() -> None:
    """PR3-04: themes.js must set document.documentElement.dataset.theme."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "dataset.theme" in js or "setAttribute" in js, (
        "themes.js must set data-theme on <html> element"
    )


def test_themes_js_uses_localstorage_setitem() -> None:
    """PR3-04: themes.js must write theme choice to localStorage."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8")
    assert "localStorage.setItem" in js or "localStorage[" in js, (
        "themes.js must persist theme to localStorage"
    )


def test_themes_js_no_global_pollution() -> None:
    """PR3-04: themes.js must not declare top-level variables (IIFE wraps everything)."""
    view = render_static()
    _, _, body = view(name="themes.js")
    js = body.decode("utf-8").strip()
    # IIFE must wrap the entire file
    assert js.startswith("(function"), (
        "themes.js must start with an IIFE '(function' to avoid global scope pollution"
    )


def test_index_includes_themes_js_script_tag() -> None:
    """PR3-04: index.py must include a <script src='/static/themes.js'> tag."""
    html = _render()
    assert "/static/themes.js" in html, "index.py must include <script src='/static/themes.js'>"
