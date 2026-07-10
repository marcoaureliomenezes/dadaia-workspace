"""Unit contract for the dashboard-only Sessions view scaffold (panel-plumbing v0.1.52 FR2).

The Sessions tab renders a 4-card cost aggregate + a cost-unknown banner from the
server-side ``/api/sessions`` aggregate envelope. The cost render mapping ('N/A'
vs '—' vs '$X.XX') against the FR1 cost-known matrix, the runtime-toggle-before-
fetch ordering, and the deleted list-era machinery (table, drawer, sort/filter,
skeleton, 10s auto-refresh) are all rendered/DOM behaviors proven by the
Playwright suite (e2e SES-DASH-01..04 renders the real matrix incl. N/A vs — vs
$X.XX). This unit test keeps the ONE thing the E2E suite cannot cheaply assert
per-push: the scaffold DOM hooks the JS keys on actually exist.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _banner_tag(html: str) -> str:
    start = html.index('id="sessions-banner"')
    tag_start = html.rfind("<", 0, start)
    tag_end = html.index(">", start)
    return html[tag_start : tag_end + 1]


def test_sessions_scaffold_dom_hooks() -> None:
    """The scaffold keeps dashboard + banner + badge + pi runtime button, drops all
    list markup, and the banner is an accessible hidden status slot after the
    dashboard, styled with hidden state + design tokens."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()

    # Surviving surface.
    assert 'id="sessions-dashboard"' in html
    assert 'id="sessions-banner"' in html
    assert 'id="sessions-last-updated"' in html
    assert 'id="sessions-runtime-btn-pi"' in html

    # Deleted list-era machinery.
    assert "sessions-table" not in html
    assert "sessions-tbody" not in html
    assert "session-drawer" not in html
    assert "sessions-filter" not in html
    assert "sessions-toolbar" not in html
    assert "data-sort-key" not in html

    # Accessible hidden status slot, rendered after the dashboard (dashboard-first).
    tag = _banner_tag(html)
    assert 'class="sessions-banner"' in tag
    assert 'role="status"' in tag
    assert 'aria-live="polite"' in tag
    assert "hidden" in tag
    assert html.index('id="sessions-dashboard"') < html.index('id="sessions-banner"')

    # CSS: hidden state + design tokens; dashboard/stat-card/badge kept, list blocks gone.
    assert ".sessions-banner[hidden]" in SESSIONS_CSS
    start = SESSIONS_CSS.index(".sessions-banner {")
    block = SESSIONS_CSS[start : SESSIONS_CSS.index("}", start)]
    assert "padding" in block
    assert "var(--" in block
    assert ".sessions-dashboard" in SESSIONS_CSS
    assert ".sessions-stat-card" in SESSIONS_CSS
    assert ".sessions-last-updated" in SESSIONS_CSS
    assert ".sessions-table" not in SESSIONS_CSS
    assert ".session-drawer" not in SESSIONS_CSS
    assert ".sessions-toolbar" not in SESSIONS_CSS
    assert "skeleton" not in SESSIONS_CSS
