# SPEC — Release: 0.5.0, candidate 9 (Job 1 the demolition; the bug window; the REBUILDs; jobs, stages and tasks; the closed rc)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-05 outside the tree (Q20); enters by `release.py new` at rc-8's CLOSURE.
**Origin:** operator-demand

- Sources, operator words verbatim: grill handoffs of 2026-10-05 `T040135Z` (Q1–Q23), `T045010Z` (R1–R10, I1–I3), `T050738Z` (scope Q1–Q3, I1–I5) under `.dadaia/handoff/dadaia-workspace/`; the demolition ruling, same day.
- No old ritual in rc-9 ("rc-9 não deve ter ritual velho, nada dele"; supersedes Q21, I4): Job 1 demolishes it ("no primeiro minuto da rc9"); Jobs 2 on run the new model.
- Scope ("Lean: J1 + REBUILDs + mechanism + laws"), demolition first: Jobs 1–5 and Reconciliation; 5 of 8 jobs (Q18).
- Job 2–3 bugs stay out of Origin (0161: no `operator-demand` plus clauses).
- Aggregated from rc-8 (Q21): T-050-173 … 176, 178, 179, 194 … 208, 214 … 216; T-050-213 is §1 (scope I1); T-050-209's REBUILD stays in rc-8.

## Bug window review

**Job 1 (the demolition) runs before this window's fixes; the window runs as Job 2.** Provisional until rc-8 closes (Q20): re-read by `bugs.py window` then (AC2.11).

- Window (rc-8 AC13.3): `found_in` or `introduced_in` in 0.5.0 or 0.4.7. Today no record carries `found_in`: T-050-209 was reverted (9018fdadb), T-050-210 … T-050-212 are open. By `ts`: 236 records since 0.4.7 opened; 9 open.
- rc-8's fixes, by `bugs.py fix` (10 linked, 0 unlinked):

| bug | fix | direction | what followed | verdict |
|---|---|---|---|---|
| `test-suite-writes-outside-tmp` | 09d259133 | neutral | rows 14, 15 | REBUILD, AC3.1 |
| `suite-fails-under-an-operator-dadaia-context` | b69ee15b9, 76d7af604 (CI follow-up) | neutral | rows 16, 17 | REBUILD, AC3.1 |
| `onboarding-next-step-names-another-context` | 6285e06b2 | positive | row 13 | fix KEEP; its test REBUILD, AC3.5 |
| `context-dead-secret-fix-line-stashes-what-dead-then-destroys` | 1ee8aa30f | positive | its secret-refusal hunk is a culprit | REBUILD, AC3.2 |
| `worktree-merge-linearizes-a-branch-already-containing-work` | 1cfc3b72d | positive | reverted (T-050-191) | done |

