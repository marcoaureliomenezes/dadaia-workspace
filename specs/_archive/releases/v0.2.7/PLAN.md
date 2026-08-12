# PLAN — Release v0.2.7 — Add Breakout (PI) to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.7
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.2.7/SPEC.md`
**Workflow:** release-definition / plan_create

## 1. Planning problem

Add a fourth local game, **Breakout (PI)**, to the panel Games tab while preserving the existing Snake, Pong, and Tetris selectors, controls, switch semantics, gameplay, and static asset serving contract.

## 2. Architectural approach

The change is additive and stays inside the current panel feature seams:

- **Markup:** `dadaia_workspace/features/panel/views/games.py` (`render_games_section`)
- **Runtime:** `dadaia_workspace/features/panel/views/assets/js/games.js`
- **Serving contract:** `dadaia_workspace/features/panel/views/static.py` (existing `games.js` path)
- **Tests:** `tests/unit/features/panel/test_games_tab.py` and `tests/e2e/panel/`

No new files outside `specs/releases/v0.2.7`, `dadaia_workspace/features/panel/**`, and `tests/{unit,e2e}/panel/**` are in scope.

## 3. Implementation contract bindings

### 3.1 Panel markup contract

In `dadaia_workspace.features.panel.views.games`:

- `render_games_section() -> str` MUST render a `button` with:
  - `class="game-choice"`
  - `data-game="breakout"`
  - `role="tab"`
  - `aria-selected` matching existing tab parity
  - visible text exactly `Breakout (PI)`
- `render_games_section` MUST render an `article` for Breakout with:
  - `data-game-panel="breakout"`
  - `id="breakout-canvas"` on a canvas
  - `id="breakout-score"` on score output
  - `button[data-action="breakout-toggle"]`
  - `button[data-action="breakout-reset"]`
  - `button[data-breakout-dir="left"]`
  - `button[data-breakout-dir="right"]`
- Existing Snake/Pong/Tetris selectors, panels, canvas IDs, score IDs, and controls remain present and unchanged.

### 3.2 Game-switch and control-routing contract in `games.js`

In `dadaia_workspace.features.panel.views.assets.js.games`:

- Keep `isPanelActive(game)` selector logic and tab/panel visibility behavior.
- `document.querySelector('[data-action="...-toggle"]')` and `...["...-reset"]` handlers must gate by active panel.
- New Breakout control handlers must not affect other game states when Breakout is inactive.

### 3.3 Breakout runtime contract

In `dadaia_workspace/features/panel/views/assets/js/games.js`, add module-local Breakout state and loop with the existing IIFE style and existing timer/control idioms:

- Brick/paddle/ball primitives (module locals, not exported):
  - canvas element lookup for `breakout-canvas`
  - paddle rectangle near bottom
  - ball position + velocity
  - score integer
  - brick matrix (5 rows × 8 columns)
  - round state + reset state for miss
- Deterministic game update behavior:
  - paddle movement from on-screen controls (`data-breakout-dir="left|right"`) and keyboard `ArrowLeft`/`ArrowRight` only when Breakout panel is active
  - wall bounces on left/right/top/bottom boundaries
  - paddle bounce on strike
  - Brick strike removes brick and increments score
  - miss below paddle reinitializes score, bricks, ball, and paddle
- Expose test seam only when `window.__DADAIA_BREAKOUT_TEST_HOOK__ === true`:

```javascript
window.__dadaiaBreakoutTest = {
  getState: function () {},
  setState: function (state) {},
  tick: function () {},
  setDirection: function (name) {},
  reset: function () {},
};
```

No new external APIs, files, or production imports are introduced.

### 3.4 Existing serving contract that must remain unchanged

- `render_games_section` path and `games.css`/`games.js` asset route constants stay unchanged.
- `tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served` keeps asserting:
  - `render_static(name='games.js')` returns status `200`
  - `content-type == "application/javascript; charset=utf-8"`
  - body bytes equal canonical `dadaia_workspace/features/panel/views/assets/js/games.js`.

## 4. Workstreams

### WS-1 — Extend unit markup assertions for new Breakout selector/panel

**Scope:** `tests/unit/features/panel/test_games_tab.py`

**Goal:** update unit coverage to include Breakout markers while preserving all existing Snake/Pong/Tetris assertions.

**Validation:**

- `pytest tests/unit/features/panel/test_games_tab.py::test_games_section_has_playable_canvas_surfaces_for_three_games`
- `python -m py_compile tests/unit/features/panel/test_games_tab.py`

### WS-2 — Add Breakout selector and panel markup

**Scope:** `dadaia_workspace/features/panel/views/games.py`

**Goal:** add Breakout control and panel markup as defined in §3.1.

**Validation:**

- `python - <<'PY'` direct render assertions against `render_games_section()` (as in WS-1 checks above)
- **Depends on:** WS-1 test contract updates

### WS-3 — Implement Breakout gameplay and active-panel control wiring

**Scope:** `dadaia_workspace/features/panel/views/assets/js/games.js`

**Goal:** implement deterministic Breakout loop and controls using existing style.

**Validation:**

- `node -e "new Function(require('fs').readFileSync('dadaia_workspace/features/panel/views/assets/js/games.js','utf8'));"`
- local `window.__dadaiaBreakoutTest` seam assertions via new e2e probe tests (WS-4)
- **Depends on:** WS-2

### WS-4 — Add Breakout runtime + control routing/e2e proof

**Scope:** `tests/e2e/panel/test_breakout_game_panel.py` (new)

**Goal:** prove Breakout-specific gameplay and four-game active-panel behavior.

**Validation:**

- `pytest tests/e2e/panel/test_breakout_game_panel.py`
- coverage must include:
  - left/right paddle movement from both on-screen and arrow controls,
  - wall bounce,
  - paddle collision,
  - brick removal and score increment,
  - miss reset (score/ball/paddle/brick state reinit),
  - selection cycle for `snake`, `pong`, `tetris`, `breakout` yielding exactly one visible panel,
  - active-panel-only routing for `...-toggle`, `...-reset`, and direction controls.
- **Depends on:** WS-2, WS-3

### WS-5 — Containment and serving-contract verification

**Scope:** `tests/unit/features/panel/test_games_tab.py`, `tests/e2e/panel/test_pong_game_panel.py`, `tests/e2e/panel/test_breakout_game_panel.py`, release-file diff review

**Goal:** preserve existing behavior and non-game scope.

**Validation:**

- `pytest tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served`
- `pytest tests/e2e/panel/test_pong_game_panel.py::test_game_choice_switches_visible_panel_single_active`
- `pytest tests/e2e/panel/test_pong_game_panel.py::test_pong_toggle_and_reset_controls_affect_active_panel_only`
- Review diff for file-scoped blast radius: no non-`features/panel` behavior changes.
- **Depends on:** WS-2, WS-3, WS-4

## 5. Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | Breakout-aware unit assertions in `test_games_tab.py` and preserved existing assertions | `pytest tests/unit/features/panel/test_games_tab.py::test_games_section_has_playable_canvas_surfaces_for_three_games` | None | WS-5 |
| WS-2 | `render_games_section()` includes Breakout control/panel markup with required IDs and `data-*` attributes | `python -m py_compile tests/unit/features/panel/test_games_tab.py` and direct render-content check | WS-1 | WS-3 |
| WS-3 | Breakout module state/loop/test-seam in `games.js` and active-panel routing logic | `node -e "new Function(require('fs').readFileSync('dadaia_workspace/features/panel/views/assets/js/games.js','utf8'));"` | WS-2 | WS-4 |
| WS-4 | Deterministic Breakout gameplay and control-routing e2e proof for 4-game navigation | `pytest tests/e2e/panel/test_breakout_game_panel.py` | WS-2, WS-3 | WS-5 |
| WS-5 | Scope-containment and unchanged static-serving proof, with no unintended non-game behavior edits | `pytest tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served && pytest tests/e2e/panel/test_pong_game_panel.py::test_game_choice_switches_visible_panel_single_active && pytest tests/e2e/panel/test_pong_game_panel.py::test_pong_toggle_and_reset_controls_affect_active_panel_only` | WS-2, WS-3, WS-4 | None |

## 6. SPEC requirement coverage

| Scoped requirement | Requirements covered by workstream(s) | Planned proof |
|---|---|---|
| FR1 | WS-1, WS-2 | unit markup assertions for `data-game="breakout"` and tab semantics |
| FR2 | WS-1, WS-2 | unit markup assertions for panel, canvas, score, actions, controls |
| FR3 | WS-3, WS-4 | Breakout state seam + e2e gameplay proofs (paddle, walls, bricks, reset) |
| FR4 | WS-5 | diff containment + untouched Snake/Pong/Tetris tests |
| FR5 | WS-3, WS-4, WS-5 | active-panel visibility + routing-only tests across 4 games |
| FR6 | WS-5 + WS-2 | existing `games.js` serving test remains unchanged and green |
| FR7 | WS-1, WS-3, WS-4, WS-5 | expanded Breakout + preserved legacy regression assertions |

## 7. Guardrails

- Do not change dependencies.
- Do not touch non-Games panel pages.
- Preserve existing Snake/Pong/Tetris behavior and test contracts.
- No public-facing production API or route-path changes.
