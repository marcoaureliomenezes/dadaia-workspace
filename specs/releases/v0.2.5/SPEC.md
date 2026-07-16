# SPEC — Release v0.2.5 — Snake wall wrap for PI workflow validation

> **Status:** Aprovado

**Release ID:** v0.2.5
**Owner:** product-engineer
**Source:** backlog `snake-wall-wrap-v025-pi-validation` plus bug
`release-definition-terminal-gate-leaves-next-workflow-preflight-unsatisfiable`
**Workflow:** release-definition / spec_create

## 1. Problem

The panel Games tab Snake game currently treats a head coordinate outside the 20×20 board as game-ending/reset behavior. This release changes that wall-contact rule while preserving the rest of the Games tab behavior. The live PI validation also exposed a workflow boundary defect: successful release definition leaves legitimate producer-owned Git state that implementation preflight rejects. This release repairs both bounded outcomes and proves the real consecutive workflow path.

## 2. Picked scope

### Backlog items

| Item | Disposition in this SPEC |
|---|---|
| `specs/backlog/20260714-snake-wall-wrap-v025-pi-validation.md` | Picked. Fully addressed by FR1–FR7. |

### Bugs

| Bug | Disposition in this SPEC |
|---|---|
| `release-definition-terminal-gate-leaves-next-workflow-preflight-unsatisfiable` | Picked. Solved by FR8. |

### Audit findings

No live audit finding is picked for this release. Archived audit material supplied to the step is historical context only and does not add release scope.

### Subsumptions

None. The workflow-boundary bug is independent of the Snake backlog item.

### Sanitization outcomes

The authoritative producer output is `snake-wall-wrap-v025-backlog-pi`; candidate-backlog scanning must not substitute a different item. Archived and terminal backlog neighbors remain historical and are not revived, consumed, or re-dispositioned by this release.

## 3. Functional requirements

### FR1 — Horizontal wall crossing wraps instead of ending the game

When the Snake head moves left from `x = 0`, the next head coordinate MUST be `x = 19` with the same `y`. When it moves right from `x = 19`, the next head coordinate MUST be `x = 0` with the same `y`.

Acceptance / verification:

- A focused automated regression test drives the Games static Snake logic to move left across the left wall and observes the new head coordinate `(19, same y)` without any reset/game-over side effect.
- A focused automated regression test drives the same logic to move right across the right wall and observes `(0, same y)` without any reset/game-over side effect.
- The proof MUST inspect the observable Snake state after a tick; merely asserting that rendering still produces nonblank pixels is insufficient.

### FR2 — Vertical wall crossing wraps instead of ending the game

When the Snake head moves up from `y = 0`, the next head coordinate MUST be `y = 19` with the same `x`. When it moves down from `y = 19`, the next head coordinate MUST be `y = 0` with the same `x`.

Acceptance / verification:

- A focused automated regression test drives movement upward across the top wall and observes `(same x, 19)` without reset/game-over.
- A focused automated regression test drives movement downward across the bottom wall and observes `(same x, 0)` without reset/game-over.
- The proof MUST use a controlled state/tick seam or equivalent JavaScript execution probe that can distinguish wrapped coordinates from a reset to the starting snake.

### FR3 — Wall contact alone does not reset, pause, clear score, or end the game

Crossing a wall MUST NOT reset the snake body, clear the score, pause the game, or invoke the existing game-over/reset path.

Acceptance / verification:

- A regression test initializes a non-starting score/body state, crosses a wall, and observes that score and body progression remain consistent with ordinary movement.
- The test MUST prove the game-over/reset path was not invoked, either by observing stable score/body state that would be reset by that path or by a controlled call-observation hook in the test harness.

### FR4 — Self-collision still uses the existing game-over/reset behavior

The release changes only wall collision semantics. Snake self-collision MUST still end/reset the game through the existing path.

Acceptance / verification:

- A regression test creates a self-collision state and observes the existing game-over/reset outcome.
- The self-collision test MUST remain separate from wall-wrap tests so a passing wall wrap cannot mask a broken self-collision path.

### FR5 — Food, scoring, and body advancement remain unchanged

Food placement/eating, score increments, and body advancement MUST remain semantically unchanged except for the new wrapped coordinate calculation.

Acceptance / verification:

- A regression test places food at the next head coordinate, executes a tick, and observes the existing score increment and growth behavior.
- A regression test covers ordinary non-food movement and observes body advancement without growth.
- Any randomness in food placement MUST be controlled or isolated so the test proves food/score behavior rather than chance placement.

### FR6 — Controls and board dimensions remain stable

The existing keyboard and direction-pad controls, start/pause/reset controls, 20×20 board, and 400×400 Snake canvas MUST remain stable.

Acceptance / verification:

