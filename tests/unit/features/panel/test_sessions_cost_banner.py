"""Unit contracts for the Sessions Codex cost banner."""

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


def test_sessions_scaffold_exposes_accessible_hidden_banner_slot() -> None:
    """The Sessions scaffold must expose a hidden status slot above the table."""
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    tag = _banner_tag(html)

    assert 'class="sessions-banner"' in tag
    assert 'role="status"' in tag
    assert 'aria-live="polite"' in tag
    assert "hidden" in tag
    assert html.index('id="sessions-banner"') < html.index('id="sessions-table-container"')


def test_sessions_banner_css_is_hidden_and_tokenized() -> None:
    """The banner CSS must hide the default slot and use design tokens."""
    from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS

    assert ".sessions-banner[hidden]" in SESSIONS_CSS
    start = SESSIONS_CSS.index(".sessions-banner {")
    block = SESSIONS_CSS[start : SESSIONS_CSS.index("}", start)]
    assert "padding" in block
    assert "var(--" in block


def test_sessions_js_toggles_codex_banner_before_rendering_rows() -> None:
    """Runtime changes and fetch success must update the banner before row rendering."""
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
    assert listener.index("updateBanner()") < listener.index("fetchSessions()")

    success = js[js.index("_allRows = data.sessions || [];") :][:300]
    assert success.index("updateBanner()") < success.index("renderTable(")


def test_sessions_js_supports_pi_cost_unknown_banner() -> None:
    """PI shares the Codex cost-unknown posture: its own banner + '—' cost (A12)."""
    js = _sessions_js()

    assert "PI_BANNER_TEXT" in js
    assert "Cost not tracked for PI" in js
    # The cost-unknown predicate must cover both codex and pi.
    assert "isCostUnknownRuntime" in js
    assert "runtime === 'codex' || runtime === 'pi'" in js
