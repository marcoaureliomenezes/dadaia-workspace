# SPEC — Release: 0.5.0, candidate 10 (the fix reader; evals T1, T2 and the first run; QUALITY's bug balance; HOOKS-DRIFT-1; the test freeze; the test tree)

**Status:** Approved
**Approval:** operator ruling 2026-10-06 (AskUserQuestion): "Aprovo SPEC + 0208–0210 (Recommended)", on 9f36ca986 (reviewer APPROVED 9f36ca986).
Amended 2026-10-06 on review M-A at cfe73a297 (factual sha/count corrections); approval basis: dd-code-reviewer re-review of the amended define head.
Amended 2026-10-07 by operator ruling: Jobs 2 and 3 annulled, Job 9 added ("Novo job no rc-10 (Recommended)").
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-06 in the `0.5.0-rc10/define` tree while rc-9 reconciles (0205).
**Origin:** backlog:agent-behavior-evals,bug-ledger-balance-and-convergence,guidance-messages-name-the-right-target,tests-tree-mirrors-the-package,unit-tier-without-processes,worktree-rows-injected-not-monkeypatched,windows-integration-coverage-gap,focused-review-on-caused-by,bugs-fix-reads-the-per-class-shape,context-dead-never-commits,bug-fix-adds-never-rewrites-asserts,caused-by-proposed-by-blame; findings:20260930-structural-convergence-F098,20260930-structural-convergence-F128

- Sources, under `.dadaia/handoff/dadaia-workspace/`:
  - `2026-10-06T015544Z-main-thread-grill-rc10-scope`: Q1–Q4, Q2b, Q5, Q6, ADR 0206.
  - `2026-10-05T040135Z-main-thread-grill-granularity-parallelism`: less Q19, which 0206 overrides.
  - `2026-10-05T005326Z-main-thread-grill-bug-window-review`: G8, G10.
- Scope (Q4): 8 jobs, the cap (0193); the bug batch and Reconciliation uncounted. The SPEC's packing, not a ruling: T1 and T2 share one job so the test freeze fits.
- Facts at 27123ce99:
  - `dadaia-evals`: annulled 2026-10-07 by operator ruling; it leaves the context, and the evals move to the library repo (Job 9).
  - Memory names 8 test files that no longer exist (3 at cfe73a297).
  - HOOKS-DRIFT-1 reads an absent hook as "differs".
- Entry order (M4): at rc-9's CLOSURE `release.py new` writes the stub `rc-10/SPEC.md`; this tree then rebases and replaces it (`release-new-adopts-a-drafted-next-rc`: rc-11).
- Bug law: 0206; no rc closes with an open bug.

## Bug window review

Read at 27123ce99 and on `wt/0.5.0-rc9/reconcile`; re-read at cfe73a297, rc-9's Reconciliation merged (`bugs.py window`, `fix`, `git show --numstat`).

- Window: 257 records (`0.4.7`, `0.5.0`); 452 with release `unknown`.
- Found in rc-9: 7, all resolved, each a row of the table. `dependabot-pyjwt-open-on-main` (found in rc-7) is resolved in rc-9.
- 13 records resolved retro in rc-9 (AC2.9) on older fixes: judged by rc-9's window (C9).
- Direction: `bugs.py fix` prints `-` for task-commit fixes; the column is hand-computed (production, then tests). → AC1.1.
- Rework count (Q5) needs AC1.1's reader; rc-11's window carries it.
- Traceability: no rc-9 resolution carries `evidence_seam`; 116 of the 317 that do name a missing file. → AC1.2.

