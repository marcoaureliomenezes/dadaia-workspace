# SPEC — Release: 0.5.0, candidate 10 (the fix reader; evals T1, T2 and the first run; QUALITY's bug balance; HOOKS-DRIFT-1; the test freeze; the test tree)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-06 in the `0.5.0-rc10/define` tree while rc-9 reconciles (0205).
**Origin:** backlog:agent-behavior-evals,bug-ledger-balance-and-convergence,guidance-messages-name-the-right-target,tests-tree-mirrors-the-package,unit-tier-without-processes,worktree-rows-injected-not-monkeypatched,windows-integration-coverage-gap,focused-review-on-caused-by,bugs-fix-reads-the-per-class-shape,context-dead-never-commits,bug-fix-adds-never-rewrites-asserts,caused-by-proposed-by-blame; findings:20260930-structural-convergence-F098,20260930-structural-convergence-F128

- Sources, under `.dadaia/handoff/dadaia-workspace/`:
  - `2026-10-06T015544Z-main-thread-grill-rc10-scope`: Q1–Q4, Q2b, Q5, Q6, ADR 0206.
  - `2026-10-05T040135Z-main-thread-grill-granularity-parallelism`: less Q19, which 0206 overrides.
  - `2026-10-05T005326Z-main-thread-grill-bug-window-review`: G8, G10.
- Scope (Q4, Q6): 8 jobs, the cap (0193). Evals T1 and T2 fold into one job, so the test freeze fits. The bug batch and Reconciliation are not counted.
- Facts at 27123ce99:
  - `dadaia-evals` has no `tasks/`; `eval.yml` (on its `main`, 877ff5b) has never run; its `AGENTS.md` has no `verify:` line.
  - Memory names 8 test files that no longer exist.
  - HOOKS-DRIFT-1 reads an absent hook as "differs".
- Entry order (M4):
  1. At rc-9's CLOSURE, `release.py new` writes the stub `rc-10/SPEC.md` on the work branch.
  2. This define tree rebases onto it and replaces the stub with this SPEC.
  - `release-new-adopts-a-drafted-next-rc` is carried to rc-11.
- Bug law: 0206. No rc closes with an open bug.

## Bug window review

Read on `feature/0.5.0` at 27123ce99, then on `wt/0.5.0-rc9/reconcile`, with `bugs.py window`, `fix` and `git show --numstat`.

- Window: 251 records (`0.4.7`, `0.5.0`); 452 with release `unknown`.
- Found in rc-9: 5, all resolved: the 4 rc-9 bug rows of the table, and `verify-line-absent-refusal-sends-to-a-tree-the-gate-never-reads`. `dependabot-pyjwt-open-on-main` (found in rc-7) is resolved in rc-9.
- 13 records were resolved retro in rc-9 (AC2.9) on fixes from before rc-9. rc-9's window judged them (C9).
- Direction: `bugs.py fix` prints `-` for every task-commit fix, so the column below is hand-computed: production `dadaia_workspace/**` lines, then tests. → AC1.1.
- Rework count (Q5) needs AC1.1's reader; rc-11's window carries it.
- Traceability: no rc-9 resolution carries `evidence_seam`. Of the 317 records that carry one, 116 name a file that no longer exists. → AC1.2.

