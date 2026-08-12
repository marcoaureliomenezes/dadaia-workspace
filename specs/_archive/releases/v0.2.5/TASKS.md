# TASKS — Release v0.2.5 — Snake wall wrap for PI workflow validation

> **Status:** Aprovado

**Release ID:** v0.2.5  
**Owner:** product-engineer  
**Source PLAN:** `specs/releases/v0.2.5/PLAN.md`  
**Workflow:** release-definition / tasks_create

## Task status markers

- `[ ]` OPEN — ready to reserve.
- `[-]` IN PROGRESS — reserved by the implementing agent.
- `[x]` DONE — completed with validation evidence in the implementing handoff/report.

## Tasks

### [x] T1 — Add state-level Snake regression coverage and guarded browser test seam

**Owner role:** software-engineer

**Preconditions:** SPEC and PLAN for v0.2.5 are `Aprovado`; this task is reserved by changing only this marker from `[ ]` to `[-]` before edits.

**Write set:**

- `dadaia_workspace/features/panel/views/assets/js/games.js`
- `tests/e2e/panel/test_snake_wall_wrap.py` (new) or an equivalently named focused browser/state probe test under `tests/e2e/panel/`

**Description:**

Establish focused automated Snake state coverage before changing wall behavior. Add the guarded test-only browser seam in `dadaia_workspace/features/panel/views/assets/js/games.js` only if needed, using the exact approved contract:

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

The hook MUST be created only when `window.__DADAIA_SNAKE_TEST_HOOK__ === true` before `games.js` initializes. `getState()` MUST return copies/primitive values with `snake: Array<{x: number, y: number}>`, `food: {x: number, y: number}`, `direction: {x: number, y: number}`, `nextDirection: {x: number, y: number}`, `score: number`, and `running: boolean`. `setState(state)` MAY accept any subset of `snake`, `food`, `direction`, `nextDirection`, `score`, and `running`; omitted fields retain current values, supplied score updates `#snake-score`, and mutation redraws Snake. `tick()` MUST call the same `snakeTick()` path used by interval gameplay. `setDirection(name)` MUST accept only `"up"`, `"down"`, `"left"`, or `"right"` and delegate to the existing reverse-direction guard. `reset()` MUST delegate to `resetSnake()`.

Add tests that initialize controlled Snake states, execute one tick through the seam or equivalent probe, and inspect observable state for:

1. left-wall crossing from `{x: 0, y: N}` to expected wrapped `{x: 19, y: N}` without reset;
2. right-wall crossing from `{x: 19, y: N}` to expected wrapped `{x: 0, y: N}` without reset;
3. top-wall crossing from `{x: N, y: 0}` to expected wrapped `{x: N, y: 19}` without reset;
4. bottom-wall crossing from `{x: N, y: 19}` to expected wrapped `{x: N, y: 0}` without reset;
5. wall contact from a non-starting score/body state proving ordinary progression and no reset path;
6. a separate self-collision state proving the existing reset outcome;
7. food at the next head coordinate proving the existing `10` point score increment, growth by one, and controlled/isolated food relocation;
8. ordinary non-food movement proving head advancement, tail pop, and unchanged length.

Do not change the toroidal wall behavior in this task except for adding the guarded test seam; wall-wrap assertions are expected to fail until T2 changes the behavior.

**Validation:**

- From the workspace root, run the new focused tests against the current behavior and capture that at least one wall-wrap assertion fails for the pre-change wall-reset implementation while the test harness can read post-tick Snake state:

  ```bash
  cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_snake_wall_wrap.py
  ```

- If the exact filename differs, run the equivalent focused test path under `tests/e2e/panel/` with the same `-p no:cacheprovider` option.
- Confirm no `.pytest_cache`, `test-results`, `playwright-report`, coverage, or other generated artifact remains inside `repos/dadaia-workspace/`.

**SPEC coverage:** FR1, FR2, FR3, FR4, FR5.

---

### [x] T2 — Implement toroidal Snake head calculation while preserving reset semantics

**Owner role:** software-engineer

