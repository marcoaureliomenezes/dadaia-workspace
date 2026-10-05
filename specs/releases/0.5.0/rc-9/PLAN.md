# PLAN — Release: 0.5.0, candidate 9

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

The SPEC says what; this PLAN holds the as-is review and the DAG; `tasks/<job>.md` holds each job's stage contracts and tasks (Q8). The operator approves this PLAN.

## As-is review

- Job 1 — the demolition (bug history at 13269b5c9; full unit table on `wt/0.5.0-rc9/job1`, carried into `tasks/job1.md`):
  - `worktree.py merge` carries five records in nine days, each patched in place: one merge holds four jobs (allowed sets, verdict, the `verify:` run, the fast-forward) for every kind. REBUILD (0190).
  - The `release`/`impl` kind split made an atom and its derived section unlandable together (`memory-update-same-commit-docs-unsatisfiable-under-the-release-kind`); 0189 layered on it and was rejected. The kinds leave (0191): `_worktree_kinds.py` becomes `_worktree_names.py`, one grammar and one tail reader.
  - `_worktree_end._verify` runs the tracked `verify:` line with `shell=True` and the full `scripts/ci.py` at every merge (gate 1, ~6 min over 67 landings). The line leaves; `ci.py` gains `task`/`stage`/`job` levels (AC1.1, AC1.2).
  - Fixed-depth path readers (`protected_glob`, `_worktree_end._target`, `_worktree_git.rows`) misread a two-level tree name; they read the grammar module.
  - `_release_plan._schedule_errors` (the Parallel schedule) has no bug of its own and leaves with its law (AC1.8); `job_errors` and `SPECS_CANON`'s `rc-<N>/tasks/<job>.md` row are added (AC1.9, AC1.10).
- Job 2 — the bug window (SPEC §Bug window review): seven open single records (AC2.1–AC2.7), UPDATE with RED first, except C7, the ledger privacy seam: two deciders of "what the push refuses", the HIGH and its 4 correlates, REBUILD (AC2.7). T-050-210 and 212 land as-is from `refs/backup/0.5.0b-impl-full`; 211 is REBUILT (no `caused_by` reset, no v33 raise); C9/C10 ledger work (AC2.9–AC2.11).
- Job 3 — the REBUILDs (bug history on `wt/0.5.0-rc9/job3`, carried into `tasks/job3.md`):
  - Test session env: three fixes in two days, each one more env key or writer; five writers and three child-env builders. Redo: one pure `suite_env(parent, home)` applied once (AC3.1).
  - `sweep.py`'s delete path: three patches in one day widening one except arm; `remove` judged by exception, `Skipped` a truthy `str`. Redo: the outcome decides, a refusal is falsy (AC3.3).
  - `context dead`: `--commit`, `commit_all` and three refusals exist only for dead's auto-sync commit. Redo: dead never commits; a dirty checkout refuses (AC3.2, 0172).
  - T-050-168's tests were re-pinned and loosened (AC3.4); `_StubDoctor` needed two repairs to track `DoctorService` (AC3.5); rows 20, 24–26 are single-site own fixes (AC3.6).
- Job 4 — the PLAN and the trio validator: after Job 1, `release.py check` validates the canon and `job_errors` only; nothing refuses a cyclic DAG, a missing Job 1, more than 8 jobs, non-test files in stage 1, overlapping `W:` in a stage, or a PLAN without DAG/hot files at `phase IMPLEMENTATION` (AC4.2, AC4.3). Surfaces: `_release_check.py`, `_release_phase.py`, `test_release_script.py`.
- Job 5 — the bugs law and the closed rc: the bugs law and its skills still teach the pile, cause groups and "fixed in any phase"; no closed block list; `release.py new` does not open a SPEC with `## Bug window review` and `check` does not require it; `bugs.py fix` does not find the REBUILD shape; `dd-code-review` still carries 0163's retired `<bug-id>#<id>` clause (AC5.1–AC5.9).
- Reconciliation: atoms Jobs 1–5 make stale (`worktrees.md`, `bug-ledger.md`, release atoms) and rc-8's closure memory items, each with its numeric check (AC6.1).

## DAG (rc-9)

The edges come from file overlap; jobs without an edge have disjoint envelopes.

| job | waits on | why |
|---|---|---|
| Job 1 | — | runs from minute 1 |
| Job 3 | — | runs from minute 1; its envelope is disjoint from Job 1's (`test_worktree_lifecycle.py`'s `base_env` call stays Job 2's, below) |
| Job 2 | Jobs 1, 3 | Job 1: both touch `scripts/ci.py` and `bugs.py` (AC2.8's 210 commits). Job 3: `base_env`'s last two callers, `test_worktree_lifecycle.py` and `test_registry_version_grammar.py`, switch to `suite_env` in Job 2 (J2.S3.T3, J2.S3.T8) |
| Job 4 | Job 1 | both touch `release.py`, `_release_check.py`, `tests/contract/test_release_script.py`, `dd-gitflow-default` and the releases law |
| Job 5 | Jobs 1, 2, 4 | Job 1: as Job 4. Job 2: `bugs.py` and `test_bug_resolution_bugs_script.py` (AC2.7, AC2.8 vs AC5.7). Job 4: `_release_check.py` (AC4.2 vs AC5.6) |
| Reconciliation | Jobs 1–5 | memory and derived docs of every job (AC1.5, AC6.1) |

- Lanes: A, Job 1 → Job 2 ∥ Job 4 → Job 5 → Reconciliation; B, Job 3 → Job 2.
- Critical path: Job 1 → Job 2 → Job 5 → Reconciliation.

- Recorded edge, Job 1 → Job 3 (R7): Jobs 1 and 3 started without an edge and overlapped on 8 files; the edge is recorded now and the overlap is a deviation (SPEC §How rc-9 runs).

### Hot files (R6)

- `specs/bugs/BUGS.jsonl` (Jobs 2, 3) is written only by `bugs.py`, and a rebase conflict is redone by its writer (ADR 0180). `PLAN.md` holds one section per job, and only that job writes it.
- `scripts/ci.py`: Job 1 (AC1.1), then Job 2 (AC2.1, AC2.8's a98e9a5e1).
- `relimpl/scripts/_release_check.py`: Job 1 (AC1.7), Job 4 (AC4.2), Job 5 (AC5.6), in that order.
- `tests/contract/test_release_script.py`: Job 1, then Job 4.
- `tests/unit/skills/test_bug_resolution_bugs_script.py`: Job 2, then Job 5.
- `tests/unit/skills/test_release_implementation_release_script.py`: Job 2 (AC2.6), then Job 5 (AC5.6).
- Generated, in no `W:` (R6): the behavior-map hash and the derived docs; each job's close task regenerates them.
