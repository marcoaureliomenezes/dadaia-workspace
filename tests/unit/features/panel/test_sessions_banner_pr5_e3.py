"""Unit tests for PR5-E3: Cost-not-tracked banner for Codex sessions.

Covers:
  - sessions.py HTML scaffold contains the banner slot with expected attributes
  - sessions.py banner slot is hidden by default (FR6: starts hidden, JS shows it)
  - sessions.py banner slot carries role="status" and aria-live="polite" (a11y)
  - sessions.py CSS contains `.sessions-banner` selector
  - sessions.py CSS banner is hidden via [hidden] rule
  - sessions.js contains CODEX_BANNER_TEXT constant with exact text
  - sessions.js contains updateBanner function declaration
  - sessions.js cost cell gating: 'codex' case renders em dash

OWASP A03: banner text is set via textContent in JS (not innerHTML), preventing XSS.
WCAG 2.1 AA: banner uses role="status" + aria-live="polite" for screen-reader announcement.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# sessions.py HTML scaffold — banner slot
# ---------------------------------------------------------------------------


def test_sessions_scaffold_contains_banner_div() -> None:
    """The sessions scaffold must include a #sessions-banner div."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    assert 'id="sessions-banner"' in html, (
        "sessions.py scaffold must contain <div id='sessions-banner'>"
    )


def test_sessions_banner_has_sessions_banner_class() -> None:
    """The banner slot must carry class='sessions-banner' for CSS targeting."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    assert 'class="sessions-banner"' in html, (
        "Banner slot must carry class='sessions-banner'"
    )


def test_sessions_banner_starts_hidden() -> None:
    """The banner slot must start hidden so it doesn't flash before JS runs."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    # The banner element line must carry the `hidden` attribute
    assert "sessions-banner" in html
    # Find the banner element specifically and confirm `hidden` is there
    banner_start = html.index('id="sessions-banner"')
    # Grab the tag region: from the opening < before banner_start to the first >
    tag_start = html.rfind('<', 0, banner_start)
    tag_end = html.index('>', banner_start)
    banner_tag = html[tag_start:tag_end + 1]
    assert 'hidden' in banner_tag, (
        "The #sessions-banner element must carry the `hidden` attribute in the scaffold"
    )


def test_sessions_banner_has_role_status() -> None:
    """Banner slot must have role='status' for accessibility (WCAG 4.1.3)."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    banner_start = html.index('id="sessions-banner"')
    tag_start = html.rfind('<', 0, banner_start)
    tag_end = html.index('>', banner_start)
    banner_tag = html[tag_start:tag_end + 1]
    assert 'role="status"' in banner_tag, (
        "The #sessions-banner element must carry role='status'"
    )


def test_sessions_banner_has_aria_live_polite() -> None:
    """Banner slot must have aria-live='polite' so screen readers announce it."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    banner_start = html.index('id="sessions-banner"')
    tag_start = html.rfind('<', 0, banner_start)
    tag_end = html.index('>', banner_start)
    banner_tag = html[tag_start:tag_end + 1]
    assert 'aria-live="polite"' in banner_tag, (
        "The #sessions-banner element must carry aria-live='polite'"
    )


def test_sessions_banner_appears_before_table_container() -> None:
    """The banner must appear above the table container in DOM order."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    banner_pos = html.index('id="sessions-banner"')
    table_pos = html.index('id="sessions-table-container"')
    assert banner_pos < table_pos, (
        "#sessions-banner must precede #sessions-table-container in DOM order"
    )


# ---------------------------------------------------------------------------
# sessions.py CSS — banner styles
# ---------------------------------------------------------------------------


def test_sessions_css_contains_banner_selector() -> None:
    """SESSIONS_CSS must contain a .sessions-banner selector."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    assert ".sessions-banner" in SESSIONS_CSS, (
        "SESSIONS_CSS must contain .sessions-banner selector for styling"
    )


def test_sessions_css_banner_hidden_rule() -> None:
    """SESSIONS_CSS must contain .sessions-banner[hidden] display:none rule."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    assert ".sessions-banner[hidden]" in SESSIONS_CSS, (
        "SESSIONS_CSS must have .sessions-banner[hidden] { display: none !important; } "
        "to ensure [hidden] overrides any display rules"
    )


def test_sessions_css_banner_has_padding() -> None:
    """Banner style block must include padding for visual affordance."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    # Find the .sessions-banner rule block
    start = SESSIONS_CSS.index(".sessions-banner")
    block_start = SESSIONS_CSS.index("{", start)
    block_end = SESSIONS_CSS.index("}", block_start)
    banner_block = SESSIONS_CSS[block_start:block_end]
    assert "padding" in banner_block, (
        ".sessions-banner CSS block must include a padding declaration"
    )


