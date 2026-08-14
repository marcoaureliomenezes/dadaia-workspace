# PLAN — Release v0.2.6 — Add Codex Pong to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.6  
**Owner:** product-engineer  
**Source SPEC:** `specs/releases/v0.2.6/SPEC.md`  
**Workflow:** release-definition / plan_create

## 1. Planning problem

Add a third playable Games-tab entry named `Pong (Codex)` with its own canvas, controls, and gameplay loop while preserving existing Snake and Tetris behavior and the current asset-serving contract. The implementation must make gameplay state and panel visibility provable with deterministic tests using state hooks and panel-runtime checks.

## 2. Architectural approach

The entire change stays in the existing panel feature surfaces:

- Games markup remains owned by `dadaia_workspace.features.panel.views.games.render_games_section() -> str`.
- Client behavior for all Games remains in `dadaia_workspace/features/panel/views/assets/js/games.js`.
- Static serving remains `dadaia_workspace.features.panel.views.static.render_static() -> Callable[..., tuple[int, str, bytes]]` and keeps serving `games.js` from the existing path and MIME contract.
- No new Python modules, APIs, or runtime dependencies are introduced.
- Tests stay in `tests/unit/features/panel/test_games_tab.py` and `tests/e2e/panel/`.

## 3. Implementation contract bindings

### 3.1 Markup contract (`dadaia_workspace.features.panel.views.games.render_games_section`)

`render_games_section() -> str` MUST return Games HTML containing:

- Existing Snake (`data-game="snake"`) and Tetris (`data-game="tetris"`) controls unchanged except for additional sibling `data-game="pong"` control.
- New `.game-choice` control:
  - `data-game="pong"`
  - label text exactly `Pong (Codex)`
  - `role="tab"` and `aria-selected` semantics matching the existing toggle pattern.
- New panel article with:
  - `data-game-panel="pong"`
  - `<canvas id="pong-canvas" width="480" height="320" ...>` (deterministic fixed dimensions)
  - `id="pong-score"`
  - start/pause button `data-action="pong-toggle"`
  - reset button `data-action="pong-reset"`
  - d-pad buttons with `data-pong-dir="up"` and `data-pong-dir="down"` (with optional left/right style extension only if useful).
- Existing Snake/Tetris `data-game`, `data-game-panel`, scoreboard IDs, toolbar actions, and d-pad/action attributes remain unchanged.

### 3.2 Game-switch contract (`games.js` event wiring)

The existing game-switch behavior stays as-is in shape:

- On `.game-choice` click, activate exactly one tab and set `aria-selected` as existing.
- Match panels by `data-game-panel === game` and enforce visibility by toggling `hidden`.
- New Pong controls must only trigger when `data-game-panel="pong"` is active.

### 3.3 Pong runtime contract (`dadaia_workspace/features/panel/views/assets/js/games.js`)

#### Player, ball, and state surface

Runtime must maintain Pong state under existing IIFE style with module-local fields (var naming consistent with `snake`/`tetris` patterns):

- Ball position vector `{x, y}` and velocity vector `{x, y}`.
- Left paddle position and velocity/state for key/button control.
- Score integer.
- Running boolean derived from the Pong interval timer.

Behavior requirements:

- Left paddle is driven by:
  - on-screen controls (`data-pong-dir="up|down"`), and
  - keyboard keys `ArrowUp`/`ArrowDown` when Pong panel is active.
- Ball reflects on top and bottom walls.
- Ball reflects on right wall.
- Contact with left paddle increments score.
- Missing the left paddle resets ball, paddle, and score to initial values.

#### Pong deterministic test seam (`window.__dadaiaPongTest`)

When `window.__DADAIA_PONG_TEST_HOOK__ === true`, expose:

