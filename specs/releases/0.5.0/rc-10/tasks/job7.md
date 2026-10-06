# TASKS — 0.5.0 rc-10, Job 7 — the tests tree mirrors the package

**Status:** Approved — by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Runs under today's law (before Job 6).

- Edges: Jobs 1, 4, 5 merged (their test files move here). Mirror rule: PLAN agent default 6; markers: agent default 7.
- AC7.2: every move is `git mv` plus merge, one feature per commit, no assert changed; check at the job gate: `git grep -h '^\s*assert' <base> -- tests | sort`, `<base>` the commit closing J7.S2, equals the same at HEAD.

## Stage J7.S1 — RED

- Contract: exit tests the AC7.3 rows RED as strict xfail; envelope `tests/test_conftest_size.py`; ACs AC7.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S1.T1 | AC7.3 | `tests/test_conftest_size.py` (pytester; moves to `tests/fixtures/` in J7.S4.T2) | RED: a test using a real-git fixture collects `medium`, a pure one `small`, wherever its folder |

## Stage J7.S2 — size from the fixture; the guard

- Contract: exit tests J7.S1 green, unit + integration green; envelope `tests/conftest.py`, `tests/unit/conftest.py`, `pyproject.toml`, `scripts/ci.py`, `.github/workflows/ci.yml`, `tests/AGENTS.md` (`:21-27`, the tier text); ACs AC7.3, AC7.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S2.T1 | AC7.3 | `tests/conftest.py` (`_PATH_MARKERS` leaves; size from the fixtures an item requests; `tests/unit/conftest.py`'s autouse moves here for `small` items, agent default 8), `tests/unit/conftest.py` (deleted), `pyproject.toml` (markers) | `test_conftest_size.py` |
| J7.S2.T3 | AC7.3 | `tests/AGENTS.md` (`:21-27`: size from the fixture, never the folder) | no test |
| J7.S2.T2 | AC7.3, AC7.4 | `scripts/ci.py`, `.github/workflows/ci.yml` (select by marker, not folder; the Windows job selects the `windows-integration-coverage-gap` cases by marker) | `tests/integration/test_ci_script.py`; check: the Windows job log lists them |

## Stage J7.S3 — the moves, one feature per task

- Contract: exit tests unit + integration + e2e green; AC7.2's assert check equal; no `tests/{unit,contract,integration}/` left; envelope `tests/**`, `scripts/guards/*.py` (path literals), `pyproject.toml`; ACs AC7.1, AC7.2
- One task per top-level owner, disjoint by construction; a test naming two owners goes to the one its asserts exercise; `test_docs_derived_from_memory.py` stays (rc-13).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S3.T1 | AC7.1, AC7.2 | `tests/core/**` (moved from today's tiers) | moved files |
| J7.S3.T2 | AC7.1, AC7.2 | `tests/features/spec_context/**` (moved from today's tiers) | moved files |
| J7.S3.T3 | AC7.1, AC7.2 | `tests/features/specs/**` (moved from today's tiers) | moved files |
| J7.S3.T4 | AC7.1, AC7.2 | `tests/features/<f>/**` for every other feature (moved from today's tiers) | moved files |
| J7.S3.T5 | AC7.1, AC7.2 | `tests/cli/**`, `tests/hooks/**`, `tests/infrastructure/**` (moved from today's tiers) | moved files |

## Stage J7.S4 — the skills, scripts and suite tests

- Contract: as J7.S3; envelope `tests/**`, `scripts/guards/*.py`, `pub/data/CONTEXT-MAP.md`; ACs AC7.1, AC7.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S4.T1 | AC7.1, AC7.2 | `tests/public/**` (moved from today's tiers) | moved files |
| J7.S4.T2 | AC7.1, AC7.2 | `tests/scripts/**`, `tests/fixtures/test_*.py` (moved from today's tiers) | moved files |
| J7.S4.T3 | AC7.1 | `scripts/guards/isolation.py`, `scripts/guards/suite.py`, `scripts/guards/slop.py`, `scripts/guards/run.py` (`:64`), `pub/data/CONTEXT-MAP.md` (`:5`) (path literals of moved files) | guard plants |

## Stage J7.S5 — the mirror guard; close

- Contract: exit tests unit + integration + e2e green; the guard red on its plants, green on the tree; envelope `scripts/guards/repo.py`, this file; ACs AC7.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J7.S5.T1 | AC7.1 | `scripts/guards/repo.py` (check `tests-mirror-the-package`, after every move: red on a planted loose file and on an empty test directory) | guard plants |
| J7.S5.T2 | — | this file | close task, last: behavior map; `test-audit:` names `test_conftest_size.py` (moves otherwise, asserts unchanged), `mutation:`; `done` |
