# TASKS — 0.5.0 rc-9, Job 5 — the bugs law and the closed rc

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage J5.S1 — RED (AC5.6, AC5.7)

- Contract: exit tests every acceptance test of the ACs served RED as strict xfail; test files only (R10); envelope `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`; ACs AC5.6, AC5.7
- ACs served: AC5.6, AC5.7.
- Envelope: `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J5.S1.T1 | AC5.6 | `tests/unit/skills/test_release_implementation_release_script.py` | RED: `test_an_rc_spec_opens_with_the_bug_window_review` | f397daa79 |
| J5.S1.T2 | AC5.7 | — (void: AC5.7's unit is met by the existing AC12.12 row of the `bugs.py fix` test) | — | — |

## Stage J5.S2 — code and law (AC5.1–AC5.9)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `relimpl/scripts/_release_new.py`, `_release_check.py`, `bugres/scripts/bugs.py`, `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`, `public/scaffold/releases/AGENTS.md`, `public/scaffold/ADRs/AGENTS.md`, `relimpl/SKILL.md`, `gitflow/SKILL.md`, `CONTEXT.md`, `public/skills/dd-code-review/SKILL.md`; ACs AC5.1–AC5.9
- ACs served: AC5.1–AC5.9.
- Envelope: `relimpl/scripts/_release_new.py`, `_release_check.py`, `bugres/scripts/bugs.py`, `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`, `public/scaffold/releases/AGENTS.md`, `public/scaffold/ADRs/AGENTS.md`, `relimpl/SKILL.md`, `gitflow/SKILL.md`, `CONTEXT.md`, `public/skills/dd-code-review/SKILL.md`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J5.S2.T1 | AC5.6 | `relimpl/scripts/_release_new.py`, `relimpl/scripts/_release_tree.py` (the check lives beside the other live-candidate checks; `_release_check.py` unchanged), `tests/unit/skills/test_release_implementation_release_script.py`, `tests/contract/test_release_script.py`, `tests/helpers/worktree_ws.py`, `tests/integration/test_shallow_history_fix_line_clears.py`, `public/entities/behavior-map.json` | `test_release_implementation_release_script.py` | 529adf0b4, 5777e2a73, 0b4bbb1c7, ba22194e3 |
| J5.S2.T2 | AC5.7 | — (void: `bugs.py fix` already links `refactor(bugs): <id> — REBUILD`, AC12.12) | — | — |
| J5.S2.T3 | AC5.1–AC5.4 | `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`, `public/entities/behavior-map.json` | no test | 27167dd0a, c4da3a10a |
| J5.S2.T4 | AC5.5 | `public/scaffold/releases/AGENTS.md`, `relimpl/SKILL.md`, `public/entities/behavior-map.json`; `public/scaffold/ADRs/AGENTS.md` untouched: AC5.5 states nothing the ADR law owns | no test | 455c17436, f12fb9536 |
| J5.S2.T5 | AC5.7 (§3a) | `gitflow/SKILL.md`, `public/entities/behavior-map.json` | no test | b9e3a0ce5, 9fae6422d |
| J5.S2.T6 | AC5.8 | `CONTEXT.md` | no test | ae69acafa |
| J5.S2.T7 | AC5.9 | `public/skills/dd-code-review/SKILL.md`, `public/entities/behavior-map.json` (no other public file carried `<bug-id>#<id>`) | no test | 13a4395a5, 7390de3e4 |
| J5.S2.T9 | AC5.2, AC5.4 (born at T3) | `public/templates/specs-AGENTS.md`, `public/data/worktrees-AGENTS.md`, `public/entities/behavior-map.json`: the two restatements become pointers to the bugs law §2 | no test | 491773802, 4a0b77faf |
| J5.S2.T10 | — (born: the law changes move the canon) | `core/specs_version.py`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py`; this repo's `specs/constitution.md`, `specs/bugs/AGENTS.md`, `specs/releases/AGENTS.md` by `specs upgrade` | `test_specs_version.py`, `test_tree5_shipped_history.py` | b9de7cd09, 8e211d445 |
| J5.S2.T8 | — | this file | close task: test-audit + mutation evidence | this commit, the close commit |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).

## Operator rulings (2026-10-05, AskUserQuestion)

- ADRs 0193 and 0201–0205 accepted, "Aceito as seis (Recommended)" (d47d276ea).
- AC5.7's unit: met by the AC12.12 row; J5.S1.T2 and J5.S2.T2 void.

## Stage J5.S3 — review rework (the Job 5 REJECTED review)

- Contract: exit tests the touched owner tests green at the task gates; unit + integration green at the stage gate; envelope the J5.S2 envelope plus `public/skills/dd-release-definition/SKILL.md`, `public/skills/dd-audit-project/PILLAR-SPECS.md`, `public/data/AGENTS.md`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py`; findings the Job 5 review HIGH 1–3, MEDIUM 1–3, LOW 1, LOW 3
- The J5.S2.T8 close (a5aefb60b) stays in history; this stage's close supersedes it.

| task | finding | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J5.S3.T1 | HIGH 1, HIGH 2, MEDIUM 1, LOW 3 (skills) | `gitflow/SKILL.md`, `public/skills/dd-release-definition/SKILL.md`, `public/skills/dd-audit-project/PILLAR-SPECS.md`, `bugres/SKILL.md`, `public/entities/behavior-map.json` | no test | 94e114580, 4cd61544c |
| J5.S3.T2 | MEDIUM 2, MEDIUM 3, LOW 3; canon 11 re-pin; `specs upgrade` | `public/scaffold/bugs/AGENTS.md`, `public/scaffold/releases/AGENTS.md`, `CONTEXT.md`, `public/data/AGENTS.md`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py`, `public/entities/behavior-map.json`; this repo's `specs/bugs/AGENTS.md`, `specs/releases/AGENTS.md` by `specs upgrade` | `test_specs_version.py`, `test_tree5_shipped_history.py` | 690c0e75f, c9afa653b, bd08719a7, 073c7ec63 |
| J5.S3.T3 | HIGH 3 (the AC5.6 check scoped per phase inside `_origin_findings`, the operator's ruling on its precedent), LOW 1 | `relimpl/scripts/_release_tree.py`, `tests/unit/skills/test_release_implementation_release_script.py` (REBUILD of the AC5.6 tests), `tests/contract/test_release_script.py` (fixture line), `public/entities/behavior-map.json` | `test_release_implementation_release_script.py`, `test_release_script.py` | d391ca8bf, 39b5f47f2, e17dabb1e |
| J5.S3.T4 | — | this file | close task: test-audit + mutation evidence | this commit, the close commit |

- Done: Job 5 closed by J5.S3.T4 (2026-10-05), superseding the J5.S2.T8 close.