| bug(s) | fix | direction (prod; tests) | what followed | verdict |
|---|---|---|---|---|
| `job-task-id-test-assumes-native-paths` (hotfix; C2) | 121ae02b2 | +5/−3; +19 | no C2 record since Job 1's matrix gate | KEEP |
| `verify-line-absent-refusal-sends-to-a-tree-the-gate-never-reads` (hotfix, CRITICAL; caused by J1.S3.T1) | a1960ffc2; the merged hotfix d1d4d36c4 (HF.T3, REBUILD of `_gate` under 0207) | a1960ffc2 +20/−15; +28. d1d4d36c4 +4/−4; +36/−3 | `_gate`'s line authority moved three times (ed26c7f0d, 8818220e3, a1960ffc2), then d1d4d36c4; nothing since | KEEP that REBUILD; rc-11 reads its rework |
| `ci-and-release-install-vulnerable-poetry` (hotfix, block 4) | 858bc97ad | workflows ±10, pyproject +3/−26; guard row `poetry-below-the-floor` | nothing | KEEP |
| `dependabot-pyjwt-open-on-main` | b3f03e3d8 (PR #277, Operational-Change Lane), resolved by c734b4bdc | lock only, on `main` | nothing | KEEP |
| `bugs-fix-lists-one-commit-twice` (caused by T-050-167) | de36b0e69 | +5/−1; +21 | the third commit on `_fixes`; bd0628092 and e638d4a88 followed on it | **REBUILD**: AC1.1, keeping its test rows |
| `bugs-fix-counts-a-reverted-fix` (caused by T-050-167) | bd0628092 | +9/−2; +22 | the fourth commit on `_fixes`; review REJECTED it at 8693810de (HIGH-A, M-1) and e638d4a88 rewrote it | **REBUILD**: AC1.1, keeping its test rows |
| the in-job correction of bd0628092 (JR.S8.T1, a task commit `bugs.py fix` does not link) | e638d4a88 | +15/−12; +31 | the fifth commit on `_fixes`; it leaves two ceilings, AC1.1 (a) and (b) | **REBUILD**: AC1.1, keeping its test rows |
| `memory-window-bound-unreachable-from-head` | cc544f66e | +4/−0; +29 | nothing on the unit since. `_memory_drift.py` carries 4 resolved records; d1e29503b (`shallow-clone-history-finding-fix-line-never-clears`, in `git()`, "the ONE history precondition") and cc544f66e (in `report`) answer one question, "is the window bound usable", in two places | **REBUILD** (by law (dd-release-definition SKILL.md:28: ≥2 bugs, a second path)): one bound precondition in `git()`'s failure arm, `report`'s probe (cc544f66e) folded into it; behaviour-preserving, no new RED, guarded by the existing rows of both fixes' tests, no assert changed; Job 1's J1.S3.T2 |
| `specs-law-file-untracked-by-gitignore` | ca56950b3 | guard +5/−15; +17 | the first fix ab57de945 was reverted inside the job by 70ef08270, whose subject cites ab57de945's dead pre-rebase sha b6b029319; 4a0d331e9 changed its test's setup only (review LOW-3; asserts byte-identical) | KEEP; its test moves with Job 7 |
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
  - No fix commit rewrites an old assert, special-cases a test value, or reaches into another feature; d1d4d36c4 and 4a0d331e9 change test setup only.
  - Second path: the stdin guard lists patch forms one by one → DELETE (AC8.3). The window bound is judged in two places (cc544f66e) → REBUILD (by law (dd-release-definition SKILL.md:28: ≥2 bugs, a second path)).
  - ≥ 2 fixes on one unit: the fix reader, 5 commits on `_fixes` (built by 48376cb96 and 19eb4c1a1; fixed by de36b0e69, bd0628092, e638d4a88) → REBUILD (AC1.1); `_memory_drift.py` (d1e29503b, cc544f66e) → REBUILD (by law (dd-release-definition SKILL.md:28: ≥2 bugs, a second path)).
- Job 1 executes the REBUILDs and builds the inputs this review lacked: direction, rework and `evidence_seam`.

## Terms

- **Fix surface**: the production lines a fix commit wrote; a **settled fix surface** survived 2 rcs untouched by another fix or REBUILD (Q5).
- **Rework**: a later commit whose diff overlaps a fix surface: a `refactor(…): REBUILD` is planned; a `fix(bugs)` of another bug is overfitting evidence.
- **Settled ledger surface**: a ledger `surface` (a directory) whose every record left the bug window with no later record on it (G8).
- **Convergence readout**: a number `## Bugs` prints at each closure, blocking nothing (Q2, Q2b).
- **RED anchor**: the sha closing a job's RED stage; after it the job's tests are frozen (Q6).

## Job 1 — the fix reader and the window's instruments

- AC1.1 One REBUILD of the `bugs.py fix` commit reader (verdict above; `bugs-fix-reads-the-per-class-shape`; Q5). de36b0e69's test rows and the two revert tests, `test_fix_drops_a_fix_commit_a_later_revert_undid` (bd0628092) and `test_fix_pairs_each_revert_with_one_commit` (e638d4a88), stay unchanged.
  - It fixes both known ceilings of the rc-9 reader: (a) reverting a revert-of-revert does not drop the fix again (the `ponytail:` at `bugs.py:118` at cfe73a297); (b) L-A: the greedy `_REVERT` capture mis-pairs a short-form revert whose tail holds a quote. Direction (agent default — unruled): pair on git's default revert subject, `Revert "<subject>"`, which survives a rebase. Rejected: pairing on the sha in the revert body (`This reverts commit <sha>.`), because a rebase leaves it citing a dead sha (bd0628092's body; 70ef08270's subject).
  - It diffs every linked commit, a shape-4 task commit included; the never-diffed `None` path leaves.
  - It links a per-class shape-4 commit by the ids on its body lines.
  - For each fix it prints the fix surface, its rework count by class, and settled fix surface or the rcs it has left.
  - `PILLAR-BUGS.md:8` ("a shape-4 task commit is counted, never diffed") is rewritten to match.
  - Everything is derived from git; nothing is stored.
  - **Unit** rows: a shape-4 resolve over two task commits gives summed numstat and a literal direction; a class commit links its body ids; a later overlapping `fix(bugs)` counts 1 overfitting, a REBUILD 1 planned; two rcs untouched read a settled fix surface; a revert of a revert of a revert drops the fix; a short-form revert whose tail holds a quote pairs with the one commit it undid.
- AC1.2 `evidence_seam` is required at resolve and checked only there (G10, 0208).
  - `bugs.py resolve --evidence-seam <path>[::node]` refuses a path git does not track, or a node any of whose `::` segments, parameter brackets stripped, is not in the file (`TestX::test_y` finds both). The check is textual and works for any language.
  - A fix with no test cites any tracked file.
  - `bugs.py check` never re-judges a seam.
  - `bugs.py window` marks a record whose seam file is gone.
  - **Unit** rows: present; untracked path; absent node; parametrized node; `TestX::test_y`; a non-test tracked file; a window row with a deleted seam.
- AC1.3 The window review compares each fix against the overfitting patterns (Q5): an assert or test changed by the fix; a special case on a test value; a new branch, flag or second path; a reach into another feature; deleted functionality; ≥ 2 fixes on the unit. Each fix then gets KEEP or REBUILD. A REBUILD reworks the fix's code and what surrounds it, and keeps the fix's tests.
  - Taught in `dd-release-definition` §1. **No test** (law text).
- AC1.4 One producer for the REBUILD-or-not line (M6). `dd-bug-resolution` `LINEAGE.md` step 7 writes it into the fix commit's body, either `rebuild: <unit> — prior fixes <id>, …` or, only when `caused_by` is none, `rebuild: none — <reason>`. `PILLAR-BUGS` gains a ninth metric: the share of fixes with `caused_by ≠ none` carrying a REBUILD: a `refactor(…): … REBUILD` subject or `REBUILD` in a `fix(bugs):` subject (121ae02b2 counts) (`focused-review-on-caused-by`, audit half; 0210). Target 100 %; it gates nothing. **No test**. Check: `grep -c 'rebuild: none — <reason>'` prints ≥ 1 in `LINEAGE.md` and in `PILLAR-BUGS.md`.
- AC1.5 Any `caused_by ≠ none`, a bug's fix or a feature task, makes the fix a REBUILD of the unit, keeping its tests (0210). Rewritten to say so: the bugs law §2's "a fix-induced one as a REBUILD" (`public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`) and `dd-code-review/SKILL.md:55`'s "state REBUILD of the unit or why not". **No test** (law text).

## Job 2 — evals: the repo law, T1 and T2

Annulled 2026-10-07 by operator ruling; replaced by Job 9.

## Job 3 — evals: the first run

Annulled 2026-10-07 by operator ruling; replaced by Job 9.

## Job 4 — QUALITY.md's bug balance and the convergence readouts

`bug-ledger-balance-and-convergence`; G8, Q2, Q2b; 0208. The generator ships with the bug skill and stays language-neutral.

- AC4.1 `QUALITY.md` `## Bugs` holds one generated fenced block, rendered from `BUGS.jsonl` alone.
  - Per surface: records, recurrences, fix-induced, archived, rcs in the window, correlates, settled ledger surface.
  - Dev-tooling surfaces form a repo-declared class (a `.gitattributes` attribute, the 0183 seam) and print apart.
  - `unknown` surfaces stay out of recurrences.
  - **Unit**: a literal ledger renders a literal block; a rerun is byte-equal.
- AC4.2 Readout 1, the Laplace trend (Kanoun & Laprie, *Handbook of Software Reliability Engineering* ch. 10), continuous time with days as the axis, over all bugs (Q2b).
  - Window: the live release plus the 3 previous published (today 0.4.5–0.5.0); it starts on the oldest one's opening day (its first `_RELEASE.json` log `ts`, archive included) and T ends on the closure day.
  - Only records with a known `found_in` count (Q2b; operator: "4 releases, eixos em dias, so found in conhecido").
  - The SPEC's reading, not a ruling: a known `found_in` is a release other than `unknown`. Release-`unknown` records (bulk imports, backfills) are counted apart. The 33 records with no `found_in` key at all are counted apart the same way. A record with rc `unknown` but a known release counts here (the axis is days); it is excluded only from per-rc tables (AC4.3).
  - u = (mean of tᵢ − T/2) / (T·√(1/(12N))), where tᵢ is a record's day offset from the window start and T is the window's length in days.
  - u ≤ −1.96 reads "converging", u ≥ +1.96 "diverging", anything else "no trend".
  - A second line counts records found on an already settled ledger surface.
  - **Unit**: t = `[1, 2, 3]` and T = 10 give `u = -1.80`, "no trend"; a release-`unknown` record is counted apart; a record with no `found_in` key is counted apart; an rc-`unknown` record of a known release counts.
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

Q6 items 1–5; 0209. Everything is judged by `git diff` over the repo's test paths, so it works for any language. Edges: Jobs 1–5, 7 and 8 → Job 6, the DAG's last job; its freeze binds every job opened after Job 6 merges, rc-10's bug batch (AC9.1), any later hotfix and Reconciliation included; the gate keeps no rc-number special case. Arm B's RED-then-fix stages already fit the freeze. Jobs 1–5, 7 and 8, AC8.2's RED included, run under today's law.

- AC6.0 A repo declares its test paths as one `tests:` line of globs in its tracked `AGENTS.md`, beside the `verify:` lines (e.g. `tests: tests/** **/*_test.go`). The gate reads it from the work branch, the authority 0207 uses, so no worktree changes what counts as a test. Job 6 commits `tests: tests/**` to dadaia-workspace's `AGENTS.md`. A repo with no `tests:` line refuses with one line in 0207's lane, `Operator action: commit the tests: line on <work branch>'s AGENTS.md`, and that act clears the block (rc-9's verify-line Stall shape). **Integration**: a worktree editing its own `tests:` line still has a test edit refused; a repo with no `tests:` line refuses with that line, and after the line is committed on the work branch the same merge lands.
- AC6.1 Tests are born only in a RED stage, one whose tasks' `W:` holds tests only. Each new test is validated before the freeze: collected, failing by assertion (never by error), test-audit, stage review. **Integration**: a RED stage whose new test errors instead of failing cannot close.
- AC6.2 From the RED anchor on, a task or job merge refuses any diff on a test file. This covers unit, integration and E2E tests and the tests that existed before; a pure rename is allowed.
  - The refusal carries one `Operator action:` line: stop and report.
  - **Integration**: an edited test refuses; a pure rename lands; a new RED stage lands.
- AC6.3 A wrong test is never edited in an implementation task. The implementer stops and reports; the amendment is a new RED stage, with its review and the operator's approval.
  - `specs/releases/AGENTS.md` §3's clause on rewriting a test in the same task leaves.
  - A REBUILD keeps the fix's tests.
  - **No test** (law text).

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

## Job 9 — evals in the library's own CI

Operator rulings 2026-10-07: the evals live in the dadaia-workspace repo and its CI; the context carries no second repo. ACs are AC11.x: AC9 is the bug batch's, AC10 Reconciliation's.

- AC11.1 `evals/` at the repo root holds `tasks/t1-cold-onboarding/`, `tasks/t2-block-list-bug/` and `scripts/compare.py`, `scripts/scan.py`, ported from dadaia-evals c075ed6.
  - Each task holds `instruction.md`, `task.toml`, `environment/Dockerfile` (environment only, the lib its last layer), `tests/test.sh` and `tests/test_grade.py`.
  - The wheel ships none of it (`packages` = `dadaia_workspace` only).
  - **Integration** (no model), in the library's test tree: each image builds with the 0.4.7 layer and with the candidate wheel; the T1 grader passes on a hand-onboarded workspace and fails on an empty one; on T2 a planted correct fix passes and a planted assert-rewriting fix fails. Check: the built wheel's file list holds no `evals/` path.
- AC11.2 One decider for the eval workflow rules: dadaia-evals' `scripts/check_workflows.py` is not ported; its clauses become the guard `no-model-api-in-ci` (`scripts/guards/repo.py`).
  - A model call only in `.github/workflows/eval.yml`; its triggers only `workflow_dispatch` and `schedule`; no self-hosted runner; the model secret read at job level only; a secret scan before any upload and before the job summary.
  - **Unit** + adversary rows, each refused: a model call in a push-triggered workflow; `eval.yml` with `pull_request`; a self-hosted runner; a workflow-level secret.
- AC11.3 `.github/workflows/eval.yml`: `workflow_dispatch` plus a weekly `schedule`; environment `evals`; builds the candidate wheel from its own checkout sha (no cross-repo `lib_ref`); a baseline input, default 0.4.7; T1 and T2, k=3; the scan before upload. **No test**. Check: the guard passes on it.
- AC11.4 The shipped law states no model-API-in-CI rule.
  - The line and its clauses leave `public/data/AGENTS.md` (map §3), `dd-gitflow-default` SKILL.md §3b, `CICD-AUTOMATION.md` and `CONTEXT.md` (the term "Evals repo").
  - Memory atoms (`specs/memory/**`) and `QUALITY.md` that name dadaia-evals as a context repo name the library's own evals.
  - **No test**. Check: `git grep -n -i 'evals repo\|dadaia-evals' -- dadaia_workspace CONTEXT.md specs/memory` prints nothing; the sweep count goes in the commit body.
- AC11.5 `eval.yml` reaches `main` through the constitution's Operational-Change Lane (operator order 2026-10-07): reviewer APPROVED, CI green. GitHub dispatches a workflow only when its file is on the default branch. **No test**. Check: `gh api repos/marcoaureliomenezes/dadaia-workspace/contents/.github/workflows/eval.yml?ref=main` succeeds.
- AC11.6 The first run (replaces AC3.1): `gh workflow run eval.yml --ref feature/0.5.0`, T1 and T2, k=3, 0.4.7 against the candidate.
  - It confirms the stamped candidate ran (`dadaia capabilities --json`) and no rate-limit error.
  - A failing grader is fixed in the grader before closure.
  - The secret `CLAUDE_CODE_OAUTH_TOKEN` lives in the repo's Environment `evals` (branches `main`, `feature/*`); the operator sets it.
  - **No test**. Check: a `_RELEASE.json` `kind: note` names the run URL, the verdict per 0178 (2), tokens and wall time.

## The bug batch

- AC9.1 Every bug found in rc-10 is resolved in rc-10 (0206).
  - A block-list bug is a hotfix at once; every other bug goes to the bug batch: after the DAG's last job, before Reconciliation, grouped by cause, a fix with `caused_by ≠ none` as a REBUILD (0210).
  - A bug found during Reconciliation is fixed inside it.
  - **No test**. Check: `bugs.py status` prints `0 open` at Reconciliation's end.

## Reconciliation

**No test**: observed by the named command or a `_RELEASE.json` line.

- AC10.1 Memory states the merged code, each atom with its derived sections in one merge (0192).
  - Every `tests/…py` path named in `QUALITY.md` and `ARCHITECTURE.md` exists. `grep -c RELEASE-TREE-MEMORY specs/memory/ARCHITECTURE.md` prints `0`.
  - F098 and F128 are dispositioned `resolved`.
- AC10.2 `## Bugs` is regenerated after the disposition sweep. `_RELEASE.json` logs the readouts, AC8.1's readout, each job's `kind: merge` entry and each job's bug-surface delta.
- AC10.3 The `measured_by` of 0208 and 0209 names cases this rc built (AC1.2, AC4.1–AC4.4; AC6.0–AC6.2); a name that moved is repaired in the 0138 lane.
- AC10.4 Each Origin backlog entry exits once, `delivered --release 0.5.0`. `agent-behavior-evals` exits after AC11.6 is logged, with 0217 ruled.
- AC10.5 Closure follows the releases law, with zero open bugs; rc-11 is defined beside it.

## ADRs

- 0176 and 0178 are accepted (Q3); the main thread writes the rulings. 0176's memory half is AC10.1. 0178 applies at rc-13's promote.
- 0174 is rejected (Q3); its live clauses are re-proposed at rc-11.
- **0208** (ADR C), accepted with this SPEC's Approval, before Job 1, as are 0209 and 0210 (G8, G10, Q2, Q2b, Q5):
  - `QUALITY.md` `## Bugs` holds a generated map plus a written review, compiled at each closure; per-bug state stays only in `BUGS.jsonl`.
  - A ledger surface settles once it leaves the window with no recurrence.
  - The map is a closure check. Context: G8 said "checked by doctor". The rc-8 W13 review (REJECTED; H7) moved it to closure, because an always-on check reddens every tree between closures. This ADR records that difference.
  - The readouts block nothing: the Laplace trend over all bugs (days axis, 4 releases, known `found_in` only), the settled-ledger-surface count, and the defective-fix rate.
  - Fix surfaces and rework are derived from git, never stored.
  - `bugs.py resolve` requires `evidence_seam`, checked textually only then.
  - Amends 0164 (4). `measured_by`: AC1.2's and AC4.1–AC4.4's cases.
- **0209**, accepted with this SPEC's Approval (Q6), "Tests are born in RED stages and frozen at the RED anchor":
  - AC6.0–AC6.3's rule; test paths are the repo's `tests:` line, read from the work branch.
  - Amends the releases law §3's same-task rewrite clause.
  - `measured_by`: AC6.0–AC6.2's cases.
- **0210**, accepted with this SPEC's Approval (operator, 2026-10-06: "(b) Qualquer caused_by ≠ none é REBUILD (Recommended)"): any `caused_by` other than none, a bug's fix or a feature task, makes the fix a REBUILD of the unit, keeping its tests. It keeps 0186 (2) and widens 0206's "a fix-induced one" (`amends: 0206`). SPEC text, not part of the ruling, which the operator accepts at Approval: a REBUILD's revert under 0186 (2) keeps the culprit's test files, so it fits 0209. `measured_by`: the ninth `PILLAR-BUGS` metric (AC1.4).
- The main thread proposes 0208–0210 in `decisions.jsonl` at Approval.
- **0217**, accepted 2026-10-07 (supersedes 0177, 0179): evals live in the library repo's own CI; no context carries an evals repo; the shipped law states no model-API-in-CI rule (Job 9). `measured_by`: the guard `no-model-api-in-ci` and AC11.4's grep.

## Replaces

- `bugs.py fix`'s never-diffed shape-4 link and `PILLAR-BUGS.md:8`; the fix reader's three rc-9 fixes, de36b0e69, bd0628092 and e638d4a88 (AC1.1).
- `_memory_drift.py`'s second window-bound precondition (cc544f66e beside d1e29503b), by Job 1's REBUILD task J1.S3.T2, behaviour-preserving (by law (dd-release-definition SKILL.md:28: ≥2 bugs, a second path)).
- 0164 (4)'s retirement of `evidence_seam` (AC1.2).
- A bare `rebuild: none` (AC1.4).
- The bugs law §2's REBUILD for a fix-induced bug only; `dd-code-review/SKILL.md:55`'s "or why not" (AC1.5).
- HOOKS-DRIFT-1's fixed "differs" (AC5.1).
- Rewriting a test in an implementation task (AC6.3).
- Loose `contract/` and `integration/` roots; the folder-derived size tier (AC7).
- Processes in the unit tier; the autouse rows monkeypatch; patched `sys.stdin` and the `hook-stdin-not-in-process` guard check (AC8).
- `docs/bug-ledger-lessons.md`'s source: the `bug-ledger` atom and today's `QUALITY.md` sections give way to `## Bugs`' written review (AC4.5).
- Stale `Measured by` paths (AC10.1).
- dadaia-evals as the context's evals repo, its `check_workflows.py` and the cross-repo `lib_ref` (AC11.1–AC11.3).
- The shipped law's model-API-in-CI line and its §3b clauses; the `CONTEXT.md` term "Evals repo" (AC11.4).

## Risks

| Weakness | Mitigation |
|---|---|
| 8 jobs is the cap. | A new need goes to rc-11. |
| Job 9 spends model quota: 12 trials. | `-n 2`, economy template, one run. |
| Jobs 7–8 change most test files. | Job 6 lands last, so its freeze does not bind them. |
| Jobs 1 and 4 share the bug skill. | Disjoint files or a PLAN edge. |

## Carried

Every active backlog id sits in the Origin or below.

- rc-11, the corpus, the law and the ADR process:
  - `public-law-language-neutral`, `dd-ask-me-owned-questioning-skill`, `adr-born-at-release-with-options`, `adr-ledger-triage-process-rules`, `architecture-adr-section-generated`;
  - rc-9's deferrals: `stage-gate-runs-the-contract-tier`, `job-gate-runs-the-law-deletion-check`, `merge-entry-times-survive-rebase`, `task-gate-mypy-follows-cross-skill-imports`, `hypothesis-cache-stays-out-of-repo-trees`, `stray-pycache-never-breaks-the-job-gate`, `task-gate-drops-deleted-paths-itself`, `release-new-adopts-a-drafted-next-rc`, `origin-findings-renamed-to-the-spec-head`, `adr-0193-records-its-amends`;
  - F088, F089, F139–F148; 0174's live clauses;
  - the task gate's `test_` name check becomes a declared owner mapping — design and intake at rc-10 Reconciliation.
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

- An evals scenario for a bug-batch fix (Q1); `evals-release-gate-status`, `evals-harness-lanes-and-benchmark`, `evals-windows-smoke`, `devin-subagent-projection`: all after 0.5.0.
- Q6 item 6, a harness read-only test layer: not taken.
- The private test-stack and commit-gate hooks: the operator's.
