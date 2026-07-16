from __future__ import annotations

import json
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow(reason="executes Games JavaScript in a Node VM")]

ROOT = Path(__file__).resolve().parents[3]
GAMES_JS = ROOT / "dadaia_workspace/features/panel/views/assets/js/games.js"


def run_breakout_probe(operations: str) -> dict[str, object]:
    script = dedent(
        """
        const fs = require('fs');
        const vm = require('vm');

        function classList(initial) {
          const values = new Set(initial || []);
          return {
            toggle: function (value, force) {
              if (force === undefined) { force = !values.has(value); }
              if (force) { values.add(value); } else { values.delete(value); }
              return force;
            },
            has: function (value) { return values.has(value); }
          };
        }

        function createElement(id, opts) {
          const options = opts || {};
          const element = {
            id: id,
            hidden: !!options.hidden,
            width: options.width || 0,
            height: options.height || 0,
            dataset: options.dataset || {},
            classList: classList(options.classList || []),
            _attributes: {},
            _listeners: {},
            _value: options.value || '0',
            setAttribute: function (name, value) { this._attributes[name] = String(value); },
            getAttribute: function (name) { return this._attributes[name]; },
            addEventListener: function (name, listener) {
              if (!this._listeners[name]) { this._listeners[name] = []; }
              this._listeners[name].push(listener);
            },
            dispatchEvent: function (event) {
              (this._listeners[event.type] || []).forEach(function (listener) { listener(event); });
            },
            click: function () { this.dispatchEvent({ type: 'click', target: this }); },
            focus: function () {},
            get value() { return String(this._value); },
            set value(value) { this._value = String(value); }
          };
          return element;
        }

        function context2d() {
          return {
            fillStyle: '', strokeStyle: '',
            beginPath: function () {}, moveTo: function () {}, lineTo: function () {}, stroke: function () {},
            fillRect: function () {}, arc: function () {}, fill: function () {}
          };
        }

        const elements = {
          'snake-canvas': createElement('snake-canvas', { width: 400, height: 400 }),
          'pong-canvas': createElement('pong-canvas', { width: 480, height: 320 }),
          'tetris-canvas': createElement('tetris-canvas', { width: 300, height: 600 }),
          'breakout-canvas': createElement('breakout-canvas', { width: 480, height: 320 }),
          'snake-score': createElement('snake-score'),
          'pong-score': createElement('pong-score'),
          'tetris-score': createElement('tetris-score'),
          'breakout-score': createElement('breakout-score'),
          'snake-panel': createElement('snake-panel', { dataset: { gamePanel: 'snake' }, classList: ['game-panel', 'active'] }),
          'breakout-panel': createElement('breakout-panel', { dataset: { gamePanel: 'breakout' }, hidden: true }),
          'pong-panel': createElement('pong-panel', { dataset: { gamePanel: 'pong' }, hidden: true }),
          'tetris-panel': createElement('tetris-panel', { dataset: { gamePanel: 'tetris' }, hidden: true }),
          'snake-choice': createElement('snake-choice', { dataset: { game: 'snake' }, classList: ['game-choice', 'active'] }),
          'breakout-choice': createElement('breakout-choice', { dataset: { game: 'breakout' }, classList: ['game-choice'] }),
          'pong-choice': createElement('pong-choice', { dataset: { game: 'pong' }, classList: ['game-choice'] }),
          'tetris-choice': createElement('tetris-choice', { dataset: { game: 'tetris' }, classList: ['game-choice'] }),
          'snake-toggle': createElement('snake-toggle', { dataset: { action: 'snake-toggle' } }),
          'snake-reset': createElement('snake-reset', { dataset: { action: 'snake-reset' } }),
          'pong-toggle': createElement('pong-toggle', { dataset: { action: 'pong-toggle' } }),
          'pong-reset': createElement('pong-reset', { dataset: { action: 'pong-reset' } }),
          'tetris-toggle': createElement('tetris-toggle', { dataset: { action: 'tetris-toggle' } }),
          'tetris-reset': createElement('tetris-reset', { dataset: { action: 'tetris-reset' } }),
          'breakout-toggle': createElement('breakout-toggle', { dataset: { action: 'breakout-toggle' } }),
          'breakout-reset': createElement('breakout-reset', { dataset: { action: 'breakout-reset' } }),
          'breakout-left': createElement('breakout-left', { dataset: { breakoutDir: 'left' } }),
          'breakout-right': createElement('breakout-right', { dataset: { breakoutDir: 'right' } }),
          'snake-up': createElement('snake-up', { dataset: { snakeDir: 'up' }}),
          'snake-left': createElement('snake-left', { dataset: { snakeDir: 'left' }}),
          'snake-down': createElement('snake-down', { dataset: { snakeDir: 'down' }}),
          'snake-right': createElement('snake-right', { dataset: { snakeDir: 'right' }}),
          'tetris-left': createElement('tetris-left', { dataset: { tetrisAction: 'left' }}),
          'tetris-rotate': createElement('tetris-rotate', { dataset: { tetrisAction: 'rotate' }}),
          'tetris-right': createElement('tetris-right', { dataset: { tetrisAction: 'right' }}),
          'tetris-down': createElement('tetris-down', { dataset: { tetrisAction: 'down' }}),
          'tetris-drop': createElement('tetris-drop', { dataset: { tetrisAction: 'drop' }}),
          'pong-up': createElement('pong-up', { dataset: { pongDir: 'up' }}),
          'pong-down': createElement('pong-down', { dataset: { pongDir: 'down' }}),
        };

        const snakeDirs = [elements['snake-up'], elements['snake-left'], elements['snake-down'], elements['snake-right']];
        const breakoutDirs = [elements['breakout-left'], elements['breakout-right']];
        const tetrisButtons = [elements['tetris-left'], elements['tetris-rotate'], elements['tetris-right'], elements['tetris-down'], elements['tetris-drop']];
        const pongDirs = [elements['pong-up'], elements['pong-down']];
        const allChoices = [elements['snake-choice'], elements['breakout-choice'], elements['pong-choice'], elements['tetris-choice']];
        const allPanels = [elements['snake-panel'], elements['breakout-panel'], elements['pong-panel'], elements['tetris-panel']];

        function panelVisibility() {
          return {
            snake: {
              hidden: elements['snake-panel'].hidden,
              active: elements['snake-choice'].classList.has('active'),
            },
            breakout: {
              hidden: elements['breakout-panel'].hidden,
              active: elements['breakout-choice'].classList.has('active'),
            },
            pong: {
              hidden: elements['pong-panel'].hidden,
              active: elements['pong-choice'].classList.has('active'),
            },
            tetris: {
              hidden: elements['tetris-panel'].hidden,
              active: elements['tetris-choice'].classList.has('active'),
            },
          };
        }

        function bindCanvas(element) {
          element.getContext = function () { return context2d(); };
          return element;
        }
        bindCanvas(elements['snake-canvas']);
        bindCanvas(elements['pong-canvas']);
        bindCanvas(elements['tetris-canvas']);
        bindCanvas(elements['breakout-canvas']);

        const document = {
          getElementById: function (id) { return elements[id]; },
          querySelectorAll: function (selector) {
            if (selector === '.game-choice') { return allChoices; }
            if (selector === '[data-breakout-dir]') { return breakoutDirs; }
            if (selector === '[data-snake-dir]') { return snakeDirs; }
            if (selector === '[data-tetris-action]') { return tetrisButtons; }
            if (selector === '[data-pong-dir]') { return pongDirs; }
            if (selector === '[data-game-panel]') { return allPanels; }
            if (selector === '[data-game-panel="snake"]') { return [elements['snake-panel']]; }
            if (selector === '[data-game-panel="breakout"]') { return [elements['breakout-panel']]; }
            if (selector === '[data-game-panel="pong"]') { return [elements['pong-panel']]; }
            if (selector === '[data-game-panel="tetris"]') { return [elements['tetris-panel']]; }
            if (selector === '[data-action="snake-toggle"]') { return [elements['snake-toggle']]; }
            if (selector === '[data-action="snake-reset"]') { return [elements['snake-reset']]; }
            if (selector === '[data-action="pong-toggle"]') { return [elements['pong-toggle']]; }
            if (selector === '[data-action="pong-reset"]') { return [elements['pong-reset']]; }
            if (selector === '[data-action="tetris-toggle"]') { return [elements['tetris-toggle']]; }
            if (selector === '[data-action="tetris-reset"]') { return [elements['tetris-reset']]; }
            if (selector === '[data-action="breakout-toggle"]') { return [elements['breakout-toggle']]; }
            if (selector === '[data-action="breakout-reset"]') { return [elements['breakout-reset']]; }
            if (selector === '[data-breakout-dir="left"]') { return [elements['breakout-left']]; }
            if (selector === '[data-breakout-dir="right"]') { return [elements['breakout-right']]; }
            if (selector === '[data-game="snake"]') { return [elements['snake-choice']]; }
            if (selector === '[data-game="breakout"]') { return [elements['breakout-choice']]; }
            if (selector === '[data-game="pong"]') { return [elements['pong-choice']]; }
            if (selector === '[data-game="tetris"]') { return [elements['tetris-choice']]; }
            return [];
          },
          querySelector: function (selector) {
            const all = document.querySelectorAll(selector);
            return all.length ? all[0] : null;
          },
          addEventListener: function (name, listener) {
            if (!document._listeners) { document._listeners = {}; }
            if (!document._listeners[name]) { document._listeners[name] = []; }
            document._listeners[name].push(listener);
          },
          dispatchEvent: function (event) {
            const eventObject = Object.assign({ preventDefault: function () {} }, event || {});
            (document._listeners && document._listeners[eventObject.type] || []).forEach(function (listener) { listener(eventObject); });
          }
        };

        const timers = [];
        const context = {
          window: { __DADAIA_BREAKOUT_TEST_HOOK__: true },
          document: document,
          console: console,
          Math: Object.create(Math),
          setInterval: function (callback) { timers.push(callback); return timers.length; },
          clearInterval: function () {}
        };
        context.window.window = context.window;
        context.window.document = document;
        context.window.Math = context.Math;
        vm.createContext(context);
        vm.runInContext(fs.readFileSync(__BREAKOUT_GAMES_JS__, 'utf8'), context);
        const hook = context.window.__dadaiaBreakoutTest;
        if (!hook) { throw new Error('Breakout test hook was not installed'); }
        function snapshotVisible() {
          return panelVisibility();
        }
        """
        + operations
    )
    script = script.replace("__BREAKOUT_GAMES_JS__", json.dumps(str(GAMES_JS)))
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_breakout_paddle_moves_with_dpad_and_keyboard_controls() -> None:
    state = run_breakout_probe(
        """
        const initial = hook.getState();
        document.querySelector('[data-game="breakout"]').click();

        document.querySelector('[data-breakout-dir="left"]').click();
        hook.tick();
        const afterLeftButton = hook.getState();

        const resetSeed = initial;
        hook.setState(resetSeed);
        document.querySelector('[data-breakout-dir="right"]').click();
        hook.tick();
        const afterRightButton = hook.getState();

        hook.setState(resetSeed);
        document.dispatchEvent({ type: 'keydown', key: 'ArrowRight' });
        hook.tick();
        const afterRightKey = hook.getState();

        console.log(JSON.stringify({ afterLeftButton, afterRightButton, afterRightKey }));
        """
    )
    assert state["afterLeftButton"]["paddleX"] < state["afterRightButton"]["paddleX"]
    assert state["afterRightButton"]["paddleX"] > state["afterLeftButton"]["paddleX"]
    assert state["afterRightButton"]["paddleX"] == state["afterRightKey"]["paddleX"]