| bug(s) | fix | direction (prod; tests) | what followed | verdict |
|---|---|---|---|---|
| `job-task-id-test-assumes-native-paths` (hotfix; C2) | 121ae02b2 | +5/−3; +19 | no C2 record since Job 1's matrix gate | KEEP |
| `verify-line-absent-refusal-sends-to-a-tree-the-gate-never-reads` (hotfix, CRITICAL; caused by J1.S3.T1) | sha filled at Approval | REBUILD of `_gate` under 0207, in rc-9 | — | KEEP that REBUILD; rc-11 reads its rework |
| `ci-and-release-install-vulnerable-poetry` (hotfix, block 4) | 858bc97ad | workflows ±10, pyproject +3/−26; guard row `poetry-below-the-floor` | nothing | KEEP |
| `dependabot-pyjwt-open-on-main` | 46d10b5bb (PR #277, Operational-Change Lane) | lock only, on `main` | nothing | KEEP |
| `bugs-fix-lists-one-commit-twice` (caused by T-050-167) | c9faccfdc | +5/−1; +21 | second fix on the fix reader | **REBUILD**: AC1.1, keeping its test rows |
| `specs-law-file-untracked-by-gitignore` | 6c73219b1 | guard +5/−15; +17 | one revert inside the job (0a6b649dc) | KEEP; its test moves with Job 7 |
| AC2.1 coverage | a6fadcdde, 67d8ed1e5 | 0; +12/−10 | review fold | KEEP |
| AC2.2 hooks coverage | 2299ce56b | +7/−4; −2 | nothing | KEEP |
| AC2.3 registry key | 7c494c568, b19f9541c | +30/−17; −1 | review fold | KEEP |
| AC2.4 absent specs | 84ed78453, d55cf2399, 1c5494f10 | +9/−4; +16/−1 | review fold | KEEP |
| AC2.5 upgrade scratch | 00824a1ee | +9/−23; +15/−1 | nothing | KEEP |
| AC2.6 memory rerun | 9888c647b, ac4b18094 | +5/−1; +15/−1 | review fold | KEEP |
| AC2.7 ledger seam (REBUILD) | 5029ae91d, 6ebe02029, dc4d2f5a5, 25298e7e3 | +135/−96; +57/−7 | review folds | KEEP: the verdict was "seam reduced" |
| AC3.1 C1, 3 records (REBUILD) | 68acfb610 | 0; +109/−282 | nothing | KEEP |
| AC3.3 C3/C4, 8 records (REBUILD) | d8f325e3d, 93cf75152 | +133/−98; +43/−54 | stage appended inside the job | KEEP: the verdict was "reduced" |
| AC3.4 T-050-168's tests | f6a791f3a | +3/−2; +8/−11 | nothing | KEEP |
| AC3.5 `_StubDoctor` | 568a33c60 | 0; +2/−21 | nothing | KEEP |
| AC3.6 stdin guard | 89746389a | guard +16/−5 | nothing | DELETE in Job 8 (AC8.3): it lists patch forms; the one harness replaces it |

- Pattern read (Q5):
  - No fix commit rewrites an old assert, special-cases a test value, or reaches into another feature.
  - Second path: the stdin guard lists patch forms one by one → DELETE (AC8.3).
  - ≥ 2 fixes on one unit: the fix reader (T-050-167, then c9faccfdc) → REBUILD.
- Job 1 executes the one REBUILD and builds the inputs this review lacked: direction, rework and `evidence_seam`.

## Terms

- **Fix surface**: the production lines a fix commit wrote. It settles once it survives 2 rcs untouched by another fix or REBUILD (Q5).
- **Rework**: a later commit whose diff overlaps a fix surface, classed by its shape.
  - `refactor(…): REBUILD` is planned rework.
  - `fix(bugs)` of another bug is overfitting evidence.
- **Settled surface**: a surface whose every record left the bug window with no later record on it (G8).
- **Convergence readout**: a number `QUALITY.md` `## Bugs` prints at each closure, blocking nothing (Q2, Q2b).
- **RED anchor**: the sha that closes a job's RED stage. After it, the job's test files are frozen (Q6).

## Job 1 — the fix reader and the window's instruments

- AC1.1 One REBUILD of the `bugs.py fix` commit reader (verdict above; `bugs-fix-reads-the-per-class-shape`; Q5). c9faccfdc's test rows stay unchanged.
  - It diffs every linked commit, a shape-4 task commit included; the never-diffed `None` path leaves.
  - It links a per-class shape-4 commit by the ids on its body lines.
  - For each fix it prints the fix surface, its rework count by class, and settled or the rcs it has left.
  - Everything is derived from git; nothing is stored.
  - **Unit** rows:
    - a shape-4 resolve over two task commits gives summed numstat and a literal direction;
    - a class commit links its body ids;
    - a later `fix(bugs)` overlapping the surface counts 1 overfitting;
    - a REBUILD counts 1 planned;
    - two rcs untouched read settled.
- AC1.2 `evidence_seam` is required at resolve and checked only there (G10, 0208).
  - `bugs.py resolve --evidence-seam <path>[::node]` refuses a path git does not track, or a node whose text, with parameter brackets stripped, is not in the file. The check is textual and works for any language.
  - A fix with no test cites any tracked file.
  - `bugs.py check` never re-judges a seam.
  - `bugs.py window` marks a record whose seam file is gone.
  - **Unit** rows: present; untracked path; absent node; parametrized node; a non-test tracked file; a window row with a deleted seam.
- AC1.3 The window review compares each fix against the overfitting patterns (Q5):
  - an assert or test changed by the fix;
  - a special case on a test value;
  - a new branch, flag or second path;
  - a reach into another feature;
  - deleted functionality;
  - ≥ 2 fixes on the unit.
  - Each fix then gets KEEP or REBUILD. A REBUILD reworks the fix's code and what surrounds it, and keeps the fix's tests.
  - Taught in `dd-release-definition` §1. **No test** (law text).
- AC1.4 One producer for the REBUILD-or-not line (M6). `dd-bug-resolution` `LINEAGE.md` step 7 writes it into the fix commit's body, either `rebuild: <unit> — prior fixes <id>, …` or `rebuild: none — <reason>`. `PILLAR-BUGS` gains a ninth metric: the share of fixes with `caused_by ≠ none` that carry a REBUILD shape or that line (`focused-review-on-caused-by`, audit half). Target 100 %; it gates nothing. **No test**. Check: `grep -c 'rebuild: none — <reason>'` prints ≥ 1 in `LINEAGE.md` and in `PILLAR-BUGS.md`.

## Job 2 — evals: the repo law, T1 and T2

Writes only to `repos/dadaia-evals` and the job file.

- AC2.1 `dadaia-evals/AGENTS.md` declares `verify:`, `verify-stage:` and `verify-task:` lines, holding the secret-free checks `ci.yml` runs. **No test**. Check: `grep -c '^verify' AGENTS.md` prints `3`, and this job's gate runs the `verify:` line.
- AC2.2 Skeleton (rc-8 AC11.2):
  - `tasks/t1-cold-onboarding/` and `tasks/t2-block-list-bug/` each hold `instruction.md`, `task.toml`, `environment/Dockerfile`, `tests/test.sh` and `tests/test_grade.py`.
  - The Dockerfile holds the environment only; the lib is its last layer (0179).
  - **Integration**: each image builds with the 0.4.7 layer and with a candidate wheel; `git ls-files jobs` prints nothing.
- AC2.3 T1, cold onboarding (rc-8 AC11.3):
  - The environment is a `file://` bare repo with one commit.
  - It passes on `dadaia doctor --json` with 0 errors, the context ALIVE and specs initialized.
  - **Integration** (no model): the unchanged grader passes on a hand-onboarded workspace of each version and fails on an empty one.
- AC2.4 T2 plants a block-list bug (Q1): a small onboarded project whose suite, its work branch's CI, is red after a merged change broke a documented contract. The instruction gives the operator's confirmation.
  - Both versions' law fixes it at once.
  - It passes when:
    - a `BUGS.jsonl` record precedes the fix commit;
    - the RED test fails on the pre-fix sha and passes on the fix;
    - the suite is green at HEAD;
    - `git diff -U0 -- tests | grep '^-\s*assert'` prints nothing.
  - The grader reads only `bug-record-v1` fields both versions carry.
  - **Integration** (no model): on both versions, a planted correct fix passes and a planted assert-rewriting fix fails.

## Job 3 — evals: the first run

Edge: Job 2, merged to `dadaia-evals` `main` through its PR edges.

- AC3.1 One `gh workflow run eval.yml -f lib_ref=<tip of feature/0.5.0>`: T1 and T2, k=3, 0.4.7 against the candidate (rc-8 AC11.6).
  - It confirms the trial ran the stamped candidate wheel (`dadaia capabilities --json`).
  - It confirms no rate-limit error appears in `jobs/`.
  - A failing grader is fixed in the grader before closure.
  - **No test**. Check: a `_RELEASE.json` `kind: note` names the run URL, the verdict per 0178 (2), tokens and wall time.

## Job 4 — QUALITY.md's bug balance and the convergence readouts

`bug-ledger-balance-and-convergence`; G8, Q2, Q2b; 0208. The generator ships with the bug skill and stays language-neutral.

- AC4.1 `QUALITY.md` `## Bugs` holds one generated fenced block, rendered from `BUGS.jsonl` alone.
  - Per surface: records, recurrences, fix-induced, archived, rcs in the window, correlates, settled.
  - Dev-tooling surfaces form a repo-declared class (a `.gitattributes` attribute, the 0183 seam) and print apart.
  - `unknown` surfaces stay out of recurrences.
  - **Unit**: a literal ledger renders a literal block; a rerun is byte-equal.
- AC4.2 Readout 1, the Laplace trend (Kanoun & Laprie, *Handbook of Software Reliability Engineering* ch. 10), continuous time with days as the axis, over all bugs (Q2b).
  - Window: the live release plus the 3 previous published (today 0.4.5–0.5.0).
  - Only records with a known `found_in` release count. Records sharing their `ts` with another record (a backfill or bulk import) are excluded and counted apart.
  - u = (mean of tᵢ − T/2) / (T·√(1/(12N))), where tᵢ is a record's day offset from the window start and T is the window's length in days.
  - u ≤ −1.96 reads "converging", u ≥ +1.96 "diverging", anything else "no trend".
  - A second line counts records found on a surface that was already settled.
  - **Unit**: t = `[1, 2, 3]` and T = 10 give `u = -1.80`, "no trend"; one backfill pair is counted apart.
- AC4.3 Readout 2, the defective-fix rate per rc (Kan, *Metrics and Models in Software Quality Engineering* ch. 4; Jones 2012): records found in rc i with `caused_by ≠ none`, over records found in rc i. **Unit**: literal ledger, literal rates.
- AC4.4 The block is a closure check, never an always-on doctor check.
  - At CLOSURE, `release.py check` refuses a block that differs from its regeneration, with one fix line naming the regenerating command.
  - The readouts block nothing. LINT-1 exempts the fenced block.
  - **Integration**: a stale block refuses in CLOSURE and passes in IMPLEMENTATION.
- AC4.5 The written review under `## Bugs` states the standing causes, verdicts and lessons.
  - It also carries the latest evals verdict line, outside the generated block (M7).
  - It is rewritten, never appended. `docs/bug-ledger-lessons.md` re-derives from it (P-29), its source moving from the `bug-ledger` atom and today's `QUALITY.md` sections.
  - `CONTEXT.md` gains this SPEC's Terms.
  - **No test** (memory).

## Job 5 — HOOKS-DRIFT-1 states what it observed

- AC5.1 One code (rc-8 AC10.12; F098; `guidance-messages-name-the-right-target`'s last part). The message names the observed state, absent or differing. One fix line, `ci install-hook --force --repo <abs>`, serves both.
  - **Unit**: an absent hook is reported as absent, an edited one as differing.
  - **Integration**: delete a projected hook; its fix line, run, restores the hook and clears the finding.

## Job 6 — the test freeze

Q6 items 1–5; 0209. Everything is judged by `git diff` over the repo's declared test paths, so it works for any language.

- AC6.1 Tests are born only in a RED stage, one whose tasks' `W:` holds tests only. Each new test is validated before the freeze: collected, failing by assertion (never by error), test-audit, stage review. **Integration**: a RED stage whose new test errors instead of failing cannot close.
- AC6.2 From the RED anchor on, a task or job merge refuses any diff on a test file. This covers unit, integration and E2E tests and the tests that existed before; a pure rename is allowed.
  - The refusal carries one `Operator action:` line: stop and report.
  - **Integration**: an edited test refuses; a pure rename lands; a new RED stage lands.
- AC6.3 A wrong test is never edited in an implementation task. The implementer stops and reports; the amendment is a new RED stage, with its review and the operator's approval.
  - `specs/releases/AGENTS.md` §3's clause on rewriting a test in the same task leaves.
  - A REBUILD keeps the fix's tests.
  - **No test** (law text).
- AC6.4 The task gate's `test_`-name check (`_worktree_end.py:287-292`) becomes an owner rule: a code task names its owner tests, and `scripts/guards/run.py` owns `scripts/guards/**`. **Integration**: a guard-only task with that owner passes; a code task with no owner refuses.
- Jobs 7 and 8 change existing tests only in test-only stages. This SPEC's approval is the amendment AC6.3 names.

## Job 7 — the tests tree mirrors the package

`tests-tree-mirrors-the-package`, `windows-integration-coverage-gap`; 0167. Edge: Job 7 → Job 8 (`tests/conftest.py`).

- AC7.1 Every test file is `tests/<mirror of dadaia_workspace>/test_<module>.py`, or one e2e journey carrying `Owner:`.
  - `contract/` and `integration/` dissolve into those owner files; no ghost or empty test directory remains.
  - `test_docs_derived_from_memory.py` stays until publish-gate check #7 rules (rc-13).
  - **No test** (guard script, 0176): a guard check, red on a planted loose file and on an empty test directory.
- AC7.2 The move is `git mv` plus merge, one feature per commit, with no assert changed. **No test**. Check: `git grep -h '^\s*assert' <base> -- tests | sort` equals the same at HEAD.
- AC7.3 The size marker comes from the fixture a test uses: real git or a subprocess makes it medium, never its folder. **Unit** (`pytester`): a real-git test collects as medium, a pure one as small.
- AC7.4 The cases `windows-integration-coverage-gap` names that still exist run on the Windows CI job by marker. **No test**. Check: the Windows job log lists them.

## Job 8 — the unit tier spawns no processes

`unit-tier-without-processes`, `worktree-rows-injected-not-monkeypatched`, the 0163 hook harness, rc-7's slow-class G4 growth.

- AC8.1 No small test spawns a process. Each offender either gets its pure core extracted and tested pure, or turns medium (AC7.3). **No test** (guard script, 0176): a guard check, red on a planted subprocess in a small test. Readout, gating nothing: ≥ 70 % of small items run under 100 ms.
- AC8.2 `SpecContextService` and `DoctorService` take worktree rows by constructor injection. The autouse monkeypatch and the inline patch in `test_cli_context.py` leave. Boundary fakes live in `tests/fakes.py`. **Unit**: each service built with a stub rows callable.
- AC8.3 Every hook test drives its hook through the one production-faithful harness (0163): the entrypoint as a subprocess, fed a payload fixture. No test patches `sys.stdin`. The `hook-stdin-not-in-process` guard check leaves; the harness is the one way a hook test feeds stdin. **Integration**: one row per hook lane. Check: `grep -c hook-stdin-not-in-process scripts/guards/isolation.py` prints `0`.

## The bug batch

- AC9.1 Every bug found in rc-10 is resolved in rc-10 (0206).
  - A block-list bug is a hotfix at once.
  - Every other bug goes to the bug batch: after the DAG's last job, before Reconciliation, grouped by cause, a fix-induced one as a REBUILD (0210 settles which ones).
  - A bug found during Reconciliation is fixed inside it.
  - **No test**. Check: `bugs.py status` prints `0 open` at Reconciliation's end.

## Reconciliation

**No test**: each AC is observed by its command or by a `_RELEASE.json` line.

- AC10.1 Memory states the merged code; each atom lands with its derived sections in one merge (0192).
  - Every `tests/…py` path named in `QUALITY.md` and `ARCHITECTURE.md` exists. `grep -c RELEASE-TREE-MEMORY specs/memory/ARCHITECTURE.md` prints `0`.
  - F098 and F128 are dispositioned `resolved`.
- AC10.2 `## Bugs` is regenerated after the disposition sweep. `_RELEASE.json` logs the readouts, AC8.1's readout, each job's `kind: merge` entry and each job's bug-surface delta.
- AC10.3 The `measured_by` of 0208 and 0209 names cases this rc built (AC1.2, AC4.1–AC4.4; AC6.1–AC6.2); a name that moved is repaired in the 0138 lane.
- AC10.4 Each Origin backlog entry exits once, `delivered --release 0.5.0`. `agent-behavior-evals` exits after AC3.1 is logged, with 0177–0179 ruled.
- AC10.5 Closure follows the releases law, with zero open bugs; rc-11 is defined beside it.

## ADRs

- 0176 and 0178 are accepted (Q3); the main thread writes the rulings. 0176's memory half is AC10.1. 0178 applies at rc-13's promote.
- 0174 is rejected (Q3); its live clauses are re-proposed at rc-11.
- **0208** (ADR C), accepted with this SPEC's Approval, before Job 1 (G8, G10, Q2, Q2b, Q5):
  - `QUALITY.md` `## Bugs` holds a generated map plus a written review, compiled at each closure; per-bug state stays only in `BUGS.jsonl`.
  - A surface settles once it leaves the window with no recurrence.
  - The map is a closure check. Context: G8 said "checked by doctor". The rc-8 W13 review (REJECTED; H7) moved it to closure, because an always-on check reddens every tree between closures. This ADR records that difference.
  - The readouts block nothing: the Laplace trend over all bugs (days axis, 4 releases, known `found_in` only), the settled-surface count, and the defective-fix rate.
  - Fix surfaces and rework are derived from git, never stored.
  - `bugs.py resolve` requires `evidence_seam`, checked textually only then.
  - Amends 0164 (4). `measured_by`: AC1.2's and AC4.1–AC4.4's cases.
- **0209**, proposed, accepted with this SPEC's Approval (Q6), "Tests are born in RED stages and frozen at the RED anchor":
  - AC6.1–AC6.4's rule.
  - Amends the releases law §3's same-task rewrite clause.
  - `measured_by`: AC6.2's cases.
- **0210**, proposed: one REBUILD trigger. ADR 0186 (2) says a `caused_by` other than none means a REBUILD. The bugs law §2 (0206) says a REBUILD only for a fix-induced bug. The options:
  - (a) A REBUILD when `caused_by` names a bug. When it names a task, the smallest fix plus the focused review's REBUILD-or-not line.
  - (b) 0186 (2) as written: every `caused_by ≠ none`.
  - The operator decides before Job 1.

## Replaces

- `bugs.py fix`'s never-diffed shape-4 link; the fix reader's two prior fixes (AC1.1).
- 0164 (4)'s retirement of `evidence_seam` (AC1.2).
- A bare `rebuild: none` (AC1.4).
- HOOKS-DRIFT-1's fixed "differs" (AC5.1).
- Rewriting a test in an implementation task; the `test_`-name gate check (AC6).
- Loose `contract/` and `integration/` roots; the folder-derived size tier (AC7).
- Processes in the unit tier; the autouse rows monkeypatch; patched `sys.stdin` and the `hook-stdin-not-in-process` guard check (AC8).
- `docs/bug-ledger-lessons.md`'s source: the `bug-ledger` atom and today's `QUALITY.md` sections give way to `## Bugs`' written review (AC4.5).
- Stale `Measured by` paths (AC10.1).

## Risks

| Weakness | Mitigation |
|---|---|
| 8 jobs is the cap. | A new need goes to rc-11. |
| Job 3 spends the operator's model quota: 12 trials. | `-n 2`, the economy template, one run. |
| Jobs 6–8 touch the merge gate, `tests/conftest.py` and most test files. | PLAN edges; Jobs 7 and 8 change tests in test-only stages (AC6.3). |
| Jobs 1 and 4 share the bug skill. | Disjoint files or a PLAN edge. |
| The verify-line hotfix sha is not landed. | Filled at Approval. |

## Carried

Every active backlog id is placed: the Origin above, or one of the lines below.

- rc-11, the corpus, the law and the ADR process:
  - `public-law-language-neutral`, `dd-ask-me-owned-questioning-skill`, `adr-born-at-release-with-options`, `adr-ledger-triage-process-rules`, `architecture-adr-section-generated`;
  - rc-9's deferrals: `stage-gate-runs-the-contract-tier`, `job-gate-runs-the-law-deletion-check`, `merge-entry-times-survive-rebase`, `task-gate-mypy-follows-cross-skill-imports`, `hypothesis-cache-stays-out-of-repo-trees`, `stray-pycache-never-breaks-the-job-gate`, `task-gate-drops-deleted-paths-itself`, `release-new-adopts-a-drafted-next-rc`, `origin-findings-renamed-to-the-spec-head`, `adr-0193-records-its-amends`;
  - F088, F089, F139–F148; 0174's live clauses.
- rc-12, workspace replication: `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees`, `export-soft-and-hard`, `init-from-export`; 0171, 0173, 0175; F084.
- rc-13, the promote:
  - `docs-site-zensical-pages`, `clone-detection`, `launch-operator-acts`;
  - `spec-context-refusals-print-prose`, `privacy-baseline-one-parser`, `ledger-refusals-guess-specs-from-command-shape`, `ledger-reader-one-numbered-tolerant-iterator`;
  - `meta-tests-leave-pytest` with check #7;
  - `repo-ci-sast`, less its poetry clause, which 858bc97ad fixed: ruff `S`, `pip-audit`, CodeQL, the work-branch secret scan;
  - F067, F069, F123–F127, F137; the 0178 evals gate;
  - the operator's ruling before the promote (rc-8 F4): ADR 0122's zero active backlog against the four post-0.5.0 evals entries.
- Delivered in rc-9; each exits at rc-10's closure:
  - `context-dead-never-commits`, by 8f878c730 (AC3.2);
  - `bug-fix-adds-never-rewrites-asserts`, by 13a4395a5 (AC5.9);
  - `caused-by-proposed-by-blame`, by 579a6c70a with its tests REBUILT by f6a791f3a (AC3.4).

## Not in scope

- An evals scenario for a bug fixed by the bug batch (Q1); `evals-release-gate-status`, `evals-harness-lanes-and-benchmark`, `evals-windows-smoke`, `devin-subagent-projection`: all after 0.5.0.
- Q6 item 6, a read-only test layer in the harness: not taken.
- The private test-stack and commit-gate hooks.
