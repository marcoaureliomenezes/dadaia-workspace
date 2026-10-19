# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-19
**Origin:** backlog:spec-context-branch-field-deleted,context-dead-snapshots-open-worktrees,export-soft-and-hard,init-from-export; bugs:import-turns-a-null-repo-url-into-none,stats-crashes-on-a-release-state-that-breaks-its-schema,worktree-sync-orphans-the-fix-sha-a-lanes-resolve-cites,push-gate-rewrite-orphans-shas-cited-in-the-range,check-relay-reads-a-pass-from-text-not-exit-status,rc-tree-absent-fix-line-does-not-clear-its-refusal,export-scratch-dir-failure-prints-no-fix-line,scan-refusal-hides-gits-reason

---

## Bug window review

**Window:** the 8 records closed from rc-18's definition (2026-10-18T16:34:46Z) to rc-19's birth: 2 live, 6 archived. The push-gate remedy squashed the rc-18 range into `995ac1256`; the two live were re-pointed to it (`7c3ba5d1d`, `1f881d404`), the six archived keep theirs. Verdicts: 2 KEEP, 6 REBUILD (R1-R3).

| bug id | fix sha (original) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `stats-invents-a-table-for-a-missing-candidate` | `c987ad086` | `_stats.py` `table`, `_window` | REBUILD R1 | the rc-18 R2/R3 rebuild; three bugs on the same read followed it in rc-18 |
| `stats-crashes-on-a-candidate-without-a-release-folder` | `242d0b830` | same | REBUILD R1 | `caused_by: J5.T2`; a branch for one input, the missing file (`_stats.py:94`) |
| `stats-crashes-on-an-unreadable-release-state` | `5621889c5` | same | REBUILD R1 | `caused_by` the row above: a second guard on the same read (`_stats.py:92-94`); the open Origin bug is the third bad input (`_stats.py:46-50`); four bugs on one read |
| `merge-checks-a-tree-ledger-with-the-instance-schema` | `187950dea`, reshaped by `2b583acf5` (J5.T15), `9ca521ca6` (J5.T16) | `_worktree_end.py` `_ledgers` | REBUILD R2 | the rc-18 R1 rebuild, reshaped twice in review; it caused the next row |
| `merge-runs-a-tree-carried-ledger-script-without-verify` | `a8abf7416` | `_ledgers`, `_kind_checks` | REBUILD R2 | `caused_by` the row above; it adds the flag `own` (`_worktree_end.py:420`, read at `:311`): one question decided by three stacked conditions (glob, single match, flag) in two functions; the unit's 4th bug in AC2.2's chain |
| `merge-gate-lets-a-test-commit-carry-source` | `995ac1256` (`09df2bff6`) | `_worktree_end.py` `_refuse_implementation_tests` | KEEP, noted | the missing half of the RED-separation rule, same loop and `_is_test_path` predicate; its RED `5ab19c1aa` only adds lines; no bug on it since 2026-10-08. Noted: its two refusal blocks mirror each other (`:259-276`) (intake) |
| `branch-d-fix-line-judges-head-not-the-upstream` | `995ac1256` (`6bb57a885`) | `_worktree_git.py` `SeveralWork` fix line, `drop_steps` | REBUILD R3 | (a) its RED `301cc9f2c` changed an existing assert (`tests/core/test_gitflow.py:205` drops `-d`), a contract change inside a fix; (b) the line's 5th bug, after four `several-work-*` ones. |
| `bugs-check-misses-a-record-both-live-and-archived` | `20fefc4a7` | `_bugs_check.py` `findings_for`, `_bugs_write.py` `append` | KEEP, noted | `caused_by: none`; a new rule, operator 2026-10-19 ("Event lines aren't records (Recommended)"): one archive reader `_archive_lines`, whose `events` flag that ruling keeps; the asserts `c96ad777d` changed were born in its own REDs (`a6ec66063`, `d3a018380`). Noted: "id taken" is decided twice, `append` (`_bugs_write.py:71`) and `findings_for` (intake) |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened): R1 `_stats.py`'s read of the release state is FR1 (Job 1); R2 `_ledgers` is FR2; R3 the `SeveralWork` fix line, with ADR 0270's prefixed reader, is AC4.4.

