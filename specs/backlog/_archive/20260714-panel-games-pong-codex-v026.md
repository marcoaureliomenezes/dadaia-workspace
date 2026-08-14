---
name: panel-games-pong-codex-v026
status: rejected
rejected_reason: "Panel Games surface removed in v0.3.0 (test-only experiment); PI harness support also removed — nothing left to validate."
opened: 2026-07-14
owner: project-manager (curates)
priority: P1
release_target: v0.2.7
source: 'operator demand 2026-07-14: expand the panel Games tab to four local games (existing Snake + Pong + Tetris + new Breakout (PI)).'
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/panel/views/index.py#render_index
    change: |
      Extend unit coverage for the Games tab to assert the new Breakout switch button,
      `data-game-panel="breakout"` panel rendering, and left/right control paths (keyboard
      and on-screen), while preserving existing Snake/Pong/Tetris assertions.
---
# BACKLOG — Extend Games tab to a fourth local game (Breakout)

**Scope:** Add Breakout as the fourth local game in the Games tab with matching style for
`render_games_section`, `games.js` gameplay extension, and unit coverage updates.

## Core problem

The Games tab currently exposes three local games in the UI while the demand is to add a
fourth game (Breakout) in the same architecture and test pattern as existing games.

## Intended behavior

- Keep the existing Snake, Pong, and Tetris markup and gameplay mechanics untouched.
- Add a new switch entry `Breakout (PI)` in the same order/style as existing game-choice buttons.
- Add a new `article[data-game-panel="breakout"]` with canvas and toolbar, plus score output.
- Add Breakout gameplay logic in `dadaia_workspace/features/panel/views/assets/js/games.js`:
  - Paddle anchored near the bottom and movable by left/right on-screen controls and arrows;
  - Ball bounces on walls and paddle
  - 5x8 brick grid that removes bricks on impact and increments score per brick;
  - Reset round state when the ball is missed.
- Extend `tests/unit/features/panel/test_games_tab.py` to cover the new switch entry,
  panel render markers, and control paths while preserving prior coverage for Snake/Pong/Tetris.

## Non-goals

- Do not alter non-Games tab pages.
- Do not add external runtime dependencies or alternate static serving paths.
- Do not alter Snake, Pong, or Tetris mechanics.

## Acceptance sketch

- A fourth selectable game, `Breakout (PI)`, appears in the Games tab switch and renders its
  panel correctly.
- Breakout gameplay is appended to `games.js` using the existing module loop/render style and
  exhibits wall/paddle bounce, scoring, brick clearing, and reset-on-loss behavior.
- Game-tab tests include explicit Breakout assertions in the same style as existing tests.
- Asset serving path and output remain unchanged: `games.js` is still served by existing static view logic.
