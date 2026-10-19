# SPEC — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-19
**Origin:** backlog:spec-context-branch-field-deleted,context-dead-snapshots-open-worktrees,export-soft-and-hard,init-from-export; bugs:import-turns-a-null-repo-url-into-none,stats-crashes-on-a-release-state-that-breaks-its-schema

---

## Bug window review

**Window:** fixes closed after rc-18's window. rc-18's table ended with the two records resolved on 2026-10-18 before its definition (`asset-count-pins-miss-the-readout-script`, `unclosed-quote-test-hand-spells-the-sync-path`), judged there. This window holds the 8 records closed from rc-18's definition (2026-10-18T16:34:46Z) to rc-19's birth: 2 live in `BUGS.jsonl`, 6 archived. The push-gate remedy re-committed the rc-18 range as one squash, `995ac1256`. The two live records were re-pointed to it (`7c3ba5d1d`, `1f881d404`), so each is judged by its `fix_files` inside `995ac1256` and by the original commit the update replaced. The six archived records still name their original commits. Each was read with `git show`, and its code was checked present at `995ac1256`. Verdicts: 2 KEEP, 6 REBUILD in three units, R1-R3.

| bug id | fix sha (original) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `stats-invents-a-table-for-a-missing-candidate` | `c987ad086` | `_stats.py` `table`, `_window` | REBUILD R1 | the rc-18 R2/R3 rebuild (n/a for a missing candidate, CLOSURE-to-CLOSURE window, counts read by running `bugs.py`); three bugs on the same read of the release state followed it inside rc-18 |
| `stats-crashes-on-a-candidate-without-a-release-folder` | `242d0b830` | same | REBUILD R1 | `caused_by: J5.T2`; it adds a branch for one input, the missing file, which is still `if path.is_file() else {}` (`_stats.py:94`), while the read stays unguarded for the next bad input |
| `stats-crashes-on-an-unreadable-release-state` | `5621889c5` | same | REBUILD R1 | `caused_by` the row above: a second guard on the same read (`parse_object` over `read_text`, `_stats.py:92-94`); the open Origin bug `stats-crashes-on-a-release-state-that-breaks-its-schema` is the third bad input on it (`_window`, `int(e["candidate"][3:])`, `e["ts"]`, `_stats.py:46-50`); four bugs on one read |
| `merge-checks-a-tree-ledger-with-the-instance-schema` | `187950dea`, reshaped by `2b583acf5` (J5.T15), `9ca521ca6` (J5.T16) | `_worktree_end.py` `_ledgers` | REBUILD R2 | the rc-18 R1 rebuild; two review rounds reshaped it, and the next row is a bug it caused |
| `merge-runs-a-tree-carried-ledger-script-without-verify` | `a8abf7416` | `_ledgers`, `_kind_checks` | REBUILD R2 | `caused_by` the row above; it adds a flag, `own: bool`, set by the caller as `kind_of(name) == "rc"` (`_worktree_end.py:420`) and read inside a comprehension filter (`if h and own`, `:311`). One question, which scripts judge this tree's ledgers, is decided by three stacked conditions in two functions: the `ls-files` glob, the single match and the flag. This is the unit's 4th bug in the chain `trio-status-canon-judged-outside-the-define-merge-gate` -> `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree` -> these two |
| `merge-gate-lets-a-test-commit-carry-source` | `995ac1256` (`09df2bff6`) | `_worktree_end.py` `_refuse_implementation_tests` | KEEP, noted | the missing half of the RED-separation rule, in the same loop with the same `_is_test_path` predicate; its RED test `5ab19c1aa` only adds lines; no other bug on the function since `freeze-deadlocks-a-repo-without-a-tests-line` (2026-10-08). Noted: its two refusal blocks mirror each other (`:259-276` at HEAD) and fold into one comparison of the path's class with the commit's (intake) |
| `branch-d-fix-line-judges-head-not-the-upstream` | `995ac1256` (`6bb57a885`) | `_worktree_git.py` `SeveralWork` fix line, `drop_steps` | REBUILD R3 | two patterns hit. (a) Its RED commit `301cc9f2c` changed an existing assert: `tests/core/test_gitflow.py:205` drops the `-d` step from the expected fix line, a contract change made inside a fix. (b) It is the 5th bug on the line, after `several-work-fix-deletes-the-checked-out-branch`, `several-work-rework-leaves-two-gitflow-tests-on-the-old-fix-line`, `several-work-agent-action-fix-breaks-the-verbatim-fix-runner-row` and `several-work-branches-blank-the-doctor-report`. ADR 0270 changes the reader `work_versions` (`:88-92`) to take a ref prefix; `drop_steps` (`:110-119`) re-reads git apart from the version list and judges local branches only |
| `bugs-check-misses-a-record-both-live-and-archived` | `20fefc4a7` | `_bugs_check.py` `findings_for`, `_bugs_write.py` `append` | KEEP, noted | `caused_by: none`. The rule is new, ruled by the operator on 2026-10-19 ("Event lines aren't records (Recommended)"). The fix deletes `archived_ids` and puts every archive read on one reader, `_archive_lines`; its `events` flag tells apart the two archive line shapes, which the same ruling keeps. The old asserts changed in `c96ad777d` were born in this bug's own RED commits (`a6ec66063`, `d3a018380`). Noted: "id taken" is still decided twice, in `append` (`taken`, `_bugs_write.py:71`) and in `findings_for`, which every write runs; `append`'s copy exists for its `--bug-id` fix line (intake) |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened):
- R1, `_stats.py`'s read of the release state: rc-19's first job. Operator, 2026-10-19: "Register, fold into case 2 in rc-19 (Recommended)", then "Run release.py check first (Recommended)". One REBUILD in which stats runs `release.py check` before it parses (FR1). It closes the open Origin bug and deletes the per-input guards of the three rows.
- R2, `_ledgers`: one decider names the ledger scripts that judge a tree. The `own` flag, the glob and the single-match rule are deleted. The contract tests of the four chain bugs stay green, unloosened.
- R3, the `SeveralWork` fix line: rebuilt together with ADR 0270's prefixed reader, so one decision names the kept work branch and the act over the local branches (FR4). The contract tests of `301cc9f2c` and of the four earlier bugs stay green.

