# PLAN — Release: 0.5.0, candidate 19

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR6, `AC<n>.<k>` belongs to FR`<n>`; Job `n` carries FR`n`); this PLAN records the as-is review, the DAG with exact write ownership and the notes the main thread needs to dispatch. Paths are repository-relative to `repos/dadaia-workspace/`; `P/` = `dadaia_workspace/`. Tasks: `tasks/job1.md` to `tasks/job6.md`.

**Evidence.** Read at HEAD `b241038f5`. Bug counts are my regex hits of the file name over `fix_files`, `component` and `title` in `specs/bugs/BUGS.jsonl` and `_archive/bugs_histo.jsonl`: order of magnitude, not a census. The as-is review of 2026-10-19 (16 findings, M1 to M16) is folded in; the deletion test is `dd-code-review` SLOP.md. Every `W:` path was checked to exist, or to be a new file the task names.

**Rulings carried (verbatim).** "Run release.py check first (Recommended)"; "alive-only origin read, highest (Recommended)"; "Delete verb-only tests; move the rest (Recommended)"; "Accept both (Recommended)" and "Accept (Recommended)" (the ADRs); pre-mortem rulings A1 to E28 (roadmap-050, 2026-10-19). Agent defaults, unruled and labelled so: R3's three seams and R5's names (§2), the Job 1 seam J1-a (check on the rc tree).

## 1. As-is review