**Preconditions:** T1 is `[x] DONE` and this task is reserved by changing only this marker from `[ ]` to `[-]` before edits.

**Write set:**

- `dadaia_workspace/features/panel/views/assets/js/games.js`

**Description:**

Change only the Snake head coordinate calculation and wall collision branch in `dadaia_workspace/features/panel/views/assets/js/games.js`. In the existing `snakeTick` path, compute the candidate head from the current head plus the current Snake direction, then normalize the candidate to the existing 20×20 board before self-collision detection:

```javascript
head.x = (head.x + 20) % 20;
head.y = (head.y + 20) % 20;
```

Remove wall bounds from the game-over/reset condition. Keep self-collision in the existing reset path. Keep `resetSnake`, `placeFood`, `drawSnake`, `snakeTick`, `setSnakeDir`, and `toggleSnake` user-visible behavior stable except for wrapped wall coordinates. Keep food comparison, score increment by `10`, `placeFood()`, body growth, ordinary tail pop, drawing, direction controls, timer behavior, and any T1 test seam `tick()` delegation unchanged. Do not edit Tetris behavior.

**Validation:**

- From the workspace root, run the focused Snake state tests and require all wall-wrap, no-reset, self-collision, food/scoring, and ordinary movement assertions to pass:

  ```bash
  cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_snake_wall_wrap.py
  ```

- Run existing Games tab smoke/static coverage that exercises Games assets:

  ```bash
  cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py
  ```

- Confirm no `.pytest_cache`, `test-results`, `playwright-report`, coverage, or other generated artifact remains inside `repos/dadaia-workspace/`.

**SPEC coverage:** FR1, FR2, FR3, FR4, FR5, FR6, FR7.

---

### [x] T3 — Add containment assertions for Games markup, static serving, dependencies, and repo hygiene

**Owner role:** software-engineer

**Preconditions:** T1 and T2 are `[x] DONE`; this task is reserved by changing only this marker from `[ ]` to `[-]` before edits.

**Write set:**

- `tests/unit/features/panel/test_games_tab.py`

**Description:**

Extend static/unit coverage for release containment without changing production behavior. Assertions MUST confirm the existing contracts remain stable:

- `dadaia_workspace.features.panel.views.games.render_games_section() -> str` still returns Games-tab HTML containing Snake and Tetris panels.
- Snake canvas remains `<canvas id="snake-canvas" width="400" height="400" ...>`.
- Snake score output remains `id="snake-score"`.
- Snake controls remain `data-action="snake-toggle"`, `data-action="snake-reset"`, and `data-snake-dir="up|left|down|right"`.
- `dadaia_workspace.features.panel.views.static.render_static() -> Callable[..., tuple[int, str, bytes]]` still returns a callable accepting `name: str = ""` plus ignored keyword args.
- `render_static()(name="games.js")` still returns status `200`, content type `application/javascript; charset=utf-8`, and packaged Games JavaScript bytes from the existing panel static asset path.
- Tetris canvas/controls and the existing `games.css` static serving smoke coverage remain present.

Do not edit panel navigation, non-game panel sections, CLI wiring, server routing, dependency metadata, public projections, or memory.

**Validation:**

- From the workspace root, run the Games tab unit/static coverage:

  ```bash
  cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py
  ```

- Run the focused Snake state tests from T1/T2 to confirm containment assertions did not disturb behavior:

  ```bash
  cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/e2e/panel/test_snake_wall_wrap.py
  ```

- Review the release diff and confirm no Tetris behavior, panel non-game files, CLI wiring, server routing, `pyproject.toml`, `poetry.lock`, package metadata, public projections, or memory files changed.
- Confirm no `.pytest_cache`, `test-results`, `playwright-report`, coverage, or other generated artifact remains inside `repos/dadaia-workspace/`.

**SPEC coverage:** FR6, FR7.

---

### [x] T4 — Make the release-definition to implementation boundary directly runnable

**Owner role:** software-engineer

**Preconditions:** The registered bug
`release-definition-terminal-gate-leaves-next-workflow-preflight-unsatisfiable` is in scope;
reserve this task before edits.