## 1. Problem

Moving a workspace to a new machine or a teammate is a manual recipe (`init`, `dadaia import`, `context alive` per context) that carries no harness and no work in flight. `dadaia export` rewrites the registry as a side effect, and `dadaia import` stores a null `repo_url` as the text `'None'` (open bug). `context alive` checks out a stored `current_branch` that is stale in 3 of 5 ALIVE contexts (backlog measure) and swallows a failed checkout as a WARNING. Work in a lane or a `wt-rc` cannot be set aside: a tree leaves only by merge or clean, and `context dead` refuses while one is open. The operator ruled the full chain into 0.5.0 (roadmap Q4/Q5) after a deep review and three grills; ADRs 0270, 0271 and 0272 restate ADRs 0171, 0173 and 0175 against today's code. Two readers also break their contract: `verdict.py stats` crashes on a release state that breaks its schema (open bug), and the bug window review found two more units patched rather than rebuilt (R2, R3).

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | the `measured_by` checks of ADRs 0270, 0271, 0272 | every one green at the rc-19 PR head | the tests named in each record; 0270's grep |
| 2 | Origin bugs | both resolved and archived | `bugs.py status` |
| 3 | `dadaia import` | absent from `dadaia --help` and `docs/cli.md` | `dadaia help tree` |
| 4 | REBUILDs R1-R3 | each lands as a REBUILD; net lines <= 0 on `_stats.py`, `_ledgers`, the several-work decision | `git diff --stat` per unit |
| 5 | readout metrics 1, 2, 4, 6, 7, 9 | beside rc-18's 6/6 (100%), 2/13 (15%), n/a, 15, 0, 6 and the rc-18 targets (<= 20%, >= 70%, <= 4 h, 0, 0, 0) | `verdict.py stats 0.5.0-rc19`; baseline: the rc-18 closure summary, `_RELEASE.json` 2026-10-19T01:55:53Z, read at `df96b6d7b` |

## 3. Non-goals

