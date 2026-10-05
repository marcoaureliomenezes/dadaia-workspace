# TASKS — 0.5.0 rc-9, Job 5 — the bugs law and the closed rc

**Status:** Draft

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## S1 — RED (AC5.6, AC5.7)

- ACs served: AC5.6, AC5.7.
- Envelope: `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J5.S1.T1 | AC5.6 | `tests/unit/skills/test_release_implementation_release_script.py` | RED: the ACs' acceptance tests |
| J5.S1.T2 | AC5.7 | `tests/unit/skills/test_bug_resolution_bugs_script.py` | RED: the ACs' acceptance tests |

## S2 — code and law (AC5.1–AC5.9)

- ACs served: AC5.1–AC5.9.
- Envelope: `relimpl/scripts/_release_new.py`, `_release_check.py`, `bugres/scripts/bugs.py`, `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`, `public/scaffold/releases/AGENTS.md`, `public/scaffold/ADRs/AGENTS.md`, `relimpl/SKILL.md`, `gitflow/SKILL.md`, `CONTEXT.md`, `public/skills/dd-code-review/SKILL.md`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J5.S2.T1 | AC5.6 | `relimpl/scripts/_release_new.py`, `_release_check.py` | `test_release_implementation_release_script.py` |
| J5.S2.T2 | AC5.7 | `bugres/scripts/bugs.py` | `test_bug_resolution_bugs_script.py` |
| J5.S2.T3 | AC5.1–AC5.4 | `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md` | no test |
| J5.S2.T4 | AC5.5 | `public/scaffold/releases/AGENTS.md`, `public/scaffold/ADRs/AGENTS.md`, `relimpl/SKILL.md` | no test |
| J5.S2.T5 | AC5.7 (§3a) | `gitflow/SKILL.md` | no test |
| J5.S2.T6 | AC5.8 | `CONTEXT.md` | no test |
| J5.S2.T7 | AC5.9 | `public/skills/dd-code-review/SKILL.md` | no test |
| J5.S2.T8 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) |
