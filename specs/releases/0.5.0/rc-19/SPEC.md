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
| `branch-d-fix-line-judges-head-not-the-upstream` | `995ac1256` (`6bb57a885`) | `_worktree_git.py` `SeveralWork` fix line, `drop_steps` | REBUILD R3 | two patterns hit. (a) Its RED commit `301cc9f2c` changed an existing assert: `tests/core/test_gitflow.py:205` drops the `-d` step from the expected fix line, a contract change made inside a fix. (b) It is the 5th bug on the line, after `several-work-fix-deletes-the-checked-out-branch`, `several-work-rework-leaves-two-gitflow-tests-on-the-old-fix-line`, `several-work-agent-action-fix-breaks-the-verbatim-fix-runner-row` and `several-work-branches-blank-the-doctor-report`. ADR 0270 extends `work_versions` (`:88-92`, local refs only) to origin refs, so a low branch that exists only on origin reaches `drop_steps`, whose `--merged`, `--unset-upstream` and `-d` steps judge local branches only (`:110-119`) |
| `bugs-check-misses-a-record-both-live-and-archived` | `20fefc4a7` | `_bugs_check.py` `findings_for`, `_bugs_write.py` `append` | KEEP, noted | `caused_by: none`. The rule is new, ruled by the operator on 2026-10-19 ("Event lines aren't records (Recommended)"). The fix deletes `archived_ids` and puts every archive read on one reader, `_archive_lines`; its `events` flag tells apart the two archive line shapes, which the same ruling keeps. The old asserts changed in `c96ad777d` were born in this bug's own RED commits (`a6ec66063`, `d3a018380`). Noted: "id taken" is still decided twice, in `append` (`taken`, `_bugs_write.py:71`) and in `findings_for`, which every write runs; `append`'s copy exists for its `--bug-id` fix line (intake) |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened):
- R1, `_stats.py`'s read of the release state: rc-19's first job. Operator, 2026-10-19: "Register, fold into case 2 in rc-19 (Recommended)". One REBUILD in which stats reads the release state through the release skill's schema-checked reader. It closes the open Origin bug and deletes the per-input guards of the three rows.
- R2, `_ledgers`: one decider names the ledger scripts that judge a tree. The `own` flag, the glob and the single-match rule are deleted. The contract tests of the four chain bugs stay green, unloosened.
- R3, the `SeveralWork` fix line: rebuilt together with ADR 0270's origin-ref reading in `work_versions`, so one decider names both the kept work branch and the drop steps, local or remote-only. The contract tests of `301cc9f2c` and of the four earlier bugs stay green.

## 1. Problem

(Describe the problem this release solves.)

## 2. Measurable Goals

(List observable outcomes.)

## 3. Non-goals

(Explicitly list what this release does NOT cover.)

## 4. Requirements

(List the scope clusters / acceptance criteria.)

## 5. Constraints and risks

(Upstream blockers, sequencing constraints, risk table.)

## 6. Open questions

(Questions the operator must decide before approval, or `none`.)
