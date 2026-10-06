# TASKS — 0.5.0 rc-10, Job 6 — the test freeze

**Status:** Draft

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Job 6 itself runs under today's law; its freeze binds every job opened after it merges and the instance is re-projected.

- **PARKED (PLAN F-3, HIGH-1):** the freeze as drawn cannot turn a RED test green (the strict-xfail removal and the pin edit are test diffs). The job does not open until the operator rules F-3 (a), (b) or (c); the rows below are redrawn then. Only J6.S2.T4's pin move to `core/specs_version.py` is choice-independent.

- Edges: Jobs 1–5, 7, 8. Test paths below are today's; the driver rewrites them to Job 7's mirror paths when the job opens. Readings: PLAN agent defaults 4 and 5 (5 is the reviewer's literal reading: anchor from subjects, fail closed, pre-anchor test lines frozen, new tests only in a tests-only stage); F-1 and F-3 open.

## Stage J6.S1 — RED

- Contract: exit tests every AC6.0–AC6.2 row RED as strict xfail; envelope `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py`; ACs AC6.0–AC6.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S1.T1 | AC6.0–AC6.2 | `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py` | RED: a worktree editing its own `tests:` line still has a test edit refused; no `tests:` line refuses with `Operator action: commit the tests: line on <work>'s AGENTS.md`, and after that commit the same merge lands; past the RED anchor a modified or deleted line of a test file existing at the anchor refuses with one `Operator action:` line, a pure rename lands, a new test lands only in a tests-only stage, an underivable anchor refuses (fail closed); a RED stage whose new test errors cannot close |

## Stage J6.S2 — the freeze

- Contract: exit tests J6.S1 green, unit + integration green; envelope `GF/_worktree_freeze.py`, `GF/_worktree_end.py`, `AGENTS.md`, `tests/conftest.py`, `pub/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `pub/data/worktrees-AGENTS.md`, `S/dd-release-definition/SKILL.md`, `relimpl/RC-FLOW.md`, the canon pin; ACs AC6.0–AC6.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S2.T1 | AC6.0, AC6.2 | `GF/_worktree_freeze.py` (new: pure judge over diff rows and stage ids; one git read), `GF/_worktree_end.py` (the `AGENTS.md` line reader lifted out of `_gate`, shared by `verify*:` and `tests:`; one call in `merge` for task and job merges) | `test_worktree_lifecycle.py` |
| J6.S2.T2 | AC6.0 | `AGENTS.md` (`tests: tests/**` beside the verify lines) | `test_worktree_lifecycle.py` |
| J6.S2.T3 | AC6.1 | `tests/conftest.py` (every strict xfail gets `raises=AssertionError`) | `test_worktree_lifecycle.py` |
| J6.S2.T4 | AC6.1–AC6.3 | `pub/scaffold/releases/AGENTS.md` (§3's same-task rewrite clause leaves; tests born in RED stages, frozen at the anchor; a REBUILD keeps the fix's tests), `specs/releases/AGENTS.md` (by `specs upgrade`), `pub/data/worktrees-AGENTS.md` (the freeze in gate 1 and 4), `S/dd-release-definition/SKILL.md` §5, `relimpl/RC-FLOW.md` step 2, `S/dd-gitflow-default/SKILL.md` and `bugres/SKILL.md` (shape-3 text, waits on F-3), `pub/entities/behavior-map.json` (their hash re-record), `core/specs_version.py` (gains `_CANON_AT`: the pin moves here, independent of F-3), `tests/unit/core/test_specs_version.py` (`_CANON_AT` leaves it), `pub/templates/shipped-hashes.json` | `test_specs_version.py`, `test_tree5_shipped_history.py`, `test_law_states_what_the_code_does.py` |
| J6.S2.T5 | — | this file | close task, last: behavior map; `test-audit:`, `mutation:`; `done` |
