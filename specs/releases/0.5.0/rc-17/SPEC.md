# SPEC — Release: 0.5.0, candidate 17 — fix the 9 weak points

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-17
**Origin:** backlog:several-work-fix-line-follow-ups,law-and-docs-text-loose-ends,ref-gate-hardening-follow-ups

Operator demand, 2026-10-17, verbatim: "we will do a last release candidate right now that must handle [the 9 weak points] ... and after finishing the release candidate that will handle all of them, we will do another one to verify if we were efficient or not."

Sources: the grill record `.dadaia/reports/dadaia-workspace/grill/rc17-weak-points.md` (rulings verbatim, findings W1–W9); the rc-16 review artifact https://claude.ai/artifact/V1WH3ZAm7sbn17AVvYX7ob (v2); ADR **0266** (amends 0159) and ADR **0267**, both accepted 2026-10-17. The CWE-427 item has no slug of its own: it is item (3) of `law-and-docs-text-loose-ends`. Paths are relative to `repos/dadaia-workspace/`.

Operator rulings, verbatim (each FR quotes its own):

- Q10 rc-17 edge: "Weak points + 3 overlaps (Recommended)". Q11 rc-18 load: "Remaining 5 follow-ups + group B (Recommended)". Confirm: "Confirm + accept both ADRs (Recommended)".
- Post-SPEC, 2026-10-17 (the grill record's `## Post-SPEC rulings and defaults`): CI timeout "Ratify 30 min (Recommended)" (§6); CWE-427 "Delete fallback, flip 3 tests (Recommended)" (FR12). Every other answer below is marked "agent default, unruled".
- Pre-mortem, 2026-10-17 (the grill record's `## Pre-mortem rulings`): the bug `ref-gate-refuses-pack-refs-of-wt-branches` "Register; R3 into rc-17 (Recommended)" (FR14); the asserts "Re-point :551, remove :557-572 (Recommended)" (FR2); "By the library's own privacy guard (tests/infrastructure/test_privacy_check.py:137, public never names gh/ruff/xfail/ci.py): the shipped readout prints local metrics only; metrics 3 and 5 move to the developer's private tool (~/.claude), metric 8 is FR1's grep test. Self-check law text stays language-agnostic ("the repo's verify: line", "removed assertions, newly skipped tests")." (FR3, FR9). These replace the Post-SPEC agent defaults on R3 (rc-18) and on `gh` (read when present).

---

## Bug window review

**Window:** fixes closed after rc-16's window (`rc-16/SPEC.md`, fixes closed to 2026-10-14T19:53Z): the 53 records rc-16 archived (`1c43b993d`, 20; `b05443f5a`, 33) plus 6 resolved in `BUGS.jsonl` on 2026-10-17, the Codex hotfix `5ba9591ff..0f49df91a` included: **59 bugs**. Each fix was read with `git show`; the sha column lists the series where the ledger `fix_sha` is only its last commit. Verdicts: 45 KEEP, 14 REBUILD in three units, R1–R3.

| bug id | fix sha(s) | unit | verdict | reason (evidence) |
|---|---|---|---|---|
| `ref-gate-malformed-line-fix-carries-placeholders` | `522a25372` | `cli/commands/ci.py` `ref_gate_check` fix text | REBUILD R1 | a hand-typed act text rewritten at its site (+1/-1): the class ADR 0266 removes |
| `several-work-branches-blank-the-doctor-report` | `681f04c77` | `features/workspace/onboarding.py` first-pass row | REBUILD R1 | +17/-5: a `try/except SeveralWorkBranches` second path that strips the label by `removeprefix` |
| `several-work-fix-deletes-the-checked-out-branch` | `af6b055e6` | `_worktree_git.py` SeveralWork, `onboarding.py` | REBUILD R1 | CRITICAL, caused by `ship-archive-never-reaches-the-next-work-branch`'s fix; two follow-up bugs rewrote two tests' asserts |
| `several-work-rework-leaves-two-gitflow-tests-on-the-old-fix-line` | `e5bc72344` | `tests/core/test_gitflow.py` | REBUILD R1 | asserts moved to the new literal; third fix on one fix line |
| `several-work-agent-action-fix-breaks-the-verbatim-fix-runner-row` | `8074a594d` | `test__worktree_end.py` | REBUILD R1 | assert changed; `fixes(two)[0]` drops the one-fix check (FR10) |
| `missing-verify-refusal-fix-is-itself-blocked` | `42bbdf11c` | `_worktree_end.py` verify refusal fix line | REBUILD R1 | an `if root` branch and a rootless `worktree sync` second spelling; first of three fixes on this line in one day |
| `verify-red-fix-line-commits-outside-a-task-tree` | `bcd1fe3cf` | same | REBUILD R1 | a per-kind branch inside the act text (+3/-1) |
| `rc-red-verify-fix-line-gives-code-no-route` | `89d7c0b28`, `aa6a3a978`, `18dd60121` | same | REBUILD R1 | a `known` branch picks the act; a hand-typed `Operator action:` |
| `operator-action-fix-lines-hand-over-agent-acts` | `29c757964`, `f5263f80f` | every `Operator action:` site, the census | REBUILD R1 | caused by `agent-acts-are-labelled-operator-action`; six sites relabelled by hand plus a census exception table (`_OPERATOR_ACTIONS`) |
| `resolve-records-a-fix-sha-a-later-rebase-unreaches` | `c10a5ebf8`, `4e9dd349c` | `_bugs_check._unreached`, `_git.py` | REBUILD R2 | first of three fixes on `_unreached`, each caused by the previous |
| `unreached-check-refuses-a-shallow-clone-that-holds-every-fix-sha`, `unreached-check-crashes-on-a-percent-in-the-script-path` | `cc76aa03c` | `_unreached` | REBUILD R2 | second fix, two bugs |
| `unreached-fix-sha-judges-only-the-main-repo` | `6449771a6` | `_unreached` | REBUILD R2 | CRITICAL, third; +27/-7: a second path for associated repos that reads `.dadaia/states/spec_contexts.json` from a skill script |
| `ref-gate-admits-a-forced-move-git-hands-a-zero-old-sha` | `a1fc328ce` | `ci.py` `ref_gate_check` | REBUILD R3 | +4: a branch re-reading the old sha; the shell hook keeps a second creation decider; six fixes on the ref gate in the window (§6 Q1) |
| `ref-gate-reads-a-sha256-zero-old-sha-as-a-move` | `cafc4003d` | `git_scan.is_zero_sha` | KEEP | one predicate replaces five literal compares |
| `ref-gate-audit-escape-judges-a-move-by-tree-diff-not-ancestry` | `0d038d7fe`, `11791da1e`, `c470bafd0` | `check_ref_policy` | KEEP | REBUILD: one decider over facts the caller reads |
| `ref-gate-admits-a-work-branch-delete-then-recreate-at-any-commit` | `1fddc9df4` | `check_ref_policy` | KEEP | REBUILD, net -1 |
| `ref-gate-trusts-a-locally-writable-origin-tracking-ref`, `ref-gate-blind-to-a-branch-rename-onto-the-work-branch` | `1038afdf0` | worktrees law line 6 | KEEP | operator ruling 2026-10-16 narrowed the promise; text only |
| `ref-gate-refuses-the-denylist-journey-raw-commit-after-install-hook` | `ceb3edcbd` | E2E push journey | KEEP | the journey follows the product order; no assert loosened |
| `ref-gate-block-fix-line-forwards-to-a-projected-runner-that-lags-the-hook` | `b2968964d`, `b103154e2` | `cli/commands/worktree.py` forwarder | KEEP | through the one marker builder (+4/-4) |
| `skill-md-split-pin-left-on-the-deleted-plain-tree` | `7702e638d` | `test_entity_doctor.py` | KEEP | test follows rc-16 AC2.3's approved contract (+10/-18) |
| `prepush-ipv4-baseline-refuses-dotted-package-versions` | `2b95d56a3` | `denylist_scan.scan_objects` | KEEP | the skip scoped to content in the one scanner (+4/-4) |
| `tests-fallback-classes-test-named-ci-files-as-tests` | `4e853dfd3` | `_worktree_end._is_test_path` | KEEP | one condition in the one classifier |
| `protected-globs-miss-a-plain-tree-path` | `7cec79317` | `workspace_layout.protected_glob` | KEEP | REBUILD, net -2 |
| `new-reconcile-opens-while-a-job-is-open` | `1a190ef5d` | `_release_phase.py` closure wait | KEEP | net -3 |
| `bound-fix-spawn-oserror-prints-a-traceback-not-a-fix` | `6de643648` | `_specs.run_cli` | KEEP | REBUILD: three spawns into one owner |
| `job-gate-runs-the-whole-ci-line-and-preflight-runs-it-again` | `58c415a56`, `7c5bd1f35` | the repo `verify:` line | KEEP | restores `ci.py job`; the law hole that let it widen is FR4 |
| `memory-citation-judge-calls-every-passthrough-verb-dead` | `2c7adb05c` | `citations.dead_verb_citations` | KEEP | the leaf rule inside the one judge (+2) |
| `frontmatter-differential-reads-scratch-files-another-worker-deletes` | `369b4c17d` | staged-assets test | KEEP | test-only, tracked files |
| `cli-prints-unicode-marks-without-setting-utf8-stdio` | `b1d7f1fa3`, `de980fea5` | `platform.use_utf8_stdio`, `__main__.py` | KEEP | one entry point |
| `utf8-stdio-stderr-test-hardcodes-a-posix-line-ending-on-windows` | `a38399c11` | `test_main__utf8_stdio.py` | KEEP | reads through `oslib.run` |
| `shipped-hashes-lack-the-win32-render-digest-of-the-current-law` | `4ce501efc`, `47e628068` | `shipped-hashes.json` | KEEP | data append |
| `tests-hand-spell-platform-paths-and-fix-lines` | `eb3e9afea`, `f42db671b`, `678904cbb` | five test files | KEEP | expectations on the kernel spelling |
| `test-fixtures-write-non-ascii-text-without-an-encoding` | `6c1e1874b`, `bce78ad80` | test fixtures | KEEP | encoding passed; FR6 makes the class static |
| `tests-type-wrong-windows-asset-counts` | `21776f5da` | characterization tests | KEEP, noted | literals set to the observed Windows counts, the tests' existing form |
| `test-runs-a-shebang-stub-directly-on-windows` | `5de38391a` | reference-transaction tests | KEEP | the one `fake_venv` builder |
| `fake-venv-copies-the-venv-redirector-not-the-base-interpreter` | `94564d7db` | `tests/fixtures/stores.py` | KEEP | +2/-2 |
| `fake-venv-cli-test-decodes-utf8-help-output-with-the-locale-codec-on-windows` | `23d40bc8f` | fixtures, `.github/workflows/ci.yml` | KEEP, noted | the commit's subject names another bug; it moves the fix-line contract rows into `tests/fixtures/fix_world.py` (net -726) and raises the Windows/macOS contract job timeout 20 -> 30 min (§6 Q4) |
| `registry-test-control-block-calls-real-os-kill-on-windows` | `73804f71b` | `test_registry.py` | KEEP | patches `os.kill` at the boundary |
| `mutate-coverage-lookup-misses-windows-backslash-keys` | `f58a8aa5a` | `scripts/mutate.py` | KEEP | one compare form |
| `init-sibling-fix-line-is-hand-joined-and-unrunnable-with-a-blank-in-the-path` | `00161a164` | `InitPlan.command` | KEEP | REBUILD onto the kernel speller |
| `memory-atom-edit-left-the-generated-catalog-stale` | `dedb3fe80` | catalog pair | KEEP | the pair lands together; FR8 places the pass |
| `hook-lane-cost-test-counts-bytecode-cache-opens` | `4ee5237f9` | `test_ctx_inject.py` | KEEP | cold cache pinned; the rejected attempt was reverted |
| `certify-journey-tests-exceed-the-medium-tier-ceiling-under-load` | `8e7c86b6e` | certification tests | KEEP | no ceiling changed; the slow journey moved to E2E |
| `cli-line-and-the-kernel-render-one-argv-two-ways-on-windows` | `671587164` | `core/cli_line.py` | KEEP | REBUILD onto the kernel `command` |
| `constitution-text-read-raises-on-a-non-utf8-constitution`, `doctor-memory-reads-crash-on-a-non-utf8-document` | `56bf1c49c` | the kernel text door | KEEP | reads through the one door |
| `kernel-round-trip-test-runs-powershell-under-posix-spelling-on-linux-and-macos` | `4f6e1d9a0` | `test__platform__command.py` | KEEP | +1/-1 |
| `os-boundary-child-process-decode-is-spelled-per-call-site`, `os-boundary-venv-layout-and-path-spelling-leak-outside-the-seam` | `2af08de96` | infrastructure onto the kernel door | KEEP | REBUILD, net -73 |
| `os-boundary-filesystem-semantics-are-assumed-posix-per-call-site` | `d502512d5` | `_atomic.py` | KEEP | the kernel `is_link` |
| `os-boundary-process-control-is-posix-only-at-the-call-site` | `b2644bd28` | `spec_context/sweep.py` | KEEP | the kernel `file_owner`, net -2 |
| `os-boundary-text-codec-is-decided-per-call-site` | `87a29d3f5`, `be928cd62` | kernel, entry points | KEEP | ADR 0265's one door |
| `win32-quote-leaves-shell-metacharacters-unquoted-in-fix-lines` | `87a29d3f5` | `_platform.quote`, `spell` | KEEP, noted | the ADR 0265 kernel (+1251/-75), redo of the reverted `17752dbd4` |
| `windows-head-with-a-blank-garbles-the-pip-launcher-command-line-in-cmd` | `cedd3456d` | `_platform.head` | KEEP | REBUILD, net -7 |
| `os-boundary-shell-spelling-has-several-producers-and-a-lossy-quoter` | `38034fc66` | kernel `command`/`inline`, Kimi wrappers | KEEP, noted | production code under a `test(` subject (+336/-75); one encoder |
| `wt-rc-merge-runs-ledger-checks-on-an-associated-repo-tree` | `183a36590` (RED), `b8bf1bb11` | `_worktree_end._ledgers` | KEEP | REBUILD: one decider for rc and backlog |
| `codex-push-rule-conflicts-with-workspace-gitflow` | `e677235a2` (RED), `f791ae8cf`; memory `152dd7b66` | `codex_assets.py` command policy | KEEP | deletion, net -8 |

**REBUILD work list** (bugs law §2; each keeps the contract tests its fixes hardened): FR1 takes R1 (AC1.4), FR2 takes R2 (AC2.5), FR14 takes R3 with `ref-gate-hardening-follow-ups` (pre-mortem ruling).

## 1. Problem

The rc-16 review found nine weak points (grill findings W1–W9): fix-induced bugs with no sibling lookup (W1); fix-line labels typed by hand at 155 sites (W2); 100 of 232 rc-16 verdicts rejected with no implementer self-check (W3); two law holes that let the job gate widen from 125 s to 1221 s for 11.6 h (W4); a closure that took unscoped work after CLOSURE (W5/W7); Windows and macOS PR reds from codec, line-ending and path classes (W6); no commit row for pure law text (W8); and memory reconciled only at CLOSURE while 13 atoms drifted after it (W9). rc-18 verifies whether rc-17 was efficient, on the readout of FR9.

## 2. Measurable Goals — the 9-metric readout (acceptance of FR9)

rc-18 is judged on this table. Baselines 1, 2, 4, 6 and 9 are agent defaults, unruled (grill record, Post-SPEC section, and the main thread 2026-10-17); the rest are the grill's findings.

| # | metric | rc-16 baseline | target | source |
|---|---|---|---|---|
| 1 | fix-induced bugs: records with `caused_by` not `none` / all records | rc-16 alone 42/56, 75 % | <= 20 % | `verdict.py stats` |
| 2 | first-pass approval: trees whose first verdict is `APPROVED` / trees | recomputed by the FR9 reader for rc-16, rc-17's method: the grill's 71/110 and the rc-16 summary's 67/121 first-pass rejected disagree | >= 70 % | `verdict.py stats` |
| 3 | merge `verify:` wall time | `ci.py job` median 1m52 over 6 runs; 125 s before, 1221 s during the J4.T16 widening (W4) | <= 150 s | the developer's private tool, outside the library |
| 4 | closure duration, CLOSURE to the candidate PR merge | 40.5 h: CLOSURE 10-16 02:12 -> PR #296 merge 10-17 18:42 | <= 4 h | `verdict.py stats` |
| 5 | CI red share of the work branch's runs | 22/93 failed since 10-14, 24 % (W6) | <= 10 % | the developer's private tool, outside the library |
| 6 | non-block commits landed after CLOSURE | 74+: the OS-boundary REBUILD commits after the CLOSURE stamp (W5/W7) | 0 | `verdict.py stats` |
| 7 | memory drift at the PR: atoms `release.py drift` names at the `wt-rc` head | 13 atoms (W9); 14 by `2aca959f9` | 0 | `verdict.py stats` |
| 8 | hand-typed fix-line labels outside the producer | 155 in 52 files (W2) | 0 | AC1.2's grep test |
| 9 | REBUILD-due fixes landed as a patch | none: starts at rc-17's own readout; the closest rc-16-era reading, not a baseline, is 14 of 59 REBUILD verdicts in this SPEC's bug window review | 0 | `verdict.py stats`, through `bugs.py stats` (AC2.8) |

## 3. Requirements

Wave ranking, by the pick: (1) law, skills and dev loop — FR3, FR4, FR5, FR7, FR8, FR11; (2) shared foundation — FR1's producer, FR2's ledger fields, FR6's lint rule; (3) features and bugs — FR1's call-site sweep with R1, FR2's append and R2, FR9, FR10, FR12, FR14 with R3; (4) promote-facing — FR13 and the closure readout.

### FR1 — one fix-line label producer (W2, ADR 0266)

Operator: "A: one act() producer (Recommended)".

- AC1.1 `act(kind, text)` in `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_platform.py` returns `Agent action: <text>` and `Operator action: <text>`; the package reaches it through `core/cli_line.py` and `core/platform.py`. Test: unit.
- AC1.2 One contract test greps every `.py` and `.sh` file under `dadaia_workspace/` and finds either label literal only in `_platform.py` and in its one named exception, `public/scripts/pre-push-ci-gate.sh:32` (a POSIX shim with no Python); law prose is not a site (metric 8). Test: unit.
- AC1.3 The per-site label checks collapse into the AC1.2 test; `tests/fixtures/fix_census.py` stays unchanged, since it censuses raises and `spell_fix` sites, not labels. The `_OPERATOR_ACTIONS` category table (`ruling`/`protected`/`reach`, the regression net of `operator-action-fix-lines-hand-over-agent-acts`) is kept and re-pointed at `act("operator", …)` calls, since no assert is removed without an operator order (agent default, unruled). The every-block AST scan renders `act(...)` calls before the sweep, so its checks keep seeing the act texts. Every fix line still clears its refusal in the existing refusal-clears tests, unchanged. Test: integration.
- AC1.4 R1: the red-verify and missing-verify refusal fix lines of `_worktree_end.py`, the SeveralWork fix line (`_worktree_git.py`, the `onboarding.py` first-pass row) and the ref gate's malformed-line fix are rebuilt onto `act()` with one path each; the contract tests their window fixes hardened stay green, unloosened. Test: unit.

### FR2 — the bug surface derived from fix files (W1, ADR 0267)

Operator: "A: derive the surface (Recommended)".

Agent defaults, unruled: `surface` stays an optional legacy property of the schema; `fix_files` is write-once at resolve; `--component` stays free text.

- AC2.1 `bugs.py append` drops `--surface` and writes no `surface`; `bug-record-v1` keeps `surface` as an optional legacy property, so the records that carry it pass `bugs.py check`. Test: unit.
- AC2.2 `bugs.py resolve` writes `fix_files`, the files its `fix_sha` touched, once; a later verb never rewrites it. Test: unit (`tests/public/skills/dd_bug_resolution/scripts/test_bugs.py`, the ADR's `measured_by`).
- AC2.3 `bugs.py append` prints every earlier bug, read from `BUGS.jsonl` and `_archive/bugs_histo.jsonl`, whose `fix_files` holds a path the new bug's `--component` text names, each line naming the REBUILD due (`REBUILD due: 3rd bug on <file>`). Test: unit.
- AC2.4 The law that reads `surface` reads the fix files instead: `dd-bug-registration` §3 step 2, `dd-bug-resolution` `LINEAGE.md` §The filter, `dd-release-definition` §2. Test: none, law text; the reviewer greps for `surface` leftovers.
- AC2.5 R2: one reader of a record's fix commit serves both `resolve`'s file list and the reachability check `_unreached`; the contract tests of the three window fixes stay green. Test: unit.

Pre-mortem, operator: "Re-point :551, remove :557-572 (Recommended)" — "test_bugs.py:551 re-pointed at fix_files; :557-572 removed with the --surface flag in a test(...) commit naming this order and ADR 0267."

- AC2.6 `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py:551` asserts the `fix_files` sibling contract instead of the `surface` candidates; `:557-572` (the tracked-directory `surface` cases) is removed with the `--surface` flag, in one `test(...)` commit naming this order and ADR 0267. Test: unit.
- AC2.7 The schema pin `tests/core/test_handoff_index__handoff_schema_contract.py:142,236-250` follows `bug-record-v1`: `surface` an optional legacy property, `fix_files` write-once. Test: unit.
- AC2.8 `bugs.py stats` reports the REBUILD-due siblings by the AC2.3 rule; metric 9 reads them through it, never through `append`. Test: unit.

### FR3 — the implementer self-check (W3)

Operator: "A: self-check, no gate change (Recommended)"; the operator asked that the gate not grow.

- AC3.1 `dd-release-implementation` states the self-check once, language-agnostic: the repo's `verify:` line, the touched test directories, and an own-diff grep (0.014 s) for hand-typed labels, platform literals, removed assertions, newly skipped tests and leftovers of the swept pattern. The repo `verify:` line (here `python scripts/ci.py job`, median 1m52) and the merge checks do not change. Test: none, law text; the reviewer confirms `git diff` of the `verify:` line is empty.
- AC3.2 The implementer personas point to that step and do not restate it. Test: none, law text.
- AC3.3 `dd-bug-registration` gains two steps: `git blame` the failing lines to propose `caused_by`; search the ledger for correlates. Test: none, law text.
- AC3.4 No shipped file FR3 or FR9 writes names `ci.py`, `ruff`, `xfail` or `gh`; `tests/infrastructure/test_privacy_check.py` `test_public_law_names_no_private_pipeline` (its pattern at `:137`) stays green, unchanged. Test: unit (existing).

### FR4 — two gate-law holes closed (W4)

Operator: "A: close both law holes (Recommended)".

- AC4.1 The root map line on gate cost (`dadaia_workspace/public/data/AGENTS.md:27`) measures a `verify:` change against the `verify:` it replaces, never against itself. Test: none, law text.
- AC4.2 `dd-grill-me` `SKILL.md:32`: Recommended never marks a heavier gate. Test: none, law text.
- AC4.3 The dev pin test of the repo `verify:` line stays, green and unchanged. Test: unit (existing).

### FR5 — closure scope (W5/W7)

Operator: "A: law line + next rc opens at once (Recommended)".

- AC5.1 After `release.py phase CLOSURE`, only block-list bugs (`specs/bugs/AGENTS.md` §2) land on the `wt-rc`; any other bug, REBUILD or operator demand becomes a job of the next rc. Test: none, law text (`RC-FLOW.md` step 4, `specs/releases/AGENTS.md`); metric 6 reads it.
- AC5.2 The closure is the reconcile alone, and the next rc is born at once. Test: none, law text; metric 4 reads it.
- AC5.3 `specs/constitution.md` §5 states that the agentic scorecard is the final rc's last implementation job before the promote, never after the closure summary. `dd-product-engineer`, the constitution's writer, lands it in its `pe` task commit, whose body quotes the Q5 ruling, the operator's decision under constitution §4 (agent default, unruled; precedent `e04ca698d`). Test: none, law text.

### FR6 — Windows by static rules (W6)

Operator: "A: static rules, no new step (Recommended)"; the grill's honest estimate is 20-25 % fewer Windows/macOS reds. This later ruling governs over ADR 0265's rejection of PLW1514.

Agent default, unruled: FR6 is a configuration pin, not a sweep. 127 of the 128 calls the grill counted already go through the `_platform` UTF-8 helpers (the 128th is `importlib.metadata`), ruff preview `PLW1514` finds 0 product hits, and the tree holds 0 CRLF files.

- AC6.1 `[tool.ruff.lint]` sets `preview = true` and `explicit-preview-rules = true` and selects `PLW1514`; it rides the existing `ruff check`, and no CI step or job is added. Test: the lint step itself (`python scripts/ci.py lint` exits 0 with the rule on).
- AC6.2 The only real hit, `evals/tasks/t2-block-list-bug/tests/test_grade.py:51`, passes its encoding; no other call is edited. Test: AC6.1's lint rule.
- AC6.3 `.gitattributes` sets `eol=lf` on `/tests` and `/scripts`. Test: none, one config line; the evidence is `git check-attr eol` on one file of each tree.

### FR7 — a `docs(law)` commit row (W8)

Operator: "A: a docs(law) row (Recommended)".

- AC7.1 `dd-gitflow-default` §3a gains a `docs(law)` row: pure law or doc text, committed in the job tree that found it, one review, no ledger record; text a program prints stays Arm B. Test: none, law text.

### FR8 — the memory pass goes last (W9)

Operator: "A: memory pass goes last (Recommended)".

- AC8.1 `RC-FLOW.md` step 4 runs `release.py drift` and the memory pass as the last reconcile step before the `wt-rc` merge and PR, after `measured_by` repairs, the measurement, the sweep and GC; the 2026-10-08 ruling stands (staleness judged by existence, `91e1d1991`). Test: none, law text; metric 7 reads it.

### FR9 — the 9-metric readout (measurement)

Operator: "A: extend verdict.py stats (Recommended)".

Pre-mortem ruling (quoted at the top): the shipped readout prints local metrics only; metrics 3 and 5 are the developer's private tool's, outside the library; metric 8 is AC1.2's one-grep test, not a reader output. Its ADD (about +40 production lines) is the one Q9 ordered.

- AC9.1 `verdict.py stats <M.m.p>-rc<N>` is REBUILT as the one reader of the §2 table: it prints metrics 1, 2, 4, 6, 7 and 9 from local ledgers, handoffs and git, each with its value and target, and the oldest verdict record it read. Test: unit, each metric over fixture ledgers and handoffs.
- AC9.2 The reader prints only those six metrics, reads no remote and spawns no host CLI; no shipped file names `gh` (AC3.4). Test: unit, the output over fixtures holds metrics 1, 2, 4, 6, 7 and 9 and no other.
- AC9.3 Every rc closure summary carries the full table: the reader's six metrics, metric 8 from AC1.2's test, metrics 3 and 5 from the developer's private tool. Test: none, the closure procedure (`RC-FLOW.md` step 4).
- AC9.4 The reader computes the rc-16 baseline of metric 2 by the method it applies to rc-17, and the rc-17 closure summary carries that reading. Test: none, the closure procedure.
- AC9.5 A lane tree (`wt-backlog-<slug>`, `wt-hotfix-<bug-id>`) counts in the rc's metric 2 when its first verdict falls between the rc's birth and its CLOSURE stamp, both read from `_RELEASE.json`'s `log`. Test: unit, a lane verdict inside and one outside the window.

### FR10 — SeveralWork fix-line follow-ups (`several-work-fix-line-follow-ups`)

Operator (Q10): "Weak points + 3 overlaps (Recommended)".

- AC10.1 `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py:213` takes `[fix] = fixes(two)`, so the one-fix check of `run_fix` holds. Test: unit.
- AC10.2 Root map §3's `Agent action: <one act>` wording agrees with the ruled SeveralWork form. Test: none, law text.

### FR11 — law and doc text loose ends (`law-and-docs-text-loose-ends`)

Operator (Q10): "Weak points + 3 overlaps (Recommended)".

- AC11.1 Items (1), (2), (4), (5) and the text parts of (3) of the entry land under FR7's row: the `bugs.py update` commit row, the `scripts/ci.py` docstring, `RELEASE-EVENTS.md:25`, `scripts/CONSUMER_VALIDATION_RECIPE.md` R-04, `docs/cli.md:10`, the scratch-only probe recipe in `dd-code-review`, the `pkill -f`/`pgrep -f` line. Test: none, law and doc text.
- AC11.2 `_release_tree.py` calls `closure_summary` once. Test: unit (existing tests green, unchanged).

### FR12 — no repo `.venv` in the hook runner search (CWE-427)

Operator (Q10): "Weak points + 3 overlaps (Recommended)". Fix shape, post-SPEC: "Delete fallback, flip 3 tests (Recommended)".

- AC12.1 `public/scripts/reference-transaction.sh:31` and `public/scripts/pre-push-ci-gate.sh:26` resolve the runner only from a `.dadaia/.venv` found walking up from the repo; the repo `.venv` fallback is deleted, and `templates/shipped-hashes.json` appends the two new digests. With no workspace venv above the repo, pre-push refuses with its existing fix line and the ref gate warns and passes. Test: integration, a planted `<repo>/.venv` runner is never run.
- AC12.2 The three tests that pin the fallback today (`test_pre_push_ci_gate__pre_push_gate_venv_probe.py` `repo_local_venv`, `test_pre_push_ci_gate.py`, `test_reference_transaction.py:202`) tighten to assert the repo `.venv` is never used, in one `test(...)` commit naming this ruling. Test: integration.

### FR13 — the memory reconcile (W9)

Operator (Q8): "rc-17 reconciles the 13 atoms". Agent default, unruled: `harness-codex` (drift's 14th at `2aca959f9`, changed by `f791ae8cf`) and every atom rc-17's own changes trigger join the pass.

- AC13.1 The rc-17 memory pass reviews or changes 14 atoms: `agent-orchestration`, `agentic-entities`, `public-asset-distribution`, `spec-context-project`, `context-management`, `specs-migration`, `workspace-doctor`, `audits-canon`, `backlog-ledger`, `bug-ledger`, `release-lifecycle`, `sdd-gate-v3`, `worktrees`, `harness-codex`; plus those rc-17 triggers, which the as-is review names as `agent-comms`, `product-vision`, `cross-platform-portability`, `workspace-init` and `QUALITY.md`, and any other atom drift names by then; `release.py drift` at the PR head names none. Test: none, the closure check (`release.py check` requires the memory entry).

### FR14 — the ref gate refuses no ref packing (bug `ref-gate-refuses-pack-refs-of-wt-branches`, R3, `ref-gate-hardening-follow-ups`)

Operator (pre-mortem): "Register; R3 into rc-17 (Recommended)" — "Job 8 = ref-gate REBUILD (R3 + ref-gate-hardening-follow-ups), registration is its first commit (shape 1 in its wt-main)."

The bug, CRITICAL, a Stall: `dadaia_workspace/hooks/ref_transaction.py:67-69` refuses any `refs/heads/wt/*` line with a zero old sha, so `git pack-refs`, which `git gc --auto` runs, fails; its fix line, `worktree new` on an existing tree, cannot be run. Reproduction: `git pack-refs --all` -> `[ref-gate] BLOCKED refs/heads/wt/0.5.0/rc-17/wt-rc`. Registration is the first commit of Job 8's `wt-main` (shape 1).

- AC14.1 A RED test reproduces the refusal: `git pack-refs --all` in a repo holding a `wt/*` branch, with the hook installed, prints `[ref-gate] BLOCKED` and fails. Test: integration.
- AC14.2 A `git pack-refs --all` or `git gc` transaction over existing `wt/*` branches passes. Test: integration for the hook, unit for the decision.
- AC14.3 A real `wt/*` creation by a raw `git branch` is still refused. Test: integration for the hook, unit for the decision.
- AC14.4 The fix line of every refusal the ref gate still prints is runnable in the state it refuses. Test: integration, each refusal's fix line run in its refused fixture.
- AC14.5 R3: one decider judges a `wt/*` ref line; the old-sha re-read branch of `a1fc328ce` and any creation decision left in the shell shim go; the contract tests of the ref gate's window fixes stay green, unloosened. Test: unit.
- AC14.6 Each item of `ref-gate-hardening-follow-ups` that survives at the rc-17 head (the PLAN's as-is review names which, with `path:line`) lands: a raise inside a decided BLOCK stays a BLOCK, the shim header states the law's `wt/*` rule, the forced-move LOWs. Test: unit for a behaviour; none for comment text or an item shown gone.
- AC14.7 Operator ruling 2026-10-17, "Refuse recreate (Recommended)": recreating a work branch (a zero-old line on `refs/heads/<work>`) passes only at a sha its `refs/remotes/origin/<work>` contains, the same rule as a move; the never-reproduced SHA-length patterns leave `ref-gate-hardening-follow-ups` for a new backlog entry at closure intake. Test: integration for the hook, unit for the decision.

## 4. Exits at closure

- `several-work-fix-line-follow-ups`, `law-and-docs-text-loose-ends` and `ref-gate-hardening-follow-ups` exit `delivered` with `--release 0.5.0`.

## 5. Not in rc-17

- rc-18, the verification rc (Q11): `worktree-scripts-loose-ends`, `skill-kernel-loose-ends`, `package-loose-ends`, `push-gate-remedy-follow-ups`, `test-quality-loose-ends`, and group B: `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees`, `launch-operator-acts`.
- Every other active backlog entry waits.

## 6. Constraints and risks

### Gate law for rc-17

- The job gate is `python scripts/ci.py job` (median 1m52). An implementer's definition of done is that, plus the touched test directories, plus the own-diff self-check of FR3. No preflight; no full CI line; CI on push is the net.
- The Windows/macOS contract job timeout stays at 30 min, raised from 20 by `23d40bc8f`. Operator, post-SPEC: "Ratify 30 min (Recommended)"; the measured Windows contract median is 27.0 min (range 15.4-27.4, 6 runs).

### Replaces

- `bugs.py append --surface` with its tracked-directory check (`_bugs_write.py:54-59`), its tests (`test_bugs.py:557-572`), and the surface-keyed candidate lookup (`_bugs_write.candidates`); the schema keeps `surface` as an optional legacy property.
- `LINEAGE.md` §The filter's "Match `surface` exactly".
- The per-site label literals `Agent action:` and `Operator action:`, 155 in 52 files.
- The per-site label checks, replaced by one grep test; `tests/fixtures/fix_census.py`, a raise/`spell_fix` census, stays, and the `_OPERATOR_ACTIONS` table stays, re-pointed (AC1.3).
- ADR 0159's pinned builder pair, for labels (amended by ADR 0266).
- The R1 per-site act branches: the `if root` rootless sync spelling, the per-kind and `known` act choices in `_worktree_end.py`, and the onboarding row's own `SeveralWorkBranches` catch.
- R2's second reachability path in `_unreached`, which reads the workspace registry from a skill script.
- Free closure scope: any non-block work on the `wt-rc` after CLOSURE.
- The current memory-pass placement: `RC-FLOW.md` step 4 runs it right after `release.py phase CLOSURE`.
- The scorecard run after the closure summary.
- The self-referential cap text: root map §1's gate-cost line read against the `verify:` being changed.
- `verdict.py stats`'s four counters (`sequences`, `verdicts`, `rejected`, `first_pass_rejected`), replaced by the 9-metric table.
- The repo `.venv` fallback of the two hook runners.
- The ref gate's refusal of every zero-old `refs/heads/wt/*` line, `git pack-refs` included, and `a1fc328ce`'s old-sha re-read branch (FR14).

### Risks

- FR1 edits about 155 call sites in one REBUILD job (ADR 0266 consequences); the AC1.2 grep is the leftover check. With the `_OPERATOR_ACTIONS` table kept, the test delta is about -10 to -30 lines, not ADR 0266's estimated -150.
- The rc's production lines grow by about +59, mostly FR9's reader (+40, the ADD Q9 ordered) and FR1's imports; the reviewer judges the stated reason.
- FR2 leaves two record shapes in the ledger; the reader treats the typed field as legacy (ADR 0267 consequences).
- FR6 removes about 20-25 % of the Windows/macOS reds by the grill's estimate; metric 5's target may not hold on static rules alone.

## 7. Open questions

- Q1–Q6 of the Draft are answered 2026-10-17 (the grill record's Post-SPEC section): Q1 §5, Q2 §2, Q3 FR12, Q4 §6, Q5 FR13, Q6 §2 and AC9.4.
- The update's four questions are answered 2026-10-17 by the main thread, each an agent default, unruled: metric 2 alone is recomputed and metric 6 keeps 74+ (§2); metric 9 starts at rc-17's readout (§2); the Q5 ruling carries the constitution line (AC5.3); AC11.2 drops the entry's unnamed "duplicated contract helpers" half.
- Pre-mortem answers 2026-10-17 (rulings quoted at the top): FR14, AC2.6-AC2.8, AC3.4, AC9.2, AC9.5.
- Open, for the main thread: (a) `ref-gate-hardening-follow-ups` carries two items FR14 does not decide: the SHA-1-length-only patterns (not reproduced) and its question for the operator, whether unmarked forced `wt/*` moves pass and whether deleting and recreating the work branch at any sha passes by design. Both ride the rc-17 closure intake unless ruled; the §4 `delivered` exit assumes that. (b) The Origin carries no `bugs:` clause: the bug is registered only by Job 8's first commit, and `release.py check` traces each Origin id back.
