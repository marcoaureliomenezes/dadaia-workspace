# SPEC — Release: 0.5.0, candidate 9 (Job 1 the demolition; the bug window; the REBUILDs; jobs, stages and tasks; the closed rc)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-05 outside the tree (Q20); enters by `release.py new` at rc-8's CLOSURE.
**Origin:** operator-demand

- Sources, operator words verbatim: grill handoffs of 2026-10-05 `T040135Z` (Q1–Q23), `T045010Z` (R1–R10, I1–I3), `T050738Z` (scope Q1–Q3, I1–I5) under `.dadaia/handoff/dadaia-workspace/`; the demolition ruling, same day.
- No old ritual in rc-9 ("rc-9 não deve ter ritual velho, nada dele"; supersedes Q21, I4): Job 1 demolishes it in code ("no primeiro minuto da rc9"); every job, Job 1 included, runs the new model (§How rc-9 runs).
- Scope ("Lean: J1 + REBUILDs + mechanism + laws"), demolition first: Jobs 1–5 and Reconciliation; 5 of 8 jobs (Q18).
- Job 2–3 bugs stay out of Origin (0161: no `operator-demand` plus clauses).
- Aggregated from rc-8 (Q21): T-050-173 … 176, 178, 179, 194 … 208, 214 … 216; T-050-213 is §1 (scope I1). T-050-209's REBUILD landed in rc-8: 0844e518e + af924c09f, done db82dc7bf.
- Carried-in, T-050-210 … 212 (AC2.8): rc-8 closed (767ba1d4f) without them. They sit only on `refs/backup/0.5.0b-impl-full`, with their atom and docs commits. AC2.10, AC2.11, AC5.4 and 0199 rest on them: the archive-by-ADR verb (210), the restored records (211) and `found_in` (212).

## Bug window review

**Job 1 (the demolition) runs before this window's fixes; the window runs as Job 2.** Re-read at rc-8's close (767ba1d4f) by `bugs.py stats` and `window` on this tree.

- Window (rc-8 AC13.3): `found_in` or `introduced_in` in 0.5.0 or 0.4.7. No record carries `found_in` until AC2.8 lands T-050-212's backfill. `bugs.py window`: 39 in the window, 12 release unknown. By `ts`: 236 records since 0.4.7 opened. 8 are open: AC2.1–AC2.7's seven, and `dependabot-pyjwt-open-on-main` (§Carried).
- rc-8's fixes, by `bugs.py fix` (10 linked, 0 unlinked):

| bug | fix | direction | what followed | verdict |
|---|---|---|---|---|
| `test-suite-writes-outside-tmp` | 09d259133 | neutral | rows 14, 15 | REBUILD, AC3.1 |
| `suite-fails-under-an-operator-dadaia-context` | b69ee15b9, 76d7af604 (CI follow-up) | neutral | rows 16, 17 | REBUILD, AC3.1 |
| `onboarding-next-step-names-another-context` | 6285e06b2 | positive | row 13 | fix KEEP; its test REBUILD, AC3.5 |
| `context-dead-secret-fix-line-stashes-what-dead-then-destroys` | 1ee8aa30f | positive | its secret-refusal hunk is a culprit | REBUILD, AC3.2 |
| `worktree-merge-linearizes-a-branch-already-containing-work` | 1cfc3b72d | positive | reverted (T-050-191) | done |

