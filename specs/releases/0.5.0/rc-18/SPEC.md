# SPEC — Release: 0.5.0, candidate 18 — clean and verify

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-18
**Origin:** backlog:worktree-scripts-loose-ends,skill-kernel-loose-ends,package-loose-ends,push-gate-remedy-follow-ups,test-quality-loose-ends,rc17-review-loose-ends,ref-gate-open-questions,evals-functional,closure-lane-for-rc-only-block-bugs; bugs:stats-invents-a-table-for-a-missing-candidate,merge-checks-a-tree-ledger-with-the-instance-schema

Operator, 2026-10-18, verbatim (grill roadmap-050): Q1 "to ship the 0.5.0 the minimal gates are the work and backlog related with documentation and how to maximaze ou discoverability and of course adoption. ... auso the evals, the onboarding. all of it must be handle seriously before we deliver the version 0.5.0"; Q2 IN 0.5.0 "the open cleanup lists, so 0.5.0 ships with 0 known defects"; Q7 "4 rcs: 18-21 (Recommended)", rc-18 "clean and verify"; Q9 "Register both, rc-18 (Recommended)"; "go ahead, man, no relax till you finish the complete 0.5.0".

Sources: the grill record `.dadaia/reports/dadaia-workspace/grill/roadmap-050.md` (roadmap section and `## rc-18 grill`, rulings verbatim); the Origin entries of `specs/backlog/BACKLOG.json` (lines 179-295); the Origin bugs (`specs/bugs/BUGS.jsonl:954-955`); ADR **0269** (accepted 2026-10-18, amends 0178); rc-17's closure summary in `specs/releases/0.5.0/_RELEASE.json`. rc-17 SPEC §2: "rc-18 is judged on this table". Paths are relative to `repos/dadaia-workspace/`. A `path:line` below is read at `6209d9ec9` or quoted from its entry; the PLAN's as-is review re-anchors each one and names any item shown gone, with evidence.

---

## Bug window review

**Window:** fixes closed after rc-17's window (rc-17 SPEC, fixes resolved to 2026-10-17): the 7 records rc-17 archived inside the rc (`71316b2ee`), the 2 closure bugs (`048a4879f`), and the 2 resolved in `BUGS.jsonl` on 2026-10-18 after the closure summary: **11 bugs**. Six of the seven at `71316b2ee` were judged in rc-17's table; each is judged again here against the rc-17 head. Each fix was read with `git show`. Verdicts: 8 KEEP, 3 REBUILD in three units, R1-R3.

| bug id | fix sha(s) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `missing-verify-refusal-fix-is-itself-blocked` | `ed95c8770`, `42bbdf11c` | `_worktree_end.py` verify refusal fix line | KEEP | rc-17 R1 delivered: `1bba55b7d` (J1.T6) rebuilt the line onto one `act()` path |
| `verify-red-fix-line-commits-outside-a-task-tree` | `bcd1fe3cf` | same | KEEP | same R1 rebuild; the per-kind tail is one `match` at `_worktree_end.py:218-228` |
| `rc-red-verify-fix-line-gives-code-no-route` | `89d7c0b28`, `aa6a3a978`, `18dd60121` | same | KEEP | same R1 rebuild; the `known` table is gone |
| `operator-action-fix-lines-hand-over-agent-acts` | `29c757964`, `f5263f80f` | every `Operator action:` site | KEEP | rc-17 FR1 (ADR 0266): one `act()` producer and AC1.2's one-grep test |
| `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree` | `183a36590` (RED), `b8bf1bb11` | `_worktree_end.py` `_checks`/`_ledgers` | REBUILD R1 | the unit's second bug is the open Origin bug `merge-checks-a-tree-ledger-with-the-instance-schema` (same `_checks`, `:290-298`); two bugs on one unit |
| `codex-push-rule-conflicts-with-workspace-gitflow` | `e677235a2` (RED), `f791ae8cf` | `codex_assets.py` command policy | KEEP | deletion, net -8 |
| `ref-gate-refuses-pack-refs-of-wt-branches` | `723e9aaa6` (RED), `09b658ec6` | `hooks/ref_transaction.py` zero-old decision | KEEP, noted | one zero-old decider in the hook, `ci.py`'s re-read deleted (+19/-14); noted: `branch_policy.py` `_audit_descendant` widened to `except Exception`, and an `is_zero_sha` choice picks the recreate fix text (AC14.4's runnable fix) |
| `append-crashes-on-the-event-shaped-archive` | `3612bb589` (RED), `15a79e2dd`, `b652b93f1` | `_bugs_store.history`, `_stats.py` | REBUILD R2 | the reader moved to one owner, but the commit says `rebuild: none` with `caused_by: J4.T3` (rc17 item 12) and `_stats.py:13` still imports `_bugs_store` across skills (rc17 item 11) |
| `stats-names-the-repo-by-its-checkout-folder` | `655fb36be` (RED), `04d82da9d` | `_stats.py` `_context` | REBUILD R2, R3 | `caused_by: J5.T4`, `rebuild: none`; it copies the git-common-dir derivation a 4th time (`_stats.py:55`, rc17 item 10); `_stats.py` carries 3 bugs with the open `stats-invents-a-table-for-a-missing-candidate` |
| `asset-count-pins-miss-the-readout-script` | `9dd383f16` | install-count literals in two characterization tests | KEEP, noted | the 5th re-pin of the same literals (137 -> 138, 160 -> 161) for one shipped file; the literals stay by the §7 ruling (a): tests expect literals, and a count derived from the roster oracle would be a tautology |
| `unclosed-quote-test-hand-spells-the-sync-path` | `e1a91d98f` | `test__worktree_end.py:1024` | KEEP, noted | the tail takes the product's kernel spelling `_sync_line` (operator: "Register + use _sync_line (Recommended)"); the startswith and no-newline asserts unchanged; its correlate `tests-hand-spell-platform-paths-and-fix-lines` cannot be recorded (FR12) |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened): FR1 takes R1, FR2 takes R2, FR3 takes R3. The rc-17 candidate review flagged both closure fixes as REBUILD in substance (`caused_by` not `none`); R2 answers it.

