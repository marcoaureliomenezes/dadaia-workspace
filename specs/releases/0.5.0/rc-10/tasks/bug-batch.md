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
| JB.S6.T3 | — | `dadaia_workspace/features/spec_context/doctor.py` (the import block ruff I001 refuses after the rebase; order only, no line changes meaning) | `ruff check`, `tests/features/spec_context/test_doctor.py` |
| JB.S6.T4 | AC9.1 | `tests/infrastructure/test_privacy_check.py` (public-law-teaches-the-private-pipeline: the strict-xfail marker line leaves, because Job 6 already cleaned the law; it XPASSes strict at 7b95b4b30) | the guard, green |

## The redo and the open bugs — stages JB.S7 to JB.S11

- Source: the early review of 7b95b4b30 (KEEP 8, REDO 12) and `bugs.py status` (13 open), grouped by structural cause; every row is bound by the pre-review checklist items 1–13.
- A REDO rebuilds forward on the named sha: its tests stay, because a revert would re-add marker lines in a mixed group, which the freeze refuses. The commit shape is `refactor(bugs): <id> — REBUILD <unit> (redo of <sha>): …`, with `bugs.py update <id> --set solution=…` in the same commit.
- Every fix row names its single decider, puts its `git grep` sweep line and hit count in the commit body (item 10), and states its net lines over its source files (item 13: ≤ 0, or why not). A gate row carries its adversary RED row, and mutation is never `skipped` on it (item 12).
- Every fix row is multi-platform by construction: a platform fact goes through `dadaia_workspace/core/platform.py` (item 11). The operator ruled on 2026-10-07: "windows deve satisfazer as mesmas necessidades que linux. as features tem que funcionar la também … toda arquitetura e a forma como metodos são programados deve pensar em ser multi-plataforma". That ruling lifts "Windows small-only for now".
- The Windows legs run the same selection as Linux. Every test that is red on Windows today (runs 37543869150, 37546529916) passes there for real: no skip, no quarantine, no marker, no exit-5 escape.
- Barriers: JB.S8 calls the helpers that JB.S7 adds. JB.S10 writes files that JB.S9 rows also write (`_worktree_end.py`, `_release_schema.py`, `release.py`, `workspace_layout.py`).
- Not in rc-10: a Windows eval job in `dadaia-evals` CI. Reconciliation registers it as a backlog entry.
- Known red at open: `tests/infrastructure/test_privacy_check.py::test_public_law_names_no_private_pipeline` XPASSes strict at 7b95b4b30, because Job 6 already cleaned the law. JB.S6.T4 removes its marker, so the JB.S6 gate is green before JB.S7 opens.

## Stage JB.S7 — RED, and the Windows helpers