- Existing Games tab asset smoke coverage remains green.
- Automated coverage asserts the Snake board still uses 20 columns by 20 rows and the existing 400×400 canvas dimensions.
- Automated coverage asserts the existing direction controls and start/pause/reset controls are still present and wired through the Games tab assets.

### FR7 — Scope containment: no Tetris, non-game panel, runtime dependency, or serving-path change

The rendered Games surface and static asset serving path MUST remain unchanged except as directly required to expose wrapped Snake behavior. Tetris and non-game panel sections MUST NOT change. No new runtime dependency, external asset, framework, or alternate static serving path may be introduced.

Acceptance / verification:

- Static or structural inspection shows `render_games_section` still exposes the same Snake/Tetris surface and controls except for the Snake wall-wrap behavior.
- Static or structural inspection shows `render_static` continues to serve the updated Games JavaScript from the existing panel static asset path.
- A diff review confirms no Tetris behavior or non-game panel sections were modified.
- Dependency metadata remains unchanged unless an existing test tool already in the project is used.

### FR8 — Consecutive workflows must not deadlock on producer-owned Git state

`implementation-reviews` MUST be directly runnable after a successful
`release-definition` for the same context/release without `--skip-preflight`, a manual
commit, or a manual push. Git dirtiness, missing upstream, and unpushed commits remain
visible warnings; the independent commit/push chokepoints remain authoritative.

Worker Ring-2 `changed_paths` MUST contain only paths changed during that worker attempt.
Pre-existing dirty paths MUST be snapshotted before execution and excluded when untouched,
while a worker modification to an already-dirty path MUST still be detected by content
change. This contract applies equally to PI and Codex headless adapters.

Acceptance / verification:

- A regression test drives release-definition success into implementation preflight with
  producer-owned dirty definition artifacts and proves preflight is OK with warnings.
- Unit tests prove dirty, missing-upstream, and unpushed Git states warn instead of block.
- Adapter tests prove untouched pre-existing paths are excluded and modified pre-existing
  paths are included for both PI and Codex.
- PI and Codex preserve `PYTHONDONTWRITEBYTECODE` through their environment allowlists so
  governed workers and reviewers cannot recreate forbidden repo-local bytecode caches.
- The real PI `v0.2.5` implementation workflow proceeds only with one documented bootstrap
  override needed to install this fix; subsequent no-override boundary validation passes.

## 4. Non-functional constraints

- Keep the implementation inside the existing panel architecture: CLI wiring remains untouched; panel static assets remain packaged source; no external CDN or JavaScript framework is added.
- Respect the product memory claim that the panel Games tab contains playable Snake and Tetris with stable controls, score, pause/start, reset, and canvas dimensions.
- Preserve repository hygiene: no generated test output, cache, Playwright report, or temporary runtime state may be left in the repository.

## 5. Traceability

| Scoped item | Requirement(s) | Acceptance evidence |
|---|---|---|
| `snake-wall-wrap-v025-pi-validation` — horizontal wrap | FR1, FR3 | Horizontal wrap regression tests; no reset/game-over observation. |
| `snake-wall-wrap-v025-pi-validation` — vertical wrap | FR2, FR3 | Vertical wrap regression tests; no reset/game-over observation. |
| `snake-wall-wrap-v025-pi-validation` — preserve self-collision | FR4 | Dedicated self-collision regression test. |
| `snake-wall-wrap-v025-pi-validation` — preserve food/score/body movement | FR5 | Food/score and ordinary movement regression tests. |
| `snake-wall-wrap-v025-pi-validation` — preserve controls and dimensions | FR6 | Games asset smoke tests plus controls/dimensions assertions. |
| `snake-wall-wrap-v025-pi-validation` — keep rendered surface/static serving path scoped | FR7 | Structural/static inspection and diff review. |
| `release-definition-terminal-gate-leaves-next-workflow-preflight-unsatisfiable` | FR8 | Consecutive-workflow preflight and per-worker changed-path delta tests. |
| `pi-headless-drops-bytecode-suppression-and-recreates-repo-caches` | FR8 | PI/Codex environment-projection tests and final full-depth hygiene scan. |

## 6. Out of scope

- Tetris behavior, layout, controls, scoring, and rendering changes.
- Panel tabs, navigation, non-game sections, panel server security, or telemetry changes.
- New runtime dependencies, external JavaScript/CSS assets, or alternate asset-serving paths.
- Memory edits during definition beyond this release SPEC artifact; current product memory remains unchanged until closure if implementation changes the current product truth.

## 7. Review expectations

Reviewers should reject this SPEC if any acceptance criterion cannot be proven through an automated test, controlled JavaScript/state probe, structural/static inspection, or explicit diff evidence. Equal visual rendering alone is not enough to prove that the internal wall-collision path changed from reset to wrap.
