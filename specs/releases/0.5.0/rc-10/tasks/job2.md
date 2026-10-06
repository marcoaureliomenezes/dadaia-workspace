# TASKS — 0.5.0 rc-10, Job 2 — evals: the repo law, T1 and T2

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

`W:` paths are relative to `repos/dadaia-evals`. Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

- Tree: `worktrees/dadaia-evals/0.5.0-rc10/job2`; every `W:` path below is relative to `repos/dadaia-evals`, this file aside.
- Precondition met (PLAN F-2): the four gate lines are on `dadaia-evals` `feature/0.5.0` by cbaa6f3, CI run 37463825307; `verify-task:` ignores the appended paths.
- Candidate wheel, one source for all four runners (`ci.yml`, `eval.yml`'s `check` job, and the `verify:`/`verify-stage:`/`verify-task:` lines): the test builds the wheel from a lib path it resolves — an env var `ci.yml` and `eval.yml` set (they check out `dadaia-workspace` at the ref), defaulting to the workspace's `repos/dadaia-workspace`; an unresolvable path FAILS the row, never skips. Both workflows stay inside the 0177 workflow check. Docker cost per gate: the task gate builds all 4 images too, because evals' `verify-task:` (cbaa6f3) runs the whole discover and ignores the appended paths; a narrower line is a gate-line change, on the operator's morning list; the stage and job gates and both workflows build 4 images (2 tasks × 0.4.7 and candidate). Known limit: `unittest.expectedFailure` counts an error as expected (PLAN reading 4).

## Stage J2.S1 — RED

- Contract: exit tests every AC2.2–AC2.4 integration row RED as strict xfail (`unittest.expectedFailure`); envelope `tests/**`; ACs AC2.2–AC2.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S1.T1 | AC2.2, AC2.3 | `tests/test_t1_cold_onboarding.py` | RED: the image builds with the 0.4.7 layer and with the candidate wheel built from the resolved lib path (unresolvable → fail); the unchanged grader passes on a hand-onboarded workspace of each version, fails on an empty one; `git ls-files jobs` prints nothing |
| J2.S1.T2 | AC2.2, AC2.4 | `tests/test_t2_block_list_bug.py`, `tests/plants/t2/**` (the planted correct and assert-rewriting fixes) | RED: on both versions the planted correct fix passes, the assert-rewriting one fails; the grader reads only `bug-record-v1` fields |

## Stage J2.S2 — the tasks

- Contract: exit tests J2.S1's rows green; `python3 -m unittest discover -s tests` green; envelope `AGENTS.md`, `tasks/t1-cold-onboarding/**`, `tasks/t2-block-list-bug/**`, `README.md`, `.github/workflows/ci.yml`, `.github/workflows/eval.yml`; ACs AC2.1–AC2.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S2.T1 | AC2.3 | `tasks/t1-cold-onboarding/` (`instruction.md`, `task.toml`, `environment/Dockerfile`: a `file://` bare repo, one commit, the lib last; `tests/test.sh`, `tests/test_grade.py`: `dadaia doctor --json` 0 errors, context ALIVE, specs initialized) | `tests/test_t1_cold_onboarding.py` |
| J2.S2.T2 | AC2.4 | `tasks/t2-block-list-bug/` (same five files: an onboarded project, red work-branch suite after a merged contract break, the operator's confirmation in the instruction; grader: record before fix, RED on pre-fix sha and green on fix, suite green at HEAD, no `-assert` line in `git diff -U0 -- tests`) | `tests/test_t2_block_list_bug.py` |
| J2.S2.T3 | AC2.1 | `README.md` | no test; check: `grep -cE '^(verify|tests:)' AGENTS.md` prints `4` |
| J2.S2.T4 | AC2.2 | `.github/workflows/ci.yml`, `.github/workflows/eval.yml` (`check` job): check out the lib at the ref and set the lib-path env var | `scripts/check_workflows.py` |
| J2.S2.T5 | — | — (close commit in `dadaia-evals`) | close task, last: `test-audit:` and `mutation:` lines (mutation over `scripts/` only if touched, else `skipped — <reason>`); this file's `done` is written by Reconciliation (an evals tree cannot write it) |

- Landing: job merge onto `feature/0.5.0`, then evals' PR edges to `develop` and `main` (Job 3's edge).
