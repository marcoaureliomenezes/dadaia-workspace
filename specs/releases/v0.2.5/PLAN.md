# PLAN — Release v0.2.5 — Snake wall wrap for PI workflow validation

> **Status:** Aprovado

**Release ID:** v0.2.5  
**Owner:** product-engineer  
**Source SPEC:** `specs/releases/v0.2.5/SPEC.md`  
**Workflow:** release-definition / plan_create

## 1. Planning problem

Implement only the Snake wall-contact semantic change in the existing panel Games tab: a head coordinate crossing the 20×20 Snake board wraps to the opposite edge instead of entering the reset/game-over path. Preserve all other Games behavior, including self-collision reset, food/scoring/body movement, controls, board dimensions, Tetris, static serving, and dependency metadata.

## 2. Architectural approach

The change stays inside the existing panel feature:

- Browser game behavior remains in `dadaia_workspace/features/panel/views/assets/js/games.js`.
- Games markup remains owned by `dadaia_workspace.features.panel.views.games.render_games_section() -> str`.
- Static asset serving remains owned by `dadaia_workspace.features.panel.views.static.render_static() -> Callable[..., tuple[int, str, bytes]]` and continues to serve `games.js` by the existing asset name and MIME type.
- Validation uses the existing pytest and Playwright/browser layers already described by quality-assurance memory; no runtime dependency, external asset, CDN, framework, CLI wiring, or alternate serving path is introduced.

## 3. Implementation contract bindings

### 3.1 Existing contracts that MUST remain stable

| Surface | Required contract |
|---|---|
| `dadaia_workspace.features.panel.views.games.render_games_section() -> str` | Still returns Games-tab HTML containing Snake and Tetris panels. Snake canvas remains `<canvas id="snake-canvas" width="400" height="400" ...>`, score output remains `id="snake-score"`, controls remain `data-action="snake-toggle"`, `data-action="snake-reset"`, and `data-snake-dir="up|left|down|right"`. |
| `dadaia_workspace.features.panel.views.static.render_static() -> Callable[..., tuple[int, str, bytes]]` | Returned callable still accepts `name: str = ""` plus ignored keyword args and returns `(status, content_type, body)`. `name="games.js"` still returns status `200`, content type `application/javascript; charset=utf-8`, and the packaged Games JavaScript bytes from the existing panel static asset path. |
| `dadaia_workspace/features/panel/views/assets/js/games.js` | Remains a browser IIFE attached to the existing Games DOM. Existing Snake functions `resetSnake`, `placeFood`, `drawSnake`, `snakeTick`, `setSnakeDir`, and `toggleSnake` keep their user-visible behavior except for wrapped wall coordinates. Existing Tetris functions and keyboard routing are not changed. |
| Dependency metadata | `pyproject.toml`, lock files, package metadata, and runtime dependency declarations remain unchanged. |

### 3.2 Test-only browser probe contract

To satisfy the SPEC requirement for observable Snake state after a tick without adding dependencies, the implementation MAY add a guarded browser test seam inside `games.js` with this exact contract:

```javascript
window.__DADAIA_SNAKE_TEST_HOOK__ = true;
window.__dadaiaSnakeTest = {
  getState: function () { return { snake, food, direction, nextDirection, score, running }; },
  setState: function (state) { /* replaces only Snake state fields supplied by tests */ },
  tick: function () { /* invokes one Snake tick synchronously */ },
  setDirection: function (name) { /* invokes existing Snake direction logic */ },
  reset: function () { /* invokes resetSnake() */ }
};
```

Binding details:

- The object MUST be created only when `window.__DADAIA_SNAKE_TEST_HOOK__ === true` before `games.js` initializes.
- `getState()` MUST return copies/primitive values, not live mutable references, with fields:
  - `snake: Array<{x: number, y: number}>`
  - `food: {x: number, y: number}`
  - `direction: {x: number, y: number}`
  - `nextDirection: {x: number, y: number}`
  - `score: number`
  - `running: boolean`
