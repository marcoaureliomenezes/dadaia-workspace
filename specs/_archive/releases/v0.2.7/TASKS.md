# TASKS — Release v0.2.7 — Add Breakout (PI) to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.7  
**Owner:** product-engineer  
**Source PLAN:** `specs/releases/v0.2.7/PLAN.md`  
**Workflow:** release-definition / tasks_create

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Tasks

- [x] **T1 - Extend unit coverage for Breakout selector and panel markers**

**Owner role:** software-engineer

**Preconditions:** `SPEC.md` and `PLAN.md` for `v0.2.7` are `Aprovado`.

**Write set:**

- `tests/unit/features/panel/test_games_tab.py`

**Description:**

Update `tests/unit/features/panel/test_games_tab.py::test_games_section_has_playable_canvas_surfaces_for_three_games` (and keep existing `test_games_assets_are_served` contract intact) so Breakout is rendered with existing tab semantics in the same control family as Snake/Pong/Tetris.

The task must assert that `dadaia_workspace.features.panel.views.games.render_games_section() -> str` includes:

- `.game-choice` with `data-game="breakout"`, label text `Breakout (PI)`, and `role="tab"` semantics consistent with existing choices,
- `article[data-game-panel="breakout"]` in the Games stage,
- stable Breakout control/output markers: `id="breakout-canvas"`, `id="breakout-score"`, `data-action="breakout-toggle"`, `data-action="breakout-reset"`, `data-breakout-dir="left"`, and `data-breakout-dir="right"`.

Preserve all existing Snake/Pong/Tetris assertions exactly.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py::test_games_section_has_playable_canvas_surfaces_for_three_games`
- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m py_compile tests/unit/features/panel/test_games_tab.py`

---

- [x] **T2 - Add Breakout game selector and panel markup to render_games_section**

**Owner role:** software-engineer

**Preconditions:** T1 is `[x]` (task complete) or reserved for implementation in the same task-order run.

**Write set:**

- `dadaia_workspace/features/panel/views/games.py`

**Description:**

Update `dadaia_workspace.features.panel.views.games.render_games_section() -> str` to include a new Breakout entry and panel with the same markup contract as existing games.

- Add `.game-choice` button in the Games switch:
  - `data-game="breakout"`, `role="tab"`, and existing tab-parity `aria-selected` behavior,
  - visible text `Breakout (PI)`.
- Add a new panel:
  - `<article data-game-panel="breakout">`
  - `<canvas id="breakout-canvas" ...>`
  - `<output id="breakout-score">`
  - `<button data-action="breakout-toggle">`
  - `<button data-action="breakout-reset">`
  - `<button data-breakout-dir="left">` and `<button data-breakout-dir="right">`

All existing Snake/Pong/Tetris markup, labels, IDs, and container structure must remain unchanged.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m py_compile tests/unit/features/panel/test_games_tab.py`
- Direct render assertion against `dadaia_workspace.features.panel.views.games.render_games_section()` in the same process as T1 scope.

---

- [x] **T3 - Add Breakout gameplay runtime in games.js and shared control wiring**

**Owner role:** software-engineer

**Preconditions:** T2 is `[x]` (task complete).

**Write set:**

- `dadaia_workspace/features/panel/views/assets/js/games.js`

**Description:**

In `dadaia_workspace.features.panel.views.assets.js.games`, add module-local Breakout state and game loop logic while preserving existing Snake/Pong/Tetris behavior.

Implement deterministic Breakout mechanics for:

- paddle location/size/state and movement via on-screen controls (`data-breakout-dir="left|right"`) and keyboard `ArrowLeft`/`ArrowRight`,
- ball and wall bounces (left/right/top/bottom panel boundaries),
- brick grid with `5×8` initialization, collision removal, and score progression,
- missed-ball round reset that reinitializes score/ball/paddle/brick state.

Maintain shared `isPanelActive(game)` gating so Breakout controls do not affect inactive panels.

Expose the deterministic test seam only when `window.__DADAIA_BREAKOUT_TEST_HOOK__ === true` in exactly this object path:

```javascript
window.__dadaiaBreakoutTest = {
  getState: function () {},
  setState: function (state) {},
  tick: function () {},
  setDirection: function (name) {},
  reset: function () {},
};
```

No public-facing production API changes beyond this seam.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && node -e "new Function(require('fs').readFileSync('dadaia_workspace/features/panel/views/assets/js/games.js','utf8'));"`
- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served`

---

- [x] **T4 - Add Breakout runtime proof and four-game control-routing e2e test**

**Owner role:** software-engineer

**Preconditions:** T2 and T3 are `[x]`.

**Write set:**

- `tests/e2e/panel/test_breakout_game_panel.py` (new)

**Description:**

Create `tests/e2e/panel/test_breakout_game_panel.py` to validate deterministic Breakout behavior through the `window.__dadaiaBreakoutTest` seam in `dadaia_workspace.features.panel.views.assets.js.games`.

Must include assertions for:

- Breakout paddle movement via on-screen controls and `ArrowLeft`/`ArrowRight`,
- wall bounce behavior,
- brick collision/removal and score increments,
- round reset when the ball passes the paddle,
- panel selection cycle with `data-game="snake"|"pong"|"tetris"|"breakout"` yields exactly one visible panel,
- action/control routing by active game only for `data-action="...-toggle"`, `data-action="...-reset"`, and on-screen direction controls.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_breakout_game_panel.py`

---

- [x] **T5 - Verify panel-scope containment and unchanged games static serving contract**

**Owner role:** software-engineer

**Preconditions:** T2, T3, and T4 are `[x]`.

**Write set:**

- `tests/unit/features/panel/test_games_tab.py`
- `tests/e2e/panel/test_pong_game_panel.py`

**Description:**

Reinforce release contract and prevent scope drift:

- keep `test_games_assets_are_served` asserting `dadaia_workspace.features.panel.views.static.render_static(name="games.js")` returns status `200`, content-type `application/javascript; charset=utf-8`, and exact bytes from `dadaia_workspace/features/panel/views/assets/js/games.js`,
- keep Snake/Pong/Tetris assertions proving unchanged selectors, controls, and behavior contracts,
- confirm four-game runtime assertions from `tests/e2e/panel/test_pong_game_panel.py` continue to validate active-panel visibility and active-panel-only toggle/reset behavior,
- perform diff-boundary review so no non-`features/panel` behavior and no non-game panel sections are edited in this release.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py::test_games_assets_are_served`
- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_pong_game_panel.py::test_game_choice_switches_visible_panel_single_active`
- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_pong_game_panel.py::test_pong_toggle_and_reset_controls_affect_active_panel_only`

## Dependency graph

`T1 -> T2 -> T3 -> T4 -> T5`

## Requirement traceability

| SPEC requirement | Task coverage | Required evidence |
|---|---|---|
| FR1 | T1, T2, T5 | games switch assertions and unchanged existing switch contract |
| FR2 | T1, T2 | Breakout panel and control markers in markup and tests |
| FR3 | T3, T4 | Breakout seam + deterministic physics/brick/reset regressions |
| FR4 | T4, T5 | Snake/Pong/Tetris behavioral preservation and diff-boundary non-regression |
| FR5 | T3, T4, T5 | Four-panel selection visibility and active-control routing |
| FR6 | T5 | `games.js` static serving contract unchanged |
| FR7 | T1, T3, T4, T5 | Combined unit/e2e assertions plus legacy regression proofs |
