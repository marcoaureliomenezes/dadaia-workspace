# SPEC — Release v0.2.7 — Add Breakout (PI) to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.7
**Owner:** product-engineer
**Source:** backlog `panel-games-pong-codex-v026`  
**Workflow:** release-definition / spec_create

## 1. Problem

The Games tab in the panel exposes only three local games (Snake, Pong, and Tetris) although the demand is for four local games. This release adds **Breakout (PI)** in the same architecture and test pattern as the existing games while preserving Snake, Pong, and Tetris behavior, layout, and serving contract.

## 2. Picked scope

### Backlog items

| Item | Disposition in this SPEC |
|---|---|
| `specs/backlog/20260714-panel-games-pong-codex-v026.md` | Picked. Fully addressed by FR1–FR7. |

### Bugs

No bug is part of this release scope.

### Audit findings

No audit finding is part of this release scope.

### Subsumptions

No subsumptions are introduced in this release.

### Sanitization outcomes

The authoritative scope producer output is `g2-backlog-pi`. This release uses only
`20260714-panel-games-pong-codex-v026` as its authoritative scope. A neighboring backlog
item `20260714-snake-wall-wrap-v025-pi-validation` is excluded from scope because it targets
release `v0.2.5` and a separate PI validation objective already addressed that behavior.

## 3. Functional requirements

### FR1 — Add Breakout game selector control in the Games switch

A new `Breakout (PI)` selector appears with existing `.game-choice` controls and matches
existing tab semantics.

Acceptance / verification:

- `render_games_section` coverage MUST assert one `.game-choice` button with
  `data-game="breakout"` and label text `Breakout (PI)` in the same control container as
  Snake/Pong/Tetris.
- The selector MUST support expected tab semantics (`role="tab"` and active/selection state
  parity with existing choices).

### FR2 — Add Breakout game panel markup

A new game panel for Breakout is rendered as `article[data-game-panel="breakout"]` with its own
canvas, score output, and toolbar controls.

Acceptance / verification:

- `render_games_section` coverage MUST assert an `article` with `data-game-panel="breakout"`.
- The panel must include:
  - a canvas for Breakout (new stable id, e.g. `breakout-canvas`),
  - score output with new stable id (e.g. `breakout-score`),
  - one start/pause action with `data-action="breakout-toggle"`,
  - one reset action with `data-action="breakout-reset"`,
  - on-screen controls with `data-breakout-dir="left"` and `data-breakout-dir="right"`.
- Existing Snake/Pong/Tetris markup and controls in `render_games_section` remain present and
  unchanged.

### FR3 — Add Breakout gameplay logic in `games.js`

Breakout gameplay is added as a deterministic, module-local game loop in the existing Games
JavaScript using the current module style.

Acceptance / verification:

- A runtime validation seam verifies that a bottom-anchored paddle exists near the bottom and
  is moved by either:
  - on-screen left/right controls (`data-breakout-dir="left|right"`), and
  - keyboard `ArrowLeft` / `ArrowRight` controls.
- Ball-paddle-wall behavior is test-proven:
  - ball bounces on left/right/top panel walls (Operator amendment 2026-07-14: the
    BOTTOM edge is the miss boundary per the demand — the ball never bounces there;
    passing the paddle at the bottom triggers the round reset below),
  - ball bounces on the paddle,
  - hitting the paddle continues game state and updates score progression according to
    brick-removal rules.
- Brick grid behavior is test-proven:
  - a 5×8 grid is initialized,
  - paddle-side collisions remove a brick on impact,
  - score increments per removed brick.
- Ball-miss behavior is test-proven:
  - when the ball passes the paddle, the round resets with score, bricks, and ball/paddle state
    reinitialized for a new round.
- Existing Snake, Pong, and Tetris logic in `games.js` is not modified except for shared
  game-switch/control wiring required for the new game.

### FR4 — Scope containment for gameplay behavior

The Breakout change is additive to panel gameplay and does not alter non-Breakout mechanics.

Acceptance / verification:

- A focused regression path explicitly proves Snake, Pong, and Tetris state transitions,
  controls, and canvas-serving behavior still match the existing tests.
- A diff boundary review confirms no edits outside panel scope and no non-game UI section edits.
- No code path for non-game panel pages is changed by this release.

### FR5 — Preserve game-switch runtime behavior with four-game navigation

Breakout integrates with the existing `games.js` game-switch controller.

Acceptance / verification:

- A runtime or e2e-like unit regression MUST prove that selecting each of
  `data-game="snake"`, `data-game="pong"`, `data-game="tetris"`, and
  `data-game="breakout"` shows exactly one matching `article[data-game-panel=...]` as visible
  while the others are hidden.
- Action controls (`data-action="...-toggle"` / `data-action="...-reset"`) and direction
  controls route to the active game panel only.

### FR6 — Keep static serving contract unchanged

`games.js` remains a canonical panel asset served from existing static routes and MIME contract.

Acceptance / verification:

- Existing asset tests in `tests/unit/features/panel/test_games_tab.py` continue to assert
  that `render_static` serves the existing Games asset path and content-type contract.
- No alternate static path or external runtime asset source is introduced for Breakout.

### FR7 — Add test coverage for Breakout selectors, panel visibility, controls, and core gameplay

Test coverage must assert Breakout behavior alongside preserved current-game regressions.

Acceptance / verification:

- `tests/unit/features/panel/test_games_tab.py` includes explicit assertions for:
  - new `data-game="breakout"` selector,
  - `article[data-game-panel="breakout"]` render markers,
  - left/right control attributes and direction hooks,
  - untouched existing Snake/Pong/Tetris assertions.
- A deterministic game-state regression path (unit/e2e as appropriate for JS-state probing)
  verifies Breakout: paddle movement, wall bounces, brick collision/removal, score updates,
  and round reset on miss.

## 4. Non-functional constraints

- No dependency additions.
- No alternate static paths.
- No gameplay or panel-serving changes outside the Games tab.
- No removal or change of Snake, Pong, or Tetris mechanics and selectors.

## 5. Traceability

| Scoped item | Requirements covered | Evidence note |
|---|---|---|
| `panel-games-pong-codex-v026` — add Breakout switch/panel | FR1, FR2, FR7 | `test_games_section_*` assertions in `tests/unit/features/panel/test_games_tab.py` for selector/panel/control IDs and preserved prior assertions |
| `panel-games-pong-codex-v026` — implement Breakout gameplay | FR3, FR7 | Focused JS-state or browser-like regression for paddle move, wall bounces, 5x8 brick collision/removal, scoring, and reset |
| `panel-games-pong-codex-v026` — runtime switch behavior | FR5, FR7 | Switch-visibility test for Snake/Pong/Tetris/Breakout and control-routing assertions |
| `panel-games-pong-codex-v026` — preserve scope and serving | FR4, FR6 | Existing game tests and asset-serving assertions remaining green; diff boundary review |

## 6. Conformance and review expectations

Reviewers should reject this SPEC if any acceptance criterion lacks an observable proof path or if any requirement broadens scope into non-Games features.
