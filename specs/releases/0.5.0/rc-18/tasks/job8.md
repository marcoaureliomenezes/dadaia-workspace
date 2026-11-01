# Job 8 — evals functional: graders that report, ADR 0269's bar, no stale names (FR11)

**Status:** Draft

Wave 2, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and §1.1.

- **Graders are test paths.** `evals/tasks/*/tests/test_grade.py` sit under a `tests/` path, so their tasks are test-class (`test(J8.T<k>)`); each is proved by its no-model row in `tests/e2e/test_evals_t*.py`, shown red against the old grader (revert-check) and green against the new. `compare.py` is not a test path: its RED task is T3 and its implementation T4.
- **ADR 0269 (b) is the bar `compare.py` applies:** block when T1 < 3/3, or T2 or T3 < 2/3 on the candidate, or a task >= 2/3 on 0.4.7 falls to <= 1/3; T3's 0.4.7 result is readout only; the docstring cites 0269. The eval run is rc-21's; `eval.yml` landing on `main` is the main thread's act.
- **AC11.2.** After the renames, `git grep -n dadaia-evals -- tests evals` prints nothing and `test_evals_scripts.py:23` names `t2-block-list-bug`.

**Gate law (rc-18).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured in rc-17; no `verify:` change). An implementer's definition of done is that run, plus the touched test directories (`tests/e2e/test_evals_scripts.py`, `tests/e2e/test_evals_t1.py`, `tests/e2e/test_evals_t2.py`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line and no newly skipped test unless this file names the order, and the sweep greps. No preflight, no full CI line; CI on push is the net. A RED task fails only on its new RED tests and says which. Every task reads `.dadaia/tmp/main-thread/20261018/rc18-common.md`.

**Sweep greps.** `git grep -n 'dadaia-evals' -- tests evals` prints nothing; `git diff <base>...HEAD -- tests evals | grep -E '^-\s*assert'` prints nothing.

Tasks: 4 (1 jr, 3 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1, T2, T3 have disjoint `W:` and start together; T4 after T3.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J8.T1 | sr | AC11.1, AC11.2 | `evals/tasks/t1-cold-onboarding/tests/test_grade.py`, `tests/e2e/test_evals_t1.py` | the T1 grader reports doctor's findings instead of crashing when doctor exits 1; its no-model row (integration); the retired name at `test_evals_t1.py:19` goes |
| J8.T2 | sr | AC11.3 | `evals/tasks/t2-block-list-bug/tests/test_grade.py`, `tests/e2e/test_evals_t2.py` | the T2 grader catches a removed assert in any form, not only a bare `assert` line (`test_grade.py:68`); its no-model rows |
| J8.T3 | sr | AC11.2, AC11.4 | `tests/e2e/test_evals_scripts.py`, `tests/helpers/evals.py` | RED, unit: one row per block reason of ADR 0269 (b) and T3's 0.4.7 result read as readout; the stale names at `test_evals_scripts.py:23,68` and `helpers/evals.py:1,67` go |
| J8.T4 | jr | AC11.4 | `evals/scripts/compare.py` | the bar of ADR 0269 (b) replaces the ADR 0178 bar; the docstring cites 0269; turns T3 green |
| J8.T5 | sr | AC11.3, AC11.4 | `evals/tasks/t2-block-list-bug/tests/test_grade.py`, `tests/e2e/test_evals_t2.py`, `tests/e2e/test_evals_scripts.py` | review: the T2 grader compares assertion nodes, so an assert edited in place fails (`d519b8332`); each `compare` block row isolates its named reason, plus a drop row outside the floors (`ed24dae35`) |

**Closure record (main thread, 2026-10-18).** 1 task landed beyond the PLAN, the rows after the planned ones, read from `git log wt/0.5.0/rc-18/wt-rc`.
