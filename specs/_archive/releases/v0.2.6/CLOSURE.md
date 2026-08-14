# Closure: Release - v0.2.6

> **Status:** Aprovado
> **Release ID:** v0.2.6
> **Owner:** product-engineer
> **Closed:** 2026-07-14

## Summary

v0.2.6 delivers the Codex Pong gameplay option in the panel Games tab as the third
scoped game choice. The shipped surface includes Pong selector/markup in `games.py`, Pong
runtime in `games.js` with deterministic state/tick helpers, and panel runtime assertions for
game-switch visibility and control targeting from the same scoped test seam. Snake/Tetris
behavior and game-serving contracts remain unchanged.

## Scope and task completion

| Task ID | Planned scope | Final state | Evidence |
|---|---|---|---|
| T1 | Pong selector and panel markup in `dadaia_workspace/features/panel/views/games.py` | Implemented and reviewed | `.dadaia/tmp/lifecycle-worker/dadaia-workspace/g1-impl-codex5-implement-attempt-0-0855a2322743.step-output.json` |
| T2 | Pong state machine and input controls in `dadaia_workspace/features/panel/views/assets/js/games.js` | Implemented and reviewed | `.dadaia/tmp/lifecycle-worker/dadaia-workspace/g1-impl-codex5-implement-attempt-0-0855a2322743.step-output.json` |
| T3 | Runtime visibility and cross-game control assertions in games.js + e2e tests | Implemented and reviewed | `tests/unit/features/panel/test_games_tab.py`, `tests/e2e/panel/test_pong_game_panel.py`, `review_combined` verification payload |
| T4 | Scope containment and static-serving contract non-regression checks | Implemented and reviewed | `.dadaia/tmp/lifecycle-worker/dadaia-workspace/g1-impl-codex5-implement-attempt-0-0855a2322743.step-output.json` |

## Validations

| Category | Command / Artifact | Evidence |
|---|---|---|
| Implementation and unit scope checks | `cd repos/dadaia-workspace && PYTHONDONTWRITEBYTECODE=1 ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/panel/test_games_tab.py tests/e2e/panel/test_pong_game_panel.py` | `implementation` step output `g1-impl-codex5-implement-attempt-0-0855a2322743.step-output.json` and recorded `passed` output from scoped pytest run |
| QA + security + code review | Combined review payload from implementation-reviews workflow (`task_id`: `g1-impl-codex5:review_combined:attempt-0`) | `.dadaia/tmp/lifecycle-worker/dadaia-workspace/g1-impl-codex5-review_combined-attempt-0-024266ceaf1b.step-output.json` with `verdict: APPROVED` |
| Workflow review reason | `test_evidence` in combined review payload | `.../g1-impl-codex5-review_combined-attempt-0-024266ceaf1b.step-output.json` reports `10 passed in 0.39s` |

## Drifts

No drift record was authored at the 2026-07-14 closure of this release. This section was
added retroactively on 2026-08-14, at archive time, to satisfy the SPEC-DOC-006
archived-CLOSURE canon (PM disposition of a v0.8.0 CLOSURE "Backlog returns" item).

No retrospective drift claim is made here — none is assertable or deniable at this
distance. The release's record is otherwise unchanged.

## Dispositions

- `specs/backlog/20260714-panel-games-pong-codex-v026.md` — `DELIVERED - v0.2.6` (implementation evidence in `g1-impl-codex5-implement-attempt-0-0855a2322743.step-output.json`).
- `specs/memory/product/panel/panel.md` — updated from Snake/Tetris wording to include Pong.

## Memory updates

- `specs/memory/product/panel/panel.md`: `Purpose/Tabs/Games` updated to state that the Games tab includes Codex Pong (`Pong (Codex)` + `data-game-panel="pong"` and deterministic canvas + input controls), while preserving Snake/Tetris unchanged behavior.

## Runtime and archive disposition

- `specs/releases/ACTIVE.md` set to `release: none` and `phase: none`.
- No `specs/_archive/` move is performed by this write scope.