```javascript
window.__dadaiaPongTest = {
  getState: function () {
    return {
      ball: { x, y },
      velocity: { x, y },
      paddleY,      // left paddle top
      paddleDy,     // velocity/state sign
      score,
      running,      // bool
      randomSeed: undefined // if implemented
    };
  },
  setState: function (state) {
    // accepts subset; updates ball, velocity, paddleY, paddleDy, score, running,
    // and redraws/persists score when supplied
  },
  tick: function () {
    // executes one Pong tick via the same in-code path as normal gameplay
  },
  setDirection: function (name) {
    // accepts "up" | "down"
  },
  keydown: function (key) {
    // test helper for ArrowUp/ArrowDown equivalent
  },
  reset: function () {
    // deterministic Pong reset
  },
  setRandomSeed: function (seed) {
    // optional; only if random reset serves ever depend on RNG
  }
};
```

This seam remains test-only and must not alter production behavior.

### 3.4 Existing public contract that must not change

- `dadaia_workspace.features.panel.views.static.render_static()` must keep `render_static(name="games.js")` returning `(200, "application/javascript; charset=utf-8", <bytes>)` from the canonical games asset path.
- `tests/unit/features/panel/test_games_tab.py` and any existing snake/tetris behavior coverage remain functionally targeted to prior selectors; no route/path constants for `games.js` change.
- No production dependencies changed in `pyproject.toml` or lock metadata.

## 4. Workstreams

### WS-1 — Add Pong control and panel markup

Scope: `dadaia_workspace/features/panel/views/games.py` and `tests/unit/features/panel/test_games_tab.py`.

Planned work:

1. Extend `render_games_section()` with the new `.game-choice` button and `data-game-panel="pong"` article.
2. Add deterministic Pong canvas dimensions, score output, toggle/reset controls, and at least `up`/`down` d-pad buttons.
3. Extend unit tests for selector/count checks and static serving assertions to cover:
   - presence of `data-game="pong"` in the same switch container,
   - presence of `data-game-panel="pong"`, `id="pong-canvas"`, `id="pong-score"`, `data-action="pong-toggle"`, `data-action="pong-reset"`, and `data-pong-dir` buttons,
   - `test_games_assets_are_served` continues asserting existing byte-equality/asset path for `games.js`.

Direct validation:

- `tests/unit/features/panel/test_games_tab.py::test_games_section_has_two_playable_canvas_surfaces` (renamed/expanded as needed or paired with Pong-specific test) passes with all expected DOM attributes.
- `tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served` includes Pong markup/static-contract assertions in addition to unchanged Snake/Tetris assertions.

### WS-2 — Implement Codex Pong gameplay state and physics

Scope: `dadaia_workspace/features/panel/views/assets/js/games.js`.

Planned work:

1. Add Pong state (`ball`, `ballVelocity`, `pongPaddleY`, `pongPaddleDy`, `pongScore`, timer).
2. Add deterministic reset (`resetPong`) and draw path aligned with existing canvas render style.
3. Add tick logic:
   - move ball by velocity,
   - bounce top/bottom,
   - bounce right wall,
   - detect left paddle collision/increment score,
   - miss-left-hand side => reset state.
4. Add control handlers:
   - on-screen d-pad (`data-pong-dir`) and keyboard mapping.
   - toggle/reset actions (`data-action="pong-toggle"`, `data-action="pong-reset"`).
5. Add/extend shared switch behavior so active game controls operate on the selected panel only.
6. Add `window.__dadaiaPongTest` seam with state + tick + controls.
7. Keep non-Pong behavior untouched (snake and tetris state transitions, serving path, and score controls).

Direct validation:

- New JS-state tests in `tests/e2e/panel/test_pong_game_panel.py` read `window.__dadaiaPongTest.getState()` and assert:
  - top-wall contact flips vertical velocity,
  - bottom-wall contact flips vertical velocity,
  - right-wall contact flips horizontal velocity,
  - paddle contact increments score,
  - miss resets ball/paddle/score to initial values.
- Deterministic setup for tests (forced/random-seed control path where needed for serve/reset) is applied before each targeted assertion.