- Contract: exit is every new row RED by assertion, the helpers importable and the rest of the suite green; envelope `tests/**`, test paths alone. Lines are only added, except the three rows ruled 2026-10-07T00:26:11Z ("Approve deleting the 3 (Recommended)"); ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S7.T1 | AC9.1 | this file (stages JB.S7–JB.S11) | no RED: `release.py check` |
| JB.S7.T2 | AC9.1 | `tests/features/spec_context/test_doctor.py` (root-allows-git, redo of c48455954: `doctor --fix` on a root holding `.git/` moves nothing; the finding is unfixable, with an `Operator action:` line) | the new row, strict xfail |
| JB.S7.T3 | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (gate-runs-the-judged-trees-own-ci-script, redo of 4936ab4f6: the adversary is a range that edits a module the declared script imports, not the literal path, and it refuses) | the new row, strict xfail |
| JB.S7.T4 | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__define_gate.py` (trio-status, redo of 78f9817da: the adversary is a define tree with a red ledger; the refusal comes once, carrying the doctor's own fix line verbatim) | the new row, strict xfail |
| JB.S7.T5 | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py` (worktree-removal, redo of 6bdab2056: a pushed branch whose remote is not `origin` is deleted on its upstream, and a failed remote delete is reported with its fix line, never hidden) | the new rows, strict xfail |
| JB.S7.T6 | AC9.1 | `tests/public/skills/dd_bug_resolution/scripts/test__ledger.py` (skill-script-root-walks, redo of c5e6cb996: `_ledger`'s walk skips a fenced root) | the new row, strict xfail |
| JB.S7.T7 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release.py` (rc-closes-with-an-open-bug, redo of df9b28641: `ship` refuses while a bug found in the shipping rc is open or deferred, relaying `bugs.py`'s line; the adversaries are a bug from another rc and a record with no `found_in`) | the new rows, strict xfail |
| JB.S7.T8 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py` (test-path-convention-is-python-only: deletes the rows `rc9-job1-shape-stage-1-source`, `stage-1-table-source`, `stage-1-non-test` under the 00:26:11Z ruling) | no RED: deletion |
| JB.S7.T9 | AC9.1 | `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py` (the second `_utc`, redo of 3fdfebebc: the one release instant reader reads an instant with no offset as UTC) | the new row, strict xfail |
| JB.S7.T10 | AC9.1 | `tests/features/spec_context/test_gate_policy__law_states_what_the_code_does.py` (manager-orchestration-skill-allows-job-dispatch: the dispatch unit is the task, ADR 0190) | the new row, strict xfail |
| JB.S7.T11 | AC9.1 | `tests/core/test_workspace_layout.py` (shipped-law-hardcodes-the-posix-venv-path: a law fragment staged under `Capabilities.detect("win32")` names `.dadaia/.venv/Scripts/dadaia.exe`) | the new row, strict xfail |
| JB.S7.T12 | AC9.1 | `tests/hooks/test_venv_guard.py` (the same bug: under win32 the guard allows the `Scripts` CLI and its block message names it) | the new rows, strict xfail |
| JB.S7.T13 | AC9.1 | `tests/fixtures/stores.py` (the Windows seam: adds the one fake-venv builder; `_exe` comes from `PLATFORM`, and the launcher is copied by its real name) | its own small rows on every OS leg |
| JB.S7.T14 | AC9.1 | `tests/fixtures/harness_env.py` (the Windows seam: adds the one child-process helper, which runs `sys.executable`, never a bare `python`, runs Git Bash, never System32 `bash`, and renames a tree holding `.git` instead of using `rmtree`) | its own small rows on every OS leg |

## Stage JB.S8 — the Windows call sites

- Contract: exit is the suite green on Linux and these files green on the Windows and macOS legs with the Linux selection. Envelope: the files below, test paths alone. They change existing test lines past the RED anchor (ADR 0209) on the operator's 2026-10-07 Windows ruling. No `windows` marker, skip or quarantine remains. T11 merges last; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S8.T1 | AC9.1 | `tests/core/test_invocation__one_bind.py` (orphan-worktree-line, fix-line-posix-bin: `workspace_cli` leaves, paths expected through `PLATFORM`, the `windows` marker leaves) | the file; RED is the Windows leg |
| JB.S8.T2 | AC9.1 | `tests/features/spec_context/test_service__context_dead_holds.py` (`workspace_cli` and the `windows` marker leave) | the file |
| JB.S8.T3 | AC9.1 | `tests/helpers/worktree_ws.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (worktree-script-run-fails-winerror-193: the stub becomes the T13 builder; the `windows` marker leaves) | both files |
| JB.S8.T4 | AC9.1 | `tests/cli/commands/test_context.py`, `tests/cli/commands/test_context__context_show_live_branch.py` (context-show-rmtree-readonly-git: the T14 rename) | both files |
| JB.S8.T5 | AC9.1 | `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py` (`workspace_cli` leaves) | the file |
| JB.S8.T6 | AC9.1 | `tests/cli/commands/test_doctor.py`, `tests/cli/commands/test_doctor__workspace_fix_lines_clear_their_finding.py` (fix-line-run-tests-spawn-wsl-bash: the T14 helper) | both files |
| JB.S8.T7 | AC9.1 | `tests/infrastructure/runtime_transforms/test_hook_wrappers.py` (hook-wrapper-unrunnable-fixture-python: the T13 builder; a dead child reads as failed, never as allow) | the file |
| JB.S8.T8 | AC9.1 | `tests/scripts/test_ci.py` (coverage-line-spawns-bare-python: `sys.executable`) | the file |
| JB.S8.T9 | AC9.1 | `tests/cli/commands/test_init__init_with_repo.py`, `tests/cli/commands/test_specs.py`, `tests/cli/commands/test_ci__push_gate_gitflow_resolution.py` (fix-line-posix-bin: expectations through `PLATFORM`) | the files |
| JB.S8.T10 | AC9.1 | `tests/infrastructure/test_ledger_scripts.py`, `tests/features/certification/test_service.py` (fix-line-posix-bin) | the files |
| JB.S8.T11 | AC9.1 | `tests/fixtures/stores.py` (`workspace_cli` is deleted once T1–T10 hold no caller) | `git grep -n workspace_cli -- tests` reports 0 hits |

## Stage JB.S9 — fixes

- Contract: exit is the JB.S7 rows green and unit + integration green on every OS leg; envelope the units named below, plus `specs/bugs/BUGS.jsonl`, written by `bugs.py` only; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S9.T1 | AC9.1 | `dadaia_workspace/core/workspace_layout.py` (one set of root entries the doctor reports and never moves: `.env`, `.git`), `dadaia_workspace/features/spec_context/doctor.py` (`_scan_places`' credential arm reads it), `tests/features/spec_context/test_doctor.py` (marker leaves) | JB.S7.T2. Decider: the set. Sweep: `git grep -nE '"\.(env\|git)"' -- dadaia_workspace/core dadaia_workspace/features/spec_context`. Net ≤ 0 |
| JB.S9.T2 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_fix.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py` (rebase-orphans and task-fix-lineage, redo of 0f466517d: one link step; the task-id link joins the subject id list instead of being a second path) | the JB.S1.T5 rows and the 6d4fe9a1e rows, unchanged. Decider: the link step. Sweep: `git grep -nE '"log"' -- dadaia_workspace/public/skills/dd-bug-resolution/scripts`. Net < 0 against 0f466517d's +84. `bugs.py fix` wall time ≤ 0f466517d^'s, both numbers in the body |
| JB.S9.T3 | AC9.1 | no backticked path; the ledger is written by bugs.py (bug-resolution-law-prescribes-rewriting-asserts, redo of ffb8e937b: the fix was 72a2d7dea (J6.S2.T4); shape 4 `chore(bugs): update … — by J6.S2.T4 (72a2d7dea)`; the ffb8e937b row was born green, and the close row hands it to test-audit) | no RED: shape 4 |
| JB.S9.T4 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` (one public `utc`; an instant with no offset is UTC), `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_quality.py` (its `_utc` is deleted and it imports the one reader), `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py` (marker leaves) | JB.S7.T9 and bb158ef13's row. Decider: `_release_schema.utc`. Sweep: `git grep -n fromisoformat -- dadaia_workspace/public/skills`. Net ≤ 0 |
| JB.S9.T5 | AC9.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (REBUILD of the merge gate's own copies, redo of 4936ab4f6 and 78f9817da: `_gate`'s judged set is every tracked path under the directories the declared line names, read from `<work>` (agent default, unruled; the reviewer judges); `_ledgers` is one fenced doctor call, its refusal relayed verbatim, and the ledger loop leaves; the Owner-tests `test_` name rule becomes the `tests:` globs through `_declared`), `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__define_gate.py` (markers leave) | JB.S7.T3, JB.S7.T4 and the JB.S3.T2 test-path row. Decider: the declared lines and the doctor. Sweep: `git grep -nE 'startswith\("test_"\)\|def _checks' -- dadaia_workspace/public/skills`. Net < 0. Mutation required (gate) |
| JB.S9.T6 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_ledger.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py` (redo of c5e6cb996: `workspace_of` and `workspace_root` collapse into one fenced walk), `tests/public/skills/dd_bug_resolution/scripts/test__ledger.py` (marker leaves) | JB.S7.T6 and the JB.S3.T6 rows. Decider: the one walk. Sweep: `git grep -nE '\.parents\b' -- dadaia_workspace/public/skills`. Net ≤ 0 |
| JB.S9.T7 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `specs/releases/AGENTS.md`, `dadaia_workspace/core/specs_version.py` (canon pin) (release-ship-requires-a-pr-number, the sweep after 7a0027440: `SHIP_PR` and `--pr <n>` become optional everywhere) | the JB.S3.T7 row. Sweep: `git grep -nE -- '--pr <n>\|SHIP_PR\|sha and number' -- dadaia_workspace specs/releases/AGENTS.md`. Net ≤ 0 |
| JB.S9.T8 | AC9.1 | `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md` (step 6: the task is the dispatch unit, ADR 0190), `tests/features/spec_context/test_gate_policy__law_states_what_the_code_does.py` (marker leaves) | JB.S7.T10. Sweep: `git grep -n "job or a task" -- dadaia_workspace specs`. Net ≤ 0 |
| JB.S9.T9 | AC9.1 | no backticked path; the ledger is written by bugs.py (public-law-teaches-the-private-pipeline: shape 4 `chore(bugs): resolve … — by JB.S7.T15 (<sha>)`) | no RED: shape 4. Sweep: the guard's `_PRIVATE_PIPELINE` over `dadaia_workspace/public` and `features/chokepoints`, 0 hits |
| JB.S9.T10 | AC9.1 | no backticked path; the ledger is written by bugs.py (guards-check-not-required-by-live-protection: shape 4, resolved by an operator act; the body carries `gh api` `branches/{develop,main}/protection` `required_status_checks` and `enforce_admins`, re-read at commit time (Guards required, read 2026-10-07T01:58Z); if `enforce_admins` is false, stop and report) | no RED: shape 4 |
| JB.S9.T11 | AC9.1 | `.github/workflows/ci.yml` (both cross legs run the Linux selection; `unit-fast-cross` installs the launcher; the `windows` step and its exit-5 escape leave), `pyproject.toml` (the `windows` marker leaves) (the 8 Windows bugs, resolved in this commit, `--evidence-loop` = the cross-leg command; a red leg at the job push reopens them) | the Windows and macOS legs green with the Linux selection (operator ruling 2026-10-07). Sweep: `git grep -nE 'windows\|-eq 5' -- .github/workflows/ci.yml pyproject.toml tests`. Net < 0 |

## Stage JB.S10 — fixes on the files JB.S9 also writes

- Contract: exit is the JB.S7 rows green and unit + integration green on every OS leg; envelope the units below, plus `specs/bugs/BUGS.jsonl`, written by `bugs.py` only; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S10.T1 | AC9.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (`_remove`), `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py` (`rows`), `scripts/guards/slop.py` (the `_rmdir` allowance row of 1361dd040 leaves), `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py` (markers leave) (redo of 6bdab2056: the remote is the branch's upstream, a failed delete surfaces, and no `suppress`) | JB.S7.T5 and the JB.S3.T4 rows. Decider: the upstream. Sweep: `git grep -nE '"origin"\|check=False\|suppress' -- dadaia_workspace/public/skills/dd-gitflow-default/scripts`. Net < 0 against 6bdab2056's +17 |
| JB.S10.T2 | AC9.1 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` (the stage-1 path rule in `stage_writes` is deleted, ruling 00:26:11Z), `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py` (marker leaves) (test-path-convention-is-python-only, both halves, resolved here) | the JB.S3.T8 row. Decider: the repo's `tests:` line. Sweep: `git grep -nE 'startswith\("tests?_?/?"\)' -- dadaia_workspace/public/skills`. Net < 0 |
| JB.S10.T3 | AC9.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py` (the one reader of `found_in` × status, as an exit with a fix line), `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py` (its ledger loop leaves, and it relays), `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` (`ship` relays) (redo of df9b28641), `tests/public/skills/dd_release_implementation/scripts/test_release.py` (markers leave) | JB.S7.T7 and the JB.S3.T7 row; if the frozen `new` row goes red, stop and report (ADR 0209). Decider: `bugs.py`. Sweep: `git grep -n found_in -- dadaia_workspace/public/skills/*/scripts`. Net ≤ 0. Mutation required (gate) |
| JB.S10.T4 | AC9.1 | `dadaia_workspace/core/workspace_layout.py` (staging renders the source form `.dadaia/.venv/bin/dadaia` from `PLATFORM`: one rendered form at install, the 29 sources untouched), `dadaia_workspace/hooks/venv_guard.py` (`_VENV_BIN` from `PLATFORM`), `dadaia_workspace/public/scripts/pre-push-ci-gate.sh` (probes `Scripts/dadaia.exe` as `_worktree_git.py:48` does, the shell's one named exception to item 11), `dadaia_workspace/public/schemas/handoff-v1.schema.json` (the description names no path), `tests/core/test_workspace_layout.py`, `tests/hooks/test_venv_guard.py` (markers leave) (shipped-law-hardcodes-the-posix-venv-path) | JB.S7.T11 and JB.S7.T12. Decider: `core/platform.py`. Sweep: `git grep -nE 'venv/bin\|"bin"' -- dadaia_workspace ':!*.md'`. Net ≤ 10 lines (one render line, not 29 copies) |

## Stage JB.S11 — close

- Contract: the map, the shipped hashes and the derived docs re-recorded last; exit the CI matrix green on every OS leg, one review; ACs AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JB.S11.T1 | — | `dadaia_workspace/public/entities/behavior-map.json`, `dadaia_workspace/public/templates/shipped-hashes.json`, the derived docs, this file (the `done` line) | `test_behavior_map.py`, `public doctor`. The body carries the sweep summary (each row's grep and its hit count), `test-audit:` (the ffb8e937b born-green row named), `mutation:`, and `bugs.py status`: 0 open for rc-10 |