def test_breakout_wall_bounce() -> None:
    state = run_breakout_probe(
        """
        const seed = hook.getState();
        hook.setState({ ball: { x: seed.canvasWidth - seed.ballRadius, y: 120 }, velocity: { x: 4, y: 0 }, score: 0, running: false });
        hook.tick();
        const right = hook.getState();
        hook.setState({ ball: { x: seed.ballRadius, y: 120 }, velocity: { x: -4, y: 0 }, score: 0, running: false });
        hook.tick();
        const left = hook.getState();
        hook.setState({ ball: { x: 200, y: seed.ballRadius }, velocity: { x: 0, y: -4 }, score: 0, running: false });
        hook.tick();
        const top = hook.getState();
        const missX = Math.max(seed.ballRadius, seed.paddleX - seed.paddleWidth - 2);
        hook.setState({
          ball: { x: missX, y: seed.canvasHeight - seed.ballRadius + 2 },
          velocity: { x: 0, y: 4 },
          score: 11,
          running: false,
        });
        hook.tick();
        const bottomMiss = hook.getState();
        console.log(JSON.stringify({ seed, right, left, top, bottomMiss }));
        """
    )
    assert state["right"]["velocity"]["x"] < 0
    assert state["left"]["velocity"]["x"] > 0
    assert state["top"]["velocity"]["y"] > 0
    assert state["bottomMiss"]["score"] == 0
    assert state["bottomMiss"]["ball"]["x"] == state["seed"]["ball"]["x"]
    assert state["bottomMiss"]["ball"]["y"] == state["seed"]["ball"]["y"]