### WS-3 — Implement and verify panel runtime switching/visibility proof

Scope: `dadaia_workspace/features/panel/views/assets/js/games.js` and `tests/e2e/panel/test_pong_game_panel.py`.

Planned work:

1. Extend DOM/runtime tests to click `.game-choice` Snake → Pong → Tetris and assert panel visibility semantics (`hidden` flags or active-state parity).
2. Verify action buttons target the active panel and not stale cross-game state:
   - start/pause on one game does not mutate hidden/non-active game state,
   - reset on one game does not leak into another game's running state.
3. Add keyboard + on-screen d-pad regression in the same test file.

Direct validation:

- Browser-executable check queries selectors (`[data-game]`, `[data-game-panel]`, `hidden`, `data-action`) and asserts visible state toggles after each click.
- Transition Snake→Pong→Tetris path yields exactly one visible panel and two hidden panels.

### WS-4 — Scope containment and non-regression checks

Scope: above files only.

Planned work:

1. Perform a scope-limited diff review for:
   - no edits to Tetris core logic,
   - no edits to route names,
   - no edits outside Games tab feature files and corresponding tests.
2. Confirm no new runtime dependencies were introduced.
3. Confirm static-serving contract remains byte-identical for `games.js` path semantics from existing entry points.

Direct validation:

- `tests/unit/features/panel/test_games_tab.py` plus targeted e2e assertions pass with unchanged Snake/Tetris selector expectations for current fixtures.
- Static-serving tests continue to assert `status == 200` and `content-type == application/javascript; charset=utf-8` for `games.js`.
- Manual dependency review on touched file list remains in `dadaia_workspace/features/panel/*` and `tests/{unit,e2e}/panel/*` only.

## 5. Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | Extended `render_games_section()` markup + unit coverage updates for Pong selector/panel scaffolding | `pytest tests/unit/features/panel/test_games_tab.py` | None | None |
| WS-2 | Pong runtime in `games.js` + deterministic `window.__dadaiaPongTest` seam | `tests/e2e/panel/test_pong_game_panel.py` state assertions for wall/contact/miss scoring; fallback to node VM helper if browser route unavailable | WS-1 | WS-3 visibility checks consume hook-driven state assertions |
| WS-3 | Runtime visibility proof for Snake↔Pong↔Tetris transition and non-leaking controls | `tests/e2e/panel/test_pong_game_panel.py` DOM query/`hidden` checks across all three games | WS-1, WS-2 | None |
| WS-4 | Scope containment evidence and serving contract non-regression | `tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served` plus diff review of touched paths | WS-1, WS-2, WS-3 | Static/route contract and dependency-scope evidence package |

## 6. SPEC requirement coverage

| SPEC requirement | Covered by workstream(s) | Planned evidence |
|---|---|---|
| FR1 | WS-1, WS-3 | Unit markup assertions on `data-game="pong"` and runtime tab contract checks |
| FR2 | WS-1, WS-3 | Unit and e2e assertions for Pong article/canvas/controls + d-pad |
| FR3 | WS-2 | JS-state/probe tests for wall bounces, paddle return score, and miss reset |
| FR4 | WS-3 | DOM visibility and button-routing tests through simulated DOM/browser path |
| FR5 | WS-4 | Targeted diff review + unchanged Snake/Tetris selector assertions |
| FR6 | WS-1, WS-4 | Existing `games.js` serving assertions retained with canonical path and MIME checks |
| FR7 | WS-1, WS-2, WS-3 | `tests/unit/features/panel/test_games_tab.py`, `tests/e2e/panel/test_pong_game_panel.py` control/state regressions |
| FR8 | WS-4 | Dependency, scope, and touched-file boundary checks |

## 7. Non-goals and guardrails

- No dependency/runtime path changes outside existing panel static serving route.
- No gameplay changes outside `games.py`/`games.js` panel scope.
- No framework, API, or dependency additions.
- No repository-wide path changes and no test artifacts under project root beyond expected test files.