- No `context dead --snapshot`, snapshots zone, WIP commit, archive tag or visibility probe (`gh`); `context dead` is unchanged (ADR 0271).
- No package-version pin and nothing installed by `init --from`: only the `export-v1` format is pinned (ADR 0272).
- Job and task trees are never paused nor carried; uncommitted work is never carried.
- Only `verdict.py stats` gains the check-first read; `_worktree_new._refuse_unready` and the other release-state readers stay (the ruling names stats; `_worktree_new` reads one field of another branch's blob).
- Every caller but `context alive` keeps reading local work branches; cleaning stale origin work branches of consumer repos is not here.
- The two push-gate bugs, the PR #298 Windows red and the six archived `fix_sha` repairs ride their own hotfix lanes (2026-10-19 rulings), outside this Origin.
- `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original` stays open; `--from` is the supported path, the copy defect is not fixed here.

## 4. Requirements

Wave ranking, by the pick: (1) law, skills and dev loop: FR1 (Job 1), FR2, FR3; (2) shared foundation: FR4; (3) features and bugs: FR5, FR6; (4) promote-facing: `docs/cli.md` regeneration and the install-count pins move with FR3, FR5 and FR6 in the job that causes them; memory and backlog exits at closure.

### FR1 — stats refuses a release state that breaks its schema (bug `stats-crashes-on-a-release-state-that-breaks-its-schema`, R1)

Operator, 2026-10-19: "Run release.py check first (Recommended)": stats runs `release.py check` through its existing `_script` and refuses with check's fix line, then parses; no new unit, no verb.

- AC1.1 RED: `verdict.py stats 0.5.0-rc18` on a `_RELEASE.json` that parses but holds (a) a log entry without `ts`, (b) a log `candidate` not shaped `rc-<N>`, (c) a log entry that is not an object exits 1 with no traceback and prints `[error]` plus exactly one `fix:` line, both `release.py check`'s for that finding. A milestone without `sha` is not a case: the schema allows it and stats reads `n/a` (as-is M15). Test: unit, one case per shape.
- AC1.2 Stats runs `release.py check` before it parses; its own repair act and the parse refusal of `_stats.py:91-94` go, and `_window` adds no guard. Test: unit (AC1.1's cases).
- AC1.3 The contract tests of the five prior stats fixes stay green: a version with no release folder still reads `n/a` throughout and exits 0. The unreadable-state cases (`{bad`, `[]`, non-UTF-8) keep exit 1 and one fix line; their expected message and fix line become check's by the ruling above, moved in a `test(...)` commit naming it. Test: unit (existing).

### FR2 — one decider names a tree's ledger scripts (R2)

- AC2.1 One decider names the scripts whose `check` judges a tree's `specs/` on merge: on a `wt-rc` the copies the tree tracks, else the instance's; a backlog lane always the instance's; an associated repo none. The `own` flag, the `ls-files` filter on it and the stacked single-match rule (`_worktree_end.py:303-314,420`) go. Test: integration.
- AC2.2 The contract tests of `trio-status-canon-judged-outside-the-define-merge-gate`, `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree`, `merge-checks-a-tree-ledger-with-the-instance-schema` and `merge-runs-a-tree-carried-ledger-script-without-verify` stay green, unloosened. Test: integration (existing).

### FR3 — `dadaia worktree pause` and `resume` (ADR 0271; backlog `context-dead-snapshots-open-worktrees`)

- AC3.1 RED: `worktree pause <path>` on a clean lane (`wt-backlog-<slug>`, `wt-hotfix-<bug-id>`) and on a clean `wt-rc` with no open child writes a commits-only bundle at `.dadaia/dist/<repo>/<name>.bundle`, verifies it, removes the tree and deletes its local branch; `worktree resume <path>` recreates the branch at the same tip and the tree, then deletes the bundle. Test: integration.
- AC3.2 Pause refuses with nothing touched: a dirty tree (one fix line: commit first), a job or task path, a `wt-rc` with an open tree below it, a failed bundle write or verify; ignored files refuse unless `--keep` or `--drop` (inherits `_kept`). It makes no commit. Test: integration.
- AC3.3 `context dead` refuses with the tree open and passes its worktree preflight after the pause; its fix line keeps naming merge and clean, and the law names pause as the third exit (as-is M10). Test: integration.
- AC3.4 Resume creates the `wt/*` branch through the CLI marker, so the reference-transaction gate passes it; resuming a lane or `wt-rc` whose branch was pushed succeeds, the PLAN stating the remote-branch rule (R3 seam). Test: integration.
- AC3.5 The `dist` zone admits the `<repo>/` bundle folders, the hard archive and the soft JSON; names and glob are the PLAN's (R5 seam). `worktrees/AGENTS.md` names `pause` and `resume` in its verb list, its exit line and its before-dead line; `dd-gitflow-default`'s verb list too. Test: unit for the zone; none for law text.

### FR4 — the stored branch is deleted; `alive` takes the highest origin work branch (ADRs 0171 + 0270; backlog `spec-context-branch-field-deleted`; R3)

Operator, 2026-10-19: "alive-only origin read, highest (Recommended)".

- AC4.1 RED: reviving a DEAD context whose clone's origin holds one work branch checks it out; two, the highest; none, the integration branch. A failed checkout refuses with one fix line, never a stderr WARNING (as-is M12). Test: integration.
- AC4.2 RED: a repo with local `{0.8.0}` and origin `{0.6.0, 0.8.0}` gives every local caller (`worktree new`, `context baseline`, `context dead`, `specs init`, `ci`, the doctor's first-pass fix) `0.8.0`, no SeveralWork (as-is M1 repro). Test: unit.
- AC4.3 `work_versions` takes the ref prefix it reads; only `alive` passes the origin prefix and takes `SeveralWork.keep`; no other unit holds a "highest" rule. Test: unit.
- AC4.4 R3: one decision in `_worktree_git.py` yields the kept version and the act over the local branches, which `drop_steps` stops re-deriving from its own git reads. The contract tests of the five SeveralWork bugs stay green, unloosened; the assert `301cc9f2c` changed (`tests/core/test_gitflow.py:205`) is held to the two-pass contract of the rc-18 closure ruling, which the PLAN cites. Test: unit.
- AC4.5 `current_branch` leaves `SpecContextProject`, the store's row mapping, `context show/list` (`stored_branch` and the stored fallback), `create`, `add_repo`/`remove_repo`, `alive`, `dead`, `migrate/state_v2`, export and the import reader. ADR 0270's grep prints only the `RepoLiveStatus` live read, the `repo_live_status` docstring reworded (as-is M4). Test: none, the grep is the evidence; output pins move with the field by ADR 0171's acceptance.
- AC4.6 `JsonContextStore` spells `schema_version` once, stamped in its one write path; `_EMPTY_CONTEXTS` and `state_v2` stop spelling it; no migration ships; a row keeps the dead key until written and no reader reads it. Test: unit.

### FR5 — `dadaia export`: read-only, soft and hard (ADRs 0175 + 0272; backlog `export-soft-and-hard`)

- AC5.1 RED: `dadaia export` writes the soft artifact: `schema_version` `export-v1`, contexts (slug, name, state, main repo url, associated `[{slug, url}]`), `dadaia_version` and the harnesses of `harness_profile.json`; the registry is byte-identical after it (`_refresh_branches` deleted). Test: integration.
- AC5.2 A main or associated repo with no remote is recorded with url `null` (one rule, R6). Test: unit.
- AC5.3 `dadaia export --hard` writes one `.tar.gz` in `.dadaia/dist/` holding only the soft JSON and `<repo>/<name>.bundle` members: a commits-only bundle of each open lane and `wt-rc` made at export time, and each pause bundle. A dirty open tree refuses with pause's commit-first fix line and the tree stays; job and task trees are not carried. Test: integration.
- AC5.4 The hard export scans the bundles' objects with the pre-push's denylist and baseline; a planted secret refuses and leaves no archive. Export runs no visibility probe and writes no ref into `repos/<slug>` (scan input: R3 seam). Test: integration.
- AC5.5 Both artifacts' JSON validates against one shipped `export-v1` schema; `ExportService` is the one owner that writes and reads the artifact, and bundles come from pause's one writer. Test: unit.

### FR6 — `init DIR --from <artifact>`; `dadaia import` deleted (ADRs 0175 + 0272; backlog `init-from-export`; bug `import-turns-a-null-repo-url-into-none`)

- AC6.1 RED, at the `init --from` artifact reader: a context whose `repo_url` is null is never registered and never stored as `'None'`; it is listed `not replicated: no remote` with one fix line (add a remote, then re-export). The reader coerces null to `""` and `register` stays the one decider (as-is M7); a null associated url follows the same rule. Test: unit.
- AC6.2 `init DIR --from` on a soft and on a hard artifact into a fresh workspace installs every harness the artifact names, registers its contexts DEAD through `register`, lists the repos `git ls-remote` cannot reach and prints `context alive <ctx>` for each context ALIVE in the artifact. A hard artifact's members are validated before extraction (fixed names only, no absolute path, no `..`, no link; stdlib `tarfile` `filter="data"`) and its bundles land in `.dadaia/dist/<repo>/<name>.bundle`; then `context alive`, `worktree resume` and doctor report no finding. Test: integration.
- AC6.3 An artifact with any other `schema_version` refuses with one fix line: re-export with the current dadaia-workspace. `dadaia_version` is read for display only. Test: unit.
- AC6.4 `--from` with `--repo` refuses with one fix line; every fix line `init` prints carries `--from` when given, built by `InitPlan.command` alone; the contract tests of the init fix-line family stay green. Test: unit.
- AC6.5 `dadaia import` is gone: `features/import_/`, `cli/commands/import_.py`, its `cli/main.py` registration and `build_import_service`; `docs/cli.md` is regenerated; `dd-cli-library`'s verb index and `scripts/CONSUMER_VALIDATION_RECIPE.md` stop naming it. Test: unit (the help-tree pin).

### Replaces

- `verdict.py stats` parsing `_RELEASE.json` itself behind per-input guards and its own repair act.
- `_ledgers`' `own` flag, its `ls-files` filter and the stacked single-match rule.
- The several-work act assembled by `drop_steps` from its own git reads apart from the version list.
- `context alive` checking out the stored `current_branch` and swallowing a failed checkout as a WARNING.
- The registry field `current_branch`, `stored_branch` in `context show/list --json`, and the stored fallback.
- Three spellings of the registry `schema_version` (`3`, `"2"`, `"2"`).
- `dadaia export` refreshing the registry's branches; the `spec-contexts-export-v1` format with `branch` and `last_sync_at`.
- `dadaia import <file>` and its reader.
- "A tree leaves only by `WT merge` or `WT clean`" (`worktrees/AGENTS.md` §3): pause is a third exit.
- The `dist` canon admitting only `spec-contexts.json`.
- `init` taking its harness only from the flag, the profile or the prompt.

### Closure

- Backlog exits, `delivered` `--release 0.5.0`: `spec-context-branch-field-deleted`, `context-dead-snapshots-open-worktrees`, `export-soft-and-hard`, `init-from-export`. Both Origin bugs resolved and archived.
- ADRs (main thread, on the 2026-10-19 rulings): 0171 and 0270 accepted (0270 amends 0171); 0271 accepted, superseding 0173 and amending 0172; 0175 and 0272 accepted (0272 amends 0175).
- Memory pass (`MEMORY-UPDATE.md`), every atom the as-is review names (M13, M14) plus the stats readers: `platform/context-portability.md` (rewritten: soft/hard export, `init --from`, its prerequisites; its catalog entry maps the deleted `features/import_/**`), `platform/context-management.md` (`:21,31,34,46`: alive, dead, import), `platform/workspace-init.md` (`--from`), `platform/workspace-doctor.md` (the `dist` zone), `sdd/worktrees.md` (`:23` the prefixed reader, `:33` the ledger decider, `:40,45` the verb list), `sdd/release-lifecycle.md` and `agents/agent-comms.md` (stats refuses on check's finding), `catalog.json` (`:528-544`), `index.md` (`:50`).

## 5. Constraints and risks

- Order: Job 1 is FR1. FR4 precedes FR5 and FR6, which edit the same files; FR5 precedes FR6 (one artifact owner, then its reader in `init`).
- `_worktree_end.py` (33 bugs) must not grow: pause lives in its own unit, and R2 shrinks `_ledgers`.
- Net lines <= 0 for FR1, FR2, FR4 and FR6 (the `import_` deletion offsets `--from`); FR3 and FR5 are net additions, a new capability no unit carries.
- Public boundary: nothing requires a remote, CI, `gh` or a vendor CLI; the scan and bundles are local; platform facts go through `core/platform.py`, archive members are POSIX names joined by `Path` (R7).
- Stats refuses on any `release.py check` error, an unrelated tree finding included: the ruled trade-off of the check-first read.
- `alive` takes the highest origin work branch even when it is stale; `fetch --prune` drops a deleted one (ADR 0270).
- An old `spec-contexts-export-v1` artifact on disk refuses with the re-export fix line.
- Two new assets (`_worktree_pause.py`, `export-v1.schema.json`) move the install-count pins, which run outside `ci.py job`; the implementer runs those two test files by name (`asset-count-pins-miss-the-readout-script`).
- Consumers of each changed public name (`dadaia import`, the artifact format, the registry key, the worktree verb list, `init`'s grammar and fix lines) are listed in the as-is review §4; a read-only `dd-researcher` pre-mortem precedes approval and the PLAN answers each hit.
- Hotfix lanes in flight on `feature/0.5.0` may touch these files; the `wt-rc` takes them by `WT sync`.

## 6. Open questions

- For the main thread: the root map §1 deletes a test only on the operator's order. Does the acceptance of 0175 + 0272 ("dadaia import is deleted") order the deletion of `dadaia import`'s own tests (`tests/features/import_/test_service.py`, the import rows of `tests/cli/commands/test_export.py`, `tests/cli/test_main__refusals_carry_a_fix.py:150`, `tests/test_container.py`)? Recommended: yes for rows that test only the deleted verb; a partition still owned by the artifact reader moves to the `init --from` tests in a `test(...)` commit naming the ruling.
- R3 (bundle basis, scratch-repo scan, a pushed lane on pause) and R5 (artifact names, the `dist/<repo>/` depth-2 glob) are agent defaults, PLAN seams for the sr, not operator questions.
