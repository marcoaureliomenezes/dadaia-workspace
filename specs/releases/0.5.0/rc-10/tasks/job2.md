# TASKS — 0.5.0 rc-10, Job 2 — evals: the repo law, T1 and T2

**Status:** Draft

`W:` paths are relative to `repos/dadaia-evals`. Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

- Tree: `worktrees/dadaia-evals/0.5.0-rc10/job2`; every `W:` path below is relative to `repos/dadaia-evals`, this file aside.
- Precondition met (PLAN F-2): the four gate lines are on `dadaia-evals` `feature/0.5.0` by cbaa6f3, CI run 37463825307; `verify-task:` ignores the appended paths.
- Candidate wheel: a `ci.yml` step builds it from `dadaia-workspace` at the given ref, inside the 0177 workflow check (`scripts/check_workflows.py` green); an image-build row with no wheel FAILS, never skips. Known limit: `unittest.expectedFailure` counts an error as expected (PLAN reading 4).

## Stage J2.S1 — RED

- Contract: exit tests every AC2.2–AC2.4 integration row RED as strict xfail (`unittest.expectedFailure`); envelope `tests/**`; ACs AC2.2–AC2.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S1.T1 | AC2.2, AC2.3 | `tests/test_t1_cold_onboarding.py` | RED: the image builds with the 0.4.7 layer and with the `ci.yml`-built candidate wheel (absent wheel → fail); the unchanged grader passes on a hand-onboarded workspace of each version, fails on an empty one; `git ls-files jobs` prints nothing |
| J2.S1.T2 | AC2.2, AC2.4 | `tests/test_t2_block_list_bug.py`, `tests/plants/t2/**` (the planted correct and assert-rewriting fixes) | RED: on both versions the planted correct fix passes, the assert-rewriting one fails; the grader reads only `bug-record-v1` fields |

## Stage J2.S2 — the tasks

- Contract: exit tests J2.S1's rows green; `python3 -m unittest discover -s tests` green; envelope `AGENTS.md`, `tasks/t1-cold-onboarding/**`, `tasks/t2-block-list-bug/**`, `README.md`, `.github/workflows/ci.yml`; ACs AC2.1–AC2.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S2.T1 | AC2.3 | `tasks/t1-cold-onboarding/` (`instruction.md`, `task.toml`, `environment/Dockerfile`: a `file://` bare repo, one commit, the lib last; `tests/test.sh`, `tests/test_grade.py`: `dadaia doctor --json` 0 errors, context ALIVE, specs initialized) | `tests/test_t1_cold_onboarding.py` |
| J2.S2.T2 | AC2.4 | `tasks/t2-block-list-bug/` (same five files: an onboarded project, red work-branch suite after a merged contract break, the operator's confirmation in the instruction; grader: record before fix, RED on pre-fix sha and green on fix, suite green at HEAD, no `-assert` line in `git diff -U0 -- tests`) | `tests/test_t2_block_list_bug.py` |
| J2.S2.T3 | AC2.1 | `AGENTS.md` (the lines' text, if the operator's commit needs a fold), `README.md` | no test; check: `grep -cE '^(verify|tests:)' AGENTS.md` prints `4` |
| J2.S2.T4 | AC2.2 | `.github/workflows/ci.yml` (the candidate-wheel build step) | `scripts/check_workflows.py` |
| J2.S2.T5 | — | — (close commit in `dadaia-evals`) | close task, last: `test-audit:` and `mutation:` lines (mutation over `scripts/` only if touched, else `skipped — <reason>`); this file's `done` is written by Reconciliation (an evals tree cannot write it) |

- Landing: job merge onto `feature/0.5.0`, then evals' PR edges to `develop` and `main` (Job 3's edge).
