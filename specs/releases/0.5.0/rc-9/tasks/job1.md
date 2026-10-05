# TASKS — 0.5.0 rc-9, Job 1 — the demolition

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

As built on `wt/0.5.0-rc9/job1` (its PLAN.md §2, carried here; it wins over the PE draft — SPEC §How rc-9 runs, Deviation). Path aliases on this file: `f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`, `GF/` = `S/dd-gitflow-default/scripts/`.

One worktree (`worktrees/dadaia-workspace/0.5.0-rc9-job1`, operator-authorized `git worktree add`); every task runs inside it. One review at its end, `scripts/ci.py` once on the result, one manual merge. No markers, no start or done commits; a task's commit subject starts with its id; a stage closes with a commit whose body carries `stage: J1.S<m> — unit+integration green`. REBUILD commits name the SPEC's Job 1 as the verdict for the demolished kinds and gate-1 code.

- From J1.S3.T7 on, tasks ran in parallel task worktrees `0.5.0-rc9/job1--J1.S3.T<k>` and landed by fast-forward (T11 and T12 in parallel; T14 and T15 in parallel).

- Gates: task — `ruff` and `mypy` on the touched files plus its owner tests (`-n 2`); stage — unit + integration (`-n 2`), green before the next stage opens; job — `scripts/ci.py` once, at the end.
- AC1.3, operator order 2026-10-05, verbatim: "a release ja tem que começar fazendo ... vocÊ está proibio de rodar 1 worktree para cada tasks ou rodar CI para cada teste ... não podemos perder mais tempo". Corrected the same day (AC1.3): one tree per job plus one `<job>--<task-id>` tree per parallel task, ≤ 5 task trees open per rc; `WT stage` opens a stage's task trees; the verify lines stay as argv (`verify:`, `verify-stage:`, `verify-task:`). As built in J1.S3.T1 (ab3dc84ec).
- Deviation, recorded: J1.S2.T3 (`ci.py` levels) and the first cut of J1.S2.T1 were written before the stage order arrived; J1.S2.T3's tests landed with its code in 0fce6c788, not as an S1 xfail.

The stages and task ids are the approved SPEC's (ad9c60c6b, Job 1 `Stages:`); the rows below refine their `W:` where the code demanded it.

- Commit ids, recorded: before the SPEC's ids existed, commits used an earlier numbering. `J1.S2.T1` of bb4ca7638 and 8aa97f23b is the SPEC's T2 + T3; `J1.S2.T3` of 0fce6c788 (as `J1-1`) is T1; `J1.S2.T5` of 9af5ec8e1 and `J1.S2.T6` of e0d1f0e5a are T5 (+ T10); `J1.S1` of 11b8a93d8 carries T3 and T4's rows; T1 and T2's tests landed with their code.

## Stage J1.S1 — RED (tests only)

- Contract: exit tests are each AC's acceptance test as a strict xfail; envelope `tests/**`.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S1.T1 | AC1.1 | `tests/integration/test_ci_script.py` | same |
| J1.S1.T2 | AC1.2–AC1.5 | `tests/integration/test_worktree_lifecycle.py`, `tests/integration/test_worktree_new.py`, `tests/helpers/worktree_ws.py` | same |
| J1.S1.T3 | AC1.2 | `tests/unit/features/chokepoints/test_push_branch_policy.py` | same |
| J1.S1.T4 | AC1.9, AC1.10, the phase move | `tests/unit/features/specs/test_canon.py`, `tests/contract/test_release_script.py`, `tests/helpers/release_state.py` | same |

## Stage J1.S2 — code and law