Order: DELETE, REBUILD, UPDATE, KEEP, ADD.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `SpecContextProject.current_branch` and its readers and writers (`core/models/spec_context.py:42`, `json_context_store.py:76,90`, `state_v2.py:85`, `service.py` create/add/remove/dead, `cli/commands/context.py:80-81`, export and import reads) | a stored snapshot, stale in 3 of 5 ALIVE contexts, read only by `alive` | 2 (`context-current-branch-stale-for-alive-repo`, `context-list-current-branch-stale-for-alive-repo`) | DELETE (J4.T9) | a second copy of "which branch" that goes stale; deleting it is the structural fix |
| `features/import_/service.py` (113 lines), `cli/commands/import_.py` (46), `cli/main.py:28,69`, `container.py:14,162` | `dadaia import <file>`: reader, envelope, `_dead_context` | 4 (`import-extracts-manifest-to-root`, `import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees`, `import-raises-keyerror-on-a-record-missing-a-field`, open `import-turns-a-null-repo-url-into-none`) | DELETE (J6.T9) | 4 bugs on one reader; the verb is replaced by `init --from`; the reader's partitions move to the export owner (J6.T4, T6) |
| `verdict.py stats` `_stats.py` `table`, `_window` | private unchecked read of `_RELEASE.json`, per-input guards, own repair act | 6, five of them one `caused_by` chain, plus open `stats-crashes-on-a-release-state-that-breaks-its-schema` | REBUILD R1 (J1.T4) | one release-state schema authority exists (`release.py check`); stats runs it first and keeps no guard |
| `_worktree_new._refuse_unready` (`:53-58`) | parses another branch's blob, reads `phase` | `worktree-new-crashes-on-an-unreadable-release-state` | REBUILD (J1.T5) | a fourth reader of one fact; reaches the same check (checklist item 3) |
| `_worktree_end._ledgers` (`:303-314`), `_kind_checks` (`:420`) | glob, single match, `own` flag in two functions | 4 in the chain, 33 on the file | REBUILD R2 (J2.T2) | one decider keyed on the tree's kind |
| `_worktree_git.py` `work_versions`, `work_version`, `SeveralWork`, `drop_steps` | local refs only; the act re-reads git apart from the version list | 7 (the SeveralWork family) | REBUILD R3 (J4.T6) | the demand changes what the reader reads; one decision yields the kept version and the act |
| `SpecContextService.alive` tail (`service.py:530-562`) | checks out the stored branch, swallows a failure as a WARNING | 2 | REBUILD (J4.T8) | the demand changes its behaviour; about 25 lines become about 8 |
| `JsonContextStore` stamp (`:23-24,108-109`), `state_v2.py:73` | three spellings (3, "2", "2") | 2 (`sa-registry-schema-version-has-three-grammars`, `migrate-and-reconcile-crash-on-a-schema-3-context-registry`) | REBUILD (J4.T10) | a fourth writer of the literal would be the layer; one stamp in `replace_raw` |
| `features/export/service.py` `ExportService` (75), `cli/commands/export.py` | `run()` rewrites the registry, writes `spec-contexts-export-v1` | 1 (`import-export-workspace-flag-re-resolves-through-ancestor-walk`) | REBUILD (J5.T5, T6) | read-only, soft and hard, and the format's one owner; a hard mode on today's `run` is a flag plus a second path |
| `cli/commands/init.py` `init`, `InitPlan`, `_plan` | one harness, optional `--repo`, fix lines from `InitPlan.command` | 6, four of them one family (a fix line that drops a flag) | REBUILD (J6.T8) | `--from` is a flag with an exclusion and a 4th harness source; it enters `InitPlan` only |
| `core/workspace_layout.py:200` `dist` Zone row | canon `{spec-contexts.json}` | 0 on the row | UPDATE (J3.T11) | admits `<registered slug>/` and the hard archive (A1) |
| `cli/commands/context.py` `_ctx_to_dict`, `state_v2.py:85`, `core/models/spec_context.py:12` | `stored_branch` fallback; row copy; `EXPORT_SCHEMA_VERSION` | 2 | UPDATE (J4.T9, J5.T5) | delete two lines; the literal becomes `export-v1` |
| `service.py` `_dead_preflight`, `delete` | dead refuses every row with an `exit`; delete removes the registry row | 7 resolved dead fixes | UPDATE (J3.T10) | dead skips `paused` rows, delete refuses while a bundle sits in `dist/<repo>/`; nothing else is added to `dead` |
| `worktree.py` `main` | verbs `new merge clean sync hash list` | 4, none on registration | UPDATE (J3.T7-T9, T12) | two parsers, two dispatch lines, `paused_rows` in `list`; docstring `:4` |
| law and docs: `public/data/worktrees-AGENTS.md`, `dd-gitflow-default/SKILL.md:86`, `dd-handoff-emitter/SKILL.md:55`, `dd-cli-library/SKILL.md:28,30`, `CONSUMER_VALIDATION_RECIPE.md:27`, `docs/getting-started.md:126`, `docs/cli.md` (generated) | verb lists, exits, the stats line | 3 law-drift bugs | UPDATE (J1.T6, J3.T12, J5.T8, J6.T10) | text moves with the job that causes it |
| install-count pins (`test_public__characterization.py:66`, `test_init__characterization.py:28,38`) | 138 Linux / 161 Windows | `asset-count-pins-miss-the-readout-script` | UPDATE (J3.T13, J5.T8) | +1 asset each (`_worktree_pause.py`, the schema) |
| `_worktree_end.py` outside `_ledgers`; `verdict.py` stats wiring; `_release_store.read_state`, `_release_schema.releases`; `register`; `push_gate.py`, `git_objects.py`, `container.py:90-118`; `_release_phase._refuse_open_worktrees` | merge gates; the stats seam; the release skill's own readers; the one insert guard; the pre-push object source and denylist | many, none in scope | KEEP | the SPEC keeps `read_state` (B11); the object source and `kind != "rc"` filter already do what the new code needs; `_worktree_end.py` must not grow, J3 only imports from it |
| `_worktree_pause.py` (new), `public/schemas/export-v1.schema.json` (new) | none | none | ADD | no unit carries a pause or a bundle; no schema covers the artifact; +2 install assets |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| is a release-state document valid | `release.py check` (`_release_tree.py`, `_release_schema.py`) | `_stats.table`, `_worktree_new._refuse_unready` | `_stats.py:91-94` parse and repair act; `_worktree_new`'s blob parse; the bug `stats-crashes-on-a-release-state-that-breaks-its-schema` |
| which scripts judge a tree's `specs/` | one decider in `_worktree_end.py`, bound once per tree kind in `_kind_checks` | the rc and backlog rows | the `own` flag, the `ls-files` filter on it, the single-match rule |
| which work branch a repo has, which wins | `_worktree_git.py` `work_versions`/`work_version`, one choice rule (`SeveralWork.keep`), reached by the package through `core/gitflow.py` | `alive` (via `origin_work_branch`), `baseline`, `dead`, `ci`, `specs init`, `worktree new`, onboarding | the stored `current_branch`; 0171's "highest on origin" as a second rule; `drop_steps`' own git reads |
| which branch a repo is on now | `GitSubprocessClient.current_branch` / `repo_live_status` | `context show/list` | `ctx.current_branch` reads |
| is a repo url obtainable at registration | `SpecContextService.register` (`_refuse_slug`) | the artifact reader (coerces null to `""`) | the reader's own null handling |
| the `export-v1` artifact, written and read | `features/export/service.py` `ExportService` + `public/schemas/export-v1.schema.json` through `_ledger.validate` | `cli/commands/export.py`, `cli/commands/init.py` | `features/import_/**`, `_refresh_branches`, `spec-contexts-export-v1` |
| a commits-only bundle of a tree | `write_bundle` in `_worktree_pause.py` | `worktree pause`, `export --hard` (by `load_owner`) | a second writer |
| when a tree may leave | `worktrees/AGENTS.md` §3: merge, clean, pause | `context dead` (skips `paused` rows) | ADR 0173's `dead --snapshot` |
| what may live in `.dadaia/dist/` | `core/workspace_layout.py` Zone `dist` | doctor, the gate, the rendered `.dadaia/AGENTS.md` table | the one-name canon |
| the registry `schema_version` | `JsonContextStore.replace_raw` | `state_v2`, `_EMPTY_CONTEXTS` (no literal) | the two other spellings |

