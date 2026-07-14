# SPEC — Release v0.2.6 — Add Codex Pong to Panel Games

> **Status:** Aprovado

**Release ID:** v0.2.6
**Owner:** product-engineer
**Source:** backlog `panel-games-pong-codex-v026`
**Workflow:** release-definition / spec_create

## 1. Problem

The panel Games tab only exposes Snake (Codex) and Tetris (PI), so users cannot launch the requested Codex Pong game beside those experiences. The existing game panel wiring and tests need a third, consistent game entry, plus explicit, inspectable runtime proofs for gameplay and visibility behavior.

## 2. Picked scope

### Backlog items

| Item | Disposition in this SPEC |
|---|---|
| `specs/backlog/20260714-panel-games-pong-codex-v026.md` | Picked. Fully addressed by FR1–FR8. |

### Bugs

No bug is part of this release scope.

### Audit findings

No audit finding is part of this release scope.

### Subsumptions

No subsumption chain is introduced by this release. The backlog item is single-item and does not supersede another open backlog or bug record.

### Sanitization outcomes

The authoritative producer output is `g1-backlog-codex2`; this release uses only that scope item. No alternate backlog item was substituted. Archive-only neighbors remain untouched.

## 3. Functional requirements

### FR1 — Add a Pong selector control in the existing Games switch

A third game-choice control for Pong appears in `render_games_section` as `Pong (Codex)` and participates in the same `data-game` switch contract as Snake and Tetris.

Acceptance / verification:

- `render_games_section` tests MUST assert one `.game-choice` button with `data-game="pong"`, label text `Pong (Codex)`, and proper tab semantics.
- Tests MUST assert the new control is in the same control container as Snake/Tetris choices and does not replace or remove existing controls.
- A deterministic UI-state check MUST confirm `data-game-panel="pong"` is addressed by this selector.

### FR2 — Add Pong panel markup with canvas and toolbar controls

A new `<article data-game-panel="pong">` is added to the same game stage with dedicated canvas, score output, start/pause control, and reset control in the existing games-toolbar pattern.

Acceptance / verification:

- `render_games_section` tests MUST assert:
  - an `article` with `data-game-panel="pong"`,
  - `id="pong-canvas"` and deterministic canvas dimensions,
  - `id="pong-score"`, `data-action="pong-toggle"`, and `data-action="pong-reset"`.
- tests MUST assert one Pong d-pad control set with on-screen direction actions for at least `up` and `down` (matching the Snake d-pad shape).
- Static asset coverage in `test_games_assets_are_served` MUST include Pong panel markup assertions.

### FR3 — Implement Codex Pong gameplay logic in `games.js`

Pong gameplay is added under the shared `games.js` module style with the following behavior:

- left paddle is controlled by on-screen controls and `ArrowUp`/`ArrowDown`.
- ball bounces on top and bottom walls;
- ball bounces on right wall;
- paddle return increments score;
- missing the paddle (ball passes it) resets paddle position, ball state, and score.

Acceptance / verification:

- A runtime test seam MUST expose Pong state in a deterministic hook path (analogous to `window.__dadaiaSnakeTest`) and include at least:
  - ball `{x,y}` and velocity `{x,y}`;
  - left paddle y-position and velocity/state;
  - score;
  - running state;
  - tick + event helpers for key/button control.
- Focused JavaScript-state tests MUST verify each behavior by reading hook state before/after deterministic ticks:
  - a top-wall contact flips vertical velocity,
  - a bottom-wall contact flips vertical velocity,
  - a right-wall contact flips horizontal velocity,
  - a paddle contact increments score and continues play,
  - a miss sets state to initial values and score to zero.
- Test setup MUST control randomness (for any future serve reset behavior) to make score/position proof deterministic.

### FR4 — Panel-runtime, browser-observable game-switch behavior

Pong must follow the existing panel runtime switch contract in both logic and visibility.

Acceptance / verification:

