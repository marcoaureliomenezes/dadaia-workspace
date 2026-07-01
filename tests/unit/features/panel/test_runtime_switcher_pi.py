"""Unit contracts for the PI runtime button in the panel switchers (A12)."""

from __future__ import annotations


def test_sessions_switcher_has_pi_button() -> None:
    from dadaia_workspace.features.panel.views.sessions import render_sessions_section

    html = render_sessions_section()
    assert 'id="sessions-runtime-btn-pi"' in html
    assert 'data-runtime-value="pi"' in html
    assert "PI runtime" in html


def test_runtime_js_allows_pi() -> None:
    from pathlib import Path

    js = Path("dadaia_workspace/features/panel/views/assets/js/runtime.js").read_text(
        encoding="utf-8"
    )
    assert "['claude', 'codex', 'pi']" in js


def test_index_localstorage_allows_pi() -> None:
    from pathlib import Path

    src = Path("dadaia_workspace/features/panel/views/index.py").read_text(encoding="utf-8")
    # The runtime-restore inline script must allow 'pi' alongside claude/codex.
    assert "r==='claude'||r==='codex'||r==='pi'" in src
