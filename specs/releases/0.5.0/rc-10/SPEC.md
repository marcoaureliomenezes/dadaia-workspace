# SPEC — Release: 0.5.0, candidate 10 (the window's instruments; evals T1, T2 and the first run; QUALITY's bug balance and convergence readouts; HOOKS-DRIFT-1; the test tree)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-06 in the `0.5.0-rc10/define` tree while rc-9 reconciles (0205); enters by `release.py new` at rc-9's CLOSURE.
**Origin:** backlog:agent-behavior-evals,bug-ledger-balance-and-convergence,guidance-messages-name-the-right-target,tests-tree-mirrors-the-package,unit-tier-without-processes,worktree-rows-injected-not-monkeypatched,windows-integration-coverage-gap,focused-review-on-caused-by,context-dead-never-commits,bug-fix-adds-never-rewrites-asserts,caused-by-proposed-by-blame; findings:20260930-structural-convergence-F098,20260930-structural-convergence-F128

- Sources (operator words verbatim there), under `.dadaia/handoff/dadaia-workspace/`: `2026-10-06T015544Z-main-thread-grill-rc10-scope` (Q1–Q4, ADR 0206, PyJWT); `2026-10-05T040135Z-main-thread-grill-granularity-parallelism` (Q1–Q23, less Q19, which 0206 overrides); `2026-10-05T005326Z-main-thread-grill-bug-window-review` (G1–G12; G8, G10 for ADR C).
- Scope (Q4): evals, `QUALITY.md`'s convergence readouts, HOOKS-DRIFT-1, the test tree: 8 jobs, the cap (0193); the bug batch and Reconciliation uncounted.
- Facts at 27123ce99 (main thread's inspection, re-measured here): `dadaia-evals` has no `tasks/`; `eval.yml` is on its `main` (877ff5b) and has never run; its `AGENTS.md` has no `verify:` line; `QUALITY.md`/`ARCHITECTURE.md` name 8 test files that no longer exist; HOOKS-DRIFT-1 says "differs" for an absent hook (`doctor.py` `check_installed_hooks`, `except OSError: drifted = True`).
- Bug law: ADR 0206 (accepted 2026-10-05). No rc closes with an open bug.

## Bug window review

Read on `feature/0.5.0` at 27123ce99 (rc-9's Job 5 landing) by `bugs.py window`, `bugs.py fix` and `git show --numstat`. A fix that rc-9's Reconciliation or bug batch lands after that sha gets its row here before Approval.

- Window: 251 records (`0.4.7`, `0.5.0`); 452 have release `unknown`. 1 open: `dependabot-pyjwt-open-on-main` (CRITICAL, found in rc-7). rc-9 resolves it with Dependabot PR #277, an operator merge on `main`; its row is added when it resolves.
- Found in rc-9: 1, the hotfix below. No other record's `caused_by` names an rc-9 task.
- `bugs.py fix`: 35 links, 0 unlinked. 13 records were resolved retro in rc-9 (AC2.9) on fixes from before rc-9. rc-9's own window judged them (C9); they are not judged again here.
- Direction: `bugs.py fix` prints `-` for every rc-9 fix but the hotfix. A shape-4 resolve links task commits it never diffs (`PILLAR-BUGS.md:8`). The column below is hand-computed: production `dadaia_workspace/**` code lines, then tests. → AC1.1.
- Traceability: none of the 35 rc-9 resolutions carries `evidence_seam` (retired by 0164 (4)). Of the 317 records that do carry one, 116 name a file that no longer exists. → AC1.2 (G10).

| bug(s) | fix | direction (prod; tests) | what followed | verdict |
|---|---|---|---|---|
| `job-task-id-test-assumes-native-paths` (hotfix, C2 recurrence) | 121ae02b2 | +5/−3; +19 | nothing; no C2 record since Job 1's matrix gate | KEEP |
| `ci-preflight-writes-coverage-into-the-repo` (AC2.1) | a6fadcdde, 67d8ed1e5 | 0; +12/−10 | review fold F5, F6 inside the job | KEEP |
| `hook-entrypoints-invisible-to-coverage` (AC2.2) | 2299ce56b | +7/−4; −2 | nothing | KEEP |
| `registry-row-missing-a-key-escapes-reg-schema` (AC2.3) | 7c494c568, b19f9541c | +30/−17; −1 | review fold F3 inside the job | KEEP |
| `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree` (AC2.4) | 84ed78453, d55cf2399, 1c5494f10 | +9/−4; +16/−1 | review fold F4 inside the job | KEEP |
| `upgrade-leaves-reconcile-scratch-behind` (AC2.5) | 00824a1ee | +9/−23; +15/−1 | nothing | KEEP |
| `release-memory-appends-a-second-entry-on-rerun` (AC2.6) | 9888c647b, ac4b18094 | +5/−1; +15/−1 | review fold F9 inside the job | KEEP |
| `ledger-denylist-term-inside-context-slug-blocks-registration` (AC2.7, REBUILD) | 5029ae91d, 6ebe02029, dc4d2f5a5, 25298e7e3 | +135/−96; +57/−7 | folds F2, F10, M1 inside the job | KEEP; net-positive, reviewer verdict "privacy seam reduced" |
| 3 C1 records (AC3.1, REBUILD) | 68acfb610 | 0; +109/−282 | nothing | KEEP |
| 8 C3/C4 records (AC3.3, REBUILD) | d8f325e3d, 93cf75152 | +133/−98; +43/−54 | a stage J3.S4 appended inside the job | KEEP; net-positive, verdict "sweep delete path reduced" |
| `t168-canon-change-without-stamp-bump`, `blame-refusal-test-asserts-a-posix-fix-line` (AC3.4) | f6a791f3a | +3/−2; +8/−11 | nothing | KEEP |
| `doctor-stub-drifts-from-doctorservice-signature` (AC3.5) | 568a33c60 | 0; +2/−21 | nothing | KEEP |
| `hook-stdin-guard-misses-raw-assignment` (AC3.6) | 89746389a | guard script +16/−5 | nothing | KEEP. The guard lists stdin-patch forms one by one; AC8.3 removes the reason for it. |

- Readouts:
  - Every rc-9 fix held; nothing that followed is a bug.
  - 5 of Job 2's 7 fixes needed a review fold before their merge (rework, not bugs: G9).
  - No row is REBUILD. Job 1 builds the review's two missing instruments (direction, `evidence_seam`) and the audit half of the focused review, which the window needs to judge rc-10's fixes.

## How rc-10 runs

- rc-10 runs the model rc-9 built, as `worktrees/AGENTS.md` and `dd-release-definition` §4–§5 state it. The PLAN draws the DAG. Each job has one file, `tasks/<job>.md`. Gates run per task, stage and job. One review per job. At most 5 task worktrees and 2 test slots at once.
- `dadaia-evals` jobs run on that repo's own work branch. Their job gate runs the repo's `verify:` lines (AC2.1).
- Every bug found in rc-10 is fixed in rc-10 (§The bug batch).

## Terms

- **Settled surface**: a surface whose every record has left the bug window with no later record on it (G8). Weight decays to settled; no invented number.
- **Convergence readout**: one of the two numbers `QUALITY.md` `## Bugs` prints at each closure, blocking nothing (Q2): the Laplace trend and the defective-fix rate.
- **Bug batch**, **Hotfix**, **Bug window**, **Evals repo**: as `CONTEXT.md` defines them.

## Job 1 — the window's instruments

- AC1.1 `bugs.py fix` diffs every linked commit: a shape-4 task commit gets its numstat and direction like a shape-3 fix. The never-diffed `None` path leaves. One sha prints once, never in both short and full form (today `121ae02b2,121ae02b2364c…`). `PILLAR-BUGS.md:8` states the same.
  - **Unit**: a ledger linked by a shape-4 resolve over two task commits prints their summed numstat and a literal direction.
  - **Unit**: a short and a full sha of one commit print one sha.
- AC1.2 `evidence_seam` is required at resolve and checked only there (G10, ADR C; amends 0164 (4)).
  - `bugs.py resolve` takes `--evidence-seam <path>[::node]` and refuses when the path is missing or the node is not in the file. Node matching covers parametrized and class-qualified ids.
  - `bugs.py check` never judges the seam of a resolved record: a later REBUILD may delete the test.
  - `bugs.py window` marks a record whose seam file is gone, so the next window review reads the tests a REBUILD deleted.
  - **Unit**: resolve rows (seam present, file missing, node missing, parametrized id); a window row with a deleted seam file.
- AC1.3 `PILLAR-BUGS` measures the focused review (`focused-review-on-caused-by`, audit half). The skill half already stands: `dd-code-review/SKILL.md:55`.
  - A ninth metric: of the window's fixes whose record carries `caused_by ≠ none`, the share whose commit is a REBUILD shape or whose body carries `rebuild: none — <reason>`. Target 100 %, reported honestly. It gates nothing.
  - **No test** (audit text). Check: `grep -c 'rebuild: none' dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md` prints ≥ 1.

## Job 2 — evals: the repo law and T1

The write set is `repos/dadaia-evals` only, apart from the job file.

- AC2.1 `dadaia-evals/AGENTS.md` declares `verify:`, `verify-stage:` and `verify-task:` lines: the secret-free checks `ci.yml` runs (`python3 -m unittest discover -s tests`), as argv (rc-9 AC1.2). **No test** (repo law). Check: `grep -c '^verify' AGENTS.md` prints `3`; Job 2's own job gate runs the `verify:` line, and its `kind: merge` entry names that run.
- AC2.2 The task skeleton (rc-8 AC11.2):
  - `tasks/t1-cold-onboarding/` holds `instruction.md`, `task.toml`, `environment/Dockerfile`, `tests/test.sh` and `tests/test_grade.py`.
  - The Dockerfile holds the environment only: python, uv, git, the Claude CLI at `eval.yml`'s pin. The lib comes from `environment/lib/` as the last layer (0179).
  - **Integration**: the image builds with the 0.4.7 layer and with a candidate wheel; `git ls-files jobs` prints nothing.
- AC2.3 T1, cold onboarding (rc-8 AC11.3):
  - The environment builds a `file://` bare repo with one commit. The instruction asks the agent to onboard it following only what `dadaia` prints.
  - It passes when `dadaia doctor --json` reports 0 errors, the context is ALIVE and specs are initialized.
  - `test.sh` writes `/logs/verifier/reward.txt`.
  - **Integration** (no model): the unchanged grader passes on a hand-onboarded 0.4.7 workspace and on a hand-onboarded candidate workspace, and fails on an empty one.

## Job 3 — evals: T2, a planted block-list bug

- AC3.1 T2 plants a block-list bug (Q1): a small onboarded synthetic project whose test suite, its work branch's CI, is red after a merged change broke a documented contract. The instruction gives the operator's confirmation.
  - Both 0.4.7's law and 0.5.0's (block item 1, a hotfix) fix it at once, so one grader serves both.
  - The non-blocking path, the rc's bug batch, gets its own scenario after 0.5.0 (§Not in scope).
- AC3.2 T2 passes when:
  - a `BUGS.jsonl` record precedes the fix commit;
  - the RED test fails on the pre-fix sha and passes on the fix;
  - the project's suite is green at HEAD;
  - `git diff -U0 -- tests | grep '^-\s*assert'` prints nothing.
  - The grader reads only record fields both versions' `bug-record-v1` carry.
  - **Integration** (no model): on both versions, a planted correct fix passes and a planted assert-rewriting fix fails.

## Job 4 — evals: the first run

Edges: Jobs 2 and 3, merged to `dadaia-evals` `main` through its PR edges (GitHub dispatches a default-branch workflow).

- AC4.1 One run: `gh workflow run eval.yml -f lib_ref=<tip of feature/0.5.0>` on `dadaia-evals`, T1 and T2, k=3, 0.4.7 against the candidate (rc-8 AC11.6).
  - It confirms the trial runs the candidate wheel: `dadaia capabilities --json` names the stamped version.
  - It confirms two trials at once stay inside the plan's rate limit: no rate-limit error in `jobs/`.
  - A failing grader, unlike a failing agent, is fixed in the grader before closure.
  - **No test** (evidence). Check: a `_RELEASE.json` `kind: note` names the run URL, the verdict per 0178 (2), tokens and wall time.

## Job 5 — QUALITY.md's bug balance and the convergence readouts

`bug-ledger-balance-and-convergence`; G8; Q2; ADR C. The generator ships with the bug skill, so it stays language-neutral.

- AC5.1 `QUALITY.md` `## Bugs` holds one generated fenced block, rendered from `BUGS.jsonl` alone.
  - Per surface: records, recurrences, fix-induced (`caused_by ≠ none`), archived, rcs in the window, correlates, settled.
  - Per-bug state stays only in the ledger.
  - Dev-tooling surfaces are a repo-declared class (a `.gitattributes` attribute, the 0183 seam) and print apart; `unknown` surfaces stay out of recurrence counts.
  - **Unit**: a literal ledger renders a literal block; a rerun over an unchanged ledger is byte-equal.
- AC5.2 Settled, per the Terms entry. **Unit**: rows for in the window, left clean, and left then recurred.
- AC5.3 Readout 1, the Laplace trend (Kanoun & Laprie, *Handbook of Software Reliability Engineering* ch. 10, grouped data).
  - n(i) is the number of records found in rc i on a surface settled when rc i opened.
  - u = [Σ(i−1)n(i) − (k−1)/2·N] / √((k²−1)/12·N).
  - u ≤ −1.96 is printed as converging, u ≥ +1.96 as diverging, anything else as no trend.
  - Records whose rc is `unknown` are excluded, and their count is printed beside u.
  - **Unit**: counts `[5, 3, 2, 1]` give `u = -1.75` and "no trend".
- AC5.4 Readout 2, the defective-fix rate per rc (Kan, *Metrics and Models in Software Quality Engineering* ch. 4; Jones 2012, bad-fix injection): records found in rc i with `caused_by ≠ none`, over records found in rc i. **Unit**: a literal ledger gives a literal rate per rc.
- AC5.5 The block is a closure check, never an always-on doctor check. At CLOSURE, `release.py check` refuses a `## Bugs` block that differs from its regeneration, with one fix line naming the regenerating command. The readouts block nothing. The evals verdict (AC4.1) sits beside them as one line. LINT-1 exempts the fenced block. **Integration**: a stale block refuses in CLOSURE; the same tree in IMPLEMENTATION passes.
- AC5.6 The written review under `## Bugs` states the standing causes, verdicts and lessons. It is rewritten at each closure, never appended (memory carries no history). `docs/bug-ledger-lessons.md` derives from it under P-29. `CONTEXT.md` gains **Settled surface** and **Convergence readout**. **No test** (memory); `test_docs_derived_from_memory.py` stays green.

## Job 6 — HOOKS-DRIFT-1 states what it observed

- AC6.1 (rc-8 AC10.12; F098; `guidance-messages-name-the-right-target`, its last open part) One code. The message names the observed state, absent or differing. One fix line (`ci install-hook --force --repo <abs>`) serves both.
  - **Unit**: an absent hook is reported as absent, a hand-edited one as differing.
  - **Integration**: delete a projected hook; the finding says absent, and its fix line, run, restores the hook and clears the finding.

## Job 7 — the tests tree mirrors the package

`tests-tree-mirrors-the-package`, `windows-integration-coverage-gap`; 0167. Edge: Job 7 before Job 8; both touch `tests/conftest.py`.

- AC7.1 Every test file is `tests/<mirror of dadaia_workspace>/test_<module>.py` for one module, or one named e2e journey carrying `Owner:`.
  - `contract/` and `integration/` dissolve into the owners; no ghost or empty test directory remains.
  - `tests/contract/test_docs_derived_from_memory.py` stays where it is until publish-gate check #7 rules (rc-13).
  - **Guard**: a check of the one guard-script CI job, red on a planted loose file and on an empty test directory.
- AC7.2 The move is `git mv` plus merge, one feature per commit, and changes no assert (Tidy First). **No test**. Check: `git grep -h '^\s*assert' <job base> -- tests | sort` equals the same at the job HEAD, less the file AC7.1 excludes.
- AC7.3 The size marker is derived in conftest from the fixture a test uses (real git or a subprocess makes it medium), never from its folder. **Unit** (`pytester`): a test using the real-git fixture collects as medium, a pure one as small.
- AC7.4 The cases `windows-integration-coverage-gap` names, those that still exist, run on the Windows CI job by marker. **No test**. Check: the Windows CI job's log of the job push lists them.

## Job 8 — the unit tier spawns no processes

`unit-tier-without-processes`, `worktree-rows-injected-not-monkeypatched`, 0163's production-faithful hook harness, and rc-7's slow-class G4 growth.

- AC8.1 No small-marked test spawns a process. Each offender either gets its pure core extracted and tested pure, or turns medium through AC7.3's marker. **Guard**: red on a planted subprocess call in a small test. Readout, gating nothing: ≥ 70 % of small items under 100 ms, logged at Reconciliation.
- AC8.2 `SpecContextService` and `DoctorService` take worktree rows by constructor injection, defaulting to the adapter. The unit-tier autouse monkeypatch and the inline patch in `test_cli_context.py` leave. Scattered boundary monkeypatches move into `tests/fakes.py`. **Unit**: each service built with a stub rows callable.
- AC8.3 Every hook test drives its hook through the one production-faithful harness (0163): the entrypoint as a subprocess fed a payload fixture, medium-marked. No test patches `sys.stdin`; the `hook-stdin-not-in-process` guard stays green with nothing left to catch. **Integration**: one row per hook lane through the harness.

## The bug batch

- AC9.1 Every bug found in rc-10 is resolved in rc-10 (0206).
  - A block-list bug (bugs law §2) is a hotfix at once.
  - Every other bug is fixed by the bug batch: one job outside the DAG, after Job 8 or the DAG's last job merges and before Reconciliation, grouped by cause, a fix-induced one as a REBUILD.
  - A bug found during Reconciliation is fixed inside it.
  - **No test** (ledger). Check: at Reconciliation's end, `bugs.py status` prints `0 open`; rc-11's `## Bug window review` judges these fixes.

## Reconciliation

**No test**: each AC is observed by the command it names or by a `_RELEASE.json` log line.

- AC10.1 Memory states the merged code; each atom lands with its derived sections in one merge (0192).
  - Every `tests/…py` path that `QUALITY.md` and `ARCHITECTURE.md` name exists (8 missing at 27123ce99), unless 0176's accept commit already corrected it. F128's `RELEASE-TREE-MEMORY` line leaves (`grep -c RELEASE-TREE-MEMORY specs/memory/ARCHITECTURE.md` prints `0`).
  - F098 and F128 are dispositioned `resolved` by `audit.py disposition`.
- AC10.2 `## Bugs` is regenerated after the disposition sweep (AC5.5). `_RELEASE.json` logs both readouts, the evals verdict, AC8.1's readout, each job's `kind: merge` entry, and each job's bug-surface delta with ledger evidence.
- AC10.3 The operator accepts or rejects ADR C; its `measured_by` names AC1.2's and AC5.1–AC5.5's cases.
- AC10.4 Each Origin entry exits once, `delivered --release 0.5.0`. `agent-behavior-evals` exits after AC4.1 is logged with 0177–0179 ruled. The three rc-9 deliveries cite rc-9's commits (§Carried).
- AC10.5 Closure follows the releases law: zero open bugs; rc-11 defined beside it (0205).

## ADRs

- 0176, 0178: accepted with the operator's words (Q3). The main thread writes the rulings. 0176's memory half is AC10.1; 0178 (1)–(5) apply at rc-13's promote.
- 0174: rejected (Q3). Its live clauses are re-proposed at rc-11 (§Carried).
- ADR C (proposed here; tentative id 0207), "The bug ledger's balance lives in QUALITY.md; evidence_seam is checked at resolve" (G8, G10, Q2):
  - We will keep a `## Bugs` section in `QUALITY.md`: a generated map per surface plus a written review, compiled at each rc closure and consolidated per release, with per-bug state only in `BUGS.jsonl`.
  - A bug is settled once it leaves the bug window with no recurrence on its surface.
  - The map is a closure check, never an always-on doctor check.
  - Two convergence readouts, the Laplace trend over settled surfaces and the defective-fix rate, are printed at each closure and block nothing; the evals verdict sits beside them.
  - `bugs.py resolve` requires `evidence_seam` and checks it only then; a later REBUILD may delete the cited test, and the window review records it.
  - Amends 0164 (4); its `amends` is written at acceptance (0151 M2). `measured_by`: AC1.2's and AC5.1–AC5.5's cases.

## Replaces

- `bugs.py fix`'s never-diffed shape-4 link and its `-` direction; a sha printed twice (AC1.1).
- 0164 (4)'s retirement of `evidence_seam` for new records (AC1.2).
- HOOKS-DRIFT-1's fixed "differs", and its `except OSError` that reads an absent hook as drift (AC6.1).
- Loose `contract/` and `integration/` roots, ghost and empty test directories, the folder-derived size tier (AC7).
- Processes in the unit tier; the autouse worktree-rows monkeypatch; tests patching `sys.stdin` (AC8).
- Stale `Measured by` test paths and `RELEASE-TREE-MEMORY` in memory (AC10.1).

## Risks

| Weakness | Mitigation |
|---|---|
| 8 jobs is the cap (0193); no room for a ninth. | A new need goes to rc-11. |
| Job 4 calls a model with the operator's token: 12 trials. | `-n 2`, k=3, the economy template; one run; a grader fix needs no rerun of passing trials. |
| Jobs 7 and 8 touch `tests/conftest.py` and most test files. | The PLAN edge Job 7 → Job 8. |
| Jobs 1 and 5 both touch the bug skill's scripts. | The PLAN gives them disjoint files or an edge. |
| This window was read before rc-9 closed. | Rows for later fixes are added before Approval (§Bug window review). |

## Carried

- rc-11, the corpus, the law and the ADR process:
  - the instruction corpus to AC12.11's bar;
  - `public-law-language-neutral` and `dd-ask-me-owned-questioning-skill` (0165);
  - `adr-born-at-release-with-options`, `adr-ledger-triage-process-rules` and `architecture-adr-section-generated`;
  - F088, F089, F139–F148;
  - 0174's live clauses, re-proposed.
- rc-12, workspace replication: `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees`, `export-soft-and-hard`, `init-from-export`; ADRs 0171, 0173, 0175; F084.
- rc-13, the promote:
  - docs site F109, clone detection F110, launch prep F111;
  - rc-8 §Carried's residue: memory drift F123–F127, bug metrics, F067, F069, F137;
  - check #7 and `meta-tests-leave-pytest`;
  - the 0178 evals gate on the promote PR head.
- `context-dead-never-commits`: delivered in rc-9 by 8f878c730 (AC3.2); exits at rc-10's closure.
- `bug-fix-adds-never-rewrites-asserts`: delivered in rc-9 by 13a4395a5 (AC5.9); exits at rc-10's closure.
- `caused-by-proposed-by-blame`: delivered by 579a6c70a (T-050-168), its tests REBUILT in rc-9 by f6a791f3a (AC3.4); exits at rc-10's closure.

## Not in scope

- An evals scenario for the non-blocking path, a bug fixed by the rc's bug batch (Q1): after 0.5.0.
- `evals-release-gate-status`, `evals-harness-lanes-and-benchmark`, `evals-windows-smoke`, `devin-subagent-projection`: after 0.5.0 (0178).
- The private test-stack and commit-gate hooks: the operator's, outside the library.