## DAG

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | — | 1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` |
| Job 2 | — | 1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__tree_ledgers.py` |
| Job 3 | — | 1 | `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/features/spec_context/service.py`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_pause.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py`, `docs/getting-started.md`, `tests/cli/commands/test_init__characterization.py`, `tests/cli/commands/test_public__characterization.py`, `tests/core/test_workspace_layout__workspace_layout_zones.py`, `tests/features/spec_context/test_service__context_dead_holds.py`, `tests/features/spec_context/test_service__spec_context_service.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_pause.py`, `tests/public/skills/dd_release_implementation/scripts/test__release_phase__fix_line.py` |
| Job 4 | Job 3 | 2 | `dadaia_workspace/cli/commands/context.py`, `dadaia_workspace/core/gitflow.py`, `dadaia_workspace/core/models/spec_context.py`, `dadaia_workspace/features/export/service.py`, `dadaia_workspace/features/import_/service.py`, `dadaia_workspace/features/migrate/state_v2.py`, `dadaia_workspace/features/spec_context/service.py`, `dadaia_workspace/infrastructure/json_context_store.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `tests/cli/commands/test_context.py`, `tests/cli/commands/test_context__characterization.py`, `tests/cli/commands/test_context__cli_output_stability.py`, `tests/cli/commands/test_context__context_show_live_branch.py`, `tests/cli/commands/test_doctor__doctor_scan_cli.py`, `tests/cli/commands/test_export.py`, `tests/core/test_gitflow.py`, `tests/features/export/test_service.py`, `tests/features/import_/test_service.py`, `tests/features/migrate/test_state_v2.py`, `tests/features/spec_context/test_doctor__spec_context_doctor.py`, `tests/features/spec_context/test_doctor__unfixable_findings_carry_their_own_fix.py`, `tests/features/spec_context/test_service__context_alive_branch.py`, `tests/features/spec_context/test_service__service_repo_url.py`, `tests/infrastructure/test_json_context_store.py`, `tests/infrastructure/test_json_context_store__registry_version_grammar.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_git.py` |
| Job 5 | Job 3, Job 4 | 3 | `dadaia_workspace/cli/commands/export.py`, `dadaia_workspace/container.py`, `dadaia_workspace/core/models/spec_context.py`, `dadaia_workspace/features/export/service.py`, `dadaia_workspace/public/schemas/export-v1.schema.json`, `docs/cli.md`, `tests/cli/commands/test_export.py`, `tests/cli/commands/test_init__characterization.py`, `tests/cli/commands/test_public__characterization.py`, `tests/features/export/test_export_hard.py`, `tests/features/export/test_export_schema.py`, `tests/features/export/test_service.py` |
| Job 6 | Job 5 | 4 | `dadaia_workspace/cli/commands/import_.py`, `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/cli/main.py`, `dadaia_workspace/container.py`, `dadaia_workspace/core/exceptions.py`, `dadaia_workspace/core/models/spec_context.py`, `dadaia_workspace/features/export/service.py`, `dadaia_workspace/features/import_/__init__.py`, `dadaia_workspace/features/import_/service.py`, `dadaia_workspace/features/spec_context/service.py`, `dadaia_workspace/public/skills/dd-cli-library/SKILL.md`, `docs/cli.md`, `scripts/CONSUMER_VALIDATION_RECIPE.md`, `tests/cli/commands/test_export.py`, `tests/cli/commands/test_help.py`, `tests/cli/commands/test_init__init_from.py`, `tests/cli/commands/test_init__init_plan.py`, `tests/cli/test_main__refusals_carry_a_fix.py`, `tests/fakes.py`, `tests/features/export/test_reader.py`, `tests/features/import_/test_service.py`, `tests/test_container.py` |

