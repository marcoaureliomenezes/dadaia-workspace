"""Unit contracts for the dashboard-only Sessions view (panel-plumbing v0.1.52 FR2).

The Sessions tab renders a 4-card cost aggregate + a cost-unknown banner from the
server-side ``/api/sessions`` aggregate envelope. These contracts pin the scaffold
shape, the banner behaviour, and the cost render mapping ('N/A' vs '—' vs '$X.XX')
against the FR1 cost-known matrix, and assert the list-era machinery (table,
drawer, sort/filter, skeleton, 10s auto-refresh) is gone.
"""

from __future__ import annotations

from pathlib import Path


def _banner_tag(html: str) -> str:
    start = html.index('id="sessions-banner"')
    tag_start = html.rfind("<", 0, start)
    tag_end = html.index(">", start)
    return html[tag_start : tag_end + 1]


def _sessions_js() -> str:
    return Path("dadaia_workspace/features/panel/views/assets/js/sessions.js").read_text(
        encoding="utf-8"
    )


def _function_body(js: str, name: str) -> str:
    marker = f"function {name}("
    start = js.index(marker)
    brace = js.index("{", start)
    depth = 0
    for index in range(brace, len(js)):
        if js[index] == "{":
            depth += 1
        elif js[index] == "}":
            depth -= 1
            if depth == 0:
                return js[brace : index + 1]
    raise AssertionError(f"Could not parse function body for {name}")


# ── Scaffold ──────────────────────────────────────────────────────────────────


def test_sessions_scaffold_is_dashboard_only() -> None:
    """The scaffold keeps dashboard + banner + badge and drops all list markup."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()

    # Surviving surface.
    assert 'id="sessions-dashboard"' in html
    assert 'id="sessions-banner"' in html
    assert 'id="sessions-last-updated"' in html
    # Runtime switcher stays (drives which runtime the aggregate reflects).
    assert 'id="sessions-runtime-btn-pi"' in html

    # Deleted list-era machinery.
    assert "sessions-table" not in html
    assert "sessions-tbody" not in html
    assert "session-drawer" not in html
    assert "sessions-filter" not in html
    assert "sessions-toolbar" not in html
    assert "data-sort-key" not in html


def test_sessions_scaffold_exposes_hidden_banner_after_dashboard() -> None:
    """The banner is an accessible hidden status slot rendered after the dashboard."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    tag = _banner_tag(html)

    assert 'class="sessions-banner"' in tag
    assert 'role="status"' in tag
    assert 'aria-live="polite"' in tag
    assert "hidden" in tag
    # Dashboard-first ordering (the aggregate cards precede the banner).
    assert html.index('id="sessions-dashboard"') < html.index('id="sessions-banner"')


def test_sessions_banner_css_is_hidden_and_tokenized() -> None:
    """The banner CSS must hide the default slot and use design tokens."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    assert ".sessions-banner[hidden]" in SESSIONS_CSS
    start = SESSIONS_CSS.index(".sessions-banner {")
    block = SESSIONS_CSS[start : SESSIONS_CSS.index("}", start)]
    assert "padding" in block
    assert "var(--" in block


def test_sessions_css_is_dashboard_only() -> None:
    """The CSS keeps dashboard/stat-card/banner/badge blocks and drops list blocks."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    assert ".sessions-dashboard" in SESSIONS_CSS
    assert ".sessions-stat-card" in SESSIONS_CSS
    assert ".sessions-last-updated" in SESSIONS_CSS
    # Deleted blocks.
    assert ".sessions-table" not in SESSIONS_CSS
    assert ".session-drawer" not in SESSIONS_CSS
    assert ".sessions-toolbar" not in SESSIONS_CSS
    assert "skeleton" not in SESSIONS_CSS


# ── Banner behaviour ──────────────────────────────────────────────────────────


def test_sessions_js_toggles_cost_banner_before_fetching() -> None:
    """Runtime changes must update the banner before re-fetching the aggregate."""
    js = _sessions_js()

    assert "CODEX_BANNER_TEXT" in js
    assert "Cost not tracked for Codex" in js
    update_banner = _function_body(js, "updateBanner")
    assert "textContent" in update_banner
    assert "innerHTML" not in update_banner
    assert "removeAttribute('hidden')" in js
    assert "setAttribute('hidden'" in js
    assert "runtime === 'codex'" in js

    listener = js[js.index("addEventListener('dadaia:runtime-change'") :][:400]
    assert listener.index("updateBanner()") < listener.index("fetchAggregate()")


def test_sessions_js_supports_pi_cost_unknown_banner() -> None:
    """PI shares the Codex cost-unknown posture: its own banner + 'N/A' cost."""
    js = _sessions_js()

    assert "PI_BANNER_TEXT" in js
    assert "Cost not tracked for PI" in js
    assert "isCostUnknownRuntime" in js
    assert "runtime === 'codex' || runtime === 'pi'" in js


# ── Cost render mapping (FR1 matrix, client half) ─────────────────────────────


def test_sessions_js_cost_mapping_covers_matrix() -> None:
    """renderDashboard maps cost per FR1: 'N/A' (cost-unknown) / '—' (null) / '$X.XX'."""
    js = _sessions_js()
    body = _function_body(js, "renderDashboard")

    # codex/pi runtime → 'N/A' (matrix case 1; runtime forces cost-unknown).
    assert "isCostUnknown ? 'N/A'" in body
    # claude with null total_cost_usd → '—' (matrix cases 2/3 — NOT 'N/A').
    assert "totalCostUsd == null ? '—'" in body
    # claude with a real amount → '$X.XX' (matrix cases 4/5 — incl. '$0.00' at 0.0).
    assert "'$' + Number(totalCostUsd).toFixed(2)" in body

    # Total Sessions keeps its "N active" sub-label from active_sessions.
    assert "active_sessions" in js
    assert "' active'" in body
    # Top Agent renders its name + session-count sub-label.
    assert "session_count" in js


def test_sessions_js_has_no_list_machinery() -> None:
    """The list/table/drawer/sort/filter and the 10s auto-refresh are gone."""
    js = _sessions_js()

    assert "setInterval" not in js
    assert "AUTO_REFRESH_MS" not in js
    assert "renderTable" not in js
    assert "openDrawer" not in js
    assert "applySort" not in js
    assert "applyFilter" not in js
    assert "sessions-tbody" not in js
    assert "data.sessions" not in js