- Held, nothing followed (KEEP): 5, both net-negative fixes among them (`bugs.py fix`). Readout: 5 of the 8 others bred a bug or were reverted.
- T-050-209, a task, bred `bug-window-tests-assume-posix-paths` (MEDIUM). rc-8's REBUILD (0844e518e) resolved it.
- Clusters:
  - Job 3's REBUILDs: C1 test session env (3 fixes, rows 14–17); C3 `sweep.py`'s except arm (rows 6, 21–23, 27, three culprits); C4 `context dead` (AC12.8's culprits, row 24); C5 T-050-168's tests (rows 10, 12); C6 `_StubDoctor` (row 13, two repairs in 2 days).
  - C2 Tests assume the host's paths: rows 5, 8, 9, 11, 12, 18 and `bug-window-tests-assume-posix-paths`, 7 records, each red only on post-merge CI. Cause: the merge gate runs local Linux only (rc-8 AC12.6). Verdict: the CI matrix at the job gate (R9, AC1.2); no per-test rule. Row 12 is Job 3's.
  - C7 The ledger privacy seam: the open HIGH and its 4 `--correlates` (`sa-ledger-write-seam-redacts-less-than-push-refuses`: fix 1bcfdba8f created the seam). Cause: two deciders of "what the push refuses"; the seam judges a value alone, the push against published prior text. REBUILD, AC2.7.
  - C8 rc-8's six single W10 records: UPDATE, RED first, AC2.1–AC2.6; a unit the as-is review finds with ≥ 2 prior fixes turns REBUILD.
  - C9 rc-8's 27 unregistered hidden breaks (AC12.4) → AC2.9.
  - C10 Non-product records (2026-10-05: 15 agent error, 89 release-born, 66 dev-tooling, 35 doubtful) and the 65 restored records on retired surfaces → AC2.10, AC2.11. Their counts are re-read after AC2.8.

## How rc-9 runs (from its first minute)

Operator, 2026-10-05: "Não será autorizado se não seguir o padrão job stage tasks, gates onde deveriam ... DESDE JA"; "proibido de rodar 1 worktree para cada tasks ou rodar CI para cada teste". rc-9 runs jobs → stages → tasks from its first commit, Job 1 included. No old ritual: no `worktree.py` kinds, no `WT merge` gate 1, no `TASKS.md`, no `[-]` markers, no start or done commits. Job 1 deletes them from the code; rc-9 never uses them, even before Job 1 lands.

**Job DAG.** The edges come from file overlap; jobs without an edge have disjoint envelopes.

| job | waits on | why |
|---|---|---|
| Job 1 | — | runs from minute 1 |
| Job 3 | — | runs from minute 1; its envelope is disjoint from Job 1's |
| Job 2 | Job 1 | both touch `scripts/ci.py` and `bugs.py` (AC2.8's 210 commits) |
| Job 4 | Job 1 | both touch `release.py`, `dd-gitflow-default` and the releases law |
| Job 5 | Jobs 1, 2, 4 | Job 1: as Job 4. Job 2: `bugs.py` and `test_bug_resolution_bugs_script.py` (AC2.7, AC2.8 vs AC5.7). Job 4: `_release_check.py` (AC4.2 vs AC5.6) |
| Reconciliation | Jobs 1–5 | memory and derived docs of every job (AC1.5, AC6.1) |

- Lanes: A, Job 1 → (Job 2 ∥ Job 4) → Job 5 → Reconciliation; B, Job 3 → Reconciliation.
- Critical path: Job 1 → Job 2 → Job 5 → Reconciliation.
- Cap: 2 test-running agents at once (operator rule), so at most 2 code jobs run tests at the same moment. If Job 3 still runs when Job 1 lands, Job 2 opens and Job 4 waits for a free slot. Law-text jobs and tasks with no tests may run beside them.
- Shared by design: `specs/bugs/BUGS.jsonl` (Jobs 2, 3) is written only by `bugs.py`, and a rebase conflict is redone by its writer (ADR 0180). `PLAN.md` holds one section per job, and only that job writes it.

**Worktrees.** One per job: `worktrees/dadaia-workspace/0.5.0-rc9-<job>` (`job1` … `job5`, `reconcile`), branch `wt/0.5.0-rc9/<job>`, cut from the work branch. There is no worktree per task. Tasks run inside their job's worktree; parallel tasks in a stage have disjoint `W:` sets. A job's PLAN section is written in its own worktree; every other specs edit goes in `0.5.0-rc9-define`.

**Gates and tests per level.** Until Job 1 lands AC1.1's levels, the driver runs these commands by hand.

| Level | Gate | Tests |
|---|---|---|
| Task | `ruff` and `mypy` on the touched files | that task's owner tests, `pytest <owner files> -n 2` |
| Stage | the barrier | unit + integration (`-n 2`); green before the next stage opens |
| Job | `scripts/ci.py` full, run ONCE on the job HEAD; CI matrix green after the push | everything `ci.py` runs; the matrix |

- Never run the full suite or `ci.py` per task, per test or per edit.

**Review.** One `dd-code-reviewer` review per job, at its end. None per task or stage, except a stage past 400 added lines (operator Q2; AC1.4).

**Merge.** Each job lands with one manual merge onto `feature/0.5.0` and one push. A later job rebases onto it. There is no `worktree.py merge` gate 1 and there are no kinds.

**Dispatch.** The main thread dispatches a job (to its driver) or a task, never a smaller step (AC1.6).

**Job files.** Each job's section below lists its stages and tasks. The job driver refines them in that job's `PLAN.md` section.
- Stage 1 writes the RED tests as strict xfail, and touches test files only. A job with no tests has no RED stage.
- A task is `J<n>.S<m>.T<k> AC — W: … — owner test`. Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/` and `bugres/` is `public/skills/dd-bug-resolution/`.
- Inside one stage, `W:` sets are disjoint, so a hot file has exactly one owning task per stage.

**Parallelism.**
- Baseline: rc-8's 1.3 (AC6.2).
- Target: ≥ 2 jobs in flight while Jobs 1 and 3 run.
- Measure: each `kind: merge` entry carries `start` and `end` (AC1.7). The jobs in flight over Job 1's window are `Σ_jobs overlap(job, Job 1) / wall(Job 1)`. AC6.2 logs this number together with the rc's `Σ wall / (max end − min start)`.

## Terms

- **Implement**: one rc's run, a DAG of jobs; not a file (Q1, Q7).
- **Job**: one measured feature, one worktree, one review and gate at its merge (Q2, Q3); **Job 1** executes §1 (Q18); in rc-9 only, Job 1 is the demolition and §1 is Job 2. A GitHub job is always "CI job".
- **Stage**: a barrier on the job branch over parallel tasks; no worktree (Q4).
- **Task**: one owner (module or law file plus its owner test file), one session (~1 h), ~100 new code lines, deletions uncounted (Q15); runs inside its job's worktree; one owner; parallel with its stage's other tasks; the unit of dispatch.
- **Envelope**: the `W:` union a job or stage may touch (R1, R7).
- **Closed stage contract**: exit tests, envelope and ACs served, fixed when the stage opens (R1).
- **Live task**: born, split or cancelled inside an open stage, unreviewed (R1).
- **Hot file**: one two tasks would write; hand-edited or generated (R6).
- **Ritual wait**: a merged job's wall time from its last task commit to its pushed merge: gates, review, CI waits.
- **Hotfix**: a block-list bug's fix, outside the DAG (Q17). **Reconciliation**: the last job, outside the 8 (Q10).

## Job 1 — the demolition

Job 1 runs exactly the model in §How rc-9 runs, like every job. "Um merge só, autorizado" still holds: one job, one merge. RED first in the owner file.

- Worktree `worktrees/dadaia-workspace/0.5.0-rc9-job1`, branch `wt/0.5.0-rc9/job1`, opened by an operator-authorized `git worktree add`.
- Gates by level. `../../../.dadaia/.venv/bin/python scripts/ci.py` runs once, on the job HEAD.
- One review at the end, then one manual merge authorized by the operator, then one push.

Stages:
- S1 RED (AC1.1–AC1.5, AC1.9, AC1.10):
  - T1 AC1.1 — W: `tests/integration/test_ci_script.py`.
  - T2 AC1.2–AC1.5 — W: `tests/integration/test_worktree_lifecycle.py`, `tests/integration/test_worktree_new.py`.
  - T3 AC1.2 — W: `tests/unit/features/chokepoints/test_push_branch_policy.py`.
  - T4 AC1.9, AC1.10 — W: `tests/unit/features/specs/test_canon.py`, `tests/unit/features/specs/test_release_tree.py`.
- S2 code and law (AC1.1–AC1.10); envelope: `scripts/ci.py`, `scripts/guards/repo.py`, `.github/workflows/ci.yml`, `gitflow/`, `relimpl/scripts/`, `core/invocation.py`, `features/chokepoints/branch_policy.py`, `features/specs/canon.py` and AC1.8's law files:
  - T1 AC1.1 — W: `scripts/ci.py` — `test_ci_script.py`.
  - T2 AC1.3 — W: `gitflow/scripts/_worktree_new.py`, `_worktree_kinds.py` (deleted), `core/invocation.py` — `test_worktree_new.py`.
  - T3 AC1.2, AC1.4, AC1.5 — W: `gitflow/scripts/worktree.py`, `_worktree_end.py`, `_worktree_git.py` — `test_worktree_lifecycle.py`.
  - T4 AC1.2 — W: `features/chokepoints/branch_policy.py`, `.github/workflows/ci.yml`, `scripts/guards/repo.py` — `test_push_branch_policy.py`.
  - T5 AC1.8 (the Parallel schedule's code), AC1.9, AC1.10 — W: `features/specs/canon.py`, `relimpl/scripts/_release_tree.py`, `_release_phase.py`, `_release_plan.py` (deleted) — `test_canon.py`, `test_release_tree.py`.
  - T6 AC1.8 — W: `public/data/worktrees-AGENTS.md`, `gitflow/SKILL.md` — no test.
  - T7 AC1.8 — W: `relimpl/RC-FLOW.md`, `relimpl/MEMORY-UPDATE.md`, `relimpl/SKILL.md` — no test.
  - T8 AC1.6, AC1.8 — W: `public/skills/dd-manager-orchestration/SKILL.md`, `public/skills/dd-release-definition/SKILL.md` — no test.
  - T9 AC1.8 (hit lines only) — W: `public/scaffold/{releases,bugs,ADRs}/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`, `public/skills/dd-code-review/SKILL.md` — no test.

- AC1.1 (a) Gates per task and stage; the full `scripts/ci.py` at every `worktree.py merge` leaves (gate 1, 0185, T-050-191; Q6, R4). Three `scripts/ci.py` levels (root `AGENTS.md`): task (ruff, mypy on touched files, owner tests), stage (lint, mypy, guards but drift, unit, integration; R6), job (the full command). A task commits on its job branch, inside the job's worktree, after its gate; a stage closes when its gate is green on the job HEAD. **Unit** (`test_ci_script.py`): each level runs only its steps; a planted failing step turns it non-zero.
- AC1.2 (a) The job gate runs the CI matrix once (Q2, Q11, R7, R9, Q13, Q14): a job's merge runs the job level on HEAD, requires an APPROVED verdict naming its green CI-matrix run, and fast-forwards; a moved work branch refuses with a rebase fix line; 0168's carry stands. `pre-push` accepts and scans `wt/<M.m.p>-rc<N>/<job>` only of `wt/`; `ci.yml` triggers on `wt/**`. A non-code merge (`define/`, `backlog/`) runs the ledger, trio and ADR validators only. The repo's `verify:` line and its `shell=True` run leave (`_worktree_end.py:124-131`, CWE-78): the job level is one argv list, `shell=False`. Check: `grep -c 'shell=True' dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` prints `0`. **Unit**: branch-policy rows. **Integration**: a verdict without the matrix run refuses; a second job's merge refuses until rebased; an invalid ledger refuses, a valid one lands with no test run. **Guard**: `ci-triggers-gitflow` pins `wt/**`.
- AC1.3 (b) One worktree per job, none per task; the worktree-kind split leaves (0106, 0124, 0148; Q4, Q5, Q8, R3, Q11): `worktrees/<repo>/<M.m.p>-rc<N>/{define,reconcile,<job>}`, branch `wt/<M.m.p>-rc<N>/<job>`; outside an rc only `backlog/<slug>`; a bug is a job. The task-worktree shape `<job>--<task-id>` and its "≤ 5 task worktrees" counter leave (operator, 2026-10-05: "proibido de rodar 1 worktree para cada tasks"). The per-kind allowed sets leave: code, tests, specs, memory and derived docs of one change are one job. A job branch takes only its tasks' commits and its rc's specs edits (R8). The job driver's own edit (AC1.6) lands as a task commit naming its id. The gate, doctor, reaper and `WT` read a worktree path's repo-relative tail through one function (`core/invocation.py`). **Integration**: `WT new` makes each shape and refuses an old-grammar name; a PROTECTED write in a job worktree is blocked; one job commits a code file and a `specs/memory/` atom together.
- AC1.4 (c) One review per job; none per worktree (Q2, Q12, Q14; rc-8 AC9.4, AC12.6, AC12.12): none at a task commit or a stage close. One per job, plus one per stage past 400 added lines (operator Q2). Added lines are the sum of `git diff --numstat` column 1 over the stage range; deletions are excluded. A non-code merge gets one pass; one definition round per document, again only on a HIGH; the verdict carries the job command's output and CI-matrix run; a REBUILD read covers every line the prior fix wrote; no APPROVED on a test-deleting `refactor(...)` without a SPEC REBUILD verdict. **Integration**: a job merge without a verdict refuses.
- AC1.5 (d) The 9-step closure leaves; Reconciliation is the last job (Q10): memory, derived docs, `measured_by` repairs, the rc's measurement, closure, one worktree. An atom and its derived sections land in one merge; the atom ↔ derived-docs hash check runs on that merge. The rejected 0189 (release kind carries derived docs) does not return. **Integration**: one merge changing an atom and its derived section passes the job gate and the drift guard; the atom alone is refused with one fix line naming the regenerating command.
- AC1.6 (e) No micro-dispatch: the main thread dispatches a job or a task; a smaller edit inside an open job is the job driver's own (`dd-manager-orchestration`), landing as a task (AC1.3). **No test** (law text, AC1.8). Check: each job's `kind: merge` log entry (AC1.7) carries `dispatches: <n>`. It is a log line, not a gate.
- AC1.7 Ritual wait is measured per job. Each merged job, Job 1 included, appends one `kind: merge` entry to `_RELEASE.json`'s `log`: `job: <name>; start: <UTC>; end: <UTC>; wall: <min>; ritual_wait: <min>; dispatches: <n>`. `start` is the committer time of the job branch's first commit; `end` is the pushed merge's time (below). `release.py` has no log verb, so the job driver writes it by Read-then-Edit (`RELEASE-EVENTS.md` §log); `release.py check` validates it. **No test** (log data).
  - Formula, over whole rcs: `1 − Σritual_wait(rc-9) / Σritual_wait(rc-8)`.
  - The rc-8 baseline comes from rc-8's git history. Both rcs use the same endpoints: the last task commit's committer time to the pushed merge. The pushed merge's time is the `createdAt` of the first push CI run (`gh run list --branch <work branch>`) whose head contains the landing. Reconciliation computes it once (AC6.2), anchored to `T040135Z`'s readout: gate 1 ~6 min on 67 landings, ~81 review rounds in 26 h.
  - Estimates, not targets: 25–35 min per rc-8 merge, ~12–15 h over ~30 merges, and ~75–80 % less ritual wait.
- AC1.8 The law follows in the same merge. Each file is rewritten once to rc-8 AC12.11's bar: `worktrees/AGENTS.md` (the tree, three gates, one review, hotfix, caps), `dd-gitflow-default` §3a's kind column, `RC-FLOW.md`'s closure steps, `MEMORY-UPDATE.md`, `dd-manager-orchestration`, and `dd-release-definition` §4–§5 (the job, stage and task shape; the Parallel schedule leaves, its `_release_plan.py` check and test with it).
  - Old-ritual lines also leave from the files Job 5 owns. Job 1 deletes only the hit lines there; Job 5 rewrites those files:
    - `scaffold/releases/AGENTS.md`, `scaffold/bugs/AGENTS.md` and `scaffold/ADRs/AGENTS.md`;
    - `skills/dd-bug-resolution/SKILL.md`, `skills/dd-release-implementation/SKILL.md` and `skills/dd-release-implementation/scripts/_release_plan.py`;
    - `dd-bug-registration` §3 and `dd-code-review` §3.
  - Today the grep also hits `data/worktrees-AGENTS.md`, `dd-gitflow-default/SKILL.md`, `_worktree_kinds.py`, `_worktree_new.py`, `RC-FLOW.md` and `MEMORY-UPDATE.md` (AC1.3 and the files above).
  - **No test** (law text). `public stage`, `install`, `doctor` and `/corpus-audit` are clean, and both checks print `0`:
    - ``grep -rnE -- '--kind (impl|bug|release|backlog)|`(impl|bug|release)` worktree|chore\(tasks\): start|Parallel schedule|Candidate closure order' dadaia_workspace/public | wc -l``.
    - The grep misses two lines, so a second check covers them: ``grep -hcE "\`bug\` or \`backlog\` worktree|its kind's" dadaia_workspace/public/skills/dd-bug-registration/SKILL.md dadaia_workspace/public/skills/dd-code-review/SKILL.md`` prints `0` per file.
- AC1.9 One TASKS file per job (R8): `rc-<N>/tasks/<job>.md`; the canon admits `tasks/`; `TASKS.md` and its `[-]` marker and start commits leave from Job 2 on, closed rcs unchanged. **Unit**: canon rows for a job file, a stray `tasks/` file, a closed rc's `TASKS.md`.
- AC1.10 The job file (Q8, Q9, R1, R5, R10, I2): per stage its contract (exit tests by level, envelope, ACs served) and its tasks (id, AC, `W:`, owner tests, RED tests); stage 1 is test-only, every acceptance test RED as strict xfail; `running` is derived (its job's worktree exists, its task commit absent), `done` written once per job by its close task; a cancelled task stays with its reason, a born one cites its AC. **Unit**: one valid job file parses; a stage-1 non-test file refuses. A cancelled task's reason stays out of the code: it is taught in `dd-release-definition` §5 and measured by Pillar 2 (AC4.2, the ruling "Skill + auditoria (Recommended)").

## Job 2 — the bug window, executed

RED first in the owner file. Job 2's close logs Δ production lines, Δ test functions and each cluster's bug-surface delta with ledger evidence (root map §1).

Stages:
- S1 RED (AC2.1–AC2.7):
  - T1 AC2.1 — W: `tests/integration/test_ci_script.py`.
  - T2 AC2.2 — W: `tests/unit/hooks/test_ctx_inject.py`.
  - T3 AC2.3 — W: `tests/integration/cli/test_registry_version_grammar.py`.
  - T4 AC2.4 — W: `tests/integration/cli/test_push_gate_gitflow_resolution.py`.
  - T5 AC2.5 — W: `tests/integration/test_cli_init.py`.
  - T6 AC2.6 — W: `tests/unit/skills/test_release_implementation_release_script.py`.
  - T7 AC2.7 — W: `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- S2 carried-in code (AC2.8: 210 and 212 as-is):
  - T1 — W: the five shas' own paths (`bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, its derived docs, `BUGS.jsonl`) — no test.
- S3 fixes and the 211 REBUILD (AC2.1–AC2.8, AC2.11's SCP and THM families):
  - T1 AC2.1 — W: `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md` — `test_ci_script.py`.
  - T2 AC2.2 — W: `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml` — `test_ctx_inject.py`.
  - T3 AC2.3 — W: `core/context_registry.py` — `test_registry_version_grammar.py`.
  - T4 AC2.4 — W: `cli/commands/ci.py` — `test_push_gate_gitflow_resolution.py`.
  - T5 AC2.5 — W: `features/reconcile/service.py`, `cli/commands/init.py` — `test_cli_init.py`.
  - T6 AC2.6 — W: `relimpl/scripts/release.py` — `test_release_implementation_release_script.py`.
  - T7 AC2.7 — W: `bugres/scripts/_ledger.py` — `test_bug_resolution_bugs_script.py`.
  - T8 AC2.8 (211), AC2.11 — W: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/` — no test; `V33_ORPHANS ≤ 31`.
- S4 ledger (AC2.9–AC2.11):
  - T1 — W: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl` (`proposed` only) — no test.

- AC2.1 Coverage data lands outside the repo (`ci-preflight-writes-coverage-into-the-repo`; F048; rc-8 AC10.2): on CI, `scripts/ci.py` and every `pytest --cov` line of `tests/README.md` and `tests/AGENTS.md`, no coverage file appears in the checkout; one decider; pytest runs with `-B` there. **Integration**: after each path, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC2.2 Hooks are visible to coverage and bounded in cost (`hook-entrypoints-invisible-to-coverage`; F051; 0118): `hooks/ctx_inject.py` and `sdd_post_gate` above 0 in CI's coverage JSON. **Unit**: one case over the hook lanes counts operations at the filesystem or subprocess seam, equal at 2 and 20 contexts; no production counter.
- AC2.3 A registry row missing a key is unreadable (`registry-row-missing-a-key-escapes-reg-schema`; 0162): the one parse raises `SchemaVersionError`. **Integration**: a row without `created_at` exits 1 with `REG-SCHEMA` and one `Operator action:` line, no `KeyError`.
- AC2.4 An absent specs tree is reported as absent (`pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043). **Unit**: with no constitution the finding names the absence and `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`.
- AC2.5 An upgrade leaves no scratch and no silent rewrite (`upgrade-leaves-reconcile-scratch-behind`; F044; 0104): `.dadaia/tmp/reconcile/` absent after `init`; `pre-push` rewritten only when its bytes differ. **Integration**: a second `init` leaves the hook's bytes untouched; a differing hook is refreshed.
- AC2.6 `release.py memory` is idempotent (`release-memory-appends-a-second-entry-on-rerun`; F097). **Unit**: a rerun over the same window exits 0, the `kind: memory` entries byte-equal.
- AC2.7 The ledger seam refuses exactly what the push refuses (`ledger-denylist-term-inside-context-slug-blocks-registration`, HIGH; **REBUILD verdict, approved with this SPEC**: unit, the ledger privacy seam; trigger ≥ 2 bugs and two deciders, C7). The seam asks the push gate's own question, published-prior-text amnesty included; its own matcher leaves. **Unit**: a table of values, seam verdict equal to push verdict per row; a context value already published in the ledger is accepted, an unpublished term is refused. **Integration**: the registered record pushes through `pre-push`.
- AC2.8 The rc-8 carried T-050-210 … 212 land from `refs/backup/0.5.0b-impl-full` (Carried-in). Each sha lands as-is, or gets a REBUILD verdict in this SPEC before it lands:
  - 210: 8de093db9 (a record leaves the ledger only by an accepted ADR), a98e9a5e1 (fold `ci.py`), e6c117c0e (bug-ledger atom sources) and a01a28e9b (re-derived docs). They land as-is.
  - 211: 8921dd17d restores 65 age-archived records under 0187 and sets 4 `caused_by` to none. **REBUILD verdict, approved with this SPEC**: the redo restores the records and keeps `caused_by` intact on the 4 records 8921dd17d set to `none`.
  - 211: e47e6d257 raises the v33 orphan ratchet from 31 to 33. That contradicts "ratchet DOWN ONLY". **REBUILD verdict, approved with this SPEC**: there is no v33 raise. The SCP and THM orphan families that the restore brings leave in the same stage: their records are archived under AC2.11 (`bugs.py archive --adr <id>`), never left unrestored, since 0187 restores them. `V33_ORPHANS ≤ 31` holds after the stage.
  - 212: 0d9fba147 backfills `found_in`. It lands as-is.
  - 798250d4a (T-050-209's backup REBUILD) does not land. 0844e518e + af924c09f supersede it in rc-8.
  - **No test** (cherry-picks and ledger data). Checks: `git cherry <work branch> refs/backup/0.5.0b-impl-full | grep -cE '^\+ (8de093db9|a98e9a5e1|e6c117c0e|a01a28e9b|0d9fba147)'` prints `0`; `bugs.py check` exits 0; `V33_ORPHANS` in `scripts/guards/slop.py` stays ≤ 31.
- AC2.9 The 27 hidden breaks are registered (C9; rc-8 AC12.4's table unchanged): one `chore(bugs): report …` with the two `caused_by` repairs; sha rows resolved retro, one shape-4 commit each; AC rows stay open for Job 3. **No test** (ledger data): `bugs.py status --all`'s open set is the Job 3 rows; `bugs.py fix <slug>` prints each sha row's shas.
- AC2.10 Non-product records ruled by class (C10; rc-8 AC13.4's classes and shape-4 commits). **No test**: `bugs.py check` exits 0; `bugs.py stats` matches the logged per-class counts.
- AC2.11 Records on retired surfaces leave by `bugs.py archive --adr <id>`, an accepted ADR each, retroactive where missing (C10; 0187 (3)). **No test**: `bugs.py window` omits them; the histo carries `archived_by`.

## Job 3 — the REBUILDs

Each **REBUILD** below is an approved REBUILD verdict once this SPEC is Approved: one commit `refactor(<task-id>): REBUILD <unit> — …`, the culprits' revert plus the smallest correct redo, culprit shas in the body (rc-8 AC12.2, AC12.12). Job 3 runs beside Job 1 from minute 1, not after AC2.9; a row AC2.9 registers after Job 3's merge is resolved retro, citing Job 3's sha.

Stages:
- S1 RED (AC3.1–AC3.3, AC3.6 rows 24–26):
  - T1 AC3.1 — W: `tests/unit/test_conftest_pollution_guard.py`.
  - T2 AC3.2, AC3.6 row 24 — W: `tests/integration/test_context_dead_holds.py`.
  - T3 AC3.3, AC3.6 rows 25, 26 — W: `tests/unit/features/spec_context/test_sweep.py`.
- S2 the REBUILDs (AC3.1–AC3.6); AC3.4 and AC3.5 rebuild test files, so they have no RED:
  - T1 AC3.1 — W: `tests/conftest.py` and rc-8 AC10.1's helpers — `test_conftest_pollution_guard.py`.
  - T2 AC3.2, row 24 — W: `features/spec_context/service.py`, `infrastructure/git_subprocess.py`, `cli/commands/context.py` — `test_context_dead_holds.py`.
  - T3 AC3.3, rows 25, 26 — W: `features/spec_context/sweep.py` — `test_sweep.py`.
  - T4 AC3.4 — W: `tests/unit/core/test_specs_version.py`.
  - T5 AC3.5 — W: `tests/unit/cli/test_exitcode_truthfulness.py`.
  - T6 AC3.6 row 20 — W: `scripts/guards/isolation.py` — `run.py --planted`.

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

Stages:
- S1 RED (AC4.2, AC4.3):
  - T1 — W: `tests/contract/test_release_script.py`.
- S2 (AC4.1–AC4.3):
  - T1 AC4.2 — W: `relimpl/scripts/_release_check.py` — `test_release_script.py`.
  - T2 AC4.3 — W: `relimpl/scripts/_release_phase.py` — `test_release_script.py`.
  - T3 AC4.2 (the four rows taught and audited) — W: `public/skills/dd-audit-project/PILLAR-SPECS.md` — no test.

- AC4.1 The PLAN (Q8, R6): §1 as-is review; the DAG of jobs, each job's envelope, edges, the critical path; the hot-file list. The Parallel schedule already left in Job 1 (AC1.8). **Unit**: AC4.2's rows.
- AC4.2 `release.py check` refuses only the rows a grill ruled with evidence, one fix line each:
  - a cyclic DAG (`T040135Z` Q8);
  - no Job 1 (Q18);
  - more than 8 jobs, Reconciliation uncounted (Q18);
  - non-test files in stage 1 (`T045010Z` R10);
  - overlapping `W:` in one stage (Q8).
  - The four other rows of `T050738Z` Q2 are not validator rows. The operator ruled (AskUserQuestion, 2026-10-05) "Skill + auditoria (Recommended)":
    - Each is taught in `dd-release-definition` §5 (rewritten in AC1.8) and measured by `dd-audit-project` Pillar 2 (`PILLAR-SPECS.md`).
    - The four rows: disjoint envelopes between edge-free jobs; a born task cites an AC; a cancelled task carries a reason; hot files (a hand-edited one in at most one `W:` per stage, a generated one in none).
    - AC test levels and post-approval changes follow the same lane: taught in `dd-release-definition` §4, measured by Pillar 2.
  - **Unit**: one table, a trio per refusal, one valid trio exiting 0.
- AC4.3 `release.py phase IMPLEMENTATION` refuses a PLAN without the DAG or the hot-file list. **Unit**.

## Job 5 — the bugs law and the closed rc

**No test** unless a level is named (law text; tests assert behaviour, not text): each file rewritten once to rc-8 AC12.11's bar; `public stage`, `install`, `doctor` and `/corpus-audit` clean.

Stages:
- S1 RED (AC5.6, AC5.7):
  - T1 AC5.6 — W: `tests/unit/skills/test_release_implementation_release_script.py`.
  - T2 AC5.7 — W: `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- S2 code and law (AC5.1–AC5.9):
  - T1 AC5.6 — W: `relimpl/scripts/_release_new.py`, `_release_check.py` — `test_release_implementation_release_script.py`.
  - T2 AC5.7 — W: `bugres/scripts/bugs.py` — `test_bug_resolution_bugs_script.py`.
  - T3 AC5.1–AC5.4 — W: `public/scaffold/bugs/AGENTS.md`, `bugres/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md` — no test.
  - T4 AC5.5 — W: `public/scaffold/releases/AGENTS.md`, `public/scaffold/ADRs/AGENTS.md`, `relimpl/SKILL.md` — no test.
  - T5 AC5.7 (§3a) — W: `gitflow/SKILL.md` — no test.
  - T6 AC5.8 — W: `CONTEXT.md` — no test.
  - T7 AC5.9 — W: `public/skills/dd-code-review/SKILL.md` — no test.

- AC5.1 The merge is the boundary (rc-8 AC12.1 as AC13.7): a bug exists once a merged change breaks a documented contract; a failure inside an unmerged worktree is rework, no record. `dd-bug-registration` §2 step 4 adds the work-branch sha that reproduces it.
- AC5.2 The block list, closed, stated once in the bugs law §2 (rc-8 AC13.2): (1) the work branch's CI is red; (2) a Stall; (3) the running task cannot deliver its AC; (4) a security finding or an open dependency-vulnerability alert; (5) data loss or corruption. Every other file points there.
- AC5.3 A block-list bug is a hotfix (Q17): registered with `caused_by`; job gate and one review; lands before any other job merge; body names `block: <item>`; no SPEC amendment.
- AC5.4 Every other bug is only registered, `found_in` its rc; the next rc's §1 reads it and its Job 1 resolves it (Q19). A fix-induced bug outside the block list is REBUILT by the next Job 1 (rc-8 AC12.2 narrowed; AC12.3 stands as block item 1). The pile, cause groups and "fixed in any phase" leave.
- AC5.5 The rc is closed (Q16, R1, R2, Q20): created, implemented, or cancelled into the next; no amendment (shape 8 keeps approval only); a new AC goes to the next rc; a red outside the envelope appends a new stage; a stage's third red gate stops the job for the operator, and the driver appends one `kind: note` log entry `stop: <job> stage <n> — third red gate` (a log line, not a gate); rc N+1 is defined while rc N implements, its §1 and Job 1 closing with rc N; one rc implements at a time.
- AC5.6 Every rc's first SPEC opens with `## Bug window review` (T-050-216; rc-8 AC13.3): `release.py new` writes the heading first; `check` refuses a live SPEC lacking it; `dd-release-definition` §1 reads `bugs.py window` and each cited test. **Unit** (`test_release_implementation_release_script.py`): `new 9.9.9`'s first `## ` is the heading; a SPEC without it exits non-zero with one fix line.
- AC5.7 §3a: the REBUILD shapes (rc-8 AC12.12), shape 3's `block: <item>`, the per-class shape 4, the archive shape. **Unit**: `bugs.py fix` finds `refactor(bugs): <id> — REBUILD`.
- AC5.8 `CONTEXT.md` gains this SPEC's Terms and Bug window; **Wave**, Pile and Cause group are absent. **No test**: `grep -cE '^\*\*(Wave|Pile|Cause group)\*\*:' CONTEXT.md` prints `0`.
- AC5.9 A bug fix adds a case (backlog `bug-fix-adds-never-rewrites-asserts`; rc-8 AC9.1's review half, carried by T-050-198):
  - `dd-code-review` names `git diff -U0 -- tests | grep -E '^-\s*assert'`.
  - The `<bug-id>#<id>` citation clause at `dd-code-review/SKILL.md:76` leaves; accepted 0163 retired it.
  - Check: `grep -rn '<bug-id>#<id>' dadaia_workspace/public | wc -l` prints `0`, so 0163's `measured_by` turns green. The entry exits `delivered` at closure by citation (no Origin clause, 0161).

## Reconciliation

**No test**: each AC is observed by the command it names or a `_RELEASE.json` log line.

Stages (no RED stage):
- S1 (AC6.1–AC6.3):
  - T1 AC6.1 — W: `specs/memory/**`, its derived docs and `catalog.json`, in one merge (AC1.5).
  - T2 AC6.1 (F131) — W: `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`.
  - T3 AC6.2 — W: `specs/releases/0.5.0/_RELEASE.json` (`log`).
  - T4 AC6.3 — W: `specs/ADRs/decisions.jsonl` (`measured_by` repairs; acceptance is the operator's).
- S2 (AC6.4):
  - T1 — W: `_RELEASE.json` (phase); rc-10's Draft SPEC goes in `0.5.0-rc10-define`.

- AC6.1 Each atom Jobs 1–5 make stale (`worktrees.md`, `bug-ledger.md`, release atoms) states the code, citing its commit, in the merge that regenerates its derived sections (AC1.5), never hand-merged; drift guard and `memory.py check` clean; catalog regenerated; a `### P-NN` change rides its accepted ADR.
  - Also rc-8's closure memory items. Each has a numeric check:
    - AC10.14's memory half: `grep -rniw union specs/memory | wc -l` prints `0`, and `worktrees.md:36` states the main-repo trio read.
    - The `ci-preflight` atom is deleted: `find specs/memory -name 'ci-preflight*' | wc -l` prints `0`. It is already 0 since 93a0154e2.
    - `AGENTS-PLACEHOLDER-1` leaves `public-asset-distribution.md:50`; the code dropped it in 7502fa4c7. Check: `grep -c AGENTS-PLACEHOLDER-1 specs/memory/product/distribution/public-asset-distribution.md` prints `0`.
    - `bug-ledger.md:5,16` (and `catalog.json`'s summary) qualify "no git-derived": the record stores none, while `bugs.py fix` and `window` derive them on read. Check: `grep -E 'git-derived' specs/memory/product/sdd/bug-ledger.md | grep -vc 'bugs.py fix'` prints `0`. `bug-ledger-lessons.md` does not exist at this head.
    - F131 is re-dispositioned `resolved` by `audit.py disposition`, citing 995a39897 and 0177; its deferral reason was false. Check: `grep 'F131"' specs/audits/20260930-structural-convergence/FINDINGS.jsonl | grep -c '"disposition": "deferred"'` prints `0`.
    - rc-8 TASKS' AC map omits AC9.1 → 198. rc-8 stays closed (0150), so the carry mark lives here, in AC5.9. Check: `git diff 767ba1d4f -- specs/releases/0.5.0/rc-8 | wc -l` prints `0`.
- AC6.2 `_RELEASE.json` logs rc-8 G1's readouts at start and end, each job's bug-surface delta, and throughput against the grill's rc-8 baseline (75 % process commits, parallelism 1.3, median task lead 1.1 h, ~81 review rounds in 26 h, gate 1 ~6 min); AC1.7's comparison and the parallelism readout of §How rc-9 runs (target ≥ 2 against 1.3), met or missed, gating nothing.
- AC6.3 Each proposed ADR below is accepted or rejected by the operator; its `measured_by` names a check this rc built, repaired in the 0138 lane where a name moved.
- AC6.4 Closure per the releases law; rc-10 defined beside it (Q20).

## Proposed ADRs (`proposed`; ids from 0190, tentative)

Each is accepted before a push deletes a law line it governs (0151 M3): 0190–0192 before Job 1's push.

- 0190 "Gates per task, stage and job; one review per job; the task is the dispatch unit" (demolition (a), (c), (e)). Supersedes 0185's full command at every merge. `measured_by`: AC1.1, AC1.2, AC1.4 cases.
- 0191 "One worktree tree per job; no kind allowed sets" (demolition (b)). Supersedes 0106; amends 0124 (specs writes land in a job, `define` or `backlog` worktree), 0125 (no task worktree; one `define` per rc). `measured_by`: AC1.3 cases.
- 0192 "Closure is the Reconciliation job; an atom and its derived sections land in one merge" (demolition (d)). Amends 0148: closure in a release worktree, the release kind's law copies, the cross-worktree derived hash leave. Replaces the rejected 0189. `measured_by`: AC1.5's case.
- 0193 "An rc is an Implement: a DAG of ≤ 8 jobs, Job 1 fixed; jobs hold stages, stages hold tasks". Amends 0152 (2): ≤ 8 jobs; the 12 KiB TASKS recommendation reads per job file. `measured_by`: AC4.2's job-count and Job 1 rows.
- 0194 "SPEC says what, PLAN draws the DAG, TASKS runs per job; task state derived, done once per job". Supersedes 0141. `measured_by`: AC1.9, AC1.10, AC4.1–AC4.3 cases.
- 0195 "An rc has closed scope; a block-list bug is a hotfix; any other waits for the next Job 1". Amends 0019: no bug fixed "at once" off the block list; rc N+1 defined while rc N implements. `measured_by`: AC5.6's cases; every `fix(bugs)` body names `block:`.
- 0196 "Closed stage contract, live tasks; each AC names its test level; stage 1 writes every RED". `measured_by`: AC4.2's stage-1 row; AC1.2's branch-policy rows; "each AC names its test level" by `dd-audit-project` Pillar 2 (audit-measured, per "Skill + auditoria (Recommended)").
- 0197 Amends 0149: tasks run parallel inside one stage with disjoint `W:`; jobs with disjoint envelopes or an edge; (3) becomes the hotfix. `measured_by`: AC4.2's stage `W:` overlap row.
- 0198 Amends 0186 (2), (5): a fix-induced bug stops work only on the block list; the verdict per 0190. `measured_by`: AC1.2's matrix case; the next audit's `PILLAR-BUGS`.
- 0199 Amends 0187 (1): a Draft `rc-<N+1>/SPEC.md` added while rc N implements does not move `found_in`. `measured_by`: an append after rc-10's Draft add, before rc-9 closes, stamps `rc-9`.

## Replaces

- Gate 1 (the full `ci.py` per merge); a review per merge; one `verify:` for every kind (AC1.1–AC1.4).
- Kinds `release`, `impl`, `bug`, their allowed sets and `<M.m.p><letter>-<kind>` grammar; the worktree per task and its cap of 5; fixed-depth path readers; unpushed worktree branches; the `verify:` line's `shell=True` run (AC1.2, AC1.3).
- The 9-step closure and its cross-worktree atom ↔ derived-docs coupling (AC1.5); micro-dispatch (AC1.6).
- One `TASKS.md` per rc, `[-]`, start and per-task done commits, the Parallel schedule (AC1.8–AC1.10).
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