**Write set:**

- `dadaia_workspace/features/lifecycle/service.py`
- `dadaia_workspace/infrastructure/headless_adapter_base.py`
- `dadaia_workspace/infrastructure/pi_runtime.py`
- `dadaia_workspace/infrastructure/codex_runtime.py`
- `tests/unit/features/lifecycle/test_preflight_service.py`
- `tests/unit/infrastructure/test_pi_runtime.py`
- `tests/unit/infrastructure/test_codex_exec_runtime.py`
- `tests/integration/cli/test_lifecycle_workflow_chain.py` (new) or an equivalently named focused integration test

**Description:**

Make Git dirtiness, missing upstream, and unpushed commits advisory in lifecycle preflight;
do not weaken binding, active-release, phase, specs-doctor, hygiene, handoff, review, commit,
CI, or push-security gates. Surface deterministic warning text for every non-clean Git
condition.

Preserve `PYTHONDONTWRITEBYTECODE` in both PI and Codex subprocess environment allowlists;
continue dropping unapproved environment keys and never add credential storage.

Before each PI/Codex subprocess attempt, snapshot the current Git changed-path set and the
content/existence state of those paths. After the attempt, derive `changed_paths` from the
before/after delta: include new/removal paths and pre-existing paths whose content changed;
exclude untouched pre-existing paths. The model self-report must never override this Git
truth.

Add a regression that models successful release-definition output followed immediately by
implementation preflight and proves the consumer is accepted without `--skip-preflight`.

**Validation:**

```bash
PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/features/lifecycle/test_preflight_service.py \
  tests/unit/infrastructure/test_pi_runtime.py \
  tests/unit/infrastructure/test_codex_exec_runtime.py \
  tests/integration/cli/test_lifecycle_workflow_chain.py
```

Run `dadaia reports workflow-doctor --json` and the workflow handoff doctor after the live
PI lifecycle completes. Confirm no repo-local cache/artifact directory was created.

**SPEC coverage:** FR8.

## Dependency graph

```text
T1 → T2 → T3
T4 (independent repair required before no-override boundary validation)
```

T1 and T2 both touch `games.js`; T2 explicitly depends on T1. T3 is last so its static assertions and diff/hygiene review can verify the final integrated state.

## Requirement traceability

| SPEC requirement | Task coverage | Required implementation evidence |
|---|---|---|
| FR1 — Horizontal wall crossing wraps | T1, T2 | Left/right post-tick state assertions pass after T2 and prove no reset. |
| FR2 — Vertical wall crossing wraps | T1, T2 | Up/down post-tick state assertions pass after T2 and prove no reset. |
| FR3 — Wall contact alone does not reset, pause, clear score, or end game | T1, T2 | Non-starting score/body wall-wrap assertion proves ordinary progression and reset path avoidance. |
| FR4 — Self-collision still resets | T1, T2 | Separate self-collision state test proves existing reset outcome. |
| FR5 — Food, scoring, and body advancement unchanged | T1, T2 | Controlled food/growth/score test and ordinary movement test pass. |
| FR6 — Controls and board dimensions remain stable | T1, T2, T3 | Static/unit assertions prove 400×400 canvas, 20×20 semantics through existing game constants/probe, and existing controls. |
| FR7 — Scope containment | T2, T3 | Games static serving assertion, diff review, no dependency metadata changes, and hygiene inspection. |
| FR8 — Consecutive workflows remain directly runnable | T4 | Preflight warnings plus content-aware PI/Codex changed-path delta and no-override transition test. |

## Release guardrails for implementers

- Do not change Tetris behavior, scoring, controls, rendering, board shape, or timer behavior.
- Do not change panel navigation, Reports, telemetry, server binding/security, CLI commands, workflow behavior, public projections, or memory.
- Do not introduce a JavaScript framework, CDN asset, new Python dependency, new package entrypoint, or alternate static asset path.
- Do not leave generated test or browser artifacts inside the repository.
- Use `-p no:cacheprovider` on every pytest command; `--cache-clear` is not a substitute.
