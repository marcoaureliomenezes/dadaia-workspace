from __future__ import annotations

import inspect
import re
from pathlib import Path

from dadaia_workspace.features.panel.views.games import render_games_section
from dadaia_workspace.features.panel.views.static import render_static


def test_games_section_has_playable_canvas_surfaces_for_three_games() -> None:
    html = render_games_section()
    assert isinstance(html, str)
    match = re.search(r'<div class="games-switch" role="tablist"[^>]*>(.*?)</div>', html, re.S)
    assert match
    switch_markup = match.group(1)
    for selector in ("snake", "breakout", "pong", "tetris"):
        assert f'data-game="{selector}"' in switch_markup
    assert re.search(
        r'<button[^>]*class="game-choice active"[^>]*data-game="snake"[^>]*role="tab"[^>]*aria-selected="true"',
        switch_markup,
        re.S,
    )
    assert re.search(
        r'<button[^>]*class="game-choice"[^>]*data-game="breakout"[^>]*role="tab"[^>]*aria-selected="false"',
        switch_markup,
        re.S,
    )
    assert re.search(
        r'<button[^>]*class="game-choice"[^>]*data-game="pong"[^>]*role="tab"[^>]*aria-selected="false"',
        switch_markup,
        re.S,
    )
    assert re.search(
        r'<button[^>]*class="game-choice"[^>]*data-game="tetris"[^>]*role="tab"[^>]*aria-selected="false"',
        switch_markup,
        re.S,
    )
    assert switch_markup.index('data-game="snake"') < switch_markup.index('data-game="breakout"')
    assert switch_markup.index('data-game="breakout"') < switch_markup.index('data-game="pong"')
    assert switch_markup.index('data-game="pong"') < switch_markup.index('data-game="tetris"')
    assert 'data-game-panel="breakout"' in html and "Breakout" in html
    assert 'data-game-panel="snake"' in html and "Snake" in html
    assert 'data-game-panel="pong"' in html and "Pong" in html
    assert 'data-game-panel="tetris"' in html and "Tetris" in html
    assert 'id="snake-canvas" width="400" height="400"' in html
    assert 'id="breakout-canvas" width="480" height="320"' in html
    assert 'id="pong-canvas" width="480" height="320"' in html
    assert 'id="tetris-canvas" width="300" height="600"' in html
    assert 'id="snake-score"' in html
    assert 'id="breakout-score"' in html
    assert 'id="pong-score"' in html
    assert 'id="tetris-score"' in html
    assert 'data-action="snake-toggle"' in html
    assert 'data-action="breakout-toggle"' in html
    assert 'data-action="pong-toggle"' in html
    assert 'data-action="tetris-toggle"' in html
    assert 'data-action="snake-reset"' in html
    assert 'data-action="breakout-reset"' in html
    assert 'data-action="pong-reset"' in html
    assert 'data-action="tetris-reset"' in html
    for direction in ("up", "left", "down", "right"):
        assert f'data-snake-dir="{direction}"' in html
    assert 'data-breakout-dir="left"' in html
    assert 'data-breakout-dir="right"' in html
    for direction in ("up", "down"):
        assert f'data-pong-dir="{direction}"' in html
    for action in ("left", "rotate", "right", "down", "drop"):
        assert f'data-tetris-action="{action}"' in html
    assert 'data-game="snake"' in html and "Codex" in html
    assert 'data-game="breakout"' in html and "Breakout (PI)" in html
    assert 'data-game="pong"' in html and "Pong (Codex)" in html
    assert 'data-game="tetris"' in html and "PI" in html
    assert (
        'data-game="snake"' in html
        and 'data-game="breakout"' in html
        and 'data-game="pong"' in html
        and 'data-game="tetris"' in html
    )


def test_games_assets_are_served() -> None:
    static_view = render_static()
    signature = inspect.signature(static_view)
    assert list(signature.parameters) == ["name", "_kwargs"]
    assert signature.parameters["name"].default == ""
    assert signature.parameters["_kwargs"].kind is inspect.Parameter.VAR_KEYWORD

    for name, content_type in (
        ("games.css", "text/css; charset=utf-8"),
        ("games.js", "application/javascript; charset=utf-8"),
    ):
        status, actual_type, body = static_view(name=name, ignored=True)
        assert status == 200
        assert actual_type == content_type
        assert body

    js_status, js_type, js_body = static_view(name="games.js")
    asset_path = (
        Path(__file__).resolve().parents[4]
        / "dadaia_workspace/features/panel/views/assets/js/games.js"
    )
    assert js_status == 200
    assert js_type == "application/javascript; charset=utf-8"
    assert js_body == asset_path.read_bytes()
