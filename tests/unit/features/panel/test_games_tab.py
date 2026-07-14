from __future__ import annotations

from dadaia_workspace.features.panel.views.games import render_games_section
from dadaia_workspace.features.panel.views.static import render_static


def test_games_section_has_two_playable_canvas_surfaces() -> None:
    html = render_games_section()
    assert 'id="snake-canvas"' in html
    assert 'id="tetris-canvas"' in html
    assert 'data-game="snake"' in html and "Codex" in html
    assert 'data-game="tetris"' in html and "PI" in html
    assert 'data-snake-dir="up"' in html
    assert 'data-tetris-action="rotate"' in html


def test_games_assets_are_served() -> None:
    for name, content_type in (
        ("games.css", "text/css; charset=utf-8"),
        ("games.js", "application/javascript; charset=utf-8"),
    ):
        status, actual_type, body = render_static()(name=name)
        assert status == 200
        assert actual_type == content_type
        assert body