- Contract: exit tests are J1.S1's, passing, plus unit + integration; ACs AC1.1–AC1.10.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S2.T1 | AC1.1 | `scripts/ci.py` | `test_ci_script.py` |
| J1.S2.T2 | AC1.3 | `GF/_worktree_new.py`, `GF/_worktree_names.py` (was `_worktree_kinds.py`), `f/spec_context/gate_policy.py`, `S/dd-bug-resolution/scripts/_specs.py` (`core/workspace_layout.py` is T5's: recorded as-built deviation, both commits wrote it), the two contract tests | `test_worktree_new.py`, `test_gate_policy.py`, `test_pre_gate.py` |
| J1.S2.T3 | AC1.2, AC1.4, AC1.5 | `GF/worktree.py`, `GF/_worktree_end.py`, `GF/_worktree_git.py`, `f/spec_context/doctor.py`, `AGENTS.md` | `test_worktree_lifecycle.py` |
| J1.S2.T4 | AC1.2 | `core/gitflow.py`, `f/chokepoints/branch_policy.py`, `.github/workflows/ci.yml`, `scripts/guards/repo.py` | `test_push_branch_policy.py`, guard plant `job-trigger` |
| J1.S2.T5 | AC1.8, AC1.9, AC1.10, the phase move | `core/workspace_layout.py` `SPECS_CANON` and `protected_glob` (the canon rows live there, not in `canon.py`), `S/dd-release-implementation/scripts/{_release_schema,_release_tree,_release_phase}.py`, `_release_plan.py` (deleted) | `test_canon.py`, `test_release_script.py` |
| J1.S2.T6 | AC1.8 | `pub/data/worktrees-AGENTS.md`, `S/dd-gitflow-default/SKILL.md` | no test |
| J1.S2.T7 | AC1.8 | `S/dd-release-implementation/{RC-FLOW,MEMORY-UPDATE,SKILL}.md` | no test |
| J1.S2.T8 | AC1.6, AC1.8 | `S/dd-manager-orchestration/SKILL.md`, `S/dd-release-definition/SKILL.md`, `S/dd-audit-project/PILLAR-SPECS.md` | no test |
| J1.S2.T9 | AC1.8 (hit lines) | `pub/scaffold/{releases,bugs,ADRs}/AGENTS.md`, `S/dd-bug-resolution/SKILL.md`, `S/dd-bug-registration/SKILL.md`, `S/dd-code-review/SKILL.md` | no test |
| J1.S2.T10 | AC1.7 | `S/dd-release-implementation/scripts/_release_check.py` | `test_release_script.py` |
| J1.S2.T11 | AC1.8 | `dadaia_workspace/features/specs/doctor_adr.py` — a ruled superseded record changes an accepted one (d8c01c5df) | `tests/contract/test_adr_canon.py` |

- The canon and law changes move the `specs_version` canon pin and the shipped template hashes; they are re-recorded with T6–T9 (stamp 9 is unshipped).
- AC1.7's own `kind: merge` entry is appended to `_RELEASE.json` at the end, after the merge times exist.

## Stage J1.S3 — review rework

- Contract: tasks are born from the job review's findings; the driver (main thread) appends each row as it is born (R1, R8); exit tests: unit + integration green, then `scripts/ci.py` once.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S3.T1 | AC1.2, AC1.3 | REBUILD: task worktrees back, nested names, verify lines as argv, `ci_run` (ab3dc84ec) | `test_worktree_new.py`, `test_worktree_lifecycle.py` |
| J1.S3.T2 | AC1.8 | law states task worktrees, the verify lines and `ci_run` (da33447df) | no test |
| J1.S3.T3 | AC1.5 | an atom changed alone is refused once, naming its re-derive (a643828fa) | `test_worktree_lifecycle.py` |
| J1.S3.T4 | AC1.10 | `TRIO` → `CANDIDATE_DOCS`, `_refuse_unapproved_docs` (def698d61) | `test_release_script.py` |
| J1.S3.T5 | — | unused | — |
| J1.S3.T6 | — | re-record behavior map, shipped law hashes, stamp-9 canon pin (0a8efbdb6) | generated |
| J1.S3.T7 | AC1.8 | the law states the nested grammar (1135896b4) | no test |
| J1.S3.T8 | AC1.8 | quickstart and journey use the nested grammar (500571da7) | no test |
| J1.S3.T9 | AC1.3 | `caused_by` accepts a job task id — one id reader (cba607aa0) | `test_bug_resolution_bugs_script.py` |
| J1.S3.T10 | — | close task: test-audit (37 files, gate passed) and mutation 477/559, skip reasons recorded (b4010dfe4) | generated |
| J1.S3.T11 | AC1.3 | REBUILD dead-holds fixtures to the nested grammar; stage S3 red #1 (32777ddc8) | `test_context_dead_holds.py` |
| J1.S3.T12 | AC1.3 | REBUILD orphan-wt fixture onto the task-merge model; stage S3 red #1 (6417b618c) | `test_doctor_fix_lines_clear_their_finding.py` |
| J1.S3.T13 | AC1.9 | re-record the dd-bug-resolution scripts hash after T9; job gate red #1 (caa074803) | `test_behavior_map.py` |
| J1.S3.T14 | AC1.1, AC1.3 | review HIGH 1, MEDIUM 4, MEDIUM 5: task gate drops deleted paths, runs `Owner-tests:` trailer tests, reads the gate line from the job branch (9a991640e, 3ee23a50c) | `test_worktree_lifecycle.py` |
| J1.S3.T15 | AC1.7, AC1.9, AC1.3 | review HIGH 3, HIGH 2 test, MEDIUM 6, LOW 7, LOW 8: `job_gate_runs` in the merge entry, a real job-file row, `_specs.py` through the one grammar (6806b5c70..79cb8e01f; the last commit re-records the hashes T14 moved) | `test_release_script.py`, owner of `_specs.py` |
| J1.S3.T16 | AC1.9 | review HIGH 2 docs: the six job files in the law's grammar, Status Approved (dfb1c4880) | `release.py check` |
| J1.S3.T17 | AC1.9 | `job_errors` reads a task table's `W:` column through `writes()`; the rework close: test-audit and mutation (9eecf14b2, 21fa3d5fd); Reconciliation exempt from the stage-1 tests-only check, its ACs having no test (ADR 0192) | `test_release_script.py` |

- Rework round recorded: the commits subjected J1.S2.T2 (567f13339), T4 (ca0137c51), T5 (19d3b50b3), T6 (d464edb7e) and T9 (d0698dbf7) after the job close (40dca7fc9), and `docs(J1.S2.T2)` 0fb5d7ad0 (quickstart `--kind` fix), answer review findings HIGH 1–2, MEDIUM 3–5; they are S3 rework under S2 ids.
- Carried to Reconciliation: review LOW 12 (trees opened under the one-level grammar lose `[protected]` glob checks; no `[protected]` section in this instance, so no exposure here) and INFO 13 (no §3a commit row for the driver's job-file edits; Job 4 or 5).