def test_breakout_brick_collision_removes_brick_and_adds_score() -> None:
    state = run_breakout_probe(
        """
        const initial = hook.getState();
        const bricks = Array.from({ length: initial.rows }, function () { return Array(initial.cols).fill(0); });
        bricks[0][0] = 1;
        const startX = initial.brickLeft + initial.brickWidth / 2;
        const startY = initial.brickTop - (initial.ballRadius + 1);
        hook.setState({
          ball: { x: startX, y: startY },
          velocity: { x: 0, y: 4 },
          bricks: bricks,
          score: 0,
          running: false,
        });
        hook.tick();
        console.log(JSON.stringify(hook.getState()));
        """
    )
    assert state["score"] == 10
    assert state["bricks"][0][0] == 0


def test_breakout_miss_resets_state() -> None:
    state = run_breakout_probe(
        """
        hook.reset();
        const seeded = hook.getState();
        hook.setState({
          ball: { x: seeded.ball.x, y: seeded.canvasHeight + seeded.ballRadius + 50 },
          velocity: { x: 0, y: 4 },
          score: 42,
          paddleY: seeded.paddleY,
          bricks: seeded.bricks,
          running: false,
        });
        hook.tick();
        console.log(JSON.stringify({ seeded, after: hook.getState() }));
        """
    )
    after = state["after"]
    seeded = state["seeded"]
    assert after["score"] == 0
    assert after["ball"] == seeded["ball"]
    assert after["paddleX"] == seeded["paddleX"]
    assert after["paddleY"] == seeded["paddleY"]


