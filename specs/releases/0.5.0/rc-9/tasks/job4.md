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
| J4.S1.T1 | AC4.2, AC4.3 | `tests/contract/test_release_script.py` | RED: the ACs' acceptance tests |

## Stage J4.S2 — (AC4.1–AC4.3)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`; ACs AC4.1–AC4.3
- ACs served: AC4.1–AC4.3.
- Envelope: `relimpl/scripts/_release_check.py`, `relimpl/scripts/_release_phase.py`, `public/skills/dd-audit-project/PILLAR-SPECS.md`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S2.T1 | AC4.2 | `relimpl/scripts/_release_check.py` | `test_release_script.py` |
| J4.S2.T2 | AC4.3 | `relimpl/scripts/_release_phase.py` | `test_release_script.py` |
| J4.S2.T3 | AC4.2 (the four rows taught and audited) | `public/skills/dd-audit-project/PILLAR-SPECS.md` | no test |
| J4.S2.T4 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).
