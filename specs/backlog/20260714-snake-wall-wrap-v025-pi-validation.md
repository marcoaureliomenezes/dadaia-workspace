---
name: snake-wall-wrap-v025-pi-validation
status: rejected
rejected_reason: "Panel Games surface removed in v0.3.0 (test-only experiment); PI harness support also removed — nothing left to validate."
opened: 2026-07-14
owner: project-manager (curates)
priority: P0
release_target: v0.2.5
source: 'operator demand 2026-07-14: deliberately small PI workflow validation release;
  make panel Snake wrap across board walls without ending the game'
intents:
- subject:
    kind: code
    ref: dadaia_workspace/features/panel/views/static.py#render_static
  change: Keep the rendered Snake/Tetris game surface and controls unchanged except
    as directly required to expose the wrapped Snake behavior; do not change Tetris
    or non-game panel sections.
- subject:
    kind: code
    ref: dadaia_workspace/features/panel/views/static.py#render_static
  change: Serve the updated Games static JavaScript from the existing panel static
    asset path; no new runtime dependency, external asset, or alternate serving path
    is introduced.
- subject:
    kind: code
    ref: dadaia_workspace/features/panel/views/static.py#render_static
  change: Add focused automated regression coverage for Snake horizontal wall wrapping,
    vertical wall wrapping, self-collision still ending/resetting, score/food behavior,
    controls, and board dimensions while keeping tests scoped to the Games tab assets
    and directly required fixtures.
---
# BACKLOG — Snake wall wrap for PI workflow validation

**Scope:** Create a deliberately small release, targeted as `v0.2.5`, to validate the dadaia workflow path with PI by changing only the panel Games tab Snake game and its focused tests.

## Core problem

Snake currently treats any out-of-bounds head position as game-ending/reset behavior in the Games JavaScript (`games.js#snakeTick` evidence from current source). For this release, wall contact must become toroidal movement instead: crossing the left/right/top/bottom board edge moves the head to the opposite edge on the same row or column.

## Intended behavior

- Moving left from `x = 0` wraps the head to `x = 19` on the same `y`.
- Moving right from `x = 19` wraps the head to `x = 0` on the same `y`.
- Moving up from `y = 0` wraps the head to `y = 19` on the same `x`.
- Moving down from `y = 19` wraps the head to `y = 0` on the same `x`.
- The board remains 20×20 cells on the existing 400×400 Snake canvas.
- Wall contact alone must not reset the snake, clear the score, pause, or otherwise end the game.

## Non-goals / preservation

- Do not change Tetris.
- Do not change the Games tab layout, tab labels, or panel-wide navigation.
- Do not change board dimensions, canvas dimensions, tick cadence, colors, score display, keyboard/d-pad controls, start/pause/reset behavior, food generation, food scoring, body advancement, or self-collision semantics except where tests need observation hooks.
- Do not introduce a new framework or external JavaScript dependency.

## Acceptance sketch

- Horizontal wrapping is covered in an automated test: moving across the left and/or right wall produces the opposite-side head coordinate without reset.
- Vertical wrapping is covered in an automated test: moving across the top and/or bottom wall produces the opposite-side head coordinate without reset.
- Regression coverage proves self-collision still uses the existing game-over/reset path.
- Regression coverage proves food/score, direction controls, body movement, and board dimensions remain intact.
- Existing Games tab smoke tests remain green; test scope stays limited to Snake/Games assets and directly required current-truth spec/memory updates.

## Grounding notes

- Existing panel memory identifies Games as local JavaScript with playable Snake/Tetris, stable dimensions, controls, score, pause/start, and reset.
- Existing source evidence shows Snake state and wall/self-collision are currently handled together in the Games static JavaScript tick path; this backlog item separates wall crossing from self-collision without widening scope.