- A panel-runtime or simulated DOM e2e check MUST drive clicks on `.game-choice` controls and assert:
  - only the selected panel is visible (`hidden = false`)
  - all non-selected panels are hidden (`hidden = true`), including transition to/from `data-game-panel="pong"`.
- The same runtime check MUST assert that start/pause/reset controls target the active game panel and that a panel state reset cannot leak between games.
- At least one runtime DOM check must exercise the DOM contract end-to-end (query selectors + `hidden` + action button activation), not only static file comparison. Operator amendment (2026-07-14): on hosts with no installed browser runtime, an executed Node/VM DOM-harness check exercising the same selectors and hidden/aria state transitions is ACCEPTED as this evidence; a real-browser (Playwright) pass is preferred where available but is not a blocking requirement for this release.

### FR5 — Preserve existing game behavior and section isolation

Snake and Tetris behavior must remain intact; no non-Games panel sections may be altered.

Acceptance / verification:

- Existing Snake/Tetris unit or e2e probes for controls and core behavior remain green and remain targeted to their prior selectors.
- A structural diff review of `render_games_section` and `games.js` MUST show no behavioral edits to Tetris logic or non-game sections in this release.
- Tetris/Snake static serving and route names remain unchanged.

### FR6 — Keep existing static-serving path and asset contract

`games.js` remains served from existing panel static asset path.

Acceptance / verification:

- `test_games_assets_are_served` MUST continue asserting `games.js` with the same response contract.
- The `games.js` test for byte-equality MUST assert the released file is served from the current canonical path.

### FR7 — Add explicit gameplay regression and visibility assertions in test suite

Implementation must include test coverage for both logic and visibility in the same scoped test areas:

- `tests/unit/features/panel/test_games_tab.py` coverage for new markup and asset hook names.
- `tests/e2e/panel/test_pong_game_panel.py` (or equivalent) coverage for game-switch DOM behavior and Pong state transitions through hook-driven ticks.

Acceptance / verification:

- A control-state regression includes both keyboard and on-screen d-pad inputs.
- A visibility regression includes selecting Snake→Pong→Tetris and asserting panel visibility toggles and active-classes or `hidden` flags.
- A gameplay regression suite includes the FR3 outcomes with direct state inspection.

### FR8 — Scope hygiene and constraints

The release must not introduce new dependencies, alternate serving paths, or non-scoped panel changes.

Acceptance / verification:

- A dependency scan on touched files shows no new runtime dependency changes.
- The touched file list is confined to Games tab scope.
- `release` output and test scope excludes non-Games tab paths.

## 4. Non-functional constraints

- No dependency or asset delivery path is changed from existing `render_static` behavior.
- No runtime framework or external API dependency is introduced.
- No gameplay changes outside the Games tab in this release.

## 5. Traceability

| Scoped item | Requirement(s) | Acceptance evidence |
|---|---|---|
| `panel-games-pong-codex-v026` — add Pong selector and markup | FR1, FR2, FR4 | `test_games_section_has_two_playable_canvas_surfaces` (extended) + panel-switch DOM probe assertions |
| `panel-games-pong-codex-v026` — implement Codex-style Pong gameplay | FR3, FR7 | `__dadaiaPongTest`-driven hook assertions and dedicated e2e gameplay regressions |
| `panel-games-pong-codex-v026` — add runtime visibility proof | FR4, FR7 | Game-switch panel visibility assertions over Snake/Pong/Tetris panels |
| `panel-games-pong-codex-v026` — preserve Snake/Tetris and scope | FR5, FR6, FR8 | Diff review + existing Snake/Tetris asset and behavior checks |

## 6. Review expectations

Reviewers should reject this SPEC if any behavior is not provable by deterministic unit/e2e state inspection, controlled JS-state probes, or direct structural assertions on generated markup and game state transitions. Visual-only checks are insufficient for FR3/FR4 without state-level proof.
