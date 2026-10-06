# TASKS — 0.5.0 rc-10, the bug batch

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Opened after Job 6: the freeze binds it. Each fix is shape 3 as Job 6 rewrites it: the RED commit in JB.S1, then a fix commit with the code, the `BUGS.jsonl` line and the marker-line deletion (0209 + F-3 (a)).

- AC9.1: every bug found in rc-10 and not fixed as a hotfix; grouped by cause; a fix with `caused_by ≠ none` is a REBUILD of the unit keeping its tests (0210). Rows are born from `bugs.py status` when the batch opens. Empty batch: the job is not opened; Reconciliation records `0 open`.

## Stage JB.S1 — RED

- Contract: exit tests one RED case per bug (or per cause group) as strict xfail, at the lowest level that detects it; envelope `tests/**`; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S1.T1 | AC9.1 | `specs/bugs/BUGS.jsonl` (the two review-reproduced LOW bugs, `chore(bugs): report`), this file | no RED: registration and rows |
| JB.S1.T2 | AC9.1 | `tests/unit/features/chokepoints/test_push_denylist_scan.py`, `tests/unit/features/chokepoints/test_push_branch_policy.py`, `tests/integration/test_push_gate_denylist.py` (push-refusal-advertises-no-verify: the five `--no-verify` expectations the operator approved, and a refusal that names no bypass) | the new row, strict xfail |
| JB.S1.T3 | AC9.1 | `tests/unit/hooks/test_root_whitelist.py`, `tests/unit/test_spec_context_doctor_root.py` (root-allows-git-and-gitignore-though-root-is-never-a-repo: the root canon rows that listed `.git` and `.gitignore`) | the changed rows and one new row, strict xfail |
| JB.S1.T4 | AC9.1 | `tests/contract/cli/test_cli_reports.py` (reports-validate-documents-exit-codes-it-never-returns) | the new row, strict xfail |
| JB.S1.T5 | AC9.1 | `tests/unit/skills/test_bug_resolution_bugs_script.py` (rebase-orphans-bug-fix-links-cited-by-sha and task-fix-over-a-bug-fix-records-no-lineage) | the new rows, strict xfail |
| JB.S1.T6 | AC9.1 | `tests/unit/features/spec_context/test_hook_refresh.py` (hook-unreadable-fix-line-crashes-installer) | the new rows, strict xfail |
| JB.S1.T7 | AC9.1 | `tests/contract/test_law_states_what_the_code_does.py` (bug-resolution-law-prescribes-rewriting-asserts, pillar-bugs-metric-reads-retired-event-stream, backlog-skill-asks-a-merge-the-writer-cannot-do) | the new rows, strict xfail |
| JB.S1.T8 | AC9.1 | `tests/contract/test_release_script.py` (release-check-fallback-fix-line-drops-specs: the fallback fix names `--specs`; the one old `endswith` row that pinned its absence) | the changed row and one new row, strict xfail |
| JB.S1.T9 | AC9.1 | `tests/unit/skills/test_bug_resolution_balance.py` (bug-balance-cuts-a-non-utc-closure-day-to-local) | the new rows, strict xfail |

- Lane B is JB.S1 and JB.S2; lane A's rows follow as JB.S3 and JB.S4 (disjoint write sets, run in two lanes on the operator's "Sim, antecipar", 2026-10-06).

## Stage JB.S2 — fixes

- Contract: exit tests JB.S1 green, unit + integration green, `bugs.py status` shows no rc-10 bug open; envelope the units the groups name, `specs/bugs/BUGS.jsonl` (by `bugs.py` only); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S2.T1 | AC9.1 | `dadaia_workspace/features/chokepoints/push_gate.py` (`_BYPASS` and its two uses leave), `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`, `dadaia_workspace/public/templates/shipped-hashes.json` (the new hook digest), the T2 test files (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T2 row; resolve with `--evidence-seam` |
| JB.S2.T2 | AC9.1 | `dadaia_workspace/core/workspace_layout.py` (`.git` and `.gitignore` leave the root canon), the T3 test files (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T3 rows |
| JB.S2.T3 | AC9.1 | `dadaia_workspace/cli/commands/reports.py` (the two exit codes the verb never returns leave its help), the T4 test file (marker leaves), `specs/bugs/BUGS.jsonl` | its JB.S1.T4 row; a REBUILD of the verb's help, `caused_by` set |
| JB.S2.T4 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_fix.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py` (one reader of task commits; `_window`'s own leaves), the T5 test file (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T5 rows; one REBUILD of the link step, two ids |
| JB.S2.T5 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md` (the clause at Phase 6 that prescribes rewriting an old assert leaves, ADR 0209), `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`, `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, the T7 test file (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T7 rows; three ids, three commits |
| JB.S2.T6 | AC9.1 | `dadaia_workspace/features/spec_context/service.py` (`hook_state`, the one decider), `dadaia_workspace/features/spec_context/doctor.py`, the T6 test file (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T6 rows; a REBUILD of the hook-state decision |
| JB.S2.T7 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (one fallback, `--specs` kept), the T8 test file (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T8 rows |
| JB.S2.T8 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_quality.py` (every instant read in UTC), the T9 test file (markers leave), `specs/bugs/BUGS.jsonl` | its JB.S1.T9 rows |
| JB.S2.T10 | — | `specs/releases/0.5.0/rc-10/tasks/job4.md` (the review label leaves two lines) | no RED: docs |
| JB.S2.T11 | — | `dadaia_workspace/public/entities/behavior-map.json` (scripts hashes of dd-bug-resolution, dd-release-implementation, re-recorded), this file (lane B's `test-audit:` and `mutation:` lines, its done line) | `test_behavior_map.py` |

- The stage gate runs once per stage.
| JB.S2.T9 | — | this file | close task, last: `test-audit:`, `mutation:`; `done` |
