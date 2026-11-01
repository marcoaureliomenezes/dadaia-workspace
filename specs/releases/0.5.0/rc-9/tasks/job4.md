# TASKS — 0.5.0 rc-9, Job 4 — the PLAN and the trio validator

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

- Merge order: Job 4's envelope overlaps Jobs 2 and 3 on shared files, so the merge order is Job 3 → Job 4 → Job 2.

## Stage J4.S1 — RED (AC4.2, AC4.3)

- Contract: exit tests every acceptance test of the ACs served RED as strict xfail; test files only (R10); envelope `tests/contract/test_release_script.py`; ACs AC4.2, AC4.3
- ACs served: AC4.2, AC4.3.
- Envelope: `tests/contract/test_release_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S1.T1 | AC4.2, AC4.3 | `tests/contract/test_release_script.py` | RED: the ACs' acceptance tests · landed 9feeae3b5 |

## Stage J4.S2 — (AC4.1–AC4.3)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `relimpl/scripts/_release_schema.py`, `relimpl/scripts/_release_tree.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `gitflow/scripts/_worktree_end.py`; ACs AC4.1–AC4.3
- ACs served: AC4.1–AC4.3.
- Envelope: `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `relimpl/scripts/_release_schema.py`, `relimpl/scripts/_release_tree.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `gitflow/scripts/_worktree_end.py`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S2.T1 | AC4.2 | `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_tree.py`, `tests/contract/test_release_script.py` | `test_release_script.py` · landed 164efe6c5 |
| J4.S2.T2 | AC4.3 | `relimpl/scripts/_release_phase.py` | `test_release_script.py` · landed 1469bb67e, c02fd7db2 |
| J4.S2.T3 | AC4.2 (the four rows taught and audited) | `public/skills/dd-audit-project/PILLAR-SPECS.md` | no test · landed 38206fef0 |
| J4.S2.T5 | AC4.2 (born: Job 1 review MEDIUM 1) | `relimpl/scripts/_release_schema.py`, `specs/releases/0.5.0/rc-9/tasks/reconcile.md` | `test_release_script.py`: Reconciliation gets an empty `## Stage JR.S1 — RED (none: AC6.1–AC6.4 have no test)`, work stages from S2; delete the `reconcile.md` exemption · landed 1a4deb88a |
| J4.S2.T6 | AC1.1, AC1.3 (born: Job 1 review LOW 2, LOW 3) | `gitflow/scripts/_worktree_end.py`, `public/data/worktrees-AGENTS.md`, `public/entities/behavior-map.json`, `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py` | `test_worktree_lifecycle.py`: a task touching non-test `.py` with no `Owner-tests:` trailer refuses; the stage gate reads `verify-stage:` from the work branch · landed 174bf1029..c5891cf84 |
| J4.S2.T7 | AC4.2 (born: the four trio rows taught) | `public/skills/dd-release-definition/SKILL.md` | no test (behavior-map hash) · landed 0d23fbdb4, 8b32912d9 |
| J4.S2.T8 | AC4.3 | `tests/helpers/release_state.py` | unit PLAN fixtures carry the DAG and hot files · landed cbec844f3 |
| J4.S2.T4 | — | `specs/releases/0.5.0/rc-9/tasks/job4.md` | close task: test-audit + mutation-diff (Q23), `done` (Q9) · landed 350b0522a, 181a02bdf, 1dcf73560 |
- Co-writes as built (one owner per path above; these tasks also touched it, sequentially): `relimpl/scripts/_release_schema.py` also by J4.S2.T1; `public/skills/dd-release-definition/SKILL.md` also by J4.S2.T5; `tests/contract/test_release_script.py` also by J4.S2.T2 and J4.S2.T5; `public/entities/behavior-map.json` also by J4.S2.T5 and J4.S2.T7 (hash re-records).

## Stage J4.S3 — review rework (AC4.2, AC4.3)

- Contract: exit tests the re-review's findings closed by RED-first rows; owner tests green at the task gates; envelope `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `relimpl/scripts/_release_schema.py`, `gitflow/scripts/_worktree_end.py`; ACs AC4.2, AC4.3
- ACs served: AC4.2, AC4.3.
- Envelope: `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `relimpl/scripts/_release_schema.py`, `gitflow/scripts/_worktree_end.py`.
- Exit tests: the re-review's findings closed by RED-first rows; owner tests green at the task gates.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S3.T1 | AC4.2, AC4.3 | `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `relimpl/scripts/_release_schema.py`, `specs/releases/0.5.0/rc-9/tasks/job1.md`, `tests/contract/test_release_script.py` | `test_release_script.py`: an empty DAG and a root file written twice in a stage refuse · landed 3e41db5bb, 1d95b6b6a, 6434a6354, bf1752afb |
| J4.S3.T2 | AC1.1, AC1.3 | `gitflow/scripts/_worktree_end.py`, `public/entities/behavior-map.json`, `tests/integration/test_worktree_lifecycle.py` | `test_worktree_lifecycle.py`: a code task whose touched `test_` file feeds its gate lands · landed 8472f2c1f, 8bf4d6695, 923d429a3 |
| J4.S3.T3 | — | `specs/releases/0.5.0/rc-9/tasks/job4.md` | close task: true `W:` paths, test-audit + mutation-diff over the job range |
- Co-writes as built: `public/entities/behavior-map.json` also by J4.S3.T1 (hash re-records).
- done: Job 4 — every task landed on `wt/0.5.0-rc9/job4`; closed by J4.S3.T3.
