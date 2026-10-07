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

## Stage J7.S5 — the mirror guard

- Contract: exit: the stage gate (lint, mypy, guards, small) green; the guard red on its plants, green on the tree; envelope `scripts/guards/repo.py`, the six e2e journeys without an `Owner:` line, `tests/fixtures/test_conftest_size.py`, `scripts/guards/run.py`, `tests/scripts/test_ci.py`; ACs AC7.1, AC7.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S5.T1 | AC7.1 | `tests/test_conftest_size.py` (moved by `git mv` into tests/fixtures, as J7.S1.T1 announced; J7.S5.T3 writes the moved file), `tests/e2e/test_push_denylist_journey.py`, `tests/e2e/test_one_line_bootstrap.py`, `tests/e2e/test_push_gate_check.py`, `tests/e2e/features/test_specs_upgrade_e2e.py`, `tests/e2e/features/test_public_pipeline.py`, `tests/e2e/features/test_ctx_inject_bind_boundary.py` (an `Owner:` docstring line), `scripts/guards/repo.py` (check `tests-mirror-the-package`, after every move: red on a planted loose file and on an empty test directory) | guard plants |
| J7.S5.T3 | AC7.3 | `scripts/guards/run.py` (one docstring line over 100 columns), `tests/fixtures/test_conftest_size.py` (one string over 100 columns), `tests/scripts/test_ci.py` (two parametrize rows: the `integration` job selects the medium tests; its asserts unchanged) | `tests/scripts/test_ci.py` |

## Stage J7.S6 — coverage over small and medium; close

- Contract: exit: the stage gate (lint, mypy, guards, small) green; `ci.py contract-coverage` green at its 80 % bar; envelope `scripts/ci.py`, `.github/workflows/ci.yml`, `scripts/guards/repo.py`, this file; ACs AC7.3, AC7.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S6.T1 | AC7.3 | `scripts/ci.py` (`contract-coverage` selects `not e2e and not quarantine`: the 80 % bar measured 69.99 % over the small tier alone, so the job covers small and medium as the Windows and macOS legs do) | `tests/scripts/test_ci.py` |
| J7.S6.T3 | AC7.4 | `.github/workflows/ci.yml` (unit-fast `timeout-minutes` 2 becomes 4, contract-coverage 5 becomes 20, integration 6 becomes 10, the two Windows and macOS legs 8 become 20 (they now run small and medium; the last feature run took 394 s on Windows for the contract leg, and `not e2e` took 6 to 10 minutes here with coverage)) | `tests/scripts/test_ci.py` |
| J7.S6.T4 | AC7.1 | `scripts/guards/repo.py` (`_mirror_key` drops a `-` to `_` replace no test path can reach: the hand mutant survived) | guard plants |
| J7.S6.T2 | — | this file | close task, last: `test-audit:` names `tests/fixtures/test_conftest_size.py` (moves otherwise, asserts unchanged), `mutation:`; `done` |

## Stage J7.S7 — the Windows legs after CI run 37543869150

- Contract: exit: the stage gate (lint, mypy, guards, small) green; the Windows legs select `(small or windows)`, macOS `not e2e`; envelope `.github/workflows/ci.yml`, the two quarantined test files; ACs AC7.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S7.T1 | AC7.4 | `.github/workflows/ci.yml` (the Windows legs select `(small or windows)`, macOS keeps `not e2e`: CI run 37543869150 failed only on Windows, in former integration tests never run there; the unit-fast leg's `timeout-minutes` back to 8, the coverage leg stays 20 for macOS's 468 s) | `tests/scripts/test_ci.py` |
| J7.S7.T2 | AC7.4 | `tests/core/test_invocation__one_bind.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (a `quarantine(bug=...)` marker on the two `windows` cases: CI run 37546529916 failed only there; bugs `orphan-worktree-line-absent-from-the-bind-block-on-windows` and `worktree-script-run-fails-winerror-193-on-windows`, operator ruling 2026-10-06) | the two files |

## Stage J7.S8 — the AC7.4 listing step lists, it does not run

- Contract: exit: the stage gate (lint, mypy, guards, small) green; the Windows legs listing step exits 0 when its selection is empty; envelope `.github/workflows/ci.yml`; ACs AC7.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S8.T1 | AC7.4 | `.github/workflows/ci.yml` (the listing step collects `-m windows` with `--collect-only`: the quarantined cases are excluded from the run, and pytest exits 5 when a selection is empty; the Windows log still lists them) | `tests/scripts/test_ci.py` |

- done: Job 7 — every task landed on `wt/0.5.0-rc10/job7` through its task merge: J7.S1.T1 a779ae604 (the AC7.3 rows, strict xfail); J7.S2.T1 6053a0e31 (size from what a module reaches, the autouse bridge, the suite guards), J7.S2.T4 c7e6d6f4f (the repo-root constant, before the AC7.2 base), J7.S2.T2 5577dffb9 (selectors by marker, the stage level without the integration job), J7.S2.T3 4bac0be82 (tests/AGENTS.md, README, the two stage-gate law lines, ADR 0167 and ADR 0190); J7.S3.T1 319d9a51b, T2 0feb4da9c and fe6065358 (the bridge also covers git-only medium tests), T3 efe0a2ed5, T4 378edd2c5 .. 148a78e61 (one commit per feature), T5 ad594ce80 .. ee4fa603e, T6 7a4fe40d7; J7.S4.T1 03f31b2c7 .. e1f110797 (one commit per skill), T2 458271228 and f2822ad00, T3 70b338d60 (the scaffold QUALITY.md law line cites ADR 0167; shipped-hashes.json appends its stub digests; `specs/memory/**` citations of moved tests stay for the reconcile job: rewriting them re-stales the README, llms.txt and docs derived-from hashes); J7.S5.T1 b082c3278 (`tests-mirror-the-package`: red on a loose test, an empty directory and an e2e journey without `Owner:`), T3 b0ee17031; J7.S6.T1 b15c3b805 (`contract-coverage` over small and medium: 83.53 % against 69.99 % over small alone), T3 b86bf2864 (timeouts), T4 06eaac50e, J7.S7.T1 221ba0bd3 (the Windows legs select small or windows after CI run 37543869150 failed only there), J7.S7.T2 3f02b7545 (the two windows cases quarantined after CI run 37546529916: bugs orphan-worktree-line-absent-from-the-bind-block-on-windows and worktree-script-run-fails-winerror-193-on-windows, registered in ef3416a1d and 1859b9665), J7.S8.T1 50ab0bbc0 (the listing step tolerates exit 5). AC7.2: `git grep -h '^\s*assert' <base> -- 'tests/*.py' | sort` equals the same at HEAD, `<base>` 4bac0be82 the commit closing J7.S2; the hoist c7e6d6f4f precedes it. Agent defaults, unruled (operator decisions 1-5 of 2026-10-06 stand): the suffix rule `test_<m>__<old stem>.py` and three merges; size per module by the seams it reaches; the `windows` marker on three cases; `not e2e` selection on the cross legs and the coverage job; timeouts raised. Bug surface of the touched feature (the test tiers and their ceilings): shrinks. The two prior ceiling bugs, `windows-xdist-workers-crash-on-unit-fast-tier` and `tier-ceiling-trips-under-coverage-instrumentation-on-windows-contract-coverage-job`, both resolved, live in the one calibration `tier_timeout_seconds`, which this job leaves as it was; the folder-to-tier table, the `contract` ceiling, `tests/unit/conftest.py`, `tests/integration/conftest.py` (a dead fixture), an empty test file and a README naming ghost files are deleted, and the one new predicate `_size` has hand mutants killed by its owner test.

