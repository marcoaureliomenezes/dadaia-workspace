# TASKS — 0.5.0 rc-9, Job 4 — the PLAN and the trio validator

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage J4.S1 — RED (AC4.2, AC4.3)

- Contract: exit tests every acceptance test of the ACs served RED as strict xfail; test files only (R10); envelope `tests/contract/test_release_script.py`; ACs AC4.2, AC4.3
- ACs served: AC4.2, AC4.3.
- Envelope: `tests/contract/test_release_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S1.T1 | AC4.2, AC4.3 | `tests/contract/test_release_script.py` | RED: the ACs' acceptance tests · landed 377f6a8b6 |

## Stage J4.S2 — (AC4.1–AC4.3)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`; ACs AC4.1–AC4.3
- ACs served: AC4.1–AC4.3.
- Envelope: `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S2.T1 | AC4.2 | `relimpl/scripts/_release_check.py` | `test_release_script.py` · landed 277348d5b |
| J4.S2.T2 | AC4.3 | `relimpl/scripts/_release_phase.py` | `test_release_script.py` · landed 52a68801f, 24118b6f5 |
| J4.S2.T3 | AC4.2 (the four rows taught and audited) | `public/skills/dd-audit-project/PILLAR-SPECS.md` | no test · landed b1d064f03 |
| J4.S2.T5 | AC4.2 (born: Job 1 review MEDIUM 1) | `relimpl/scripts/_release_schema.py`, `public/skills/dd-release-definition/SKILL.md`, `specs/releases/0.5.0/rc-9/tasks/reconcile.md` | `test_release_script.py`: Reconciliation gets an empty `## Stage JR.S1 — RED (none: AC6.1–AC6.4 have no test)`, work stages from S2; delete the `reconcile.md` exemption, its row pair and the §5 clause · landed 2e0aff354 |
| J4.S2.T6 | AC1.1, AC1.3 (born: Job 1 review LOW 2, LOW 3) | `gitflow/scripts/_worktree_end.py` | `test_worktree_lifecycle.py`: a task touching non-test `.py` with no `Owner-tests:` trailer refuses; the stage gate reads `verify-stage:` from the work branch · landed d6030ebc6..d45482779 |
| J4.S2.T7 | AC4.2 (born: the four trio rows taught) | dd-release-definition SKILL.md §4/§5 (J4.S2.T5's path, see the deviation below); generated: its behavior-map hash | no test (behavior-map hash) · landed 59b4c5ff9, 0d90fea49 |
| J4.S2.T4 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) · landed the `chore(tasks): done job4` commit and the `chore(J4.S2.T4)` close commit |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).
- As-built deviation: J4.S2.T1 also wrote `relimpl/scripts/_release_tree.py` and `relimpl/scripts/_release_schema.py` (outside its stated write set); J4.S2.T6 also wrote `tests/helpers/worktree_ws.py` (the fixture its rows need); J4.S2.T7 wrote `public/skills/dd-release-definition/SKILL.md`, J4.S2.T5's path in the same stage — T5 owns it, the double write is recorded, not repeated.
- done: Job 4 — every task landed on `wt/0.5.0-rc9/job4`; closed by J4.S2.T4.
