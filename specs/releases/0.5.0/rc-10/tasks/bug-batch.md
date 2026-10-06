# TASKS — 0.5.0 rc-10, the bug batch

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Opened after Job 6: the freeze binds it. Each fix is shape 3 as Job 6 rewrites it: the RED commit in JB.S1, then a fix commit with the code, the `BUGS.jsonl` line and the marker-line deletion (0209 + F-3 (a)).

- AC9.1: every bug found in rc-10 and not fixed as a hotfix; grouped by cause; a fix with `caused_by ≠ none` is a REBUILD of the unit keeping its tests (0210). Rows are born from `bugs.py status` when the batch opens. Empty batch: the job is not opened; Reconciliation records `0 open`.

## Stage JB.S1 — RED

- Contract: exit tests one RED case per bug (or per cause group) as strict xfail, at the lowest level that detects it; envelope `tests/**`; ACs AC9.1
- JB.S1.T1 opened the batch before the RED rows: it registered the two bugs the review reproduced (specs/bugs/BUGS.jsonl, two `chore(bugs): report` commits) and wrote the rows of this file.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S1.T2 | AC9.1 | `tests/unit/features/chokepoints/test_push_denylist_scan.py`, `tests/unit/features/chokepoints/test_push_branch_policy.py`, `tests/integration/test_push_gate_denylist.py` (push-refusal-advertises-no-verify: the five `--no-verify` expectations the operator approved, and a row for a refusal that names no bypass) | the new row, strict xfail |
| JB.S1.T3 | AC9.1 | `tests/unit/hooks/test_root_whitelist.py`, `tests/unit/test_spec_context_doctor_root.py` (root-allows-git-and-gitignore-though-root-is-never-a-repo: the root canon rows that listed `.git` and `.gitignore`) | the changed rows and two new rows, strict xfail |
| JB.S1.T4 | AC9.1 | `tests/contract/cli/test_cli_reports.py` (reports-validate-documents-exit-codes-it-never-returns) | the new row, strict xfail |
| JB.S1.T5 | AC9.1 | `tests/unit/skills/test_bug_resolution_bugs_script.py` (rebase-orphans-bug-fix-links-cited-by-sha and task-fix-over-a-bug-fix-records-no-lineage) | the new rows, strict xfail |
| JB.S1.T6 | AC9.1 | `tests/unit/features/spec_context/test_hook_refresh.py` (hook-unreadable-fix-line-crashes-installer) | the new rows, strict xfail |
| JB.S1.T7 | AC9.1 | `tests/contract/test_law_states_what_the_code_does.py` (bug-resolution-law-prescribes-rewriting-asserts, pillar-bugs-metric-reads-retired-event-stream, backlog-skill-asks-a-merge-the-writer-cannot-do) | the new rows, strict xfail |
| JB.S1.T8 | AC9.1 | `tests/contract/test_release_script.py` (release-check-fallback-fix-line-drops-specs: the fallback fix names `--specs` and pairs no half refusal, the one old `endswith` row that pinned its absence; bug-balance-cuts-a-non-utc-closure-day-to-local: the window ends on the UTC day) | the changed row and three new rows, strict xfail; two commits |

- Lane B is JB.S1 and JB.S2; lane A's rows follow as JB.S3 and JB.S4 (disjoint write sets, run in two lanes on the operator's "Sim, antecipar", 2026-10-06).

## Stage JB.S2 — fixes

- Contract: exit tests JB.S1 green, unit + integration green, `bugs.py status` shows no rc-10 bug open; envelope the units the groups name, `specs/bugs/BUGS.jsonl` (by `bugs.py` only, one `resolve` line in each fix commit); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S2.T1 | AC9.1 | this file (rows corrected: the registration is a bullet of stage JB.S1, no row writes the ledger) | no RED: `release.py check` |
| JB.S2.T2 | AC9.1 | `dadaia_workspace/features/chokepoints/push_gate.py` (`_BYPASS` and its two uses leave), `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`, `dadaia_workspace/public/templates/shipped-hashes.json` (the new hook digest), `tests/unit/features/chokepoints/test_push_denylist_scan.py` (marker leaves) | its JB.S1.T2 row; resolve with `--evidence-seam` |
| JB.S2.T3 | AC9.1 | `dadaia_workspace/core/workspace_layout.py` (`.git` and `.gitignore` leave the root canon), `tests/unit/hooks/test_root_whitelist.py`, `tests/unit/test_spec_context_doctor_root.py` (markers leave) | its JB.S1.T3 rows |
| JB.S2.T4 | AC9.1 | `dadaia_workspace/cli/commands/reports.py` (the two exit codes the verb never returns leave its help), `tests/contract/cli/test_cli_reports.py` (marker leaves) | its JB.S1.T4 row; a REBUILD of the verb's help, `caused_by` set |
| JB.S2.T5 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_fix.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py` (one reader of a task's commits; `_window`'s own leaves), `tests/unit/skills/test_bug_resolution_bugs_script.py` (markers leave) | its JB.S1.T5 rows; one REBUILD of the link step, two ids |
| JB.S2.T6 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md` (the clause that prescribes rewriting an old assert leaves, ADR 0209), `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`, `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `tests/contract/test_law_states_what_the_code_does.py` (markers leave) | its JB.S1.T7 rows; three ids, three commits |
| JB.S2.T7 | AC9.1 | `dadaia_workspace/features/spec_context/service.py` (`hook_state`, the one decider), `dadaia_workspace/features/spec_context/doctor.py`, `tests/unit/features/spec_context/test_hook_refresh.py` (markers leave) | its JB.S1.T6 rows; a REBUILD of the hook-state decision |
| JB.S2.T8 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` (one fallback, `--specs` kept), `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_quality.py` (every instant read in UTC), `tests/contract/test_release_script.py` (markers leave) | its JB.S1.T8 rows; two ids, two commits |
| JB.S2.T10 | — | `specs/releases/0.5.0/rc-10/tasks/job4.md` (the review label leaves two lines) | no RED: docs |
| JB.S2.T11 | AC9.1 | the push_gate.py and test_bug_resolution_bugs_script.py of T2 and T5, one more commit each (`_refusal` loses its strip; the mutation rows of the fix reader and the window); no other path | the survivors of `mutation_diff` over T2-T8 |
| JB.S2.T12 | AC9.1 | no backticked path (the ledger by bugs.py): four bugs the operator confirmed on 2026-10-06 (specs/bugs/BUGS.jsonl, four `chore(bugs): report` commits; their fixes belong to the other lanes) | no RED: registration |
| JB.S2.T13 | — | `dadaia_workspace/public/entities/behavior-map.json` (skill and scripts hashes of dd-backlog-definition, dd-audit-project, dd-bug-resolution, dd-release-implementation, re-recorded after lane B), this file (rows) | `test_behavior_map.py` |
| JB.S2.T9 | — | this file | close task, last: `test-audit:`, `mutation:`; `done` |
