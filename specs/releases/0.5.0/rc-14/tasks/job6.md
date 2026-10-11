# Job 6 — dev loop: dead ci.py code, ci.py --changed, v33 deleted, the diet list, two CI bugs (FR9, FR10)

**Status:** Draft

Wave 1. Jobs 1 and 15 edit `scripts/guards/slop.py` and `tests/infrastructure/test_privacy_check.py` later; this job deletes v33 and fixes the bytecode assertion, and leaves the V32 ceilings and the public-law guard line to Job 15 (they can only be lowered or added once the skill jobs have deleted their hits).

- v33 is DELETED, not scoped (the operator allowed deletion if it never caught real slop): with the ceiling at 0 it reports 31 orphan families with `specs/` and 21 without it, all noise (`ADR`, `SHA`, `UTF`, `B`, `C`, `D`); the ledger holds one bug on it. It leaves with `V33_ORPHANS`, its plants and `tests/scripts/guards/test_slop.py` (50 lines, a duplicate of `--planted`).
- `scripts/impact.py` is a developer read, called only by `ci.py --changed`; no gate, no `verify:` line and no CI job calls it (AC10.2).
- The diet list is closed and measured: `test_python_env__honesty_residue.py` (32 lines, whole file), `tests/features/specs/test_rules.py:74-79`, `test_service__service_harness_profile.py:67-74`, `test_docs_derived_from_memory.py` down to `test_the_cli_reference_is_the_committed_output_of_the_generator` (187 to about 36 lines). The entity-doctor test of the list leaves with Job 7. The other items of AC9.1 (conftest duplicates, mutation wiring, repo scan, hygiene) no longer exist at HEAD (`git ls-files | grep -iE 'mutation|mutmut|suite_cannot_reach|repo_self_scan|source_repo_hygiene'` prints nothing); each deletion commit names the check that still catches what it caught.
- AC9.4: the bytecode assertion judges tracked files (`git ls-files`), not the working tree; the shipped contract stays the build exclude. AC9.5: the six lines leave; the first Windows/macOS PR run is the GREEN evidence, and any defect it exposes is proposed as a bug, never masked (ADR 0220 P5).
- Test-side first: T1, T2, T7; then T3, T4, T8 after their tests; T5, T6 any time. T7 and T8 edit one file: T8 runs after T7.
- Commit bodies carry the grep and its count for each deletion: `git grep -n -E 'PYTHONUTF8|PYTHONIOENCODING' -- .github` (6, then 0); `git grep -n 'v33' -- scripts tests` (then 0 outside the memory atom the Reconciliation edits); the tests deleted by line count.
- Net lines: dev production code about −13 (deletes: `ci.py` dead code 21, v33 about 64, `ci.yml` 6; adds: `impact.py` about 70, `--changed` about 8), tests about −300. The `impact.py` ADD cannot shrink the feature; the operator ordered it.
- Pre-review checklist: one `ci.py` job level (no second path), no cross-component import (`impact.py` is run as a script), sweep lines above with counts, no platform fact, net lines as stated.

Tasks: 8 (4 jr, 4 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J6.T1 | sr | AC10.1 | `tests/scripts/test_impact.py` | RED, integration: in a temporary git repo with a package and tests, `ci.py --changed` lists every test file that imports, transitively, a changed module, runs them, and names each changed file the import graph cannot map; a skill-script change maps to `tests/public/skills/<skill>/` by directory. New file, owner `test_impact.py` |
| J6.T2 | sr | AC9.2 | `tests/scripts/test_ci.py` | RED, integration: `ci.py task <file>` and `ci.py stage` are unknown jobs (exit non-zero); `ci.py job` runs lint, typecheck, guards and unit-fast, in that order. Owner `test_ci.py` |
| J6.T3 | sr | AC9.2, AC10.1 | `scripts/ci.py`, `scripts/impact.py` | delete `_task`, the `task` branch and the `stage` alias of `plan`, `STAGE`'s extra name and the docstring lines; add `--changed` calling `impact.py` (ast import graph over the package and tests, the mirrored-directory rule for skill-script tests; stdlib only). Owners T1, T2 |
| J6.T4 | jr | AC9.3 | `scripts/guards/slop.py`, `tests/scripts/guards/test_slop.py` | delete `v33`, its helpers, `V33_ORPHANS`, its plants and the guard test. Owner `python scripts/guards/run.py` and `--planted` exit 0 |
| J6.T5 | jr | AC9.1 | `tests/infrastructure/test_python_env__honesty_residue.py`, `tests/features/specs/test_rules.py`, `tests/features/workspace/test_service__service_harness_profile.py`, `tests/contract/test_docs_derived_from_memory.py` | the closed delete list above; the surviving tests of each file stay green unedited |
| J6.T6 | jr | AC9.5 | `.github/workflows/ci.yml` | delete the three `env:` blocks that set `PYTHONUTF8` and `PYTHONIOENCODING`. RED evidence: the grep with six hits; GREEN: zero hits and every leg green on the PR |
| J6.T7 | sr | AC9.4 | `tests/infrastructure/test_privacy_check.py` | RED, unit: a case in a temporary git repo where an ignored `__pycache__/x.pyc` under `public/` keeps the contract green and a tracked one fails it. Owner `test_privacy_check.py` |
| J6.T8 | jr | AC9.4 | `tests/infrastructure/test_privacy_check.py` | replace the working-tree `rglob` bytecode assertion with the tracked-files check of T7. After T7 |
