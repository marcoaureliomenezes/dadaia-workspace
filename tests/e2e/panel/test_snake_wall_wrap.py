from __future__ import annotations

import json
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow(reason="executes Games JavaScript in a Node VM")]

ROOT = Path(__file__).resolve().parents[3]
GAMES_JS = ROOT / "dadaia_workspace/features/panel/views/assets/js/games.js"


def run_snake_probe(operations: str) -> dict[str, object]:
    script = dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');
        const scoreValues = {{ 'snake-score': '0', 'tetris-score': '0' }};
        function context2d() {{
          return {{
            fillStyle: '', strokeStyle: '',
            fillRect: function () {{}}, beginPath: function () {{}},
            moveTo: function () {{}}, lineTo: function () {{}}, stroke: function () {{}}
          }};
        }}
        function element(id) {{
          return {{
            id: id,
            hidden: id === 'tetris-panel',
            dataset: {{}}, classList: {{ toggle: function () {{}} }},
            setAttribute: function () {{}}, addEventListener: function () {{}},
            focus: function () {{}}, getContext: function () {{ return context2d(); }},
            get value() {{ return scoreValues[id]; }},
            set value(value) {{ scoreValues[id] = String(value); }}
          }};
        }}
        const elements = {{
          'snake-canvas': element('snake-canvas'),
          'tetris-canvas': element('tetris-canvas'),
          'snake-score': element('snake-score'),
          'tetris-score': element('tetris-score'),
          'snake-panel': element('snake-panel'),
          'tetris-panel': element('tetris-panel')
        }};
        const document = {{
          getElementById: function (id) {{ return elements[id]; }},
          querySelectorAll: function () {{ return []; }},
          querySelector: function (selector) {{
            if (selector === '[data-action="snake-toggle"]' || selector === '[data-action="snake-reset"]' ||
                selector === '[data-action="tetris-toggle"]' || selector === '[data-action="tetris-reset"]') {{
              return element(selector);
            }}
            if (selector === '[data-game-panel="snake"]') {{ return elements['snake-panel']; }}
            if (selector === '[data-game-panel="tetris"]') {{ return elements['tetris-panel']; }}
            return element(selector);
          }},
          addEventListener: function () {{}}
        }};
        const timers = [];
        const context = {{
          window: {{ __DADAIA_SNAKE_TEST_HOOK__: true }}, document: document, console: console,
          Math: Object.create(Math),
          setInterval: function (fn) {{ timers.push(fn); return timers.length; }},
          clearInterval: function () {{}}
        }};
        context.window.window = context.window;
        context.window.document = document;
        context.window.Math = context.Math;
        context.Math.random = function () {{ return 0.95; }};
        vm.createContext(context);
        vm.runInContext(fs.readFileSync({json.dumps(str(GAMES_JS))}, 'utf8'), context);
        const hook = context.window.__dadaiaSnakeTest;
        if (!hook) {{ throw new Error('Snake test hook was not installed'); }}
        {operations}
        """
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def tick_from_state(state: dict[str, object]) -> dict[str, object]:
    return run_snake_probe(
        f"""
        hook.setState({json.dumps(state)});
        hook.tick();
        console.log(JSON.stringify(hook.getState()));
        """
    )


def test_left_wall_crossing_wraps_without_reset() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 0, "y": 6}, {"x": 0, "y": 7}, {"x": 0, "y": 8}],
            "food": {"x": 5, "y": 5},
            "direction": {"x": -1, "y": 0},
            "nextDirection": {"x": -1, "y": 0},
            "score": 30,
            "running": False,
        }
    )
    assert state["snake"][0] == {"x": 19, "y": 6}
    assert state["score"] == 30
    assert state["running"] is False


def test_right_wall_crossing_wraps_without_reset() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 19, "y": 6}, {"x": 19, "y": 7}, {"x": 19, "y": 8}],
            "food": {"x": 5, "y": 5},
            "direction": {"x": 1, "y": 0},
            "nextDirection": {"x": 1, "y": 0},
            "score": 20,
            "running": False,
        }
    )
    assert state["snake"][0] == {"x": 0, "y": 6}
    assert state["score"] == 20


def test_top_wall_crossing_wraps_without_reset() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 6, "y": 0}, {"x": 7, "y": 0}, {"x": 8, "y": 0}],
            "food": {"x": 5, "y": 5},
            "direction": {"x": 0, "y": -1},
            "nextDirection": {"x": 0, "y": -1},
            "score": 20,
            "running": False,
        }
    )
    assert state["snake"][0] == {"x": 6, "y": 19}
    assert state["score"] == 20


def test_bottom_wall_crossing_wraps_without_reset() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 6, "y": 19}, {"x": 7, "y": 19}, {"x": 8, "y": 19}],
            "food": {"x": 5, "y": 5},
            "direction": {"x": 0, "y": 1},
            "nextDirection": {"x": 0, "y": 1},
            "score": 20,
            "running": False,
        }
    )
    assert state["snake"][0] == {"x": 6, "y": 0}
    assert state["score"] == 20


def test_wall_contact_from_non_starting_state_uses_ordinary_progression() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 0, "y": 3}, {"x": 0, "y": 4}, {"x": 0, "y": 5}, {"x": 1, "y": 5}],
            "food": {"x": 10, "y": 10},
            "direction": {"x": -1, "y": 0},
            "nextDirection": {"x": -1, "y": 0},
            "score": 40,
            "running": False,
        }
    )
    assert state["snake"] == [
        {"x": 19, "y": 3},
        {"x": 0, "y": 3},
        {"x": 0, "y": 4},
        {"x": 0, "y": 5},
    ]
    assert state["score"] == 40
    assert state["food"] == {"x": 10, "y": 10}


def test_self_collision_still_resets_snake() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 5, "y": 5}, {"x": 5, "y": 6}, {"x": 4, "y": 6}, {"x": 4, "y": 5}],
            "food": {"x": 10, "y": 10},
            "direction": {"x": 0, "y": 1},
            "nextDirection": {"x": 0, "y": 1},
            "score": 50,
            "running": True,
        }
    )
    assert state["snake"] == [{"x": 8, "y": 10}, {"x": 7, "y": 10}, {"x": 6, "y": 10}]
    assert state["score"] == 0
    assert state["food"] == {"x": 14, "y": 10}
    assert state["running"] is False


def test_food_at_next_head_increments_score_grows_and_relocates_food() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 8, "y": 8}, {"x": 7, "y": 8}, {"x": 6, "y": 8}],
            "food": {"x": 9, "y": 8},
            "direction": {"x": 1, "y": 0},
            "nextDirection": {"x": 1, "y": 0},
            "score": 10,
            "running": False,
        }
    )
    assert state["score"] == 20
    assert len(state["snake"]) == 4
    assert state["snake"][0] == {"x": 9, "y": 8}
    assert state["food"] == {"x": 19, "y": 19}


def test_ordinary_non_food_movement_advances_head_and_pops_tail() -> None:
    state = tick_from_state(
        {
            "snake": [{"x": 8, "y": 8}, {"x": 7, "y": 8}, {"x": 6, "y": 8}],
            "food": {"x": 2, "y": 2},
            "direction": {"x": 1, "y": 0},
            "nextDirection": {"x": 1, "y": 0},
            "score": 10,
            "running": False,
        }
    )
    assert state["snake"] == [{"x": 9, "y": 8}, {"x": 8, "y": 8}, {"x": 7, "y": 8}]
    assert state["score"] == 10


def test_direction_seam_delegates_to_reverse_direction_guard() -> None:
    state = run_snake_probe(
        """
        hook.setState({
          snake: [{x: 8, y: 8}, {x: 7, y: 8}, {x: 6, y: 8}],
          direction: {x: 1, y: 0}, nextDirection: {x: 1, y: 0},
          food: {x: 2, y: 2}, score: 0, running: false
        });
        hook.setDirection('left');
        hook.tick();
        console.log(JSON.stringify(hook.getState()));
        """
    )
    assert state["snake"][0] == {"x": 9, "y": 8}