## 1. Problem

Moving a workspace is a manual recipe (`init`, `dadaia import`, `context alive` per context) carrying no harness and no work in flight; `export` rewrites the registry, `import` stores a null `repo_url` as `'None'` (open bug). `context alive` checks out a stored `current_branch` that is stale in 3 of 5 ALIVE contexts and swallows a failed checkout as a WARNING. Work in a lane or a `wt-rc` cannot be set aside: a tree leaves only by merge or clean, and `context dead` refuses while one is open. The operator ruled the chain into 0.5.0 (roadmap Q4/Q5); ADRs 0270-0272 restate 0171, 0173 and 0175 against today's code. `verdict.py stats` crashes on a release state that breaks its schema (open bug); the bug window found two units patched, not rebuilt (R2, R3). A history rewrite orphans a resolved record's `fix_sha` (FR7).

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | the `measured_by` checks of ADRs 0270, 0271, 0272, 0273 | every one green at the rc-19 PR head | the tests named in each record; 0270's grep |
| 2 | Origin bugs | every one resolved and archived | `bugs.py status` |
| 3 | `dadaia import` | absent from `dadaia --help` and `docs/cli.md` | `dadaia help tree` |
| 4 | REBUILDs R1-R3 | each lands as a REBUILD; net lines <= 0 on `_stats.py`, `_ledgers`, the several-work decision | `git diff --stat` per unit |
| 5 | readout metrics 1, 2, 4, 6, 7, 9 | beside rc-18's 6/6 (100%), 2/13 (15%), n/a, 15, 0, 6 and the rc-18 targets (<= 20%, >= 70%, <= 4 h, 0, 0, 0) | `verdict.py stats 0.5.0-rc19`; baseline: rc-18's closure summary, read at `df96b6d7b` |

## 3. Non-goals

- No `context dead --snapshot`, snapshots zone, WIP commit, archive tag or visibility probe (`gh`); `context dead` is unchanged (ADR 0271).
- No package-version pin and nothing installed by `init --from`: only the `export-v1` format is pinned (ADR 0272).
- Job and task trees are never paused nor carried; uncommitted work is never carried.
- `_release_store.read_state` stays: the release skill's reader, the one `check` uses (B11).
- Every caller but `context alive` keeps reading local work branches; stale origin work branches are not cleaned here.
- The denylist push-gate bug, the PR #298 Windows red and the six archived `fix_sha`s keep their hotfix lanes; the rewrite one joins FR7.
- `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original` stays open; `--from` is the supported path.

## 4. Requirements

Wave ranking, by the pick: (1) law, skills and dev loop: FR1 (Job 1), FR2, FR3, FR7 (Job 7); (2) shared foundation: FR4; (3) features and bugs: FR5, FR6; (4) promote-facing: `docs/cli.md` and the install-count pins move with the job that causes them; memory and backlog exits at closure.

### FR1 — stats refuses a release state that breaks its schema (bug `stats-crashes-on-a-release-state-that-breaks-its-schema`, R1)

Operator, 2026-10-19: "Run release.py check first (Recommended)": stats runs `release.py check` through its existing `_script` and refuses with check's fix line, then parses; no new unit, no verb. By law (B6-B10): stats relays check's first error and its fix line as is.