## 1. Problem

rc-17 fixed the nine weak points; its own readout missed metric 2 (first-pass approval 4/8, 50 %, target >= 70 %) and metric 1 read 1/1 over a window that ends at CLOSURE, so the two closure bugs fell outside it. Two bugs block the next rcs: the readout invents values for a candidate that does not exist, and a self-hosted `wt-rc` that changes a ledger schema cannot merge. Nine backlog entries hold the open cleanup lists; 0.5.0 ships with 0 known defects (Q2). The eval gate of ADR 0178 contradicts itself and is amended by ADR 0269. rc-18 cleans those lists and verifies rc-17 on the same table.

## 2. Measurable Goals — the 9-metric readout, rc-18 judged against rc-17

Same metrics and targets as rc-17 §2; rc-17's values are the baseline. Source of each baseline: rc-17's closure summary (`_RELEASE.json`, 2026-10-18T12:14:34Z), except 4 and 5, read after the summary.

| # | metric | rc-17 baseline | target | source |
|---|---|---|---|---|
| 1 | fix-induced bugs: `caused_by` not `none` / closed records | 1/1 (100 %), window ending at CLOSURE; recomputed by AC2.2 | <= 20 % | `verdict.py stats` |
| 2 | first-pass approval: trees whose first verdict is `APPROVED` / trees | 4/8 (50 %) | >= 70 % | `verdict.py stats` |
| 3 | merge `verify:` wall time | median 105 s over 4 job merges | <= 150 s | the developer's private tool, outside the library |
| 4 | closure duration, CLOSURE to the candidate PR merge | 10.8 h: CLOSURE 2026-10-18T04:24:02Z -> PR #297 merge `59c99be43` 15:11:40Z | <= 4 h | `verdict.py stats` |
| 5 | CI red share of the work branch's runs | 2/7 (29 %), rc-17 birth to PR #297 merge (`gh run list --branch feature/0.5.0`, read 2026-10-18) | <= 10 % | the developer's private tool, outside the library |
| 6 | non-block commits landed after CLOSURE | 0 at the summary | 0 | `verdict.py stats` |
| 7 | memory drift at the PR | 0 | 0 | `verdict.py stats` |
| 8 | hand-typed fix-line labels outside the producer | 0 | 0 | rc-17 AC1.2's grep test |
| 9 | REBUILD-due fixes landed as a patch | 0; recomputed by AC2.2 | 0 | `verdict.py stats` |

## 3. Requirements

