# Job 1 — T3 = onboard, then stop (FR2)

**Status:** Draft

| task | who | AC | `W:` | owner test | outcome |
|---|---|---|---|---|---|
| J1.T1 | sr | AC2.1, AC2.2 | `tests/e2e/test_evals_t3.py` `tests/helpers/evals.py` | `tests/e2e/test_evals_t3.py` | RED: the grader table inverted and partitioned by act |
| J1.T2 | sr | AC2.1, AC2.2, AC2.3 | `evals/tasks/t3-discovery/tests/test_grade.py` | `tests/e2e/test_evals_t3.py` | REBUILD of the grader; the rows of J1.T1 go green |

Wave 2, with Jobs 2 and 3 (disjoint `W:`). PLAN sections 1, 2 and 5 hold the design. Docker is required: a missing tool fails the row (that file's header). Each task's Definition of done is `python scripts/ci.py job`, then `pytest tests/e2e/test_evals_t3.py tests/e2e/test_evals_scripts.py`. Never the full CI line.

## J1.T1 — RED rows

The operator's order, named in the `test(J1.T1)` commit body: "Onboard, then stop (Recommended)" (R2). The table flips and grows; no assert is deleted or loosened.

- The onboarded fixture earns `1` both with `specs init` (`ONBOARDED_T3`) and without it (a new constant: the same onboarding, no `specs init`).
- Rows that today expect `1` now expect `0`: `HAND_T3`, `RENAMED_T3`, `SPEC_T3`, `TRACED_T3`. `STUB_T3` and `REJECTED_T3` stay `0` and now fail for the act, not the missing entry. `true` (no ALIVE context) stays `0`.
- One new row per act of AC2.2, each beside an otherwise-passing onboarded fixture, each expecting `0`:
  - (a) a `worktree new` and nothing else (a tree under `worktrees/`);
  - (b) a backlog entry written in the main repo's own `specs/backlog/`, no worktree (`RENAMED_T3` is close; keep one row per act);
  - (c) a `specs/releases/*/rc-*/SPEC.md` in the main repo;
  - (d) a file under `.dadaia/states/verdicts/<context>/`, written by hand;
  - (f) a file under `.dadaia/sessions/`, written by hand;
  - a doctor error on an otherwise-onboarded workspace.
- (e), a merge, is observed as "the project's code moved", pinned by the `calc-*` rows (uncommitted, commit, new branch, raw merge, push, git worktree), each failing only for its act (PLAN section 6, point 4).
- Ids stay descriptive. The test name and docstring state the new rule ("the grader rewards onboarding and nothing past it").
- The rows must fail on the current grader for the real reason (`ONBOARDED_T3` earns `0` today, `HAND_T3` earns `1`); record the red run in the commit body. If the no-`specs init` row finds a doctor error in that state, stop and return the finding to the main thread (PLAN risk 5).

## J1.T2 — the grader

- Keep the ALIVE check on `file:///srv/demo.git` and the doctor check.
- Delete `filled`, `clean`, the `BACKLOG`, `RELEASE` and `DEMAND` constants, the `worktree list` walk and the specs-initialized requirement (`specs init` decides nothing).
- The new check is a set-difference on listed paths: the entries of `/workspace/worktrees/`, the files under `/workspace/.dadaia/states/verdicts/`, the files under `/workspace/.dadaia/sessions/`, any `specs/releases/*/rc-*/SPEC.md` of the main repo, and a backlog entry (`active[]` or a line of `_archive/backlog_histo.jsonl`) of the main repo. Each hit is one problem line. No forged-versus-real branch, no `dadaia worktree list`: a broken registry must not hide a tree.
- Gate: `git diff --numstat` shows `test_grade.py` net lines ≤ 0 (SPEC goal 5, AC2.3). `instruction.md`, `task.toml` and `compare.py` stay byte-identical (AC2.4); check with `git diff --name-only`.
- The commit subject is `test(J1.T2): …` (a test-glob file, as `b1d8c5004` and `9c76d7d68`).