- `setState(state)` MAY accept any subset of `snake`, `food`, `direction`, `nextDirection`, `score`, and `running`; omitted fields retain current values. It MUST redraw Snake after mutation and MUST update `#snake-score` when `score` is supplied.
- `tick()` MUST execute the same logic used by the interval-driven Snake game; it MUST NOT bypass collision, scoring, growth, body advancement, or reset behavior.
- `setDirection(name)` accepts only `"up"`, `"down"`, `"left"`, or `"right"` and delegates to the existing reverse-direction guard.
- `reset()` delegates to `resetSnake()`.
- The hook is a test seam only; no production markup, controls, rendering path, or dependency changes may depend on it.

If implementation can prove the same state-level assertions with an equivalent browser execution probe without adding this hook, it may do so, but the proof still must expose the same state fields and same one-tick control listed above.

## 4. Workstreams

### WS-1 — Establish state-level Snake regression coverage

Create focused automated tests before changing behavior.

Planned files:

- Add browser-backed Playwright coverage under `tests/e2e/panel/` or unit/static coverage under `tests/unit/features/panel/` using the existing test toolchain.
- Extend `tests/unit/features/panel/test_games_tab.py` only for static/structural assertions that do not require browser state.

Required tests:

1. Left-wall wrap: initialize Snake with head at `{x: 0, y: N}`, direction left, non-starting score/body, food not on the next head; execute one tick and assert head becomes `{x: 19, y: N}` while score and non-reset body progression remain ordinary.
2. Right-wall wrap: initialize head at `{x: 19, y: N}`, direction right; assert head becomes `{x: 0, y: N}` without reset.
3. Top-wall wrap: initialize head at `{x: N, y: 0}`, direction up; assert head becomes `{x: N, y: 19}` without reset.
4. Bottom-wall wrap: initialize head at `{x: N, y: 19}`, direction down; assert head becomes `{x: N, y: 0}` without reset.
5. Wall contact no-reset: use a score/body state that `resetSnake()` would visibly change; after a wrapping tick, assert score is preserved unless food is eaten, body length/progression is ordinary, and `running` is not forced off by the reset path.
6. Self-collision still resets: create a body that collides on the next tick and assert the existing reset outcome (`snake` returns to the start body, score returns to `0`, food returns to the reset food coordinate, and timer/running state is stopped).
7. Food/scoring/growth unchanged: place food at the next wrapped or ordinary head coordinate, tick once, and assert score increments by the existing `10`, body grows by one, and food relocation is controlled/stubbed or isolated from chance.
8. Ordinary movement unchanged: place food away from the next ordinary coordinate, tick once, and assert head advances, tail pops, and length is unchanged.
9. Dimensions/controls unchanged: assert the Games markup still exposes Snake 20×20 semantics through the 400×400 canvas and the existing start/pause/reset and four direction controls.

Direct validation:

- Focused tests fail against the current wall-reset implementation for at least one wall-wrap assertion.
- Tests inspect observable Snake state after a tick through the bound test seam or equivalent probe; nonblank canvas evidence alone is not accepted.

### WS-2 — Implement toroidal Snake head calculation

Change only the Snake head coordinate calculation and wall collision branch in `games.js`.

Required strategy:

- Compute the candidate head from `snake[0] + snakeDir`.
- Normalize the candidate to the 20×20 board before self-collision detection:
  - `x = (x + 20) % 20`
  - `y = (y + 20) % 20`
- Remove wall bounds from the reset/game-over condition; keep self-collision in the existing reset path.
- Keep food comparison, score increment, `placeFood()`, body growth, ordinary tail pop, drawing, direction controls, and timer behavior unchanged.
- If WS-1 introduced the guarded test seam, ensure `tick()` calls the exact `snakeTick()` path rather than duplicating game logic.

Direct validation:

- WS-1 wall-wrap, no-reset, self-collision, food/scoring, and ordinary movement tests pass.
- Existing Games asset smoke tests continue to pass.

### WS-3 — Prove containment of Games surface and serving path

Validate that the release did not modify out-of-scope behavior.

Required strategy:

- Keep `render_games_section()` markup stable except for no markup change expected by this SPEC.
- Keep `render_static()` behavior and asset name `games.js` unchanged.
- Do not touch Tetris logic except incidental context lines required by the same file edit; no semantic Tetris change is allowed.
- Do not touch panel tabs, non-game panel sections, CLI wiring, server routing, dependency metadata, public projections, or memory.