def test_sessions_css_banner_uses_token_background() -> None:
    """Banner background must use a CSS variable (design token), not a raw hex value."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    start = SESSIONS_CSS.index(".sessions-banner {")
    block_start = SESSIONS_CSS.index("{", start)
    block_end = SESSIONS_CSS.index("}", block_start)
    banner_block = SESSIONS_CSS[block_start:block_end]
    assert "var(--" in banner_block, (
        ".sessions-banner must use CSS custom properties (design tokens), not raw hex values"
    )


# ---------------------------------------------------------------------------
# sessions.js — banner constant and function presence (static text analysis)
# ---------------------------------------------------------------------------


def _read_sessions_js() -> str:
    js_path = Path(
        "dadaia_workspace/features/panel/views/assets/js/sessions.js"
    )
    return js_path.read_text(encoding="utf-8")


def test_sessions_js_codex_banner_text_constant() -> None:
    """sessions.js must define CODEX_BANNER_TEXT with the exact required string."""
    js = _read_sessions_js()
    assert "CODEX_BANNER_TEXT" in js, (
        "sessions.js must declare CODEX_BANNER_TEXT constant"
    )
    assert "Cost not tracked for Codex" in js, (
        "CODEX_BANNER_TEXT must equal 'Cost not tracked for Codex'"
    )


def test_sessions_js_update_banner_function() -> None:
    """sessions.js must define an updateBanner function."""
    js = _read_sessions_js()
    assert "function updateBanner()" in js, (
        "sessions.js must define updateBanner() function"
    )


def test_sessions_js_update_banner_shows_on_codex() -> None:
    """updateBanner must remove [hidden] when runtime === 'codex'."""
    js = _read_sessions_js()
    # Check the removeAttribute('hidden') path for codex
    assert "removeAttribute('hidden')" in js, (
        "updateBanner must call removeAttribute('hidden') to reveal the banner for Codex"
    )


def test_sessions_js_update_banner_hides_on_claude() -> None:
    """updateBanner must set [hidden] when runtime is not 'codex'."""
    js = _read_sessions_js()
    assert "setAttribute('hidden'" in js, (
        "updateBanner must call setAttribute('hidden', '') to hide the banner for non-Codex runtimes"
    )


def test_sessions_js_update_banner_called_on_runtime_change() -> None:
    """The dadaia:runtime-change listener must call updateBanner() before fetching."""
    js = _read_sessions_js()
    # Find the addEventListener call for the runtime-change event.
    # Use the addEventListener pattern to skip comments that also contain the event name.
    listener_marker = "addEventListener('dadaia:runtime-change'"
    listener_start = js.index(listener_marker)
    # Take a 400-char window after the addEventListener declaration
    window = js[listener_start:listener_start + 400]
    pos_update = window.find("updateBanner()")
    pos_fetch = window.find("fetchSessions()")
    assert pos_update != -1, (
        "The dadaia:runtime-change listener must call updateBanner()"
    )
    assert pos_fetch != -1, (
        "The dadaia:runtime-change listener must call fetchSessions()"
    )
    assert pos_update < pos_fetch, (
        "updateBanner() must be called before fetchSessions() in the runtime-change listener"
    )


def test_sessions_js_cost_cell_gated_by_runtime() -> None:
    """buildRowHtml must gate the Cost cell: 'codex' → '—', else fmtCost()."""
    js = _read_sessions_js()
    # The row builder must branch on runtime === 'codex'
    assert "runtime === 'codex'" in js, (
        "buildRowHtml must check runtime === 'codex' to gate the Cost cell"
    )


def test_sessions_js_update_banner_called_after_fetch() -> None:
    """fetchSessions success path must call updateBanner() before renderTable()."""
    js = _read_sessions_js()
    # Find the fetch success handler (after _allRows = data.sessions)
    marker = "_allRows = data.sessions || [];"
    fetch_success_start = js.index(marker)
    window = js[fetch_success_start:fetch_success_start + 300]
    pos_update = window.find("updateBanner()")
    pos_render = window.find("renderTable(")
    assert pos_update != -1, (
        "fetchSessions success handler must call updateBanner()"
    )
    assert pos_render != -1, (
        "fetchSessions success handler must call renderTable()"
    )
    assert pos_update < pos_render, (
        "updateBanner() must be called before renderTable() in the fetch success handler"
    )