def test_game_choice_switches_four_games_single_visible_panel() -> None:
    state = run_breakout_probe(
        """
        const start = snapshotVisible();
        document.querySelector('[data-game="breakout"]').click();
        const breakout = snapshotVisible();
        document.querySelector('[data-game="pong"]').click();
        const pong = snapshotVisible();
        document.querySelector('[data-game="tetris"]').click();
        const tetris = snapshotVisible();
        document.querySelector('[data-game="snake"]').click();
        const snake = snapshotVisible();
        console.log(JSON.stringify({ start, snake, breakout, pong, tetris }));
        """
    )
    assert state["snake"]["snake"]["hidden"] is False
    assert state["snake"]["breakout"]["hidden"] is True
    assert state["snake"]["pong"]["hidden"] is True
    assert state["snake"]["tetris"]["hidden"] is True

    assert state["breakout"]["breakout"]["hidden"] is False
    assert state["breakout"]["snake"]["hidden"] is True
    assert state["breakout"]["pong"]["hidden"] is True
    assert state["breakout"]["tetris"]["hidden"] is True

    assert state["pong"]["pong"]["hidden"] is False
    assert state["pong"]["snake"]["hidden"] is True
    assert state["pong"]["breakout"]["hidden"] is True
    assert state["pong"]["tetris"]["hidden"] is True

    assert state["tetris"]["tetris"]["hidden"] is False
    assert state["tetris"]["snake"]["hidden"] is True
    assert state["tetris"]["breakout"]["hidden"] is True
    assert state["tetris"]["pong"]["hidden"] is True


def test_breakout_controls_only_route_when_breakout_active() -> None:
    state = run_breakout_probe(
        """
        const initial = hook.getState();
        document.querySelector('[data-game="snake"]').click();
        hook.setState({ score: 12, bricks: initial.bricks, ball: initial.ball, velocity: initial.velocity, running: false });
        document.querySelector('[data-action="breakout-toggle"]').click();
        document.querySelector('[data-breakout-dir="right"]').click();
        const inactive = hook.getState();

        document.querySelector('[data-game="breakout"]').click();
        document.querySelector('[data-breakout-dir="right"]').click();
        hook.tick();
        const active = hook.getState();

        document.querySelector('[data-action="breakout-reset"]').click();
        const resetAfterRun = hook.getState();

        document.querySelector('[data-game="pong"]').click();
        document.dispatchEvent({ type: 'keydown', key: 'ArrowLeft' });
        const wrongPanelKey = hook.getState();

        console.log(JSON.stringify({ inactive, active, resetAfterRun, wrongPanelKey }));
        """
    )
    assert state["inactive"]["running"] is False
    assert state["inactive"]["score"] == 12
    assert state["inactive"]["paddleX"] == state["wrongPanelKey"]["paddleX"]
    assert state["active"]["paddleX"] > state["inactive"]["paddleX"]
    assert state["resetAfterRun"]["score"] == 0
