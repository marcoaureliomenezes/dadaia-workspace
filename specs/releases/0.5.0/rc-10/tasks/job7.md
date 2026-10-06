# TASKS — 0.5.0 rc-10, Job 7 — the tests tree mirrors the package

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Runs under today's law (before Job 6).

- Edges: Jobs 1, 4, 5 merged (their test files move here). Mirror rule: PLAN agent default 6; markers: agent default 7.
- AC7.2: every move is `git mv` plus merge, one feature per commit, no assert changed; check at the job gate: `git grep -h '^\s*assert' <base> -- tests | sort`, `<base>` the commit closing J7.S2, equals the same at HEAD.

## Stage J7.S1 — RED

- Contract: exit tests the AC7.3 rows RED as strict xfail; envelope `tests/test_conftest_size.py`; ACs AC7.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S1.T1 | AC7.3 | `tests/test_conftest_size.py` (pytester; moves to `tests/fixtures/` in J7.S4.T2) | RED: a test using a real-git fixture collects `medium`, a pure one `small`, wherever its folder |

## Stage J7.S2 — size from the fixture; the guard

- Contract: exit: J7.S1 green, the stage gate (lint, mypy, guards, small) green; envelope `tests/conftest.py`, `tests/unit/conftest.py`, `pyproject.toml`, `scripts/ci.py`, `scripts/guards/suite.py`, `scripts/guards/run.py`, `.github/workflows/ci.yml`, `tests/AGENTS.md` (`:21-27`, the tier text), `tests/README.md`, `tests/integration/test_ci_script.py`, `tests/contract/test_release_script.py`; ACs AC7.3, AC7.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S2.T1 | AC7.3 | `tests/conftest.py` (`_PATH_MARKERS` leaves; size from the fixtures an item requests; `tests/unit/conftest.py`'s autouse moves here for `small` items, agent default 8), `tests/unit/conftest.py` (deleted), `pyproject.toml` (markers `small`, `medium`, `windows` added; `unit`, `contract`, `integration` stay registered as inert aliases until the last move), `scripts/guards/suite.py`, `scripts/guards/run.py` (the tier checks and the probe read the size marker, not the folder) | `test_conftest_size.py` |
| J7.S2.T3 | AC7.3 | `tests/AGENTS.md` (`:21-27`: size from the fixture, never the folder), `tests/README.md` (the run commands), `pub/data/worktrees-AGENTS.md` (`:20`, the stage gate: lint, mypy, guards, small; closing line `stage: <id> — small green`), `pub/skills/dd-gitflow-default/SKILL.md` (`:65`, the same closing line) (Amends ADR 0190, stage level, by operator order 2026-10-06), `pub/entities/behavior-map.json` (the two hash tuples those law edits stale) | no test |
| J7.S2.T4 | AC7.2 | `tests/contract/test_release_script.py` (the repo-root expression hoisted to one module constant, so the move leaves its assert line untouched) | `tests/contract/test_release_script.py` |
| J7.S2.T2 | AC7.3, AC7.4 | `scripts/ci.py`, `.github/workflows/ci.yml` (the stage level drops the integration job: lint, typecheck, guards, the small tier; select by marker, not folder; the Windows and macOS legs select `not e2e and not quarantine` and list the `windows-integration-coverage-gap` cases by marker), `tests/integration/test_ci_script.py` (its planted tests carry the new marker) | `tests/integration/test_ci_script.py`; check: the Windows job log lists them |

## Stage J7.S3 — the moves, one feature per task

- Contract: exit: the stage gate (lint, mypy, guards, small) green; AC7.2's assert check equal; every core, feature, cli, hooks and infrastructure test moved (the skills, scripts and suite tests move in J7.S4, after which no `tests/{unit,contract,integration}/` is left); envelope `tests/**`, `scripts/guards/*.py` (path literals), `pyproject.toml`; ACs AC7.1, AC7.2
- One task per top-level owner, disjoint by construction; a test naming two owners goes to the one its asserts exercise; `test_docs_derived_from_memory.py` stays (rc-13).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S3.T1 | AC7.1, AC7.2 | `tests/core/**` (moved from today's tiers) | moved files |
| J7.S3.T2 | AC7.1, AC7.2 | `tests/features/spec_context/**` (moved from today's tiers); `tests/conftest.py` (the worktree-rows bridge covers every test that reaches git but no process: two tests that were `unit` import `real_git`, so they are `medium`, and read the real rows without it) | moved files |
| J7.S3.T3 | AC7.1, AC7.2 | `tests/features/specs/**` (moved from today's tiers) | moved files |
| J7.S3.T4 | AC7.1, AC7.2 | `tests/features/<f>/**` for every other feature (moved from today's tiers); `tests/unit/features/specs/test_doctor_ledger_invariants.py` deleted (empty file) | moved files |
| J7.S3.T5 | AC7.1, AC7.2 | `tests/cli/**`, `tests/hooks/**`, `tests/infrastructure/**`, `tests/test_container.py`, `tests/fixtures/_store_contract.py` (moved from today's tiers); `tests/integration/conftest.py` deleted (its one fixture is requested by no test) | moved files |
| J7.S3.T6 | AC7.1 | `scripts/guards/slop.py` (the `parity:` pins `:45-65` and the two imports `:86-87` name the new paths; runs after T1-T5 so the stage's guards pass) | guard plants |

## Stage J7.S4 — the skills, scripts and suite tests

- Contract: as J7.S3; envelope `tests/**`, `scripts/guards/*.py`, `pub/data/CONTEXT-MAP.md`; ACs AC7.1, AC7.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S4.T1 | AC7.1, AC7.2 | `tests/public/**` (moved from today's tiers); `scripts/guards/slop.py` (the three `parity:` pins naming a skill-script test), `tests/core/test_workspace_layout.py` (its `_PARITY` string equals the `_ledger.py` pin) | moved files |
| J7.S4.T2 | AC7.1, AC7.2 | `tests/scripts/**`, `tests/fixtures/test_*.py`, `tests/fixtures/statement_ids.json` (moved from today's tiers); `tests/contract/README.md` and the empty `tests/unit/features/specs/test_doctor_ledger_invariants.py` (J7.S3.T4 did not delete it) deleted; the planted tests of `tests/scripts/test_ci.py` drop their transitional `unit` marker | moved files |
| J7.S4.T3 | AC7.1 | `pyproject.toml` (the `unit`, `contract`, `integration` aliases leave with the last move), `tests/contract/test_docs_derived_from_memory.py` (its alias marker line), `scripts/guards/suite.py` (`statement_ids.json` path), `pub/data/CONTEXT-MAP.md` (`:5`), `pub/scaffold/memory/QUALITY.md` (`:20-21`, ADR 0167), `pub/templates/shipped-hashes.json` (the new stub digests, append-only), the source comments naming a moved test (`f/specs/canon.py`, `f/specs/doctor.py`, `core/spec_status.py`, `core/release_state.py`, `core/doctor_rules.py`, `infrastructure/runtime_transforms/codex_assets.py`, `f/specs/citations.py`) (path literals of moved files) | guard plants |

## Stage J7.S5 — the mirror guard; close

- Contract: exit: the stage gate (lint, mypy, guards, small) green; the guard red on its plants, green on the tree; envelope `scripts/guards/repo.py`, the six e2e journeys without an `Owner:` line, this file; ACs AC7.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S5.T1 | AC7.1 | `tests/e2e/test_push_denylist_journey.py`, `tests/e2e/test_one_line_bootstrap.py`, `tests/e2e/test_push_gate_check.py`, `tests/e2e/features/test_specs_upgrade_e2e.py`, `tests/e2e/features/test_public_pipeline.py`, `tests/e2e/features/test_ctx_inject_bind_boundary.py` (an `Owner:` docstring line), `scripts/guards/repo.py` (check `tests-mirror-the-package`, after every move: red on a planted loose file and on an empty test directory) | guard plants |
| J7.S5.T2 | — | this file | close task, last: behavior map; `test-audit:` names `test_conftest_size.py` (moves otherwise, asserts unchanged), `mutation:`; `done` |
