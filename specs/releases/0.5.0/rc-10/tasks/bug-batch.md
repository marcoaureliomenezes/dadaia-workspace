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
| JB.S2.T14 | — | this file (T11 names the paths it extends) | no RED: `release.py check` |
| JB.S2.T15 | AC9.1 | the service.py and test_hook_refresh.py of T7, one more commit (a forced install sets an unreadable hook aside; the path-delete guard allows no deletion there) | the rows of T7 |
| JB.S2.T16 | — | `dadaia_workspace/features/chokepoints/branch_policy.py` (a PR-only refusal's fix is an operator action on the user's git host), `tests/unit/features/chokepoints/test_push_branch_policy.py`, `tests/integration/test_refusal_fix_lines_clear_their_refusal.py` (the operator-approved lines) | the two rows that locked the `gh` line; one site of public-law-teaches-the-private-pipeline |
| JB.S2.T9 | — | `specs/releases/0.5.0/rc-10/tasks/bug-batch.md` | close task of both lanes, last: `test-audit:`, `mutation:` lines; the job's `done` line |

- Lane A is JB.S3, JB.S4 and JB.S5 (the same write-set rule). The operator's rulings of 2026-10-06 that shape it: "Aceito: apagar _check_stray (Recommended)", "Job hotfix sem SPEC (Recommended)", "para os usuários do dadaia-workspace CI em repo remoto não deve ser de forma alguma obrigatorio", "Registra os 4 e corrige na rc-10 (Recommended)", "Aprovo (a)-(d) (Recommended)", and "Público, sem bloquear (Recommended)".

## Stage JB.S3 — RED (lane A)

- Contract: exit tests one RED case per bug, or per cause group, as strict xfail, at the lowest level that detects it; the operator-approved old lines change here and nowhere else; envelope `tests/**`; ACs AC9.1
- Old lines changed in this stage, each on the operator's approval of 2026-10-06: `test_a_stray_job_branch_commit_refuses` is deleted ("Aprovo (a) e (b) (Recommended)", the deletion of the stray check); lines 393-397 of `test_worktree_lifecycle.py` expect a job to land with no `ci_run` ("Aprovo (a)-(d) (Recommended)"); the stale-balance row of `test_release_script.py` expects a warning, not an error ("Público, sem bloquear (Recommended)").
- Bugs without a RED row of their own: `job-merge-accepts-any-ci-run-url` and `job-merge-requires-a-remote-ci-run` share the one deletion, so one RED row; `public-law-teaches-the-private-pipeline` belongs to the law lane.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S3.T1 | AC9.1 | `specs/releases/0.5.0/rc-10/tasks/bug-batch.md` (the rows of lane A) | no RED: `release.py check` |
| JB.S3.T2 | AC9.1 | `tests/integration/test_worktree_lifecycle.py` (check-stray-laundered-by-rebase: the stray test leaves and a directly committed code change lands once reviewed; job-merge-requires-a-remote-ci-run and job-merge-accepts-any-ci-run-url: the `ci_run` test turned around; gate-runs-the-judged-trees-own-ci-script: a task and a job editing the declared line's script refuse; test-path-convention-is-python-only: a task naming a `*_test.py` owner lands) | the new rows, strict xfail |
| JB.S3.T3 | AC9.1 | `tests/integration/test_worktree_new.py` (a block-list hotfix opens with no rc SPEC, refuses without an open bug record, and merges) | the new rows, strict xfail |
| JB.S3.T4 | AC9.1 | `tests/integration/test_worktree_removal.py` (worktree-removal-leaves-empty-parent-and-remote-branch: a merge removes the emptied rc folder and the pushed branch, `list` reports an empty folder) | the new rows, strict xfail |
| JB.S3.T5 | AC9.1 | `tests/integration/test_worktree_define_gate.py`, `tests/fixtures/stores.py` (trio-status-canon-judged-outside-the-define-merge-gate: the stub CLI answers `doctor`; a define merge runs it fenced to its tree and refuses on its exit) | the new rows, strict xfail |
| JB.S3.T6 | AC9.1 | `tests/integration/test_skill_script_workspace_root.py` (skill-script-root-walks-ignore-the-fence: each skill script walk skips a fenced root) | the new rows, strict xfail |
| JB.S3.T7 | AC9.1 | `tests/unit/skills/test_release_implementation_release_script.py` (rc-closes-with-an-open-bug: `new` refuses while a bug found in the live rc is open or deferred; release-ship-requires-a-pr-number: `ship` with no `--pr` records `pr: null`) | the new rows, strict xfail |
| JB.S3.T8 | AC9.1 | `tests/contract/test_release_script.py` (a stale `## Bugs` block is a warning at closure, the one old row of it changed; test-path-convention-is-python-only: a first stage naming `pkg/x_test.go` passes) | the changed row and the new row, strict xfail |

## Stage JB.S4 — fixes (lane A)

- Contract: exit tests JB.S3 green, unit + integration green, `bugs.py status` shows no lane A bug open except the one waiting for the operator's approval of its old rows; envelope the units the groups name, `specs/bugs/BUGS.jsonl` (by `bugs.py` only, one `resolve` line in each fix commit); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S4.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py`, `dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py`, `dadaia_workspace/public/schemas/handoff-v1.schema.json`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `tests/helpers/worktree_ws.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/integration/test_worktree_new.py`, `tests/integration/test_worktree_removal.py`, `tests/integration/test_worktree_define_gate.py`, `tests/integration/test_skill_script_workspace_root.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py` (the worktree and workspace-root fixes, one commit each, markers leave) | its JB.S3.T2-T6 rows; ADRs 0190 (amended by 0212) and 0215 rule it; check-stray, gate-runs-the-judged-trees-own-ci-script, the `ci_run` pair, trio-status-canon, worktree-removal, skill-script-root-walks, and the hotfix job |
| JB.S4.T2 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `tests/unit/skills/test_release_implementation_release_script.py`, `tests/contract/test_release_script.py` (rc-closes-with-an-open-bug, release-ship-requires-a-pr-number, and the stale balance block as a warning; markers leave) | its JB.S3.T7-T8 rows |

## Stage JB.S5 — close (lane A)

- Contract: the behavior map re-recorded after lane A's law and script edits; exit unit + integration green; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S5.T1 | — | `dadaia_workspace/public/entities/behavior-map.json` (skill and scripts hashes after lane A) | `test_behavior_map.py` |

## Stage JB.S6 — stage-gate repairs and the map (lane A)

- Contract: the stage gate of JB.S4 green again (guards v32 and v38, unit, integration) and the behavior map re-recorded last; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S6.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/scaffold/memory/AGENTS.md` (the line is back to its published bytes), `scripts/guards/slop.py` (one allowance row) | `test_worktree_removal.py` |
| JB.S6.T2 | — | `dadaia_workspace/public/entities/behavior-map.json` (skill and scripts hashes after the repairs) | `test_behavior_map.py` |