Wave ranking, by the pick: (1) law, skills and dev loop — FR10's law line, FR11's law and ADR text, FR12; (2) shared foundation — FR3, FR5; (3) features and bugs — FR1, FR2, FR4, FR6, FR7, FR8, FR9, FR10's test; (4) promote-facing — FR11's evals and eval.yml, FR13.

An entry item already gone at the rc-18 head closes with its evidence (`path:line` or a grep) and needs no code (rc-17 AC14.6 form). Two are shown gone by inspection: skill-kernel (1)'s `registry.py:230` `ss` spawn now runs in `_platform._ss` (`_platform.py:313-318`, catches `OSError`); push-gate (5)'s `_audit_only` left `ci.py` and lives as `branch_policy._audit_descendant` (`features/chokepoints/branch_policy.py:168`).

### FR1 — a tree's ledgers are checked by the tree's own scripts (bug `merge-checks-a-tree-ledger-with-the-instance-schema`, R1)

Operator (Q9): "Register both, rc-18 (Recommended)".

- AC1.1 RED: in a self-hosted workspace, a `wt-rc` whose library adds a ledger field merges: its ledger checks run the tree's own `bugs.py`, `backlog.py` and `release.py` (today `_worktree_end.py:293`, `Path(__file__).resolve().parents[2]`, the instance copy). Test: integration.
- AC1.2 A consumer repo, whose tree carries no library, keeps the instance's ledger scripts; an associated repo's merge still runs none (`b8bf1bb11`'s contract). Test: integration.
- AC1.3 R1: one decider picks the ledger scripts and the repo they judge; the contract tests of `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree` stay green, unloosened. Test: unit.

### FR2 — the readout (bug `stats-invents-a-table-for-a-missing-candidate`, R2, `rc17-review-loose-ends` (6), (8), (9), (11), (12))

Operator (Q9): "Register both, rc-18 (Recommended)". Agent default, unruled (grill `## rc-18 grill`): "a candidate's window runs from the previous candidate's CLOSURE to its own CLOSURE, so no bug falls between two windows. This applies to metrics 1 and 9; the gap was a defect of the reader."

- AC2.1 RED: `verdict.py stats 0.5.0-rc99` for a candidate the log never names prints `n/a` for every metric or refuses with one fix line, never values (today `_stats.py:43`, `min(..., default="9")`). Test: unit.
- AC2.2 Metrics 1 and 9 count the bugs closed from the previous candidate's CLOSURE stamp to this one's (today birth to CLOSURE, `_stats.py:36-49,86-88`, item (9): 39 bugs fell in no window); the rc-18 closure summary carries rc-17's metrics 1 and 9 recomputed this way. Test: unit, a bug closed between two candidates counts in exactly one.
- AC2.3 `_stats.py` reaches the bug ledger by running `bugs.py`, never by importing `_bugs_store` (item (11), `_stats.py:13`). Test: unit.
- AC2.4 Item (6): the stray `# fmt: skip` on the tuple closings (`_stats.py:115,122`) go; the birth default `''` (`:45`) and the `--ancestry-path` bound of metrics 4 and 6 (`:69`) are pinned by tests, the PLAN choosing `--first-parent` where the back-merge `f9fc04f21` would miscount. Test: unit.
- AC2.5 Item (8): metric 9's `named_paths` tokenizer (`_bugs_write.py:47-50`) does not count a bare top-level directory word and splits a trailing period. Test: unit.
- AC2.6 Item (12): `dd-bug-resolution` states that a fix whose `caused_by` is not `none` names its REBUILD unit, never `rebuild: none`. Test: none, law text.
- AC2.7 R2: the contract tests of `append-crashes-on-the-event-shaped-archive` and `stats-names-the-repo-by-its-checkout-folder` stay green, unloosened. Test: unit.

### FR3 — one git-common-dir helper (`rc17-review-loose-ends` (10), (4), R3)

- AC3.1 One `_git` helper derives the main checkout from the git common dir; its four copies call it: `_stats.py:55`, `dd-bug-resolution/scripts/_bugs_check.py:170`, `dd-release-implementation/scripts/_release_phase.py:84`, `hooks/ref_transaction.py:44` (the hook reaches it by its own runner, never by a cross-component import). Test: unit, a worktree and its main checkout answer alike.
- AC3.2 Item (4): the helper's docstring states that main is the parent of the git common dir and what a `rev-parse` failure returns; `_siblings` (`_bugs_check.py:164-166`) stops restating it. Test: unit for the failure value.

### FR4 — worktree scripts (`worktree-scripts-loose-ends` (1)-(8))

- AC4.1 (1) One owner beside `_worktree_names` decides the level-folder rule; its three deciders call it: `_worktree_new.py:26-33`, `_worktree_end.py:119-128` `_rmdir`, `_worktree_git.py:182-192` `_strays`. Test: unit.
- AC4.2 (2) `_strays`' level exemption is bounded by depth and name; the dead `max(..., 1)` floor (`_worktree_end.py:122`) goes; sync's dirty cascade gets a test; `flow_for` (`_worktree_git.py:70`) runs once per merge; the rerun fix spells an absolute path; sync's own `worktree.py list` fix line is runnable; `levels/*.md` (4 lines each) reach rc-16 AC7.2's 5-10. Test: unit per behaviour; none for text.
- AC4.3 (3) `sync`'s `rebase --fork-point` (`_worktree_sync.py:53`) never drops a commit that was once on the parent and later removed from it. Test: integration.
- AC4.4 (4) `not_a_name` (`_worktree_git.py:122-124`) names no hard-coded `0.5.0`; the leaf grammar is read only through `NAME_RE` (extra readers in `_release_phase.py` and `_worktree_new.py`); the closure fallback fix line (`_release_phase.py:90`) is runnable for an orphan branch and tested. Test: unit.
- AC4.5 (5) `_is_test_path` (`_worktree_end.py:233`) is rebuilt or kept by the as-is review's deletion test, with its reason. Test: unit when rebuilt.
- AC4.6 (6) An associated repo's `worktree new` of a job reads the phase from its own context's main repo `wt-rc` and its refusal names that tree; tested. Test: integration.
- AC4.7 (7) Two shape-1 registrations merge back to back with no manual verdict rebind. Test: integration.
- AC4.8 (8) A `wt/*` branch with no tree, left at a closure, is removed by a verb's runnable fix line before the next CLOSURE refuses on it. Test: integration.

### FR5 — skill kernel and bug ledger (`skill-kernel-loose-ends` (1)-(5), `rc17-review-loose-ends` (7), (13))

- AC5.1 (1) Every skill-script spawn refuses an `OSError` with one fix line: `_release_phase.py:66`, `_backlog_exit.py:32`; root-found plus CLI-missing is tested for the three `_specs.run_cli` callers. Test: unit.
- AC5.2 (2) The law states that `DADAIA_WT=1` reaches every `scrubbed_env` child, so raw git inside `verify:` passes the ref hook by design. Test: none, law text.
- AC5.3 (3) `bugs.py append` accepts repeated `--correlates` and states the comma form in its help. Test: unit.
- AC5.4 (4) The `_bugs_check.py` local name `update` is renamed; the near-copy tests at `test_bugs.py:229-249,252-263` are parametrized with `:190-226`; the cut message no longer says "no fix_sha can be judged"; `_release_schema.py:114` uses `_git.shallow` (`_git.py:45`); the test name `test_the_unreached_fix_sha_fix_line_is_one_act_without_a_placeholder` matches its pinned `fix_sha=SHA`. Test: unit.
- AC5.5 (5) `_ledger.py:164` stops reading `.dadaia/states/privacy_denylist.json` from a skill script; the denylist reaches it by argument or by running its owner. Test: unit.
- AC5.6 rc17 (7): `bugs.py check` reads each fix commit once for reachability (`_bugs_check.py:181-184` calls `fix_files` only for that); its time on the current ledger returns to the pre-rc-17 reading (479 ms on 69 shas). Test: unit for the single read; the timing is the reviewer's evidence.
- AC5.7 rc17 (13): ADR 0267's sibling lookup covers the records without `fix_files` (4 of 1164 carry it) by one backfill from `fix_sha` or by the one reader's fallback, the PLAN choosing. Test: unit.

### FR6 — package loose ends (`package-loose-ends` (1)-(8))

Agent default, unruled: "`.gitattributes` `dadaia-dev-tooling`: deleted as dead text, since no reader remains."

- AC6.1 (1) One several-work-branches class: `core/gitflow.py:99`'s double inheritance goes, `ci.py` catches the core class. Test: unit.
- AC6.2 (2) `specs init` cuts the work branch from `origin/<work>`, else the integration branch (today `git switch -c` from HEAD, `cli/commands/specs.py:204`). Test: integration.
- AC6.3 (3) `specs init`'s `[committed]` guard is tested; the stale texts are corrected: the `--replace-foreign` help (`specs.py:128`), the docstring (`:238`), the `[moved] ... (staged, not committed)` line (`:250`), `infrastructure/git_subprocess.py` `work_version`'s docstring. Test: integration for the guard; none for text.
- AC6.4 (4) `doctor_memory.py:96-99`'s "fill or delete the atom" fix names the atom's file. Test: unit.
- AC6.5 (5) `infrastructure/privacy_check.py` honours the baseline's `skip_paths`; the pipeline-name test skips only the matched path, not the whole `exclude_paths` line. Test: unit.
- AC6.6 (6) A planted `.git` under a worktree no longer switches stray detection (`core/workspace_layout.py:286-290`). Test: unit.
- AC6.7 (7) `preview = true` stays while PLW1514 is preview in the locked ruff 0.16.2 (`ruff rule PLW1514`: "This rule is in preview and is not stable"); KEEP, closed with that evidence. Test: none.
- AC6.8 (8) `.gitattributes:3,4,7` (`dadaia-dev-tooling`) are deleted. Test: none, config; evidence `git grep -n dadaia-dev-tooling` prints nothing.

### FR7 — push-gate remedy (`push-gate-remedy-follow-ups` (1)-(5))

Agent default, unruled: "`--rewrite-from` is a flag on the existing leaf, so the cap holds unchanged. The verb's help states the remedy flag."

- AC7.1 (1) The 30-leaf cap (`tests/cli/commands/test_help.py:62-70`) holds unchanged; `push-gate-check --help` names `--rewrite-from` as the remedy (`cli/commands/ci.py:214-215,234`). Test: unit (existing cap; one help assert).
- AC7.2 (2), (3) The whole-range collapse and the listed-file residual are stated in the verb's help as its contract. Test: none, help text pinned by AC7.1's assert.
- AC7.3 (4) `ci.py:105,134`'s `isinstance(decision, GateDecision)` checks go once the decision carries its listed paths. Test: unit.
- AC7.4 (5) shown gone (above). Test: none.

### FR8 — test quality (`test-quality-loose-ends` (1)-(5), `rc17-review-loose-ends` (5), (14), (15))

- AC8.1 (1) The Job 2/3 LOWs: inert verdict-binding cases and the inert `declared_verify` removed or made live, the for/if setup loop flattened, the lost dirty-tree case restored, the 13 stale docstrings corrected, the one contract pinned in three files kept in one, the vacuous asserts at `tests/infrastructure/test_entity_doctor.py:487-493` made to assert. Test: unit.
- AC8.2 (2) The pinned `verify:` line has one home; `tests/scripts/test_ci.py:151` goes. Test: unit (the kept home).
- AC8.3 (3) `tests/features/workspace/test_onboarding.py:153-162` takes opaque pass-through strings. Test: unit.
- AC8.4 (4), rc17 (15) No test writes `tests/tmp/` in the checkout: `tests/fixtures/test_conftest_size.py:57-61` writes under `tmp_path`, and the merge-time residue is reproduced and registered or shown gone. Test: unit.
- AC8.5 (5) "A refusal's fix line runs" has one home in the `fix_world` census: `tests/public/scripts/test_reference_transaction__work_branch.py:470-520` `_fix_command` and its copies fold into it. Test: integration.
- AC8.6 rc17 (5) The `fixes(x)[0]` sites unpack exactly one fix: `test__worktree_end.py:171,196,549,669`, `test__worktree_new.py:276`. Test: unit.
- AC8.7 rc17 (14): the install-count literals stay (`test_public__characterization.py:66`, `test_init__characterization.py:28,38`); rc17 item 14 closes KEEP (§7 ruling (a)). Test: none, no change.

### FR9 — law and doc text (`rc17-review-loose-ends` (1)-(3))

- AC9.1 (1) `scripts/CONSUMER_VALIDATION_RECIPE.md:38` R-04 says the "fill or delete" fix appears only when both slug and title are tokens (`doctor_memory.py:53-56,96-99`). Test: none, doc text.
- AC9.2 (2) `tests/features/specs/test_canon__scaffold_placeholder_repair.py:1-6`'s docstring drops the overreach and the false "the upgrade dry run reports it". Test: none, docstring.
- AC9.3 (3) `scripts/ci.py:86`'s `plan()` docstring states what an empty argv runs. Test: none, docstring.

### FR10 — ref gate open questions (`ref-gate-open-questions` (1), (2))

Operator (rc-18 grill Q1): "Pass by design (Recommended)" — "`wt/*` refs are private working branches, and `worktree merge` is the chokepoint. The rc states this in one law line, plus a test pinning that a forced `wt/*` move passes; it adds no gate. Recreating the work branch at another sha is already refused (rc-17 FR14, "Refuse recreate")."

- AC10.1 One law line in `dadaia_workspace/public/data/worktrees-AGENTS.md`: a forced `wt/*` move passes by design; `worktree merge` is the chokepoint. Test: none, law text.
- AC10.2 A forced, unmarked move of an existing `wt/*` branch passes the reference-transaction hook. Test: integration, no gate added.
- AC10.3 Work-branch recreation stays as rc-17 AC14.7 ruled; the stale reading at `tests/features/chokepoints/test_branch_policy.py:253` and rc-16 AC3.1 is reconciled to it. Test: unit (existing).
- AC10.4 (1) The SHA-1-length-only patterns (`handoff-v1.schema.json:53`, `bug-record-v1.schema.json:52`, `_grammar.py:26` `SHA_RE`, `release-state-v1.schema.json:178,183,188`, `workspace_layout.py:420`) accept a 64-hex sha, or each is shown unreachable in a SHA-256 repository. Test: unit, a 64-hex sha per pattern.

### FR11 — evals functional, ADR 0269's text and law side (`evals-functional` (1)-(5))

Operator (Q6): "T1+T2 Claude, + discovery T3 (Recommended)"; rc-18 grill Q2: "Amend: record-only delta + T3 gates (Recommended)", now ADR 0269 (amends 0178). The eval run is rc-21's.

- AC11.1 (1) The T1 grader reports doctor's findings instead of crashing when doctor exits 1 (`evals/tasks/t1-cold-onboarding/tests/test_grade.py:12-20`, `check=True`). Test: integration, the grader's no-model row.
- AC11.2 (2) No stale eval name remains: `tests/e2e/test_evals_scripts.py:23` names `t2-block-list-bug`; `:68`, `tests/helpers/evals.py:1,67` and `tests/e2e/test_evals_t1.py:19` stop naming the retired `dadaia-evals`. Test: E2E (existing rows); evidence `git grep -n dadaia-evals -- tests evals` prints nothing.
- AC11.3 (3) The T2 grader catches a removed assert in any form, not only a bare `assert` line (`evals/tasks/t2-block-list-bug/tests/test_grade.py:68`). Test: integration, the grader's no-model row.
- AC11.4 (4) `evals/scripts/compare.py` applies ADR 0269 (b): block when T1 < 3/3, or T2 or T3 < 2/3 on the candidate, or a task >= 2/3 on 0.4.7 falls to <= 1/3; T3's 0.4.7 result is readout only; its docstring cites 0269. Test: unit, one row per block reason and T3's baseline read as readout.
- AC11.5 (4) The memory reconcile names ADR 0269 as the eval gate; `specs/memory/ARCHITECTURE.md:221` is the ledger-rendered line of the accepted 0178 record, whose title stays as accepted, and 0269's line (`:273`) carries the amendment. Test: none, memory text.

### FR12 — a closure lane for a block-list bug in rc-only code (`closure-lane-for-rc-only-block-bugs` (1)-(3))

Operator (Q1, Q2): "0 known defects"; brief: write the problem and the AC, the lane's design is the sr's at the PLAN.

The problem: after `release.py phase CLOSURE`, the bugs law admits a block-list bug only "through the version's hotfix lane and `worktree sync`" (`dadaia_workspace/public/scaffold/bugs/AGENTS.md:22`), but a hotfix lane is cut from the work branch, where code that exists only on the `wt-rc` is absent. rc-17 landed two such fixes on `wt-rc` by operator ruling ("Fix on wt-rc (Recommended)"): `append-crashes-on-the-event-shaped-archive` and `stats-names-the-repo-by-its-checkout-folder`; their `bugs.py update` and `resolve` commits (`c15018918`, `a2c64d47e`) have no row in the commit-shape table for that tree. `correlates` is write-once, so a reviewer's later correlate cannot be recorded: `asset-count-pins-miss-the-readout-script`, and `unclosed-quote-test-hand-spells-the-sync-path` against `tests-hand-spell-platform-paths-and-fix-lines`.

- AC12.1 (1) The law names one lane for a block-list bug in code that exists only on the `wt-rc` after CLOSURE, with its tree, its gate and its merge; no operator ruling is needed per case. Test: none, law text, unless the PLAN's design changes a verb (then integration).
- AC12.2 (2) `dd-gitflow-default` §3a gives that lane's registration, `bugs.py update` and `resolve` commits a row. Test: none, law text.
- AC12.3 (3) A correlate found after registration is recordable by a verb, and the two rc-17 cases are recorded with it. Test: unit for the verb.

### FR13 — the verification readout

Operator, rc-17 (rc-17 SPEC header): "after finishing the release candidate that will handle all of them, we will do another one to verify if we were efficient or not."

- AC13.1 The rc-18 closure summary carries §2's table: the reader's metrics 1, 2, 4, 6, 7 and 9, metric 8 from rc-17 AC1.2's test, metrics 3 and 5 from the developer's private tool, each beside its rc-17 baseline and target. Test: none, the closure procedure.

## 4. Exits at closure

- All nine Origin entries exit `delivered` with `--release 0.5.0`: `worktree-scripts-loose-ends`, `skill-kernel-loose-ends`, `package-loose-ends`, `push-gate-remedy-follow-ups`, `test-quality-loose-ends`, `rc17-review-loose-ends`, `ref-gate-open-questions`, `evals-functional`, `closure-lane-for-rc-only-block-bugs`. Inside `rc17-review-loose-ends`, item (14) closes KEEP (AC8.7).
- Both Origin bugs are resolved and archived.
- `eval.yml` lands on `main` through the Operational-Change Lane (ADR 0217(5)), so its weekly cron can fire (`main` holds the skeleton of `7af463ec0`). That act is the main thread's, after the rc-18 PR; it is an exit condition, not a task.

## 5. Not in rc-18

- rc-19, export (Q5, opened by a deep review and a grill): `spec-context-branch-field-deleted`, `context-dead-snapshots-open-worktrees`, `export-soft-and-hard`, `init-from-export`.
- rc-20, adoption and T3: `adoption-and-discoverability`, `eval-t3-discovery`, with the portfolio page in parallel (Q3).
- rc-21, prove and ship: the agentic scorecard >= 9, the T1+T2+T3 eval run recorded per ADR 0269, `launch-operator-acts`, `promote-gate-050`, the promote.
- 0.6.0 (Q2, Q8): `worktree-layout-per-context`, `context-show-derives-worktrees`, `multi-platform-by-construction-migration`, `bug-stats-hotspots-and-age`, `audit-project-scorecard-cycle`, `repo-ci-sast-gates`, `eval-codex-lane-in-library-ci`, `evals-benchmark-lanes`, `release-approve-requires-evals-gate`, `windows-smoke-t1-at-release`.

## 6. Constraints and risks

### Gate law for rc-18

- The job gate is `python scripts/ci.py job` (rc-17 metric 3: median 105 s). An implementer's definition of done is that, plus the touched test directories, plus the own-diff self-check. No preflight; no full CI line; CI on push is the net.

### Replaces

- `_worktree_end._checks`' instance-copy script path for a tree that carries its own library (`:293`).
- `_stats._window`'s `default="9"` and its birth-to-CLOSURE window for metrics 1 and 9; `_stats.py`'s import of `_bugs_store`.
- The four git-common-dir derivations, replaced by one `_git` helper.
- The three level-folder deciders, replaced by one owner.
- `core/gitflow.py`'s double-inheriting `SeveralWorkBranches`; `specs init`'s cut from HEAD.
- The `.gitattributes` `dadaia-dev-tooling` lines.
- The second homes of the `verify:` pin (`test_ci.py:151`) and of "a refusal's fix line runs" (`_fix_command`).
- `compare.py`'s ADR 0178 bar (T1 3/3 and the paired drop only), replaced by ADR 0269 (b).
- The write-once `correlates`; per-case operator rulings for rc-only closure fixes.

### Risks

- FR4, FR5 and FR8 touch many small units; the as-is review may find more items gone, which shrinks the rc.
- FR1's decider must not become a per-repo branch; the reviewer judges it against R1.
- FR12's lane design is open until the PLAN; a heavier lane than a law line plus one row needs its stated reason.

## 7. Open questions — resolved

Operator, 2026-10-18 (main thread): "Approve (Recommended)". The main thread's rulings on the Draft's three questions, folded above:

- (a) The install-count pins keep their literals: root map §1 says tests expect literals, and a count derived from the roster oracle would be a tautology. AC8.7 and the bug window row read KEEP; rc17 item (14) closes KEEP (§4).
- (b) The renderer does not change: ADR 0269's adr-list line carries the 0178 amendment; AC11.5 stands as written.
- (c) Metric 6 is reported as the reader prints it, `9dd383f16` included if the reader counts it.

### Main-thread rulings during implementation (2026-10-18)

Each is recorded in its job file's closure record.

- **Job 3 sweep lines.** Ruled: line 1 reads "no `fmt: skip` on a bare tuple closing"; the 8 one-line `fmt: skip` in `_stats.py` are the file's idiom. Ruled: line 2 (net ≤ 0) records net +3 against wt-rc, accepted for the two-read merge pick and the shared `reached`.
- **Job 3 tests.** Ruled: `test_bugs.py`'s trace pins assert by outcome; one `rev-list` read replaces the per-sha `merge-base`.
- **The R3 helper contract (Job 2 R3, Job 7 "Hook").** Ruled: `rev-parse --git-common-dir`, resolved, its parent; not `--path-format=absolute`. J7.T2 closed with no change.
- **AC8.2.** Ruled: `tests/scripts/test_ci.py:151` stays; it pins `ci.py`'s step plan, and the `verify:` line's one home is `test__worktree_end.py`.
- **AC8.4, narrowed.** Ruled: conftest classification stays keyed to the checkout, so `test_conftest_size.py` keeps its `tests/tmp/` module; `test_suite_session_env.py` places its module in the checkout, since its subject is the checkout tripwire. The merge-time residue is the main thread's reproduction at the job-7 merge; its result was not given to the closure pass. The job-7 review and re-review read `git status --short --ignored` after `ci.py job`: only `__pycache__`.
- **AC8.1.** Ruled: "13 stale docstrings" has no recorded source list (source list not recorded); bounded to the four touched files, 3 corrected.
- **AC8.5.** Ruled: one census row, for the work-branch force refusal; the creation and recreate refusals stay outside the census and go to the backlog (`rc18-review-loose-ends`).
- **AC4.4.** Ruled: the closure prints the worktree owner's `exit`, else its `fix`; the consumer authors no line (J4.T4). The earlier "runnable orphan merge line" ruling was wrong and was reverted after review.
- **The closure set (J4.T8, supersedes the J4.T6 ruling).** Ruled: CLOSURE holds every owner row of the repo except `kind == "rc"` and the tree it runs from, which keeps rc-17's contracts in `test__specs__workspace_root.py` (old-grammar work blocks; the running tree is spared). The owner gives every row a line, pinned by a partition test. `RC-FLOW.md` step 4 ("job, task or lane tree") under-stated the set and is corrected in the closure's law pass.
- **J5.T15–T18.** Ruled: the three wt-rc reds from Job 5 are fixed (the privacy path literal; the empty level folder; `_ledgers` takes the tree's copy only on exactly one `-z` match); the orphan row deletes through `drop_steps`, the one decider shared with the work-branch fix; the stale single-pass test in `test_git_subprocess.py` drives two passes. J5.T16 finding 2 (a symlinked level folder) was unreachable, since `_target` resolves first: no change.
- **J7.T7/T8.** Ruled: the census runs the printed fix; `Case.play` is the one place that plays a case's act, for both census drivers.
- **wt-rc took feature/0.5.0 twice by merge commit** (`a927901a6`, `4f1efa703`), not by rebase. Ruled: rebasing 132 rc commits conflicted; the merge resolved `test__worktree_git.py` once.
- **AC4.7.** Dropped on operator order ("Drop the rebind (Recommended)"): the rebind is reverted and AC4.7 returns to the backlog (`rc18-review-loose-ends`).
- **AC5.5.** KEEP on operator order ("KEEP, drop the RED (Recommended)"): the J2.T8 RED was deleted.
- **J5.T14.** Ruled: an off-grammar orphan branch names `git branch -d` only when HEAD holds it, else the dead flow's archive rule owns it; J5.T8's `-D` was the symptom patch.
