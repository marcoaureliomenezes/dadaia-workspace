# TASKS — Release v0.2.6 — Add Codex Pong to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.6  
**Owner:** product-engineer  
**Source PLAN:** `specs/releases/v0.2.6/PLAN.md`  
**Workflow:** release-definition / tasks_create

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Tasks

- [x] **T1 - Add Pong selector and panel markup in Games view**

**Owner role:** software-engineer

**Preconditions:** `SPEC.md` and `PLAN.md` for `v0.2.6` are `Aprovado`.

**Write set:**

- `dadaia_workspace/features/panel/views/games.py`
- `tests/unit/features/panel/test_games_tab.py`

**Description:**

Implement the new Pong entry and panel in `dadaia_workspace.features.panel.views.games.render_games_section() -> str`.

- Add a `.game-choice` control with:
  - `data-game="pong"`
  - label text exactly `Pong (Codex)`
  - `role="tab"` and `aria-selected` behavior aligned to existing switch semantics.
- Add new markup in the same games switch container so Snake/Tetris choices remain unchanged.
- Add `<article data-game-panel="pong">` containing:
  - `<canvas id="pong-canvas" width="480" height="320" ...>`
  - score element `id="pong-score"`
  - start/pause button `data-action="pong-toggle"`
  - reset button `data-action="pong-reset"`
  - d-pad controls using `data-pong-dir="up"` and `data-pong-dir="down"`
- Do not change non-game sections or any Snake/Tetris control IDs, `data-game` values, or `data-game-panel` bindings.

**Validation:**

- `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py`

**SPEC coverage:** FR1, FR2, FR5.

---

- [x] **T2 - Add Codex Pong state, physics, and test seam in games.js**

**Owner role:** software-engineer

**Preconditions:** `T1` is `[x]`.

**Write set:**

- `dadaia_workspace/features/panel/views/assets/js/games.js`

**Description:**

Extend `dadaia_workspace/features/panel/views/assets/js/games.js` with a Pong runtime module-local state and deterministic tick path.

- Add Pong state vectors: ball `{x, y}`, velocity `{x, y}`, `pongPaddleY`, `pongPaddleDy`, `pongScore`, and running timer state.
- Implement Paddle and ball updates so:
  - `data-pong-dir="up|down"` and `ArrowUp`/`ArrowDown` steer paddle (only for active `data-game-panel="pong"`).
  - top/bottom wall contacts invert ball vertical velocity,
  - right wall contacts invert ball horizontal velocity,
  - left-paddle contact increments score,
  - ball miss resets paddle/ball/score to initial values.
- Keep Snake and Tetris logic untouched.
- Add `window.__dadaiaPongTest` guarded by `window.__DADAIA_PONG_TEST_HOOK__ === true` with methods:
  - `getState`, `setState`, `tick`, `setDirection`, `keydown`, `reset`, `setRandomSeed`
  - state includes at least ball, velocity, `paddleY`, `paddleDy`, `score`, `running`.

**Validation:**

- `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_pong_game_panel.py -k "pong"`

**SPEC coverage:** FR2, FR3, FR8.

---

- [x] **T3 - Add runtime game-switch visibility and cross-game control assertions**

**Owner role:** software-engineer

**Preconditions:** `T1` and `T2` are `[x]`.

**Write set:**

- `dadaia_workspace/features/panel/views/assets/js/games.js`
- `tests/e2e/panel/test_pong_game_panel.py`

**Description:**

Wire and prove three-panel runtime behavior in `games.js` and browser-observable tests.

- Ensure `.game-choice` selection keeps exactly one `data-game-panel` visible (`hidden == false`) and non-selected panels hidden.
- Keep existing game-switch semantics and activate tab classes/`aria-selected` as in current implementation.
- Ensure `data-action="pong-toggle"` and `data-action="pong-reset"` affect only active game panel state.
- Extend/implement e2e assertions for Snake→Pong→Tetris transitions, including keyboard and on-screen `data-pong-dir` controls for Pong.
- Assert FR3 replayable outcomes through `window.__dadaiaPongTest`:
  - top-wall flip,
  - bottom-wall flip,
  - right-wall flip,
  - paddle hit increases score,
  - miss resets ball/paddle/score and restores initial motion state.

**Validation:**

- `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_pong_game_panel.py`

**SPEC coverage:** FR1, FR3, FR4, FR7.

---

- [x] **T4 - Verify scope containment and static-serving contract non-regression**

**Owner role:** software-engineer

**Preconditions:** `T1`, `T2`, and `T3` are `[x]`.

**Write set:**

- `tests/unit/features/panel/test_games_tab.py`

**Description:**

Lock scope to panel-owned paths and keep asset contract unchanged for `games.js`.

- Keep `test_games_assets_are_served` assertions for `render_static(name="games.js")` on canonical path and MIME `application/javascript; charset=utf-8`.
- Keep Snake/Tetris selectors, score IDs, and controls unchanged by design.
- Confirm no edits to non-Games section templates, route maps, dependency manifests, or non-panel modules.
- Confirm no dependency additions.

**Validation:**

- `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py`
- `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_pong_game_panel.py`

**SPEC coverage:** FR4, FR5, FR6, FR8.

## Dependency graph

T1 → T2 → T3 → T4

## Requirement traceability

| SPEC requirement | Task coverage | Required evidence |
|---|---|---|
| FR1 | T1, T3 | games.js markup/switch + `.game-choice` interaction checks |
| FR2 | T1, T3 | `data-game-panel="pong"` markup and control assertions |
| FR3 | T2, T3 | `__dadaiaPongTest` assertions for wall contacts, score, and miss reset |
| FR4 | T3, T4 | panel visibility (`hidden`) and active-control targeting |
| FR5 | T1, T4 | unchanged Snake/Tetris selectors and section isolation |
| FR6 | T1, T4 | `render_static` path and MIME/content contract |
| FR7 | T1, T2, T3 | unit/e2e control and gameplay regressions |
| FR8 | T4 | scope and dependency boundary review in `tests` layer |
