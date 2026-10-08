# TASKS — 0.5.0 rc-10, the closure tail

**Status:** Approved
**Approval:** by operator order 2026-10-07 ("confirmos. faça 1, então 2, 3, 4 e so pare quando finalizar o passo 5") and the review-of-reports grill rulings 2026-10-07; dd-code-reviewer APPROVED at the job review.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Opened after rc-10 merged into develop: bugs remain found_in rc-10 and ADR 0206 closes no rc over an open bug. Bound by the freeze (ADR 0209). Every fix row names its single decider, puts its `git grep` sweep line and hit count in the commit body, and states net lines over its source files (≤ 0, or why not); a fix with `caused_by ≠ none` is a REBUILD of its unit keeping its tests (0210); the `BUGS.jsonl` line is written by `bugs.py resolve` only. `deferred` counts as open (operator ruling), so the deferred bugs below are fixed here.

- AC9.1: every bug found in rc-10 is resolved in rc-10 (0206). AC10.2, AC10.4, AC10.5: the closure acts of the SPEC (readouts and merge entries; backlog and audit exits; closure with zero open bugs).

## Stage JT.S1 — RED

- Contract: exit tests one strict-xfail RED case per bug (or cause group), at the lowest seam; the row for `git-errors-replace-has-no-row` is a coverage gap that passes on arrival, so it carries no marker; envelope `tests/**`; ACs AC9.1
- JT.S1.T1 opened the job: it registered the 5 bugs the review reproduced (specs/bugs/BUGS.jsonl, commits 40bcd2066 and aaff3c016) and wrote this file.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JT.S1.T2 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py` (release-check-reads-status-of-backlog-exits: a backlog histo line `{"id","disposition":"rejected"}` traces; release-definition-law-claims-a-deleted-stage-one-check: `dd-release-definition/SKILL.md` states no refusal of a stage 1 writing non-tests, via its `_SKILL` reader; release-check-reds-main-after-an-operational-lane-commit, check side: `release.py check` on a CLOSURE-shipped release does not re-judge its closed memory window against commits made after the ship) | the three new rows, strict xfail |
| JT.S1.T3 | AC9.1 | `tests/features/import_/test_service.py` (import-raises-keyerror-on-a-record-missing-a-field: a record without `name` raises `DadaiaError` naming `name` with one fix line, literal message) | the new row, strict xfail |
| JT.S1.T4 | AC9.1 | `tests/public/skills/dd_spec_navigator/scripts/test__memory_drift.py` (release-check-reds-main-after-an-operational-lane-commit: a squash-merged main, where the window's `until` is no ancestor of HEAD, is not refused as a clone problem) | the new rows, strict xfail |
| JT.S1.T5 | AC9.1 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py` (bug-fix-links-a-task-id-across-rcs: `bugs.py fix` for a bug `found_in` rc-10 resolved `by <task-id>` links no commit of another rc carrying the same bare id) | the new row, strict xfail |
| JT.S1.T6 | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_freeze.py` (freeze-has-no-lane-for-an-approved-amendment: a frozen-test change in a `refactor(…): REBUILD …` commit naming a bug id the ledger holds merges and the refusal's fix line names the bug-proposal act; adversaries: a REBUILD subject naming no record, and one naming a non-bug id, still refuse) | the new rows, strict xfail |
| JT.S1.T7 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release.py` (memory-written-before-closure-phase: `phase CLOSURE` runs from the Reconciliation tree once every other job merged; the Reconciliation template and `MEMORY-UPDATE.md` state the order RC-FLOW step 4 states, read from the shipped law files) | the new rows, strict xfail |
| JT.S1.T8 | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (git-errors-replace-has-no-row: a latin-1 byte in the work branch's `AGENTS.md`, its `tests:` line still declared by `_declared`, literal expected value) | the new row, no marker: it passes on arrival |

## Stage JT.S2 — fixes

- Contract: exit tests JT.S1 green, unit + integration green, `bugs.py status` shows 0 open and 0 deferred rc-10 bugs; envelope the units the rows name, `specs/bugs/BUGS.jsonl` (by `bugs.py resolve` only, one line in each fix commit); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JT.S2.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (`standing()` reads `disposition`, the one decider; `_window_findings` judges no shipped release's closed window), `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py` (the ancestor refusal), `dadaia_workspace/public/skills/dd-release-definition/SKILL.md` (the clause at line 65 leaves), `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py`, `tests/public/skills/dd_spec_navigator/scripts/test__memory_drift.py` (markers leave) | its three JT.S1.T2 rows and the JT.S1.T4 row; three ids, three commits. Sweeps: `git grep -nE "get\(.status.\) == .rejected." -- dadaia_workspace`; `git grep -n "stage 1 whose tasks write anything but tests" -- dadaia_workspace specs`. The window fix is a REBUILD of the window judgement keeping its tests, `caused_by` set; W: refined by its diagnosis within the release-check scripts. Net ≤ 0 |
| JT.S2.T2 | AC9.1 | `dadaia_workspace/features/import_/service.py` (`_read` validates the export record once, naming the missing field with one fix line, ADR 0158; `_dead_context` indexes nothing unvalidated), `tests/features/import_/test_service.py` (marker leaves) | its JT.S1.T3 row. Decider: `_read`. `cli/commands/import_.py` keeps its `DadaiaError` catch and gains none |
| JT.S2.T3 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_fix.py` (the link step takes commits of the record's `found_in` rc only), `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py` (marker leaves) | its JT.S1.T5 row. REBUILD of the link step (lineage: J1.S2.T1 fix reader, JB.S2.T5, JB.S9.T2), the old rows unchanged, `caused_by` set. Decider: the link step. Net ≤ 0 |
| JT.S2.T4 | AC9.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_freeze.py` (admits a frozen-test change only in a REBUILD-shaped subject naming a bug id the ledger holds, read by relaying `bugs.py`, never importing a sibling skill, ADR 0150; its refusal fix line names the proposal act), `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (the ledger read, if the relay lives at the verb edge), `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_freeze.py` (markers leave) | its JT.S1.T6 rows. REBUILD of the amendment decision, `caused_by` set. Decider: `judge`. Gate change: the adversary rows (no record, non-bug id) stay and mutation is never `skipped` |
| JT.S2.T5 | AC9.1 | no backticked path; the ledger is written by bugs.py (git-errors-replace-has-no-row: shape 4 `chore(bugs): resolve … — by JT.S1.T8`, no code) | no RED: the row passed on arrival |
| JT.S2.T6 | AC9.1 | `pyproject.toml` (ruff `select` gains `PLW1514`, preview), `.github/workflows/ci.yml` (`PYTHONUTF8: "1"` leaves lines 43, 198, 226) (subprocess-text-encoding-has-no-guard, ADR 0220 P5/P10) | `ruff check --preview --select PLW1514 dadaia_workspace scripts` 0 hits; no new guard script. Sweep: `git grep -n PYTHONUTF8 -- .github pyproject.toml` 0 hits. Net ≤ 0 |
| JT.S2.T7 | AC9.1 | no backticked path; the ledger is written by bugs.py (panel-telemetry-sqlite-corrupts-under-concurrent-access: shape 4 `chore(bugs): resolve … — by 545ce34ef`, its surface deleted by "demolish the panel") | no RED: no code |

## Stage JT.S3 — the memory order (a barrier after JT.S2: JT.S2.T1 and the amended `test_release*.py` files precede it)

- Contract: exit tests the JT.S1.T7 rows green, unit + integration green; envelope the units the row names, `specs/bugs/BUGS.jsonl` (by `bugs.py resolve` only); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JT.S3.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md` (step 1's order leaves; it points to RC-FLOW step 4), `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md` (step 4, the one home of the order), `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py` (`phase CLOSURE` runs from the Reconciliation tree), the Reconciliation template under `dadaia_workspace/public/scaffold/releases/`, `tests/public/skills/dd_release_implementation/scripts/test_release.py` (markers leave) | its JT.S1.T7 rows. Deletion of one of the two orders, no new check. Sweep: `git grep -n "no memory write before" -- dadaia_workspace specs`. Net ≤ 0 |
| JT.S3.T2 | — | `dadaia_workspace/public/entities/behavior-map.json` (skill and scripts hashes, re-recorded after JT.S2 and JT.S3.T1) | `tests/infrastructure/test_entity_doctor.py` |

## Stage JT.S4 — closure acts

- Contract: no tests (ledger, backlog, ADR and release-state writes); exit `release.py check` exit 0, `bugs.py status` 0 open, `backlog.py check` clean; envelope `specs/releases/0.5.0/rc-10/tasks/job10.md`, `specs/backlog/**`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/ADRs/decisions.jsonl`, `specs/releases/0.5.0/_RELEASE.json`; ACs AC10.2, AC10.4, AC10.5
- One writer per path per stage: `decisions.jsonl` and `_RELEASE.json` each have one task here.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JT.S4.T1 | AC10.5 | `specs/releases/0.5.0/rc-10/tasks/job10.md` (K3: Status Draft → Approved) | no RED: `release.py check` |
| JT.S4.T2 | AC10.4 | `specs/backlog/**` (K1: `law-one-home-per-rule` exits `delivered --release 0.5.0` for its AC12.6 half by `backlog.py exit`; a new entry re-intakes its residual (a)-(c), operator ruling "Exit delivered + re-intake rest") | `backlog.py check` |
| JT.S4.T3 | AC10.4 | `specs/audits/20260930-structural-convergence/FINDINGS.jsonl` (K9: F001 → resolved, cause removed; F008 → open again; by `audit.py disposition`) | `audit.py` |
| JT.S4.T4 | AC10.5 | `specs/ADRs/decisions.jsonl` (ADR proposal `freeze-exit-test-wrong`, amends 0209: the agent never edits a frozen test, it exits "test wrong/impossible" as a bug proposal and the fix lands as one REBUILD commit once the operator confirms; proposed, never accepted) | `dadaia doctor`; commit `docs(adr): propose freeze-exit-test-wrong` |
| JT.S4.T5 | AC10.2 | `specs/releases/0.5.0/_RELEASE.json` (K4: the `kind: merge` entry of the rc-10 reconcile job; K2, last and after JT.S2.T1: the closure narrative `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`, RC-FLOW step 4, RELEASE-EVENTS.md). This job's own `kind: merge` entry is written at its merge by the main thread | `release.py check` exit 0 |
| JT.S4.T6 | — | this file | close task, last: `test-audit:`, `mutation:` lines; the job's `done` line |