Edges and why. Job 4 waits on Job 3 (`service.py`: dead and delete in Job 3, alive and the field in Job 4). Job 5 waits on Job 3 (`write_bundle`) and Job 4 (`export/service.py`, the model). Job 6 waits on Job 5 (`container.py`, `docs/cli.md`, `export/service.py`, `test_export.py`). The `W:` sets inside wave 1 are disjoint (`release.py check` verifies it). The longest chain is Job 3, 4, 5, 6 (four waves). The SPEC's wave ranking (law and dev loop, foundation, features) maps to waves 1, 2, 3 to 4. Jobs 1 and 2 are REBUILDs and carry no dependency; Job 1 is first in the order the SPEC gives and runs with Jobs 2 and 3.

## 2. Notes for dispatch

- **Gate law.** The repo `verify:` is `python scripts/ci.py job` (stages lint, typecheck, guards, unit-fast, doctor: `scripts/ci.py:88`; rc-18's PLAN §2 cites a median of 1m52, rc-17 metric 3, not re-measured here); no `verify:` change. Each job file states the definition of done: that run, the touched test directories, the own-diff self-check, the sweep greps; no preflight, no full CI line.
- **Test-first.** A RED task touches only test files; an implementation task none. Test-class tasks (fixture sweeps, pin moves, verb-only deletions) are `test(...)` commits naming the ruling.
- **R3 seams, settled.** (a) Bundle basis: `git bundle create <file> <branch> --not --remotes=origin` (A5), verified; one writer, `write_bundle`. (b) Scan input: a scratch bare repo under `.dadaia/tmp/` with alternates to the repo's object store, one `refs/remotes/origin/p<i>` per prerequisite sha of the bundle header, `git bundle unbundle`, then the pre-push matcher's `new_objects`; it needs no new reader, writes nothing into `repos/<slug>` and excludes exactly what the bundle does not carry. (c) A pushed lane or `wt-rc`: pause deletes the local ref only; origin's stays; resume refuses while the local branch exists and sets no upstream; a branch origin already holds in full gives an empty range, git refuses the bundle and pause refuses with nothing touched (the fix names `merge`).
- **R5 names, settled.** The soft artifact keeps `.dadaia/dist/spec-contexts.json` (one rename deleted; an old file there refuses by its `schema_version`). The hard archive is `.dadaia/dist/workspace-export.tar.gz`; its members are `spec-contexts.json` and `<repo>/<name>.bundle`. The `dist` canon admits those two names and `<registered slug>/` (A1).
- **Seam J1-a.** `_refuse_unready` runs the check on the rc tree's `specs/`; if the tree can be absent while its branch exists, T5 reports it before editing.
- **Import tests.** J6.T4 moves, J6.T5 deletes; the move precedes the delete so no partition is lost.
- **Reproject.** After Job 3 merges, `public install` and `public doctor` (`[ok] public-privacy`); never hand-edit a projected file.
- **Closure acts that are not tasks.** The memory pass (SPEC §Closure, PE), the four backlog exits, the two Origin bugs resolved, the ADR state, the readout table of `verdict.py stats 0.5.0-rc19` after the memory pass (AC1.5).
- **Pre-mortem answers.** A1: J3.T6, T10, T11. A2: J3.T2. A3: J3.T7. A4: J3.T4, T9, T10. A5: J3.T1, T7. B6 to B12: Job 1 (B12 is J1.T6). C13 to C22: the consumer's own job (help text, `dd-cli-library`, `CONSUMER_VALIDATION_RECIPE.md`: J6.T10; getting-started, `worktree.py:4`: J3.T12; docstrings: J6.T9, `tests/fakes.py:76`: J6.T5); the atoms: closure (§3). C18: J5.T1, T2. C20: J4.T2, T7. D23: SPEC §5 states it, no task. E26 to E28: J5.T3, T6, J6.T7.

## 3. Open points and SPEC findings

- **Atoms in a job.** SPEC AC6.5 and §Closure say the atoms citing `dadaia import` change in FR6's job. `release.py check` refuses a `specs/memory` path in a task's `W:` (`_release_schema.py:313`), and doctor reports a dead citation as a WARNING that is "a closure finding, never a mid-task red" (`doctor_memory.py:255`). They move in the PE's closure memory pass, and no job `verify:` goes red on them.
- **AC5.5 reader.** The SPEC puts "writes and reads" in FR5; the reader's only consumer and its tests are FR6, so Job 5 ships the writer and the schema and Job 6 moves the reader into `ExportService` (a half-built reader in Job 5 would have no caller and would pre-empt the RED of AC6.1).
- **AC4.4 assert.** `tests/core/test_gitflow.py:205` already states the contract; it changed in `301cc9f2c` under the main-thread ruling of 2026-10-18, so no assert moves in FR4 and the SPEC's bug-window row (pattern (a)) is satisfied by that ruling; J4.T3 keeps the assert byte for byte.
- **AC4.2.** Its first case passes today (it guards the widening); only the origin-prefix cases are red.
- **Order inside Job 4.** T7 (ADD `origin_work_branch`) precedes the DELETE T9 because T8 calls it.

## 4. Net lines and the stated reasons

Estimates from the current line counts, not measurements; the reviewer reads `git diff --stat` per unit. Production is `dadaia_workspace/**`.

| job | expectation | reason |
|---|---|---|
| 1 | `_stats.py` -2 to -4 (`:91-94` out, a check call and relay in), `_worktree_new.py` -1 to -3 | REBUILD, at most 0 |
| 2 | `_ledgers` -4 to -8 | REBUILD, at most 0 |
| 3 | about +190 (`_worktree_pause.py` +160, `service.py` +12, layout +6) | a new capability no unit carries (SPEC §5); `_worktree_end.py` untouched |
| 4 | about -45 (the field and the alive tail out, `origin_work_branch` +10, the reader's prefix +8) | DELETE and REBUILD |
| 5 | about +130 | a new capability (hard export, the scan, the schema) |
| 6 | about -40 (`import_` -159, the reader moved, extraction +40, `init` +40) | the deletion offsets `--from` |
