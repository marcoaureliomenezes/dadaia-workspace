# TASKS — 0.5.0 rc-10, job encoding

**Status:** Approved
**Approval:** by operator order 2026-10-07 and the operator ruling 2026-10-08 (bug `release-check-skips-a-rebased-away-until`, the tail review's HIGH 1); the dd-code-reviewer job review is pending.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Opened after the tail merged into the work branch; bound by the freeze (ADR 0209), ADR 0206 (no rc closes over an open bug) and ADR 0210 (`caused_by ≠ none` is a REBUILD). Every fix row names its single decider, puts its `git grep` sweep line and hit count in the commit body, and states net lines over its source files (≤ 0, or why not); the `BUGS.jsonl` line is written by `bugs.py resolve` only. `deferred` counts as open (operator ruling), so both bugs below resolve here.

- AC9.1: every bug found in rc-10 is resolved in rc-10 (0206). AC10.2, AC10.4, AC10.5: the closure acts of the SPEC.
- Bug `subprocess-text-encoding-has-no-guard`: the withdrawn PLW1514 patch does not flag `subprocess.run(…, text=True)`; the one decider is a new AST check in `scripts/guards/slop.py`, planted, with the 12-site `encoding=` sweep.
- Bug `release-check-skips-a-rebased-away-until` (HIGH): `_window_findings` deletes its `git merge-base --is-ancestor` skip; `drift.report` stays the one reach check; the closed window is a fact of local git (HEAD on the constitution's `gitflow:` principal), the fixture's principal is its constitution line.

## Stage JE.S1 — RED

- Contract: exit tests the rows below at `tests/public/skills/dd_release_implementation/scripts/test_release.py` (an amend-orphaned `until` off the principal refuses, naming the not-an-ancestor refusal, strict xfail; a `--no-ff` promote on the principal then an atom move is clean, strict xfail; a squash promote on the principal is clean and passes on arrival, no marker); envelope `tests/**`; ACs AC9.1
- The guard bug takes no RED row: its evidence is the planted adversary (`run.py --planted`), and no `tests/**` line changes in its fix.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S1.T1 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release.py` (release-check-skips-a-rebased-away-until: three new rows, literal exit codes and the refusal text) | the two window rows strict xfail; the squash row passes on arrival |

## Stage JE.S2 — fixes

- Contract: exit tests JE.S1 green, unit + integration green, `python scripts/guards/run.py` and `run.py --planted` as specified; envelope the units the rows name; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S2.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (`_window_findings` drops the `--is-ancestor` skip and judges the window closed only when HEAD is on the principal), `tests/public/skills/dd_release_implementation/scripts/test_release.py` (markers leave; the frozen `--no-ff` row `test_check_names_the_moved_source_when_until_is_history_of_head` moves to a non-principal branch, through the REBUILD lane), `specs/memory/product/sdd/release-lifecycle.md` (lines 38 and 60 agree) | its JE.S1.T1 rows. One `refactor(bugs): release-check-skips-a-rebased-away-until — REBUILD _window_findings: …` commit; `caused_by` from `resolve`'s blame candidates (`release-check-reds-main-after-an-operational-lane-commit`, whose fix dd5399f08 wrote the skip). Lineage: cc544f66e, d1e29503b, b50f0c971, 73983ae3c, dd5399f08. Decider: `_window_findings` asking `drift.report` once. Net ≤ 0 over the source file, or the body names why |
| JE.S2.T2 | AC9.1 | `scripts/guards/slop.py` (new AST check after `v40`, its `_PLANTS`), `dadaia_workspace/cli/commands/ci.py`, `dadaia_workspace/infrastructure/certification_process.py`, `dadaia_workspace/infrastructure/git_subprocess.py`, `dadaia_workspace/infrastructure/python_env.py`, `dadaia_workspace/infrastructure/subprocess_runner.py`, `scripts/guards/repo.py`, `scripts/guards/run.py` | no `tests/**` line; `run.py --planted` red on each plant, green on CONTROL. Decider: the slop check. Sweep: the AST scan, 12 sites before, 0 after (in the body). Gate change: hand mutants through `--planted`, never `skipped` |

## Stage JE.S3 — QUALITY and derived docs (a barrier after JE.S2)

- Contract: exit `bugs.py balance --check` and `tests/infrastructure/test_entity_doctor.py` green; envelope `specs/memory/QUALITY.md`, `specs/memory/product/catalog.json`, `dadaia_workspace/public/entities/behavior-map.json`; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S3.T1 | AC9.1 | `specs/memory/QUALITY.md` (the `## Bugs` block by `bugs.py balance --write`), `specs/memory/product/catalog.json` (by `memory.py catalog generate` after any atom edit), `dadaia_workspace/public/entities/behavior-map.json` (re-recorded only if the entity doctor names stale rows) | `bugs.py balance --check`, `tests/infrastructure/test_entity_doctor.py` |

## Stage JE.S4 — closure acts (a barrier after JE.S3)

- Contract: no tests; exit `release.py check` exit 0, `bugs.py status` 0 open and 0 deferred; envelope `specs/memory/**`, `specs/releases/0.5.0/_RELEASE.json`, `specs/audits/**` dispositions, this file; ACs AC10.2, AC10.4, AC10.5
- Rows only here: owned later by the main thread and `dd-product-engineer`.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S4.T1 | AC10.2 | `specs/memory/**` (the atoms `release.py check` names as moved, by `release.py memory`, MEMORY-UPDATE.md) | `release.py check` exit 0 |
| JE.S4.T2 | AC10.2 | `specs/releases/0.5.0/_RELEASE.json` (K2, the closure narrative `log` entries: `summary`, `size`, `drifts`, `artifact-gc` (doctor dry, then `--fix`), `test-dispositions`, `dispositions`; the tail's `kind: merge` entry) | `release.py check` exit 0 |
| JE.S4.T3 | — | this file | close task, last: `test-audit:`, `mutation:` lines; the job's `done` line |


## Stage JE.S5 — RED (bug `release-check-parses-the-gitflow-in-the-skill`)

- Contract: exit tests the rows below; `release.py check` on the principal without `--principal` refuses (passes on arrival, no marker); the doctor path (`script_findings`) over a YAML `gitflow:` block and over a constitution with none (the default principal) shows no `LEDGER-RELEASE-SCHEMA` window finding after a squash promote and an atom move (strict xfail); envelope `tests/**`; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S5.T1 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release.py` (one new row, no marker), `tests/infrastructure/test_ledger_scripts__release_window_principal.py` (new file, two parametrized rows) | the doctor rows strict xfail; the no-`--principal` row passes on arrival |

## Stage JE.S6 — the REBUILD (a barrier after JE.S5)

- Contract: exit tests JE.S5 green, the JE.S1 rows green through `--principal`, unit + integration green, `python scripts/guards/run.py`; envelope the units the row names; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S6.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (`_on_principal` deleted; `_window_findings` and `check` take the principal), `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` (`check --principal`), `dadaia_workspace/infrastructure/ledger_scripts.py` (a `LedgerScript` row field naming the flag; the value from `core.gitflow.read_gitflow`), `tests/public/skills/dd_release_implementation/scripts/test_release.py` (the JE.S1 rows and the two frozen JT.S1.T4 rows pass `--principal`; `_declare_principal` leaves), `tests/infrastructure/test_ledger_scripts__release_window_principal.py` (marker leaves) | its JE.S5.T1 rows. One `refactor(bugs): release-check-parses-the-gitflow-in-the-skill — REBUILD _window_findings: …` commit. Lineage: cc544f66e, d1e29503b, b50f0c971, 73983ae3c, dd5399f08, 2c7369c9a, 7e05b3148. Decider: `core.gitflow.read_gitflow` (ADR 0144), the skill reads no constitution. Gate change: hand mutants, adversary rows. Net ≤ 0 over `_release_tree.py` |

## Stage JE.S7 — the closure pass after the principal REBUILD (a barrier after JE.S6)

- Contract: no tests; exit `release.py check` exit 0, `bugs.py balance --check` exit 0, `bugs.py status` 0 open and 0 deferred; envelope `specs/memory/**`, the derived docs whose atom changed, `specs/releases/0.5.0/_RELEASE.json`, this file; ACs AC10.1, AC10.2
- The authorized rebase onto the work branch's registration of `release-check-parses-the-gitflow-in-the-skill` orphaned the first memory entry's `until`; that entry left history, so one memory entry covers the whole window from the tail's.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JE.S7.T1 | AC10.1 | `specs/memory/QUALITY.md` (`## Bugs` by `bugs.py balance --write`), `specs/memory/product/platform/workspace-doctor.md` (the release script's check takes the principal), `specs/memory/product/catalog.json`, `specs/memory/product/index.md`, the derived docs of a changed atom, `specs/releases/0.5.0/_RELEASE.json` (the memory entry by `release.py memory`) | `release.py check` exit 0, `tests/contract/test_docs_derived_from_memory.py` |
| JE.S7.T2 | — | this file | close task, last: `test-audit:`, `mutation:` lines; the job's `done` line |

- done: rc-10 job encoding — every task of JE.S1 to JE.S7 landed on `wt/0.5.0-rc10/encoding`; `release-check-skips-a-rebased-away-until`, `subprocess-text-encoding-has-no-guard` (guard v41, its scripts/ half committed on the work branch as d731bc911 by authorized operator act) and `release-check-parses-the-gitflow-in-the-skill` (registered on the work branch as a1343aaec, the job rebased onto it by operator ruling) are resolved, so rc-10 holds 0 open and 0 deferred bugs; one memory entry covers the job; the closure narrative, its note and the artifact GC are logged; closed by JE.S7.T2.