- AC1.1 RED: `verdict.py stats 0.5.0-rc18 --specs <tree>` on a `_RELEASE.json` that parses but holds (a) a log entry without `ts`, (b) a log `candidate` not shaped `rc-<N>`, (c) a log entry that is not an object exits 1 with no traceback and prints `[error]` plus exactly one `fix:` line, both `release.py check`'s for that finding. A milestone without `sha` is not a case: the schema allows it and stats reads `n/a` (as-is M15). Test: unit, one case per shape.
- AC1.2 Stats runs `release.py check --specs <specs>` through `_script` with `ok=(0, 1)` before it parses (today `_script` returns None on exit 1, `_stats.py:36-39`); its own repair act and the parse refusal of `_stats.py:91-94` go, and `_window` adds no guard. Test: unit (AC1.1's cases).
- AC1.3 The contract tests of the five prior stats fixes stay green: a version with no release folder still reads `n/a` throughout and exits 0. The unreadable-state cases (`{bad`, `[]`, non-UTF-8) keep exit 1 and one fix line; their expected message and fix line become check's, in a `test(...)` commit naming the stats-reader ruling. A non-UTF-8 state is a check finding, never a check traceback (`_release_tree.py:205`); if check crashes on it, Job 1's RED covers that. Test: unit.
- AC1.4 `_worktree_new._refuse_unready` (`_worktree_new.py:53-58`, a raw parse of another branch's blob) reaches the same schema verdict instead of its own parse, swept into Job 1; `dd-handoff-emitter/SKILL.md:55` states that stats refuses a release state `release.py check` refuses. Test: unit; none for the SKILL line.
- AC1.5 During CLOSURE, check refuses until the memory pass is recorded (`_release_tree.py:246-265`), so the closure readout runs after the memory pass (B8, the accepted cost). Test: none, closure order.

### FR2 — one decider names a tree's ledger scripts (R2)

- AC2.1 One decider names the scripts whose `check` judges a tree's `specs/` on merge: on a `wt-rc` the copies the tree tracks, else the instance's; a backlog lane always the instance's; an associated repo none. The `own` flag, the `ls-files` filter on it and the stacked single-match rule (`_worktree_end.py:303-314,420`) go. Test: integration.
- AC2.2 The contract tests of `trio-status-canon-judged-outside-the-define-merge-gate`, `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree`, `merge-checks-a-tree-ledger-with-the-instance-schema` and `merge-runs-a-tree-carried-ledger-script-without-verify` stay green, unloosened. Test: integration (existing).

### FR3 — `dadaia worktree pause` and `resume` (ADR 0271; backlog `context-dead-snapshots-open-worktrees`)

- AC3.1 RED: `worktree pause <path>` on a clean lane (`wt-backlog-<slug>`, `wt-hotfix-<bug-id>`) and on a clean `wt-rc` with no open child writes `git bundle create <file> <branch> --not --remotes=origin` (A5: the basis is what origin holds) at `.dadaia/dist/<repo>/<name>.bundle`, named by `as_posix()`, verifies it, removes the tree and deletes its branch by `update-ref -d` under the CLI marker (A3: `branch -d` cannot delete an unmerged lane); `worktree resume <path>` recreates the branch at the same tip and the tree, then deletes the bundle. Test: integration.
- AC3.2 Pause refuses with nothing touched: a dirty tree (one fix line: commit first), a tree holding ignored files (one fix line; no `--keep`/`--drop`, since `_kept` copies into the merge-only repo tree, `_worktree_end.py:75-121`; A2 supersedes the R4 default), a job or task path, a `wt-rc` with an open tree below it, a failed bundle write or verify. It makes no commit. Test: integration.
- AC3.3 `context dead` refuses with the tree open and passes its worktree preflight after the pause; its fix line keeps naming merge and clean, and the law names pause as the third exit (as-is M10). Test: integration.
- AC3.4 Resume creates the `wt/*` branch through the CLI marker, so the reference-transaction gate passes it; resuming a lane or `wt-rc` whose branch was pushed succeeds, the PLAN stating the remote-branch rule (R3 seam). Test: integration.
- AC3.5 The `dist` canon admits `<registered slug>/` by the existing registered-slug mechanism (no `*` glob), the hard archive and the soft JSON, so `doctor --fix` never moves a bundle (today `{spec-contexts.json}`, `workspace_layout.py:199-200,314-345`); `context delete` refuses while `dist/<repo>/` holds a pause bundle, its fix: resume or move it (A1). Archive names are the PLAN's (R5). `worktrees/AGENTS.md` names `pause` and `resume` in its verb list, exit line and before-dead line; so do `dd-gitflow-default`'s list, `worktree.py:4` and `docs/getting-started.md:126`. Test: unit for the zone and the delete refusal; none for text.
- AC3.6 Paused work stays visible (A4): `worktree list` shows each pause bundle as a `paused` row whose exit is its `resume` line (today none, `_worktree_git.py:169-182`); release closure refuses a paused tree like an open one; `context dead` passes it. Test: integration.

### FR4 — the stored branch is deleted; `alive` takes the highest origin work branch (ADRs 0171 + 0270; backlog `spec-context-branch-field-deleted`; R3)

Operator, 2026-10-19: "alive-only origin read, highest (Recommended)".

- AC4.1 RED: reviving a DEAD context whose clone's origin holds one work branch checks it out; two, the highest; none, the integration branch. A failed checkout refuses with one fix line, never a stderr WARNING (as-is M12). Test: integration.
- AC4.2 RED: a repo with local `{0.8.0}` and origin `{0.6.0, 0.8.0}` gives every local caller (`worktree new`, `context baseline`, `context dead`, `specs init`, `ci`, the doctor's first-pass fix) `0.8.0`, no SeveralWork (as-is M1 repro). Test: unit.
- AC4.3 `work_versions` takes the ref prefix it reads, local by default, so its positional callers stay unchanged (`_worktree_new.py:70,72`, `core/gitflow.py:112,115`, C20); the origin read lists `refs/remotes/origin/<work>*` (`for-each-ref`). Only `alive` passes the origin prefix and takes `SeveralWork.keep`; no other unit holds a "highest" rule. Test: unit.
- AC4.4 R3: one decision in `_worktree_git.py` yields the kept version and the act over the local branches, which `drop_steps` stops re-deriving from its own git reads. The contract tests of the five SeveralWork bugs stay green, unloosened; the assert `301cc9f2c` changed (`tests/core/test_gitflow.py:205`) states the contract `sdd/worktrees.md:23` records: an unmerged lower is merged into the higher this pass and deleted on the next. Test: unit.
- AC4.5 `current_branch` leaves `SpecContextProject`, the store's row mapping, `context show/list` (`stored_branch` and the stored fallback), `create`, `add_repo`/`remove_repo`, `alive`, `dead`, `migrate/state_v2`, export and the import reader. ADR 0270's grep prints only the `RepoLiveStatus` live read; the `repo_live_status` docstring (as-is M4) and `cli/commands/context.py:67`'s docstring are reworded. Test: none, the grep is the evidence; output pins move by ADR 0171's acceptance.
- AC4.6 `JsonContextStore` spells `schema_version` once, stamped by `replace_raw` (`restore` puts back a snapshot byte for byte, `json_context_store.py:108-119`); `_EMPTY_CONTEXTS` and `state_v2` stop spelling it; no migration ships; a row keeps the dead key until written and no reader reads it. Test: unit.

### FR5 — `dadaia export`: read-only, soft and hard (ADRs 0175 + 0272; backlog `export-soft-and-hard`)

- AC5.1 RED: `dadaia export` writes the soft artifact: `schema_version` `export-v1`, contexts (slug, name, state, main repo url, associated `[{slug, url}]`), `dadaia_version` and the harnesses of `harness_profile.json`; `state` is the registry's lowercase value (today `state.name`, `export/service.py:32`, against the store's `.value`), pinned in the schema; the registry is byte-identical after it (`_refresh_branches` deleted); `export --help` stops naming `import` (`cli/commands/export.py:23-26`). Test: integration.
- AC5.2 A main or associated repo with no remote is recorded with url `null` (one rule, R6). Test: unit.
- AC5.3 `dadaia export --hard` writes one `.tar.gz` in `.dadaia/dist/` holding only the soft JSON and `<repo>/<name>.bundle` members, names built with `as_posix()`: a bundle of each open lane and `wt-rc` made at export time on AC3.1's basis, and each pause bundle. A dirty open tree refuses with pause's commit-first fix line and the tree stays; job and task trees are not carried. Test: integration.
- AC5.4 The hard export scans the bundles' objects with the pre-push's denylist and baseline; a planted secret refuses and leaves no archive. Export runs no visibility probe and writes no ref into `repos/<slug>` (scan input: R3 seam). Test: integration.
- AC5.5 Both artifacts' JSON validates against one shipped `export-v1` schema; `ExportService` is the one owner that writes and reads the artifact, and bundles come from pause's one writer. Test: unit.

### FR6 — `init DIR --from <artifact>`; `dadaia import` deleted (ADRs 0175 + 0272; backlog `init-from-export`; bug `import-turns-a-null-repo-url-into-none`)

- AC6.1 RED, at the `init --from` artifact reader: a context whose `repo_url` is null is never registered and never stored as `'None'`; it is listed `not replicated: no remote` with one fix line (add a remote, then re-export). The reader coerces null to `""` and `register` stays the one decider (as-is M7); a null associated url follows the same rule. Test: unit.
- AC6.2 `init DIR --from` on a soft and on a hard artifact into a fresh workspace installs every harness the artifact names, registers its contexts DEAD through `register`, lists the repos `git ls-remote` cannot reach and prints `context alive <ctx>` for each context ALIVE in the artifact. A hard artifact's members are validated before extraction against a member pattern (the JSON or `<slug>/<name>.bundle`; no absolute path, no `..`, no link; stdlib `tarfile` `filter="data"`) and its bundles land in `.dadaia/dist/<repo>/<name>.bundle`; then `context alive`, `worktree resume` (a lane whose base exists only locally included) and doctor report no finding. Test: integration.
- AC6.3 An artifact with any other `schema_version` refuses with one fix line: re-export with the current dadaia-workspace. `dadaia_version` is read for display only. Test: unit.
- AC6.4 `--from` with `--repo` refuses with one fix line; every fix line `init` prints carries `--from` when given, built by `InitPlan.command` alone; the contract tests of the init fix-line family stay green. Test: unit.
- AC6.5 `dadaia import` is gone: `features/import_/`, `cli/commands/import_.py`, its `cli/main.py` registration and `build_import_service`; `docs/cli.md` is regenerated; `dd-cli-library/SKILL.md:28`, its verb index and `scripts/CONSUMER_VALIDATION_RECIPE.md` stop naming it; docstrings naming it are reworded (`core/exceptions.py:36,112`, `spec_context/service.py:269`, `core/models/spec_context.py:11`, `tests/fakes.py:76`). Atoms citing it (`context-portability.md`, `context-management.md:44,46`, `catalog.json`, `index.md`) change in this job: doctor's citation check flags a dead verb (`doctor_memory.py:264`, `citations.py:214-237`). Operator: "Delete verb-only tests; move the rest (Recommended)": verb-only rows go; partitions the reader owns move to the `init --from` tests in a `test(...)` commit naming it. Test: unit (the help-tree pin).

### FR7 — a resolved bug's fix is its id-bearing commit (ADR 0273; bugs `worktree-sync-orphans-the-fix-sha-a-lanes-resolve-cites`, `push-gate-rewrite-orphans-shas-cited-in-the-range`)

Amendment, operator 2026-10-19: "Cite by the id-bearing commit (Recommended)", then "Add as rc-19 Job 7 (Recommended)": the approved rc-19 gains ADR 0273 (accepted here, amending 0267, before Job 7 starts) and Job 7. Both bugs join the Origin once rc-19 syncs with `feature/0.5.0`, which holds them; `release.py check` refuses an id absent here.

- AC7.1 RED: `bugs.py check` exits 0, with no ledger step, after `worktree sync` rebases a lane's `fix(bugs): <id> — …` commit and after `push-gate-check --rewrite-from` folds it. It refuses with one fix line a resolved record carrying `fix_sha` when no commit HEAD reaches holds a line starting `fix(bugs): ` or `refactor(bugs): ` naming its id before ` — ` (a group too), or HEAD reverts the only one (a later `Revert "<its subject>"`). A revert holding `fix(bugs): <id> — revert <culprit subject>` cites it. The shallow-clone finding stands. Test: unit for check; integration for sync and the fold.
- AC7.2 `bugs.py resolve` derives `fix_sha` and `fix_files` from that commit, refusing with one fix line when there is none; `--fix-sha` goes; `fix_sha` is write-once in `bug-record-v1`; `by_file` reads `fix_files`, else that commit's files. Test: unit.
- AC7.3 The fold's message holds every folded message in order, after the new one when given; the re-point fix line and `_cited_ids` (reverted by the CI-red lane) stay out. Test: integration.
- AC7.4 Before the check change, one shape-4 `chore(bugs): archive <ids>` takes out of `BUGS.jsonl` every terminal record the new check refuses at Job 7's base (the 26 task-fixed counted at `06ca6c045`, and `rewrite-remedy-fix-line-bypasses-the-one-renderer`, resolved by the revert `5a063078b`), its body naming the count. Test: none, `bugs.py check` exit 0 at the job head.
- AC7.5 The sha-contract asserts in `test_bugs.py` (`fix_sha` unreached, its fix line, `update` re-pointing) move to the id contract in a `test(...)` commit naming 0273's acceptance; `specs/bugs/AGENTS.md` and its scaffold source state the cite rule in one line; `LINEAGE.md` and `dd-release-definition` §1 step 6 find a fix by its id line. Test: unit for the asserts; none for text.
- AC7.6 After a RED of the push-gate orphaning, one shape-3 group commit names both bugs; the `worktree-sync-…` resolve states it re-fixes the push-gate bug. Test: integration (AC7.1's fold case).

### Replaces

- `verdict.py stats` parsing `_RELEASE.json` itself behind per-input guards and its own repair act.
- `_worktree_new._refuse_unready` parsing `_RELEASE.json` raw.
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
- `bugs.py check` judging a resolved record by whether a ref reaches its `fix_sha`.
- The rewrite remedy's re-point fix line, and a fold keeping only the oldest subject.
- `bugs.py resolve --fix-sha` and `update` re-pointing `fix_sha`.

### Closure

- Backlog exits, `delivered` `--release 0.5.0`: `spec-context-branch-field-deleted`, `context-dead-snapshots-open-worktrees`, `export-soft-and-hard`, `init-from-export`. Every Origin bug resolved and archived.
- ADRs (main thread, on the 2026-10-19 rulings): 0171 and 0270 accepted (0270 amends 0171); 0271 accepted, superseding 0173 and amending 0172; 0175 and 0272 accepted (0272 amends 0175); 0273 accepted (amends 0267).
- Memory pass (`MEMORY-UPDATE.md`): `platform/context-portability.md` (rewritten; its catalog entry maps the deleted `features/import_/**`), `platform/context-management.md` (`:21,31,34,46`), `platform/workspace-init.md`, `platform/workspace-doctor.md`, `sdd/worktrees.md` (`:23,33,40,45`), `sdd/release-lifecycle.md`, `sdd/bug-ledger.md` (FR7), `agents/agent-comms.md`, `catalog.json` (`:528-544`), `index.md` (`:50`), `ARCHITECTURE.md`'s features map (`:118-123`); lines citing `dadaia import` change in FR6's job.

## 5. Constraints and risks

- Order: Job 1 is FR1. FR4 precedes FR5 and FR6, which edit the same files; FR5 precedes FR6 (one artifact owner, then its reader in `init`).
- `_worktree_end.py` (33 bugs) must not grow: pause lives in its own unit, and R2 shrinks `_ledgers`.
- Net lines <= 0 for FR1, FR2, FR4 and FR6 (the `import_` deletion offsets `--from`); FR3 and FR5 are net additions, a new capability no unit carries.
- Public boundary: nothing requires a remote, CI, `gh` or a vendor CLI; the scan and bundles are local; platform facts go through `core/platform.py`, archive members are POSIX names joined by `Path` (R7).
- Stats refuses on any `release.py check` error, an unrelated tree finding included: the ruled trade-off of the check-first read.
- Check's fix line for a schema finding is generic; stats relays it as is (B10).
- `alive` takes the highest origin work branch even if stale: it runs no fetch, so a branch deleted upstream counts until the operator's own `fetch --prune` (D23), correcting ADR 0270's immutable consequence line.
- An old `spec-contexts-export-v1` artifact on disk refuses with the re-export fix line.
- Two new assets (`_worktree_pause.py`, `export-v1.schema.json`) move the per-platform install-count pins, outside `ci.py job`: the implementer recounts each literal and runs those test files by name (`asset-count-pins-miss-the-readout-script`). The shipped-hashes pin moves with Job 7's bugs-law source edit.
- Consumers of each changed public name: as-is review §4 and the `dd-researcher` pre-mortem (2026-10-19), every hit in an AC; the PLAN answers each.
- Hotfix lanes on `feature/0.5.0` reach the `wt-rc` by `WT sync`. Job 7 follows rc-19's sync with the CI-red revert lane; the denylist hotfix waits for Job 7 on `feature/0.5.0`.

## 6. Open questions

none. R3's remaining seams and R5 (names) are the sr's PLAN defaults.
