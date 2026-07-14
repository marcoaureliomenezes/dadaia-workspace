from __future__ import annotations

import json
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow(reason="executes Games JavaScript in a Node VM")]

ROOT = Path(__file__).resolve().parents[3]
GAMES_JS = ROOT / "dadaia_workspace/features/panel/views/assets/js/games.js"


def run_pong_probe(operations: str) -> dict[str, object]:
    template = dedent(
        """
        const fs = require('fs');
        const vm = require('vm');

        const scoreValues = {
          'snake-score': '0',
          'pong-score': '0',
          'tetris-score': '0',
          'breakout-score': '0',
        };

        function makeClassList(initial) {
          const values = new Set(initial || []);
          return {
            toggle: function (value, force) {
              if (force === undefined) {
                force = !values.has(value);
              }
              if (force) {
                values.add(value);
              } else {
                values.delete(value);
              }
              return force;
            },
            has: function (value) {
              return values.has(value);
            }
          };
        }

        function createElement(id, dataset, classList, hidden) {
          const element = {
            id: id,
            hidden: !!hidden,
            dataset: dataset || {},
            classList: makeClassList(classList || []),
            _attributes: {},
            _listeners: {},
            setAttribute: function (name, value) {
              this._attributes[name] = String(value);
            },
            getAttribute: function (name) {
              return this._attributes[name];
            },
            addEventListener: function (name, listener) {
              if (!this._listeners[name]) {
                this._listeners[name] = [];
              }
              this._listeners[name].push(listener);
            },
            dispatchEvent: function (event) {
              (this._listeners[event.type] || []).forEach((listener) => {
                listener(event);
              });
            },
            click: function () {
              this.dispatchEvent({ type: 'click', target: this });
            },
            focus: function () {},
          };
          if (id.endsWith('-score')) {
            Object.defineProperty(element, 'value', {
              get: function () {
                return scoreValues[id];
              },
              set: function (value) {
                scoreValues[id] = String(value);
              },
            });
          }
          return element;
        }

        function context2d() {
          return {
            fillStyle: '',
            strokeStyle: '',
            fillRect: function () {},
            beginPath: function () {},
            moveTo: function () {},
            lineTo: function () {},
            stroke: function () {},
            arc: function () {},
            fill: function () {},
          };
        }

        const elements = {
          'snake-canvas': createElement('snake-canvas'),
          'pong-canvas': createElement('pong-canvas'),
          'tetris-canvas': createElement('tetris-canvas'),
          'breakout-canvas': createElement('breakout-canvas'),
          'snake-score': createElement('snake-score'),
          'pong-score': createElement('pong-score'),
          'tetris-score': createElement('tetris-score'),
          'breakout-score': createElement('breakout-score'),
          'snake-panel': createElement('snake-panel', { gamePanel: 'snake' }, ['game-panel', 'active']),
          'breakout-panel': createElement('breakout-panel', { gamePanel: 'breakout' }, ['game-panel'], true),
          'pong-panel': createElement('pong-panel', { gamePanel: 'pong' }, ['game-panel'], true),
          'tetris-panel': createElement('tetris-panel', { gamePanel: 'tetris' }, ['game-panel'], true),
          'snake-choice': createElement('snake-choice', { game: 'snake' }, ['game-choice', 'active']),
          'breakout-choice': createElement('breakout-choice', { game: 'breakout' }, ['game-choice']),
          'pong-choice': createElement('pong-choice', { game: 'pong' }, ['game-choice']),
          'tetris-choice': createElement('tetris-choice', { game: 'tetris' }, ['game-choice']),
          'snake-toggle': createElement('snake-toggle', { action: 'snake-toggle' }),
          'snake-reset': createElement('snake-reset', { action: 'snake-reset' }),
          'pong-toggle': createElement('pong-toggle', { action: 'pong-toggle' }),
          'pong-reset': createElement('pong-reset', { action: 'pong-reset' }),
          'tetris-toggle': createElement('tetris-toggle', { action: 'tetris-toggle' }),
          'tetris-reset': createElement('tetris-reset', { action: 'tetris-reset' }),
          'breakout-toggle': createElement('breakout-toggle', { action: 'breakout-toggle' }),
          'breakout-reset': createElement('breakout-reset', { action: 'breakout-reset' }),
          'breakout-left': createElement('breakout-left', { breakoutDir: 'left' }),
          'breakout-right': createElement('breakout-right', { breakoutDir: 'right' }),
          'snake-up': createElement('snake-up', { snakeDir: 'up' }),
          'snake-left': createElement('snake-left', { snakeDir: 'left' }),
          'snake-down': createElement('snake-down', { snakeDir: 'down' }),
          'snake-right': createElement('snake-right', { snakeDir: 'right' }),
          'tetris-left': createElement('tetris-left', { tetrisAction: 'left' }),
          'tetris-rotate': createElement('tetris-rotate', { tetrisAction: 'rotate' }),
          'tetris-right': createElement('tetris-right', { tetrisAction: 'right' }),
          'tetris-down': createElement('tetris-down', { tetrisAction: 'down' }),
          'tetris-drop': createElement('tetris-drop', { tetrisAction: 'drop' }),
          'pong-up': createElement('pong-up', { pongDir: 'up' }),
          'pong-down': createElement('pong-down', { pongDir: 'down' }),
        };

        const allChoices = [
          elements['snake-choice'],
          elements['breakout-choice'],
          elements['pong-choice'],
          elements['tetris-choice'],
        ];
        const allPanels = [
          elements['snake-panel'],
          elements['breakout-panel'],
          elements['pong-panel'],
          elements['tetris-panel'],
        ];
        const snakeDirs = [elements['snake-up'], elements['snake-left'], elements['snake-down'], elements['snake-right']];
        const tetrisButtons = [elements['tetris-left'], elements['tetris-rotate'], elements['tetris-right'], elements['tetris-down'], elements['tetris-drop']];
        const pongDirs = [elements['pong-up'], elements['pong-down']];
        const breakoutDirs = [elements['breakout-left'], elements['breakout-right']];

        function bindCanvas(el) {
          el.getContext = function () { return context2d(); };
        }

        bindCanvas(elements['snake-canvas']);
        bindCanvas(elements['pong-canvas']);
        bindCanvas(elements['tetris-canvas']);
        bindCanvas(elements['breakout-canvas']);

        const document = {
          getElementById: function (id) {
            return elements[id];
          },
          querySelectorAll: function (selector) {
            if (selector === '.game-choice') {
              return allChoices;
            }
            if (selector === '[data-breakout-dir]') {
              return breakoutDirs;
            }
            if (selector === '[data-snake-dir]') {
              return snakeDirs;
            }
            if (selector === '[data-tetris-action]') {
              return tetrisButtons;
            }
            if (selector === '[data-pong-dir]') {
              return pongDirs;
            }
            if (selector === '[data-pong-dir="up"]') {
              return [elements['pong-up']];
            }
            if (selector === '[data-pong-dir="down"]') {
              return [elements['pong-down']];
            }
            if (selector === '[data-game-panel]') {
              return allPanels;
            }
            if (selector === '[data-game-panel="snake"]') {
              return [elements['snake-panel']];
            }
            if (selector === '[data-game-panel="breakout"]') {
              return [elements['breakout-panel']];
            }
            if (selector === '[data-game-panel="pong"]') {
              return [elements['pong-panel']];
            }
            if (selector === '[data-game-panel="tetris"]') {
              return [elements['tetris-panel']];
            }
            if (selector === '[data-action="snake-toggle"]') {
              return [elements['snake-toggle']];
            }
            if (selector === '[data-action="snake-reset"]') {
              return [elements['snake-reset']];
            }
            if (selector === '[data-action="pong-toggle"]') {
              return [elements['pong-toggle']];
            }
            if (selector === '[data-action="pong-reset"]') {
              return [elements['pong-reset']];
            }
            if (selector === '[data-action="tetris-toggle"]') {
              return [elements['tetris-toggle']];
            }
            if (selector === '[data-action="tetris-reset"]') {
              return [elements['tetris-reset']];
            }
            if (selector === '[data-action="breakout-toggle"]') {
              return [elements['breakout-toggle']];
            }
            if (selector === '[data-action="breakout-reset"]') {
              return [elements['breakout-reset']];
            }
            if (selector === '[data-breakout-dir="left"]') {
              return [elements['breakout-left']];
            }
            if (selector === '[data-breakout-dir="right"]') {
              return [elements['breakout-right']];
            }
            if (selector === '[data-game="snake"]') {
              return [elements['snake-choice']];
            }
            if (selector === '[data-game="breakout"]') {
              return [elements['breakout-choice']];
            }
            if (selector === '[data-game="pong"]') {
              return [elements['pong-choice']];
            }
            if (selector === '[data-game="tetris"]') {
              return [elements['tetris-choice']];
            }
            return [];
          },
          querySelector: function (selector) {
            const all = document.querySelectorAll(selector);
            return all.length ? all[0] : null;
          },
          addEventListener: function () {},
          dispatchEvent: function () {},
        };

        const timers = [];
        const context = {
          window: { __DADAIA_PONG_TEST_HOOK__: true },
          document: document,
          console: console,
          Math: Object.create(Math),
          setInterval: function (callback) { timers.push(callback); return timers.length; },
          clearInterval: function () {},
        };
        context.window.window = context.window;
        context.window.document = document;
        context.window.Math = context.Math;
        vm.createContext(context);
        vm.runInContext(fs.readFileSync(__GAMES_JS__, 'utf8'), context);
        const hook = context.window.__dadaiaPongTest;
        if (!hook) {
          throw new Error('Pong test hook was not installed');
        }
        """
        + operations
    )
    template = template.replace("__GAMES_JS__", json.dumps(str(GAMES_JS)))
    completed = subprocess.run(
        ["node", "-e", template],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_game_choice_switches_visible_panel_single_active() -> None:
    state = run_pong_probe(
        """
        function snapshot() {
          return {
            snake: {
              hidden: document.querySelector('[data-game-panel="snake"]').hidden,
              active: document.querySelector('[data-game="snake"]').classList.has('active'),
            },
            breakout: {
              hidden: document.querySelector('[data-game-panel="breakout"]').hidden,
              active: document.querySelector('[data-game="breakout"]').classList.has('active'),
            },
            pong: {
              hidden: document.querySelector('[data-game-panel="pong"]').hidden,
              active: document.querySelector('[data-game="pong"]').classList.has('active'),
            },
            tetris: {
              hidden: document.querySelector('[data-game-panel="tetris"]').hidden,
              active: document.querySelector('[data-game="tetris"]').classList.has('active'),
            },
          };
        }

        const start = snapshot();
        document.querySelector('[data-game="snake"]').click();
        const snake = snapshot();
        document.querySelector('[data-game="breakout"]').click();
        const breakout = snapshot();
        document.querySelector('[data-game="pong"]').click();
        const pong = snapshot();
        document.querySelector('[data-game="tetris"]').click();
        const tetris = snapshot();
        console.log(JSON.stringify({ start, snake, breakout, pong, tetris }));
        """
    )
    assert state["start"]["snake"]["hidden"] is False
    assert state["start"]["snake"]["active"] is True
    assert state["start"]["breakout"]["hidden"] is True

    assert state["breakout"]["breakout"]["hidden"] is False
    assert state["breakout"]["breakout"]["active"] is True

    assert state["pong"]["pong"]["hidden"] is False
    assert state["pong"]["pong"]["active"] is True

    assert state["tetris"]["tetris"]["hidden"] is False
    assert state["tetris"]["tetris"]["active"] is True


def test_pong_toggle_and_reset_controls_affect_active_panel_only() -> None:
    state = run_pong_probe(
        """
        hook.setState({ ball: {x: 100, y: 120}, velocity: {x: 3, y: 2}, paddleY: 120, score: 8, running: false });
        document.querySelector('[data-game="snake"]').click();
        document.querySelector('[data-action="pong-toggle"]').click();
        const beforeActivate = hook.getState();
        document.querySelector('[data-action="pong-reset"]').click();
        const inactiveReset = hook.getState();
        document.querySelector('[data-game="pong"]').click();
        document.querySelector('[data-action="pong-toggle"]').click();
        const afterToggle = hook.getState();
        document.querySelector('[data-action="pong-reset"]').click();
        const afterReset = hook.getState();
        document.querySelector('[data-game="snake"]').click();
        document.querySelector('[data-action="pong-toggle"]').click();
        const afterRevert = hook.getState();
        document.querySelector('[data-game="tetris"]').click();
        document.querySelector('[data-action="pong-reset"]').click();
        const afterWrongPanelReset = hook.getState();
        console.log(JSON.stringify({
          beforeActivate,
          inactiveReset,
          afterToggle,
          afterReset,
          afterRevert,
          afterWrongPanelReset,
        }));
        """
    )
    assert state["beforeActivate"]["running"] is False
    assert state["inactiveReset"]["running"] is False
    assert state["inactiveReset"]["score"] == 8
    assert state["afterToggle"]["running"] is True
    assert state["afterReset"]["score"] == 0
    assert state["afterRevert"]["running"] is False
    assert state["afterWrongPanelReset"]["score"] == 0


def test_pong_keyboard_and_dpad_controls_move_paddle() -> None:
    state = run_pong_probe(
        """
        document.querySelector('[data-game="pong"]').click();
        hook.setState({ ball: {x: 240, y: 160}, velocity: {x: 3, y: 2}, paddleY: 120, paddleDy: 0, score: 0, running: false });
        hook.keydown('ArrowUp');
        hook.tick();
        const afterKey = hook.getState();
        hook.setState({ ball: afterKey.ball, velocity: afterKey.velocity, paddleY: afterKey.paddleY, paddleDy: 0, score: afterKey.score });
        document.querySelector('[data-pong-dir="down"]').click();
        hook.tick();
        const afterDpad = hook.getState();
        document.querySelector('[data-game="snake"]').click();
        hook.keydown('ArrowDown');
        const afterWrongPanelKey = hook.getState();
        console.log(JSON.stringify({ afterKey, afterDpad, afterWrongPanelKey }));
        """
    )
    assert state["afterKey"]["paddleY"] < state["afterDpad"]["paddleY"]
    assert state["afterDpad"]["paddleY"] == state["afterWrongPanelKey"]["paddleY"]