Direct validation:

- `tests/unit/features/panel/test_games_tab.py` confirms Snake and Tetris canvases, labels, controls, and `games.js`/`games.css` serving still work.
- A static/diff review confirms Tetris behavior and non-game panel files are unchanged.
- Dependency metadata remains unchanged.
- Repo hygiene scan or post-test inspection confirms no `.pytest_cache`, `test-results`, `playwright-report`, coverage, or other generated artifacts remain in the repository.

### WS-4 — Repair the release-definition to implementation boundary

Change lifecycle Git cleanliness from a mechanical preflight block to explicit advisory
warnings. Preserve safety at the actual boundaries: worker changed-path enforcement,
pre-commit presence warning, CI preflight, and exact-SHA pre-push security verdict.

Because definition artifacts legitimately remain dirty between workflows, capture a
content-aware Git snapshot immediately before each PI/Codex worker attempt and report only
the paths that the attempt added, removed, or changed. An untouched pre-existing path is
not attributed to the worker; a pre-existing path whose content changes is attributed.

Add unit coverage for warning semantics and both adapters, plus an integration regression
that feeds successful release-definition state directly into implementation preflight
without `--skip-preflight`.

## 5. Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | State-level Snake regression tests and optional guarded test probe contract usage | New tests fail against current wall-reset behavior where feasible and assert post-tick Snake state, controls, and dimensions | WS-1 | Final pass deferred to WS-2 after behavior change |
| WS-2 | Toroidal head calculation in `games.js` with self-collision reset preserved | WS-1 focused tests pass; existing Games asset smoke tests pass | WS-1, WS-2 | None |
| WS-3 | Containment evidence for markup, static serving, dependencies, repo hygiene, and Tetris/non-game non-change | Static/unit assertions, diff review, dependency metadata check, hygiene inspection | WS-1, WS-2, WS-3 | None |
| WS-4 | Direct workflow transition plus content-aware per-worker changed-path attribution | Preflight warning tests, PI/Codex adapter tests, consecutive-workflow integration test | WS-4 | One bootstrap override is recorded for the live run that installs the fix |

## 6. SPEC requirement coverage

| SPEC requirement | Covered by workstream(s) | Evidence planned |
|---|---|---|
| FR1 — Horizontal wall crossing wraps | WS-1, WS-2 | Left/right post-tick state assertions showing `(19, same y)` and `(0, same y)` without reset. |
| FR2 — Vertical wall crossing wraps | WS-1, WS-2 | Up/down post-tick state assertions showing `(same x, 19)` and `(same x, 0)` without reset. |
| FR3 — Wall contact alone does not reset, pause, clear score, or end game | WS-1, WS-2 | Non-starting score/body wall-wrap test plus reset-path-sensitive state assertions. |
| FR4 — Self-collision still resets | WS-1, WS-2 | Separate self-collision state test asserting the existing reset outcome. |
| FR5 — Food, scoring, and body advancement unchanged | WS-1, WS-2 | Controlled food-at-next-head growth/score test and ordinary non-food advancement test. |
| FR6 — Controls and board dimensions remain stable | WS-1, WS-3 | Markup/static assertions for 20×20 board semantics, 400×400 canvas, direction controls, and start/pause/reset controls. |
| FR7 — Scope containment | WS-3 | Static serving assertion for `render_static`, structural/diff review for `render_games_section`, no Tetris/non-game changes, and no dependency metadata change. |
| FR8 — Consecutive workflows do not deadlock on producer Git state | WS-4 | No-override transition regression and PI/Codex content-aware changed-path tests. |

## 7. Non-goals and guardrails

- Do not change Tetris behavior, scoring, controls, rendering, board shape, or timer behavior.
- Do not change panel navigation, reports, telemetry, server binding/security, CLI commands, or workflow behavior.
- Do not introduce a JavaScript framework, CDN asset, new Python dependency, new package entrypoint, or alternate static asset path.
- Do not edit product memory in this release-definition PLAN step; memory truth is updated only during closure if the implemented product state changes.
- Do not leave generated test or browser artifacts inside the repository.