- Held, nothing followed (KEEP): 5, both net-negative fixes among them (`bugs.py fix`). Readout: 5 of the 8 others bred a bug or were reverted.
- T-050-209, a task, bred `bug-window-tests-assume-posix-paths` (MEDIUM): rc-8's REBUILD, else AC2.11.
- Clusters:
  - Job 3's REBUILDs: C1 test session env (3 fixes, rows 14–17); C3 `sweep.py`'s except arm (rows 6, 21–23, 27, three culprits); C4 `context dead` (AC12.8's culprits, row 24); C5 T-050-168's tests (rows 10, 12); C6 `_StubDoctor` (row 13, two repairs in 2 days).
  - C2 Tests assume the host's paths: rows 5, 8, 9, 11, 12, 18 and `bug-window-tests-assume-posix-paths`, 7 records, each red only on post-merge CI. Cause: the merge gate runs local Linux only (rc-8 AC12.6). Verdict: the CI matrix at the job gate (R9, AC1.2); no per-test rule. Row 12 is Job 3's.
  - C7 The ledger privacy seam: the open HIGH and its 4 `--correlates` (`sa-ledger-write-seam-redacts-less-than-push-refuses`: fix 1bcfdba8f created the seam). Cause: two deciders of "what the push refuses"; the seam judges a value alone, the push against published prior text. REBUILD, AC2.7.
  - C8 rc-8's six single W10 records: UPDATE, RED first, AC2.1–AC2.6; a unit the as-is review finds with ≥ 2 prior fixes turns REBUILD.
  - C9 rc-8's 27 unregistered hidden breaks (AC12.4) → AC2.8.
  - C10 Non-product records (2026-10-05: 15 agent error, 89 release-born, 66 dev-tooling, 35 doubtful) and the 65 restored records on retired surfaces → AC2.9, AC2.10, counts re-read at rc-8's close.

## Terms

- **Implement**: one rc's run, a DAG of jobs; not a file (Q1, Q7).
- **Job**: one measured feature, one worktree tree, one review and gate at its merge (Q2, Q3); **Job 1** executes §1 (Q18); in rc-9 only, Job 1 is the demolition and §1 is Job 2. A GitHub job is always "CI job".
- **Stage**: a barrier on the job branch over parallel tasks; no worktree (Q4).
- **Task**: one owner (module or law file plus its owner test file), one session (~1 h), ~100 new code lines, deletions uncounted (Q15); one worktree; the unit of dispatch.
- **Envelope**: the `W:` union a job or stage may touch (R1, R7).
- **Closed stage contract**: exit tests, envelope and ACs served, fixed when the stage opens (R1).
- **Live task**: born, split or cancelled inside an open stage, unreviewed (R1).
- **Hot file**: one two tasks would write; hand-edited or generated (R6).
- **Ritual wait**: a merged job's wall time from its last task commit to its pushed merge: gates, review, CI waits.
- **Hotfix**: a block-list bug's fix, outside the DAG (Q17). **Reconciliation**: the last job, outside the 8 (Q10).

## Job 1 — the demolition

Lands as one merge ("Um merge só, autorizado"): one worktree, one review at its end, `scripts/ci.py` once on the result, the main thread's authorized manual merge, one push. RED first in the owner file.

- AC1.1 (a) Gates per task and stage; the full `scripts/ci.py` at every `worktree.py merge` leaves (gate 1, 0185, T-050-191; Q6, R4). Three `scripts/ci.py` levels (root `AGENTS.md`): task (ruff, mypy on touched files, owner tests), stage (lint, mypy, guards but drift, unit, integration; R6), job (the full command). A task fast-forwards onto its job branch after its gate; a stage closes only with no task worktree open and its gate green. **Unit** (`test_ci_script.py`): each level runs only its steps; a planted failing step turns it non-zero. **Integration**: a red task gate lands nothing, a green one lands; a stage with an open task worktree cannot close.
- AC1.2 (a) The job gate runs the CI matrix once (Q2, Q11, R7, R9, Q13, Q14): a job's merge runs the job level on HEAD, requires an APPROVED verdict naming its green CI-matrix run, and fast-forwards; a moved work branch refuses with a rebase fix line; 0168's carry stands. `pre-push` accepts and scans `wt/<M.m.p>-rc<N>/<job>` only of `wt/`; `ci.yml` triggers on `wt/**`. A non-code merge (`define/`, `backlog/`) runs the ledger, trio and ADR validators only. **Unit**: branch-policy rows. **Integration**: a verdict without the matrix run refuses; a second job's merge refuses until rebased; an invalid ledger refuses, a valid one lands with no test run. **Guard**: `ci-triggers-gitflow` pins `wt/**`.
- AC1.3 (b) One tree per job; the worktree-kind split leaves (0106, 0124, 0148; Q4, Q5, Q8, R3, Q11): `worktrees/<repo>/<M.m.p>-rc<N>/{define,reconcile,<job>,<job>--<task-id>}/`, branches `wt/<M.m.p>-rc<N>/<job>[--<task-id>]`; outside an rc only `backlog/<slug>/`; a bug is a job. The per-kind allowed sets leave: code, tests, specs, memory and derived docs of one change are one job. A job branch takes only task merges and its rc's specs edits (R8). The gate, doctor, reaper and `WT` read a worktree path's repo-relative tail through one function. ≤ 5 task worktrees per rc. **Integration**: `WT new` makes each shape, refuses an old-grammar name and a 6th task worktree; a PROTECTED write in a task worktree is blocked; one job commits a code file and a `specs/memory/` atom together; a stray job-branch commit refuses.
- AC1.4 (c) One review per job; none per worktree (Q2, Q12, Q14; rc-8 AC9.4, AC12.6, AC12.12): none at a task or stage merge; one per job, plus one per stage past ~400 new lines; a non-code merge one pass; one definition round per document, again only on a HIGH; the verdict carries the job command's output and CI-matrix run; a REBUILD read covers every line the prior fix wrote; no APPROVED on a test-deleting `refactor(...)` without a SPEC REBUILD verdict. **Integration**: a task merge lands with no verdict; a job merge without one refuses.
- AC1.5 (d) The 9-step closure leaves; Reconciliation is the last job (Q10): memory, derived docs, `measured_by` repairs, the rc's measurement, closure, one worktree. An atom and its derived sections land in one merge; the atom ↔ derived-docs hash check runs on that merge. The rejected 0189 (release kind carries derived docs) does not return. **Integration**: one merge changing an atom and its derived section passes the job gate and the drift guard; the atom alone is refused with one fix line naming the regenerating command.
- AC1.6 (e) No micro-dispatch: the main thread dispatches a job or a task; a smaller edit inside an open job is the job driver's own (`dd-manager-orchestration`). **No test** (law text, AC1.8); AC1.7 counts dispatches per job.
- AC1.7 Ritual wait is measured per job: each merged job, Job 1 included, logs in `_RELEASE.json` its wall time, ritual wait and dispatch count; AC6.2 compares rc-9's per-job ritual wait with rc-8's per-merge 25–35 min, the rc total with rc-8's ~12–15 h (~30 merges). Target ~75–80 % less ritual wait: an estimate, not a promise. **No test** (log data).
- AC1.8 The law follows in the same merge, each file rewritten once to rc-8 AC12.11's bar: `worktrees/AGENTS.md` (the tree, three gates, one review, hotfix, caps), `dd-gitflow-default` §3a's kind column, `RC-FLOW.md`'s closure steps, `MEMORY-UPDATE.md`, `dd-manager-orchestration`. **No test** (law text): `public stage`, `install`, `doctor` clean; `/corpus-audit` clean.
- AC1.9 One TASKS file per job (R8): `rc-<N>/tasks/<job>.md`; the canon admits `tasks/`; `TASKS.md` and its `[-]` marker and start commits leave from Job 2 on, closed rcs unchanged. **Unit**: canon rows for a job file, a stray `tasks/` file, a closed rc's `TASKS.md`.
- AC1.10 The job file (Q8, Q9, R1, R5, R10, I2): per stage its contract (exit tests by level, envelope, ACs served) and its tasks (id, AC, `W:`, owner tests, RED tests); stage 1 is test-only, every acceptance test RED as strict xfail; `running` is derived (the worktree exists), `done` written once per job by its close task; a cancelled task stays with its reason, a born one cites its AC. **Unit**: one valid job file parses; a stage-1 non-test file and a cancelled task without a reason refuse.

## Job 2 — the bug window, executed

RED first in the owner file. Job 2's close logs Δ production lines, Δ test functions and each cluster's bug-surface delta with ledger evidence (root map §1).

- AC2.1 Coverage data lands outside the repo (`ci-preflight-writes-coverage-into-the-repo`; F048; rc-8 AC10.2): on CI, `scripts/ci.py` and every `pytest --cov` line of `tests/README.md` and `tests/AGENTS.md`, no coverage file appears in the checkout; one decider; pytest runs with `-B` there. **Integration**: after each path, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC2.2 Hooks are visible to coverage and bounded in cost (`hook-entrypoints-invisible-to-coverage`; F051; 0118): `hooks/ctx_inject.py` and `sdd_post_gate` above 0 in CI's coverage JSON. **Unit**: one case over the hook lanes counts operations at the filesystem or subprocess seam, equal at 2 and 20 contexts; no production counter.
- AC2.3 A registry row missing a key is unreadable (`registry-row-missing-a-key-escapes-reg-schema`; 0162): the one parse raises `SchemaVersionError`. **Integration**: a row without `created_at` exits 1 with `REG-SCHEMA` and one `Operator action:` line, no `KeyError`.
- AC2.4 An absent specs tree is reported as absent (`pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043). **Unit**: with no constitution the finding names the absence and `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`.
- AC2.5 An upgrade leaves no scratch and no silent rewrite (`upgrade-leaves-reconcile-scratch-behind`; F044; 0104): `.dadaia/tmp/reconcile/` absent after `init`; `pre-push` rewritten only when its bytes differ. **Integration**: a second `init` leaves the hook's bytes untouched; a differing hook is refreshed.
- AC2.6 `release.py memory` is idempotent (`release-memory-appends-a-second-entry-on-rerun`; F097). **Unit**: a rerun over the same window exits 0, the `kind: memory` entries byte-equal.
- AC2.7 The ledger seam refuses exactly what the push refuses (`ledger-denylist-term-inside-context-slug-blocks-registration`, HIGH; **REBUILD verdict, approved with this SPEC**: unit, the ledger privacy seam; trigger ≥ 2 bugs and two deciders, C7). The seam asks the push gate's own question, published-prior-text amnesty included; its own matcher leaves. **Unit**: a table of values, seam verdict equal to push verdict per row; a context value already published in the ledger is accepted, an unpublished term is refused. **Integration**: the registered record pushes through `pre-push`.
- AC2.8 The 27 hidden breaks are registered (C9; rc-8 AC12.4's table unchanged): one `chore(bugs): report …` with the two `caused_by` repairs; sha rows resolved retro, one shape-4 commit each; AC rows stay open for Job 3. **No test** (ledger data): `bugs.py status --all`'s open set is the Job 3 rows; `bugs.py fix <slug>` prints each sha row's shas.
- AC2.9 Non-product records ruled by class (C10; rc-8 AC13.4's classes and shape-4 commits). **No test**: `bugs.py check` exits 0; `bugs.py stats` matches the logged per-class counts.
- AC2.10 Records on retired surfaces leave by `bugs.py archive --adr <id>`, an accepted ADR each, retroactive where missing (C10; 0187 (3)). **No test**: `bugs.py window` omits them; the histo carries `archived_by`.
- AC2.11 Provisional: `bug-window-tests-assume-posix-paths` if open at rc-8's close, and each fix-induced record of rc-8's tail, each given an AC and level before approval.

## Job 3 — the REBUILDs

Each **REBUILD** below is an approved REBUILD verdict once this SPEC is Approved: one commit `refactor(<task-id>): REBUILD <unit> — …`, the culprits' revert plus the smallest correct redo, culprit shas in the body (rc-8 AC12.2, AC12.12). After AC2.8.

- AC3.1 One test session env, one owner (**REBUILD**: unit, the test session env; culprits 09d259133, 4ca3d7136 (i, ii), b69ee15b9's in-process line, 76d7af604's conftest hunk; trigger ≥ 2 fixes, C1; rows 14, 16, 17; rc-8 AC10.1 re-cut):
  - A pure `suite_env(parent, home)`, applied once per process by `pytest_configure`; every child env is `suite_env(...) | overrides`; every other env write and helper leaves (rc-8 AC10.1's list).
  - The tripwire exits 1 on a gained `__pycache__` under `dadaia_workspace/` or `tests/`, or a gained entry under the parent `HOME`'s `.cache`.
  - **Unit**: `suite_env`'s literal parametrize row. **Integration** (`pytester`): an inner run under an operator `DADAIA_CONTEXT` and a foreign `HOME` passes, its child seeing the temp `HOME`; one writing a watched `__pycache__` exits 1. **E2E**: rc-8 AC10.1's acceptance command on a clean checkout exits 0 and prints no `__pycache__`.
- AC3.2 `context dead` never commits (**REBUILD** per 0172: unit `context dead`; culprits 49f9940c7, 934377e89, 92a727a20, 1ee8aa30f's secret-refusal hunk; C4; rc-8 AC12.8): `dead --commit`, `commit_all` and dead's consent, secret and identity refusals leave; a dirty checkout refuses, one fix line per file; the push passes `pre-push`. **Integration**: 0172's `measured_by`.
- AC3.3 `sweep.py`'s delete path and result protocol (**REBUILD** U1, U2: culprits 8f329db3a, af2154d5a, b9b28202d; C3; rows 6, 21–23, 27; rc-8 AC12.13 unchanged, its cases the RED). **Unit**: those cases; a non-empty directory judged by `occupied` with no Python-version branch.
- AC3.4 T-050-168's tests (**REBUILD**: culprits a41c69967, aed2ac322, 7196e1473; d66e50c66 kept; C5; rows 10, 12; rc-8 AC12.9). **Unit**: `test_a_canon_change_bumps_the_stamp` passes with its original assert and rule; the refusal row compares `stderr` lines for equality on every OS.
- AC3.5 `_StubDoctor` leaves (**REBUILD**: culprits 86f4cd992, 686ec7b40; C6; row 13; rc-8 AC12.10). **Unit**: the real `DoctorService` over a tmp workspace keeps each case's exit code.
- AC3.6 Own fixes, not REBUILDs (rc-8 AC12.14; body `rebuild: none — Q24`): row 20 (**unit**: `run.py --planted` turns red on a raw `sys.stdin` assignment); row 24 (**integration**: dead holds a submodule, its relative gitdir resolves after the move); row 25 (**unit**: one walk per expired entry at the filesystem seam); row 26 (**unit**: a root-level held symlink keeps its hold clock, 0074).

## Job 4 — the PLAN and the trio validator

- AC4.1 The PLAN (Q8, R6): §1 as-is review; the DAG of jobs, each job's envelope, edges, the critical path; the hot-file list. The Parallel schedule leaves. **Unit**: AC4.2's rows.
- AC4.2 `release.py check` refuses, one fix line each (Q8, Q18, R1, R5–R8, I2): a cyclic DAG; no Job 1; > 8 jobs (Reconciliation uncounted); edge-free jobs with overlapping envelopes; overlapping `W:` in one stage; a `W:` outside its stage envelope; a hand-edited hot file twice in one stage; a generated hot file in any `W:`; a born task without an AC; a cancelled one without a reason; non-test files in stage 1; a SPEC AC without a test level; a SPEC or PLAN changed after approval; a stage contract changed after it opened. **Unit**: one table, a trio per refusal, one valid trio exiting 0.
- AC4.3 `release.py phase IMPLEMENTATION` refuses a PLAN without the DAG or the hot-file list. **Unit**.
- AC4.4 `dd-release-definition` §4–§5 state the job/stage/task shape once, to AC12.11's bar. **No test** (law text, as Job 5).

## Job 5 — the bugs law and the closed rc

**No test** unless a level is named (law text; tests assert behaviour, not text): each file rewritten once to rc-8 AC12.11's bar; `public stage`, `install`, `doctor` and `/corpus-audit` clean.

- AC5.1 The merge is the boundary (rc-8 AC12.1 as AC13.7): a bug exists once a merged change breaks a documented contract; a failure inside an unmerged worktree is rework, no record. `dd-bug-registration` §2 step 4 adds the work-branch sha that reproduces it.
- AC5.2 The block list, closed, stated once in the bugs law §2 (rc-8 AC13.2): (1) the work branch's CI is red; (2) a Stall; (3) the running task cannot deliver its AC; (4) a security finding or an open dependency-vulnerability alert; (5) data loss or corruption. Every other file points there.
- AC5.3 A block-list bug is a hotfix (Q17): registered with `caused_by`; job gate and one review; lands before any other job merge; body names `block: <item>`; no SPEC amendment.
- AC5.4 Every other bug is only registered, `found_in` its rc; the next rc's §1 reads it and its Job 1 resolves it (Q19). A fix-induced bug outside the block list is REBUILT by the next Job 1 (rc-8 AC12.2 narrowed; AC12.3 stands as block item 1). The pile, cause groups and "fixed in any phase" leave.
- AC5.5 The rc is closed (Q16, R1, R2, Q20): created, implemented, or cancelled into the next; no amendment (shape 8 keeps approval only); a new AC goes to the next rc; a red outside the envelope appends a new stage; a stage's third red gate stops the job for the operator; rc N+1 is defined while rc N implements, its §1 and Job 1 closing with rc N; one rc implements at a time.
- AC5.6 Every rc's first SPEC opens with `## Bug window review` (T-050-216; rc-8 AC13.3): `release.py new` writes the heading first; `check` refuses a live SPEC lacking it; `dd-release-definition` §1 reads `bugs.py window` and each cited test. **Unit** (`test_release_implementation_release_script.py`): `new 9.9.9`'s first `## ` is the heading; a SPEC without it exits non-zero with one fix line.
- AC5.7 §3a: the REBUILD shapes (rc-8 AC12.12), shape 3's `block: <item>`, the per-class shape 4, the archive shape. **Unit**: `bugs.py fix` finds `refactor(bugs): <id> — REBUILD`.
- AC5.8 `CONTEXT.md` gains this SPEC's Terms and Bug window; **Wave**, Pile and Cause group are absent. **No test**: `grep -cE '^\*\*(Wave|Pile|Cause group)\*\*:' CONTEXT.md` prints `0`.

## Reconciliation

**No test**: each AC is observed by the command it names or a `_RELEASE.json` log line.

- AC6.1 Each atom Jobs 1–5 make stale (`worktrees.md`, `bug-ledger.md`, release atoms) states the code, citing its commit, in the merge that regenerates its derived sections (AC1.5), never hand-merged; drift guard and `memory.py check` clean; catalog regenerated; a `### P-NN` change rides its accepted ADR.
- AC6.2 `_RELEASE.json` logs rc-8 G1's readouts at start and end, each job's bug-surface delta, and throughput against the grill's rc-8 baseline (75 % process commits, parallelism 1.3, median task lead 1.1 h, ~81 review rounds in 26 h, gate 1 ~6 min); AC1.7's comparison, met or missed, gating nothing.
- AC6.3 Each proposed ADR below is accepted or rejected by the operator; its `measured_by` names a check this rc built, repaired in the 0138 lane where a name moved.
- AC6.4 Closure per the releases law; rc-10 defined beside it (Q20).

## Proposed ADRs (`proposed`; ids from 0190, tentative)

Each is accepted before a push deletes a law line it governs (0151 M3): 0190–0192 before Job 1's push.

- 0190 "Gates per task, stage and job; one review per job; the task is the dispatch unit" (demolition (a), (c), (e)). Supersedes 0185's full command at every merge. `measured_by`: AC1.1, AC1.2, AC1.4 cases.
- 0191 "One worktree tree per job; no kind allowed sets" (demolition (b)). Supersedes 0106; amends 0124 (specs writes land in a job, `define` or `backlog` worktree), 0125 (5 task worktrees, one `define` per rc). `measured_by`: AC1.3 cases.
- 0192 "Closure is the Reconciliation job; an atom and its derived sections land in one merge" (demolition (d)). Amends 0148: closure in a release worktree, the release kind's law copies, the cross-worktree derived hash leave. Replaces the rejected 0189. `measured_by`: AC1.5's case.
- 0193 "An rc is an Implement: a DAG of ≤ 8 jobs, Job 1 fixed; jobs hold stages, stages hold tasks". Amends 0152 (2): ≤ 8 jobs; the 12 KiB TASKS recommendation reads per job file. `measured_by`: AC4.2's job-count and Job 1 rows.
- 0194 "SPEC says what, PLAN draws the DAG, TASKS runs per job; task state derived, done once per job". Supersedes 0141. `measured_by`: AC1.9, AC1.10, AC4.1–AC4.3 cases.
- 0195 "An rc has closed scope; a block-list bug is a hotfix; any other waits for the next Job 1". Amends 0019: no bug fixed "at once" off the block list; rc N+1 defined while rc N implements. `measured_by`: AC5.6's cases; every `fix(bugs)` body names `block:`.
- 0196 "Closed stage contract, live tasks; each AC names its test level; stage 1 writes every RED". `measured_by`: AC4.2's level, stage-1 and contract rows; AC1.2's branch-policy rows.
- 0197 Amends 0149: tasks run parallel inside one stage with disjoint `W:`; jobs with disjoint envelopes or an edge; (3) becomes the hotfix. `measured_by`: AC4.2's overlap rows.
- 0198 Amends 0186 (2), (5): a fix-induced bug stops work only on the block list; the verdict per 0190. `measured_by`: AC1.2's matrix case; the next audit's `PILLAR-BUGS`.
- 0199 Amends 0187 (1): a Draft `rc-<N+1>/SPEC.md` added while rc N implements does not move `found_in`. `measured_by`: an append after rc-10's Draft add, before rc-9 closes, stamps `rc-9`.

## Replaces

- Gate 1 (the full `ci.py` per merge); a review per merge; one `verify:` for every kind (AC1.1–AC1.4).
- Kinds `release`, `impl`, `bug`, their allowed sets and `<M.m.p><letter>-<kind>` grammar; fixed-depth path readers; unpushed worktree branches (AC1.2, AC1.3).
- The 9-step closure and its cross-worktree atom ↔ derived-docs coupling (AC1.5); micro-dispatch (AC1.6).
- One `TASKS.md` per rc, `[-]`, start and per-task done commits, the Parallel schedule (AC1.9, AC1.10, AC4.1).
- SPEC amendments; the pile, cause groups; any-phase bug fixes; a fix-induced bug stopping the line in any rc (AC5.3–AC5.5).
- The ledger seam's own matcher (AC2.7); Job 3's units; **Wave** (AC5.8).

## Risks

| Weakness | Mitigation |
|---|---|
| Job 1 merges before the CI-matrix gate exists. | Its verdict names Windows/macOS unverified (rc-8 AC12.6). |
| Jobs 1, 4, 5 share `dd-gitflow-default/SKILL.md`, `release.py`, the releases law. | A PLAN edge or one owner per file (R7). |

## Carried

- rc-10: the evals lane (`agent-behavior-evals`; 0177, 0178; T-050-185, 186, 188); `QUALITY.md`'s convergence indicator (T-050-180; 0176); HOOKS-DRIFT-1 (T-050-177); rc-8 §Carried's other rc-9 items.
- rc-10 … rc-13: the rest of rc-8 §Carried; promote at rc-13 (Q22); `dependabot-pyjwt-open-on-main` closes there (scope I2).

## Not in scope

- The private test-stack and commit-gate hooks (Q23, I1) are the operator's, outside the library.
