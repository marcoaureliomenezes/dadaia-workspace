# TASKS — 0.5.0 rc-10, the bug batch

**Status:** Draft

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Opened after Job 6: the freeze binds it. Each fix is shape 3 as Job 6 rewrites it: the RED commit in JB.S1, then a fix commit with the code, the `BUGS.jsonl` line and the marker-line deletion (0209 + F-3 (a)).

- AC9.1: every bug found in rc-10 and not fixed as a hotfix; grouped by cause; a fix with `caused_by ≠ none` is a REBUILD of the unit keeping its tests (0210). Rows are born from `bugs.py status` when the batch opens. Empty batch: the job is not opened; Reconciliation records `0 open`.

## Stage JB.S1 — RED

- Contract: exit tests one RED case per bug (or per cause group) as strict xfail, at the lowest level that detects it; envelope `tests/**`; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S1.T1+ | AC9.1 | the owner test file of each bug's seam | born per cause group |

## Stage JB.S2 — fixes

- Contract: exit tests JB.S1 green, unit + integration green, `bugs.py status` shows no rc-10 bug open; envelope the units the groups name, `specs/bugs/BUGS.jsonl` (by `bugs.py` only); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S2.T1+ | AC9.1 | per cause group, disjoint | its JB.S1 case; resolve with `--evidence-seam` |
| JB.S2.T9 | — | this file | close task, last: `test-audit:`, `mutation:`; `done` |
