# PLAN — Release: 0.5.0, candidate 23

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR9; `AC<n>.<k>` belongs to FR`<n>`); this PLAN records the as-is review (section 1), the DAG of seven jobs in four waves (the DAG heading), how to dispatch them and what each costs (section 2), the acts that are not tasks (section 3), the consumers of every rebuilt grammar and name (section 4), the sequencing hazards (section 5) and the rulings carried (section 6). Task files: `tasks/job1.md` to `tasks/job7.md`. Paths are repository-relative to `repos/dadaia-workspace/`.

**Evidence.** The as-is review is `dd-sw-engineer-sr`'s read-only pass of 2026-10-24 at `origin/feature/0.5.0` (rc-22 tip); its full text is the appendix of this PLAN, copied from `.dadaia/tmp/dd-sw-engineer-sr/20261024/eval-pipeline/as-is-and-options.md`, with the measured readouts of its section 1.3. Where the appendix and the SPEC disagree, the SPEC wins: the appendix predates the operator's grill, and its OpenCode material (its sections 4, J5, Q4, Q5) is out of scope (SPEC section 3). Every ledger count below is the id-line query `git log -E --grep '^(fix|refactor)\(bugs\):' -- <file>` at the `wt-rc` HEAD, never `fix_files`. Measured on the define tree on 2026-10-24 with the workspace venv: `scripts/guards/run.py` 21.5 s, `scripts/guards/run.py --planted` 26.7 s (219 rows), `tests/e2e/test_evals_scripts.py` 23 rows in 0.90 s, `tests/scripts/guards/test_repo.py` 6 rows in 1.33 s. The `ci.py job` figure of about 73 s is the main thread's brief; the rc-22 audit measured 74.3 s. Every size is an estimate and labelled unmeasured; the pipeline runtime is an estimate (section 2).

**Rulings carried.** The SPEC's R0 to R6 (the grill handoff `2026-10-24T035818Z-main-thread-grill-eval-pipeline`): Claude Code and Codex gate, OpenCode follows the operator's validation; the check is required on the promote PR; the ChatGPT login stays; the wheel is shared; the grader self-tests are read, not rerun; no grader or task changes. ADR 0274 (candidate-only), ADR 0217 (2) (one decider, applied per job), ADR 0277 (2) (the allowed set) and ADR 0279 (only a subagent-keyed harness is judged by the product, so AC4.2 is Codex's only guard) bind the work. ADR 0281 is proposed (Job 2); its acceptance is the operator's (section 3).

## 1. As-is review

One row per touched unit, DELETE, REBUILD, UPDATE, KEEP, ADD last. A unit is REBUILD-due when a child bug landed after its last REBUILD (ADR 0280 clause 4): none is, on this surface. The REBUILD verdicts below are the demand-changes-its-fundamental-behaviour trigger (`dd-release-definition` section 2). The eval surface has two closed bugs, both an instruction-and-grader divergence in T3 (`t3-grader-requires-an-active-backlog-entry`, `t3-instruction-omits-backlog-demand`, caused by `J7.T3` of rc-22): the lesson carried is that a harness variant changes only the harness label and never the instruction-and-grader contract (R06, R07).

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| **R01** `.github/workflows/eval.yml` (50 lines) | one job `eval`: one harness, one secret at job env, the wheel built in-job, `-n 2` over nine trials, compare, scan, summary and upload in one runner | 1 id-line commit (`cf063d8c8`, the version-label REBUILD of two lines); 0 children after it | REBUILD | question: *which stages run, with which secret each, and what concludes the run*. The demand changes the shape (prepare, six legs, aggregate, result). The single job, its job-env secret, its in-job wheel build and its `-n 2` leave with it. Tasks J6.T3 to J6.T5 |
| **R02** `evals/scripts/compare.py` (68 lines) | floors keyed by task only, a table with no harness axis and no interval; the forged-verdict check reads Claude transcripts only, so a Codex trial is never zeroed | 1 id-line commit (`cf063d8c8`, the same label REBUILD); `ea8875e8b` added the forged check (rc-22 FR13, not a bug) | REBUILD | question: *which trials pass for which (harness, task), and which verdict acts are forged*. One identity table per harness replaces the Claude-only `reviewer`/`forged` pair; the leg and the table share the floors and the statistics. Net lines grow by the harness axis, the demand. J3.T1 to J3.T4 |
| **R03** `evals/scripts/scan.py` (27 lines) | one plain-text `SCAN_SECRET` plus `sk-ant-[\w-]{20,}` | 0 | REBUILD | question: *what values must no uploaded file hold*. One needle becomes a needle set (JSON leaves, key and JWT shapes, account ids). J3.T5, J3.T6 |
| **R04** `scripts/guards/repo.py` `no_model_calls_in_ci`, its helpers `:162-307` and its planted rows `:913-1100` | judges every `eval.yml` job as the one job: `actions/download-artifact@` is `action-prefix-lookalike`, a wheel upload is `upload-other-path`, any job without the scan line is `summary-unscanned`; `_cli_pin` reads only the workflow `env` | 9 id-line commits on the file, none a child after the eval rule's last touch (`cf063d8c8`); 34 commits in all | UPDATE | the rules hold per job; only what the multi-job shape needs changes (SPEC AC8.1, AC8.2); no planted row is deleted or loosened (AC8.3). J6.T1, J6.T2, and the anchors in J6.T3 to J6.T5 |
| **R05** `.github/workflows/ci.yml`, `.github/required-checks.json` | no job reads an eval result; `required-checks-listed` demands every PR job be listed | `ci.yml` 10 id-line commits, `required-checks.json` 1 (`fd7c96fb2`); none on a job like this one | UPDATE | one model-free job and one list entry are the whole gate (SPEC AC5.1, AC5.3); the heavier options, a `release.yml` job or both, were weighed in the appendix section 5 and not chosen. J7.T4 |
| **R06** `evals/tasks/**` (instructions, `project.sh`, Dockerfiles, `task.toml`, graders) | harness-neutral graders; two lines name the harness (T1 `instruction.md:1`, T2 `environment/project.sh:45`) | `project.sh` 2 id-line commits (the version-label REBUILDs); instruction 0; the T3 pair above | KEEP | no tracked task file changes (AC3.2); the variants are rendered outside the tree (R07) |
| **R07** `evals/scripts/render.py` + `tests/e2e/test_evals_render.py` | none | none | ADD | no unit can carry it: the two tokens live in task files that must stay untouched. About 25 lines. J4 |
| **R08** `evals/scripts/preflight.py` | none | none | ADD | no unit can carry it: `scan.py` cannot (guard `scan-wrong-path` refuses any `run` holding `scan.py` that is not the canonical line); about 25 lines. J3.T6 |
| **R09** `evals/scripts/gate.py` + `tests/e2e/test_evals_gate.py` | none | none | ADD | the one reader of "may this PR deploy"; about 60 lines. J7 |
| **R10** `evals/RESEED.md` | none (the re-seed steps live only in the operator's head) | none | ADD | AC6.2's one doc home, named by the preflight error. J5 |
| **R11** `tests/e2e/test_evals_scripts.py` (123 lines) | scan exit codes, floors, forged rows built from a Claude transcript | 1 id-line commit (`cf063d8c8`) | UPDATE | gains harness-keyed floors, a Codex rollout fixture, the statistics literals, the needle rows and the preflight rows; the existing rows keep their expected exits (hazard H1). J3 |
| **R12** `tests/e2e/test_evals_t1.py`..`t3.py`, `tests/helpers/evals.py` (grader self-tests) | oracle and null rows against built images; run by `E2E Python` on every PR (184 s, CI run 40049028058) | the T3 pair | KEEP | the pipeline reads that check on its sha and never reruns it (AC1.2, root map section 1) |
| **R13** `.github/workflows/release.yml` | `release-gate` approval is the human read | 0 on this surface | KEEP | SPEC non-goal; ADR 0178 (4) keeps the human read |
| **R14** GitHub Environment `evals` and its secrets | branch policy `feature/*` and `main`; `CLAUDE_CODE_OAUTH_TOKEN`, `CODEX_AUTH_JSON` present (read through the API on 2026-10-24) | none | KEEP | operator-owned; a PR ref cannot read it, which is why the gate only reads a run (appendix section 5) |
| **R15** ADRs 0178, 0217, 0225, 0269, 0274, 0277, 0279 and `specs/ADRs/decisions.jsonl` | the manual read is the gate (0178 (4)); the Eval gate status is deferred to 0.6.0 (0269 (c)); 0225 (a Codex lane) is proposed | none | ADD 0281 | the record is committed in the define step (Job 2); the relations are written by the operator's acceptance commit. No ADR is edited |
| **R16** memory: `specs/memory/product/distribution/agent-evals.md`, `QUALITY.md` P-33 and `:48`, `pypi-distribution.md:27`, `ARCHITECTURE.md` ADR list, the atoms the session-check hotfix left stale | state "one dispatch-or-schedule workflow", the Claude-only transcript rule (`agent-evals.md:19`) | none | UPDATE | the closure act of `dd-product-engineer` (FR9, `MEMORY-UPDATE.md`), never a task (`release.py check` refuses `specs/memory` in a `W:`) |
| **R17** the three consumers of this rc's backlog: `eval-codex-lane-in-library-ci`, `release-approve-requires-evals-gate`, `evals-benchmark-lanes` | `idea` entries that describe pieces of this pipeline | none | KEEP | their disposition is the main thread's operator-gated intake (section 3), never a task |
| **R18** `scripts/ci.py` `JOBS` and the `verify:` line | `ci.py job` is lint, typecheck, guards, unit-fast, doctor; `E2E Python` runs `tests/e2e` | 10 id-line commits on `ci.yml`, none about the gate | KEEP | gates are settled law; no step is added to it |
| **R19** the Codex T3 stop: root map lines 9, 50 and 54 (`dadaia_workspace/public/data/AGENTS.md`) | after the hotfix, line 9 no longer says "its next act is Operator action: relaunch…", but still opens "the agent session launches at its root, always", and lines 50 and 54 still name relaunching | the hotfix chain `d5394fbdd`, `b1b5a0f9c`, `1857ae8ba` (rc-22 window, judged KEEP in the SPEC) | KEEP, pending Job 1 | whether the new text still stops Codex is unknown; Job 1 answers it by observation, and no floor moves |

### 1.1 Authorities

One row per touched question, one authority each; `consults` calls the authority, `deleted` leaves with the row's task.

| question | authority | consults | deleted |
|---|---|---|---|
| which (harness, task) pairs pass, and their floors | `evals/scripts/compare.py` (the floor table and the statistics) | `--table` reads the legs' `leg.json`; the workflow only runs it | the floors keyed by task only; the table with no harness axis |
| is a verdict act forged, per harness | `compare.py`'s identity table (`claude-code`, `codex`) | the leg mode; ADR 0279 states the law it enforces where the product does not | the Claude-only `reviewer` and `forged` pair |
| which values no uploaded file may hold | `evals/scripts/scan.py` (the needle set) | `preflight.py` reads the same value only to check it is non-empty and, for Codex, JSON | the one plain needle |
| may this PR into `main` deploy | `evals/scripts/gate.py` | `ci.yml` job `Eval gate`; the `release-gate` approval stays the human read | the manual read as the only gate (ADR 0178 (4), ADR 0269 (c)'s deferred status) |
| which model-call shapes are allowed in CI | the guard `no-model-api-in-ci`, per job | `eval.yml` | the single-job assumptions (`_ACTIONS`, `_UPLOADED`, `summary-unscanned` for every job) |
| the CLI version of a harness | Claude Code: `env.CLAUDE_CODE_VERSION` in `eval.yml`; Codex: its matrix row | the guard `eval-cli-pin` (Dockerfile `ARG`s, the Claude row, a row's `version`) | none |
| which tracked task text carries a harness label | `evals/scripts/render.py` (two tokens) | the Codex legs | none |
| what the candidate wheel is | the `prepare` job's artifact and sha256 | every leg compares its download to the output | the wheel built in the leg's own job |

## DAG

One job per node; a wave opens when the previous wave has merged into the `wt-rc` (SPEC section 4, wave ranking). The `W:` of each row is the exact union of its job file's tasks. Waves 1 and 2 hold jobs with disjoint `W:`, which run together; Jobs 6 and 7 are serial inside.

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | - | 1 | `specs/releases/0.5.0/rc-23/tasks/job1.md` |
| Job 2 | - | 1 | `specs/ADRs/decisions.jsonl` |
| Job 3 | Job 2 | 2 | `evals/scripts/compare.py` `evals/scripts/scan.py` `evals/scripts/preflight.py` `tests/e2e/test_evals_scripts.py` |
| Job 4 | Job 2 | 2 | `evals/scripts/render.py` `tests/e2e/test_evals_render.py` |
| Job 5 | Job 2 | 2 | `evals/RESEED.md` |
| Job 6 | Job 3, Job 4, Job 5 | 3 | `.github/workflows/eval.yml` `scripts/guards/repo.py` `tests/scripts/guards/test_repo.py` |
| Job 7 | Job 6 | 4 | `evals/scripts/gate.py` `tests/e2e/test_evals_gate.py` `.github/workflows/ci.yml` `.github/required-checks.json` |

Edges and why. Job 3, 4 and 5 wait on Job 2 only because the SPEC ranks the law first; no byte of Job 2 is read by them. Job 6 waits on Jobs 3 to 5 because the workflow runs `compare.py`, `scan.py`, `preflight.py`, `render.py` and names `evals/RESEED.md`; it also needs ADR 0281 accepted (an operator act, section 3), which is not an edge a merge can carry. Job 7 waits on Job 6 because the gate reads the run that Job 6's workflow produces and the SPEC ranks it last among the features. Job 1 has no dependent: its answer decides whether goal 2 can go green on the run on E. No two jobs of a wave share a path; the guard `release.py check` refuses an overlap.

Task counts: Job 1 has 2, Job 2 has 1, Job 3 has 6, Job 4 has 2, Job 5 has 1, Job 6 has 5, Job 7 has 4: 21 tasks, 14 `sr` and 7 `jr`. Every behaviour with a statable test is a RED task then an implementation task; DELETE and REBUILD tasks precede ADD tasks inside a job (Job 3: the REBUILDs of `compare.py` and `scan.py` come before `preflight.py`, which rides J3.T6).

AC map. AC1.1 to AC1.3: J6.T3 (the preflight script: J3.T5, J3.T6). AC2.1 to AC2.4: J6.T1 to J6.T3. AC3.1: Job 4. AC3.2: no job touches `evals/tasks/*/tests/`; the reviewer reads `git diff --name-only`. AC4.1 to AC4.3: J3.T1 to J3.T4. AC4.4: J6.T4. AC4.5: J3.T5, J3.T6. AC4.6, AC4.7: J3.T3, J3.T4, J6.T5. AC5.1 to AC5.3: Job 7. AC6.1: J6.T4. AC6.2: Job 5. AC7.1: Job 2. AC8.1 to AC8.3: J6.T1, J6.T2. AC9.1: closure (section 3). Goals 1 to 3 and 5: the run on E (section 3); goal 4: Job 7 and the operator's branch-protection act.

## 2. Jobs, sizes and dispatch

Sizes are estimates, unmeasured. The job gate is the repo `verify:` line, `python scripts/ci.py job` (about 73 s; `guards` and `guards --planted` are 48 s of it, measured), unchanged by this candidate: no preflight before review, no step added to it, never the full CI line. Each task's definition of done is that line plus the test directories its change reaches (the job files name them).

| job | tasks (sr / jr) | new lines (estimate) | `verify:` per task | reached tests, measured or estimated |
|---|---|---|---|---|
| Job 1 | 2 / 0 | none (readout) | none: no code | none; a local Codex T3 re-run by the main thread, about $0.32 notional and 5 min (trial figures of the 2026-10-24 readout) |
| Job 2 | 1 / 0 | 1 ledger line (done) | none: ledger line | `doctor` `LEDGER-ADR-SCHEMA`, run on the define tree: 0 hits |
| Job 3 | 3 / 3 | about 240 test, about 220 source | 73 s | `tests/e2e/test_evals_scripts.py`: 0.90 s for 23 rows (measured), a few seconds after the new rows (estimate) |
| Job 4 | 1 / 1 | about 40 test, 25 source | 73 s | `tests/e2e/test_evals_render.py`: a second or two (estimate) |
| Job 5 | 1 / 0 | about 40 doc lines | 73 s | none (AC6.2) |
| Job 6 | 4 / 1 | about 90 test, 40 source, 10 planted rows, about 150 YAML | 73 s; each added planted row adds about 0.12 s to `guards --planted` (26.7 s over 219 rows, derived) | `tests/scripts/guards/test_repo.py`: 1.33 s for 6 rows (measured) |
| Job 7 | 2 / 2 | about 120 test, 60 source, 20 YAML | 73 s | `tests/e2e/test_evals_gate.py`: a few seconds (estimate) |

**Dispatch.** The `wt-rc` define commits come first; then wave 1: Job 1 T1, with the main thread's re-run between T1 and T2. Wave 2: Jobs 3, 4 and 5 together, at most 4 agents. Inside Job 3 the chain is T1, then T2 with T3, then T4 with T5, then T6 (T2 and T3 differ in file, as do T4 and T5). Wave 3: Job 6, serial T1 to T5. Wave 4: Job 7, serial T1 to T4. About 15 task-hours in a chain, an estimate counted from the serial stages (2 in wave 1, 4 in Job 3, 5 in Job 6, 4 in Job 7) at about an hour each. One `dd-code-reviewer` review per job merge.

**Cost and gate.** No gate, lock, repo, layer or review round is added beyond the SPEC's `Eval gate` job. It runs only on a PR into `main` and costs about 15 s there (one `gh` call and one `git diff`; an estimate, unmeasured). The pipeline replaces the manual read as the deploy gate and deletes the single-job `eval`. It does not rerun the grader self-tests, which cost 184 s (measured, CI run 40049028058): `prepare` reads their check run in one API call.

**The new pipeline's runtime (estimate).** About 18 min wall per run: `prepare` about 0.5 min, the slowest leg (T3 on Claude: 15.3 min trial time plus about 1 min setup), `aggregate` about 0.5 min, with six legs concurrent. The sources: trial `result.json` timestamps of run 40050879271 (appendix section 1.3) and the SPEC's own estimate. It is not measured: the runner concurrency limit and the Claude OAuth rate limit across concurrent legs are unverified, so the first run on E measures it. Today's single job is 36.9 min (run 40050879271, measured) and 31.05 min (run 39462036716, measured). Model cost per run: Claude Code $16.29 and Codex $1.49 notional (measured, harbor `cost_usd`).

## 3. Acts that are not tasks

- **The operator question, one, before Job 6 merges.** (a) Accept ADR 0281 and reject ADR 0225 as subsumed; the main thread writes the `ruling` and the two relations in the `docs(adr): accept` commit (`supersedes` `0269,0277`, `amends` `0217`). (b) Branch protection: once the run on E is green and `Eval gate` has run once, the operator adds `Eval gate` to `main`'s required status checks (ADR 0078), with the one `gh api` command the main thread hands over. Both are operator acts the roles cannot take (`specs/ADRs/AGENTS.md` section 2).
- **The Job 1 re-run.** After J1.T1 merges, the main thread runs the local Codex T3 re-run described in `tasks/job1.md` and hands J1.T2 its output directory.
- **The run on E** (goals 1 to 3 and 5). After the last commit that touches a path outside the allowed set of ADR 0277 (2) (so after the reconcile that carries the memory pass), the main thread dispatches `eval.yml` on the work branch (`gh workflow run eval.yml --ref feature/0.5.0`) and watches it to green (the watch-ci rule). The result and E are recorded in `_RELEASE.json`'s `log` (allowed after E). A red leg is rerun alone (`gh run rerun <id> --failed`).
- **Closure** (FR9): the memory pass of `MEMORY-UPDATE.md` for R16; `release.py` closure verbs.
- **Intake.** Dispositions of the backlog entries in R17 are the main thread's operator-gated intake. `dd-sw-engineer-sr` proposes: `eval-codex-lane-in-library-ci` delivered by the Codex legs, `release-approve-requires-evals-gate` superseded by `Eval gate`, `evals-benchmark-lanes` kept. The OpenCode backlog entry already exists (SPEC section 3).
- **Arm B.** A finding of J1.T2 that the Codex stop is a product contract break goes to the operator as a `bug-proposal:`; it is never part of this release's gate wiring.

## 4. Pre-mortem consumers

A read-only `dd-researcher` pre-mortem precedes the SPEC approval (`dd-release-definition` section 2); the consumers below were swept by `dd-sw-engineer-sr` at definition with `git grep` over this repo and the other eight repos of the workspace (0 hits in any of them for `evals/scripts/(compare|scan)` and `eval\.yml`), and each answer is a task.

| name or grammar changed | consumers (hit count in this repo, ledgers excluded) | answer |
|---|---|---|
| `compare.py` invocation and its Markdown table | `eval.yml` (2), `tests/e2e/test_evals_scripts.py` (3), `agent-evals.md` (1) | the leg mode keeps `compare.py DIR` (existing rows run unchanged but for `agent_info`, H1); the workflow call is rewritten in J6.T3 and J6.T5; the atom at closure (R16) |
| `scan.py` and `SCAN_SECRET` | `eval.yml` (1), the guard `_SCAN` constant (10 hits in `repo.py`), `tests/e2e/test_evals_scripts.py` (3 + 4 env uses) | the name and the canonical line `python3 evals/scripts/scan.py evals/jobs evals/summary.md` do not change; the needle set is internal |
| the job id `eval`, the artifact `jobs` and the output path `evals/jobs/cand` | `eval.yml` (2), `repo.py` planted-row anchors (about 45 rows, 16 on `evals/summary`) | each anchor is kept or re-pointed in J6.T3 (H2); the artifact becomes `jobs-<harness>-<task>`, read by `aggregate` only |
| the floors `{t1: 3, t2: 2, t3: 2}` and ADR 0277 (1), 0274 (5) | `compare.py`, the ADR text, `agent-evals.md` | the floors do not change; they apply to both harnesses (SPEC AC4.7) |
| the required-checks list | `required-checks-listed` (1 guard), branch protection | J7.T4 adds the entry and the job together; the operator applies protection (section 3) |
| `CLAUDE_CODE_VERSION` and the task Dockerfiles | `eval.yml`, 3 Dockerfiles, the guard `eval-cli-pin` (3 hits in `repo.py`) | unchanged; the guard gains matrix rows (J6.T2) |

## 5. Sequencing hazards

- **H1. The existing floor rows lack `agent_info`.** `_job` in `tests/e2e/test_evals_scripts.py` writes no `agent_info`, and the new leg exits 1 on an unknown harness. J3.T1 adds `agent_info.name` to that helper, a fixture change that keeps every expected exit, named in its commit; no assert is moved or loosened.
- **H2. Planted-row anchors.** About 45 rows of `repo.py` are anchored on literal text of today's `eval.yml`; `_edit` raises `plant anchor lost` when one disappears. J6.T3 keeps each anchor at least once or re-points the row in the same commit; J6.T4 and J6.T5 re-run `scripts/guards/run.py --planted` before committing.
- **H3. Guards green at each merge.** `ci.py job` runs `guards --planted` at every task merge, so the guard widens (J6.T2) before the workflow is rewritten (J6.T3), and the two never merge apart.
- **H4. `scan-wrong-path`.** Any `run` that holds `scan.py` and is not the canonical line is refused, so the preflight is its own script and `scan.py` takes no verb.
- **H5. Credentials.** Harbor's agent env falls back to all of `os.environ` (harbor 0.23.0 `agents/installed/base.py:642-649`), so a leg reads exactly one secret expression at job level; the ChatGPT refresh token rotates (measured: `last_refresh` renewed by age after 8 days), so a Codex leg can go red until the secret is re-seeded (`evals/RESEED.md`).
- **H6. The YAML has no test below the run on E.** The lowest-level tests of the workflow are the guard's canonical-shape rows (J6.T1) and planted rows (J6.T2); a defect first seen on E is fixed by the red-CI loop, not by a new gate. Each dispatch is one pipeline run (about $17.78 notional, section 2).
- **H7. `E2E Python` runs `tests/e2e` on every PR.** The three eval test files add seconds, not minutes (0.90 s measured for 23 existing rows), and each carries its `Owner:` line (the guard `tests-mirror-the-package`).
- **H8. Variant drift.** The render fails on a token that is absent, so a reworded instruction cannot drift unseen (the T3 bug pair).
- **H9. The Codex CLI pin.** `0.145.0` refuses `openai/gpt-6.1-sol`; the workspace host has `0.164.0`; the matrix pins `0.163.0`, the version measured working on the readout. The pin is a matrix literal with one owner; the guard checks it exists.
- **H10. E is invalidated by any later commit outside the allowed set.** A memory atom, a doc or a source file changed after E fails `Eval gate` and costs a new pipeline run. The run on E therefore follows the reconcile (section 3), and any later rc that changes code needs its own run.
- **H11. Codex T3 may stay red.** Goal 2 needs T3 at least 2 of 3 on Codex; the local readout is 0 of 3. Job 1 may end in an Arm B proposal; no floor moves, and goal 2 stays red until the cause is fixed or ruled.

## 6. Rulings carried

Operator: R0 to R6 of the grill handoff, restated in SPEC section 1. By law: ADR 0274 (1) and (5); ADR 0217 (2); ADR 0277 (2); ADR 0279; the root map section 1 gate-cost clause (no new gate, no step that reruns a merge check, a heavier option never the recommended one). Main thread, in the dispatch of this definition: Job 1 is read-only and asks the main thread for one local run; graders and tasks stay untouched; the memory pass is the closure's and not a job; the ADR proposal commit is `docs(adr): propose multi-harness-eval-deploy-gate`, in the define step, before the jobs that depend on it (Job 2).

Decisions this PLAN takes where the SPEC is silent, for the operator's PLAN approval: (1) the wheel upload is not a publish for the guard (`tasks/job6.md`); (2) a leg fails on its own floor, so a rerun of the failed leg alone is possible; (3) harbor retries with `--max-retries 2` over the eight listed exception types; (4) a leg's output sits at `evals/jobs/<harness>/<task>/`; (5) `result` is a three-result check kept because SPEC goal 1 names a final result job, and a reviewer may fold it into `aggregate` at no loss since the run conclusion already fails on any red job; (6) the Claude matrix row repeats `2.1.284` and the guard checks it equals `env.CLAUDE_CODE_VERSION`, because the `env` context is not available in `strategy`.

## Appendix — the as-is file in full

Copied verbatim from `.dadaia/tmp/dd-sw-engineer-sr/20261024/eval-pipeline/as-is-and-options.md` (written 2026-10-24, before the grill); its headings are demoted by two levels. The SPEC's rulings supersede its sections 7 and 8 and all OpenCode material.

### Agent-eval CI pipeline as the deploy gate — as-is review and design options

Author: dd-sw-engineer-sr, 2026-10-24. Read-only on `repos/dadaia-workspace` at `origin/feature/0.5.0` (rc-22 tip, wheel label `0.5.0rc22`). Feeds the rc-23 SPEC after the operator's grill. No repo change was written.

Arm A (feature). Bug-history read first (permanent-architecture rule): the eval surface has two closed bugs, both an instruction/grader divergence in T3 (`t3-grader-requires-an-active-backlog-entry`, `t3-instruction-omits-backlog-demand`, caused_by `J7.T3`). Lesson for section 3: a harness variant must change only the harness label, never the instruction/grader contract. `compare.py` was last rebuilt by `ea8875e8b` (forged-verdict zeroing, R71). The eval files total about 430 lines of source plus 4 grader files; the redesign below adds about 250 lines (new scripts and a workflow) and deletes about 40 (single-harness assumptions), so it does not shrink the feature. Every added line is justified by a new axis the demand names (harness, gate).

Labels: **measured** = read from a named source; **estimate** = derived arithmetic, not run; **unverified** = could not be checked locally.

---

#### 1. As-is

##### 1.1 Files, what each fixes in place, what a redesign must change

| unit | `path:line` | today | what it fixes in place (redesign must change) |
|---|---|---|---|
| Workflow | `.github/workflows/eval.yml:1-51` | One job `eval` (`:15`), `harbor run -p evals/tasks -a claude-code -m anthropic/claude-sonnet-5 --ak version=$CLAUDE_CODE_VERSION -k 3 -n 2` (`:37`), then compare (`:40`, `continue-on-error`), scan (`:42`), summary (`:43`), upload (`:44-49`), exit 1 on compare failure (`:50-51`) | one harness, one model, one secret at job env (`:19-21`), one job, triggers dispatch and weekly cron only (`:5-8`), env pin `CLAUDE_CODE_VERSION` (`:13`) read by the `eval-cli-pin` guard, Environment `evals` (`:17`), wheel built in-job (`:29-30`), wheel copied into every task's `environment/lib/` (`:36`) |
| Compare | `evals/scripts/compare.py:14-15` | `TRIALS = 3`; `FLOOR = {t1 3, t2 2, t3 2}` keyed by task only | no harness axis; floors identical for all; table has no harness column; no interval |
| Forged-verdict check | `compare.py:18-38` | reads `agent/**/*.jsonl` as Claude Code transcripts: subagent identity = sibling `*.meta.json` `agentType == "dd-code-reviewer"` and parent dir `subagents` (`:21-24`); the act = assistant `Bash` tool_use whose `command` holds `verdict.py` and `--verdict` (`:34-36`) | Claude-layout only: on a Codex trial no line has `type == "assistant"`, so it never zeroes: a silent pass (a forged verdict on Codex would count) |
| Scan | `evals/scripts/scan.py:84-85` | one `SCAN_SECRET` value plus `sk-ant-[\w-]{20,}` | one secret, plain text; Codex `auth.json` is a JSON of several token values (id/access/refresh) and the account ids; the OpenAI key shape and JWT shape are not scanned |
| Guard | `scripts/guards/repo.py:162-307` (`no_model_calls_in_ci`) | judges every `eval.yml` job: triggers dispatch/schedule only (`:51,181-195`); exact hosted runner (`:198-220`); secret only in job `env`; actions allowlist `actions/checkout@`, `actions/upload-artifact@` only (`:57,198-220`); EVERY job must carry the canonical scan line `python3 evals/scripts/scan.py evals/jobs evals/summary.md` (`:54,265-282`, rule `summary-unscanned` when absent) and upload only `evals/jobs/`, `evals/summary.md` (`:56`); `_cli_pin` reads workflow `env.CLAUDE_CODE_VERSION` (`:285-293`) | single-job shape: a `prepare` job without a scan trips `summary-unscanned`; `download-artifact` trips `action-prefix-lookalike`; a wheel artifact path trips `upload-other-path`; `workflow_call` trips `trigger-other` (so no reusable eval workflow) |
| Guard planted rows | `scripts/guards/repo.py:913-1100` | about 45 planted edits anchored on literal eval.yml text: `runs-on: ubuntu-24.04`, `      - run: pipx install poetry`, `    environment: evals\n`, `actions/upload-artifact@043`, the scan line, `cat evals/summary.md >>`; `_edit` raises `plant anchor lost` when an anchor is gone (`:840-841`) | every anchor must survive in the new workflow, or the row is re-pointed (cheap: same text appears in each job) |
| Required checks | `scripts/guards/repo.py:680-690` (`required-checks-listed`), `.github/required-checks.json` | every job of a workflow with a `pull_request` trigger must be listed | eval.yml has no PR trigger (guard forbids it); a PR-visible gate must live in `ci.yml` and be added to the list |
| Task T1 | `evals/tasks/t1-cold-onboarding/instruction.md:1` | names "for the Claude Code harness" | the only harness-specific word in T1 |
| Task T2 | `evals/tasks/t2-block-list-bug/environment/project.sh:45` | `dadaia init /workspace --harness claude --repo file:///srv/demo.git` | the only harness-specific line in T2; baked into the image at build |
| Task T3 | `evals/tasks/t3-discovery/instruction.md` | names no harness | none |
| Dockerfiles | `evals/tasks/*/environment/Dockerfile:2-5` | `ARG CLAUDE_CODE_VERSION=2.1.284`, `npm install -g @anthropic-ai/claude-code@…`; last layer `COPY lib/` (the run's wheel) | pin ties image to the Claude CLI (guard `eval-cli-pin`); harbor installs Codex/OpenCode itself at run time (`--ak version=`), so no image change is needed for them |
| Graders | `evals/tasks/*/tests/test_grade.py`, `test.sh` | read workspace state through the installed CLI and git; none reads the agent harness | harness-neutral already; T2's grader reads `/opt/eval/base` and the repo, not transcripts |
| Grader self-tests | `tests/e2e/test_evals_t1.py`, `test_evals_t2.py` (oracle: planted correct fix passes `:30-33`; null/assert-rewrite rows fail), `test_evals_t3.py`, `tests/helpers/evals.py:26-63` (`HAND`, `ONBOARDED_T3`… typed with `--harness claude`) | docker images built from `environment/` + this checkout's wheel; run in `ci.yml` job `E2E Python (pytest)` (`ci.yml:270-299`, `scripts/ci.py:62-66`) on every PR and push | already a required check on every PR; **measured** job wall 184 s (CI run 40049028058); a docstring records the whole suite at 95 s (run 37554712931) |
| Script tests | `tests/e2e/test_evals_scripts.py:44-123` | scan exit codes, compare floors, forged-verdict rows built from a Claude transcript fixture (`_transcript`, `:101-111`) | gains harness-keyed floors and a Codex rollout fixture |
| Release | `.github/workflows/release.yml:96-109` | `approve` (environment `release-gate`, required reviewers) echoes "approved"; no reference to evals anywhere in release.yml | the manual read is the whole gate; ADR 0269 (c) deferred an `evals/gate` status |
| CI | `.github/workflows/ci.yml:11-23` | triggers push `main`/`develop`/`feature/**`/`wt/**`, `pull_request` to `main`/`develop`, `workflow_call` (used by release.yml `:54-60`) | place for a model-free `Eval gate` job |
| Environment | GitHub API (measured 2026-10-24) | Environment `evals`: branch policy `feature/*` and `main` (not `develop`, not PR refs); secrets `CLAUDE_CODE_OAUTH_TOKEN` (2026-10-07), `CODEX_AUTH_JSON` (2026-10-24); `main` and `develop` require 18 contexts, `strict: true` on main | a `pull_request` job could not read `evals` secrets (ref `refs/pull/N/merge` matches no branch policy) |
| Memory | `specs/memory/product/distribution/agent-evals.md:5,14-22`; `specs/memory/QUALITY.md:27` (P-33), `:48`; `specs/memory/product/distribution/pypi-distribution.md:27`; `specs/memory/ARCHITECTURE.md:223,233,275,280,283` | state "one dispatch-or-schedule workflow", "a gated task below its floor", the Claude-only transcript rule (`agent-evals.md:19`) | atoms rewritten at closure (shape 9) |

##### 1.2 ADR clauses (all in `specs/ADRs/decisions.jsonl`)

| ADR (line) | status | clause | effect on the redesign |
|---|---|---|---|
| 0178 (`:178`) | accepted | (1) eval dispatched on the evaluated sha before the promote PR merges; (4) the operator reads the verdict from the job summary and logs it in `_RELEASE.json`; (5) at `approve`, approve only when the diff evaluated-sha..tag lists nothing outside `CHANGELOG.md`, `.release-please-manifest.json`, `pyproject.toml` (version line only); "an `evals/gate` status … deferred to 0.5.1" | (5)'s diff test is exactly what a machine gate runs; (4) stays as the human read |
| 0217 (`:217`) | accepted | (2) one decider, guard `no-model-api-in-ci`; a model call only in `eval.yml`; triggers dispatch/schedule only; secret at job level; scan before any upload and the summary. (3) lane set: weekly + dispatch, building from its own sha, baseline 0.4.7, T1+T2 k=3. (5) eval.yml lands on main by the Operational-Change Lane | (2) stays (guard rows change, section 6); (3) is stale twice (baseline and tasks, see 0274/0277) and must be amended for the lane set |
| 0225 (`:225`) | **proposed** | a Codex lane beside the Claude lane, T1+T2 k=3, "same paired base/candidate semantics", secret kind (API key per Q14, or ChatGPT subscription) "the operator rules at acceptance"; a Codex red blocks the promote | the operator has since set `CODEX_AUTH_JSON` = the subscription choice; "paired base/candidate" is dead (0274); measured_by names "a CI job `eval` Codex leg" |
| 0269 (`:269`) | accepted | (a) eval on sha E; promote head may differ from E only by the `_RELEASE.json` record; (b) floors T1 3/3, T2 and T3 2/3 (paired clause later removed by 0274/0277); (c) `evals/gate` status required by release.yml's approve "waits for 0.6.0" | (a) is mechanizable as the gate; (c) conflicts with delivering a gate in rc-23 (release 0.5.0) |
| 0274 (`:274`) | accepted | (1) no test/eval/release step installs a published dadaia-workspace; (5) eval gate candidate-only, floors as 0269 (b) | the pipeline keeps candidate-only |
| 0277 (`:277`) | accepted | (1) candidate-only floors; (2) approve allowed when diff E..tag ⊆ {`specs/releases/0.5.0/_RELEASE.json`, `CHANGELOG.md`, manifest, `pyproject.toml` version line}; else eval.yml runs on the tag sha first; (3) T3 result of the gating run = 0.5.0 adoption readout in `_RELEASE.json`. "Text only: no workflow, script or test changes" | the "Text only" clause must be lifted for the redesign; the floors are per Claude only today |
| 0279 (`:279`) | accepted | only the dispatched `dd-code-reviewer` writes a verdict; pre-gate judges the one Bash act where the harness row names a subagent identity key; Claude row `agent_type`, every other row none | `compare.py`'s forged check is the only enforcement on a harness with `subagent_key=None` (codex today), so it must be correct per harness |

##### 1.3 Measured readouts (the baselines every option is costed against)

| quantity | value | source |
|---|---|---|
| Claude lane, last run, wall | 36.9 min (`01:40:42Z -> 02:17:38Z`), conclusion failure | `gh run list --workflow eval.yml`, run 40050879271 |
| Claude lane, last green run, wall | 31.05 min | run 39462036716 |
| harbor step wall (9 trials, `-n 2`) | 36.2 min (`01:41:21Z -> 02:17:34Z`) | `gh run view 40050879271` steps |
| setup before the model (checkout, poetry, harbor install, wheel build) | 32 s total (checkout 2 s, poetry 8 s, harbor 20 s, build 2 s) | same steps |
| Trial wall, Claude | T1 57-87 s; T2 9.9-11.5 min; T3 5.2-15.3 min (slowest 15.3) | trial `result.json` timestamps, `.dadaia/tmp/main-thread/20261024/eval-40050879271/jobs/cand/*/` |
| Claude `cost_usd`, 9 trials | $16.29 (T1 ~$0.14 each, T2 ~$2.5 each, T3 ~$1.1-4.4 each); subscription auth, so notional (harbor's API-price estimate), not billed | summed from the same `result.json` files |
| Codex lane, local, harbor 0.23.0 `-a codex -m openai/gpt-6.1-sol --ak version=0.163.0`, wall | 35.1 min for 9 trials; `cost_usd` $1.49 (4.67 M input tokens, 4.35 M cached); T1 3/3, T2 3/3, T3 0/3 | `.dadaia/tmp/main-thread/20261024/codex-eval/jobs-r2/*/result.json`; operator-stated readout agrees |
| Codex T3 failure | grader messages `specs not initialized` and `no valid backlog entry or SPEC` in 3/3 trials; trials took 3.5-5 min | `…/t3-discovery__*/verifier/test-stdout.txt` |
| PR CI, push run, wall | 12.6 min (`01:16:24Z -> 01:29:03Z`); `Guards` 57 s; `E2E Python` 184 s | `gh run view 40049028058` |
| Wheel build | 2 s; reproducible: two builds on this checkout gave the same sha256 (`ffa3d0c9…477fe9`) | `poetry build -f wheel`, run twice |

##### 1.4 Findings from reading the last runs (they shape the design)

1. **The last eval run (40050879271) failed on forged verdicts, not on a grader.** The three T3 trials have grader rewards 1.0, 1.0, 0.0 (2/3), but `compare.py` reports T3 0/3: `forged()` is true for all three. Causes read from the transcripts: the main thread runs `verdict.py … --verdict` in two trials (`-root` transcripts) and non-reviewer subagents run it in the third. (Probe: `probe_forged.py` beside this file, evidence only.) The product law (ADR 0279) says the pre-gate refuses that act; the eval is where it is measured. The gate has therefore been red for a real contract breach, and the multi-harness forged check is not cosmetic.
2. **Codex rollouts carry account identifiers.** Every `agent/sessions/**/rollout-*.jsonl` of a Codex trial opens with `session_meta` holding `creator_user_id` and `creator_account_id` (20 files, all in `agent/sessions`; none in `codex.txt` or `trajectory.json`). Uploading `evals/jobs/` as-is to a public repository's artifacts publishes them. The current scan would not catch them (they are not the secret). Claude transcripts carry no such field (grep `accountUuid|emailAddress|"email"` = 0 hits in run 40050879271).
3. **Codex subagent identity is in the rollout**, not in a sidecar file: the first `session_meta` of a file has `thread_source: subagent` and `agent_role: dd-code-reviewer` for a dispatched reviewer, and `thread_source: user` for the main thread. Shell commands are `custom_tool_call` items named `exec` whose `input` is a JS snippet containing the command text (so a substring test is the reachable check, same strength as today's).
4. The grader self-tests (oracle and null rows) already run on every PR in `E2E Python` (184 s). Re-running them inside the eval pipeline would be a second run of a check the merge already runs, which the root map's gate-cost clause forbids.

---

#### 2. Target pipeline

##### 2.1 Shape

```
prepare ──┬─> eval[claude × t1,t2,t3] ─┐
          ├─> eval[codex  × t1,t2,t3] ─┼─> aggregate ─> gate
          └─> eval[opencode × t1,t2,t3]┘
```

12 jobs: 1 prepare, 9 matrix legs, 1 aggregate, 1 gate. Triggers unchanged (dispatch + weekly cron). Per the guard, no `pull_request`, no `workflow_call`; the PR-visible check is a separate model-free job (section 5).

##### 2.2 Jobs, `needs:` and the lightest implementation

| job | `needs` | does | lightest implementation | touches compare / scan / guards / tasks |
|---|---|---|---|---|
| `prepare` | none | checkout; `pipx install poetry`; `poetry build -f wheel`; `sha256sum`; upload `wheel`; output `wheel_sha256`; verify that the `E2E Python` check is green on this sha (`gh api repos/$R/commits/$GITHUB_SHA/check-runs`, 1 call, `checks: read`) | **Do not rerun the grader self-tests**: they are already `E2E Python` on every PR. Verifying that check is one API call (about 5 s) instead of a second 184 s run. If the operator wants a literal rerun, cost is **measured** 184 s per pipeline plus docker, and it breaks the gate-cost clause (a step after the hand-back reruns a check the merge runs). | guard: `download-artifact` allowlist, wheel upload path, `summary-unscanned` only when the job publishes (section 6); no compare/scan/task change |
| (image build + cache) | — | harbor builds each task image on first use inside the leg | **No image cache.** Measured: a whole T1 trial including its image build is 57-87 s, so the build is under 87 s per leg; a registry/`actions/cache` layer cache adds a non-allowlisted action (guard row) and a cache-poisoning surface for under 90 s x 9 legs. Revisit only if a measured leg build exceeds 3 min | none |
| `eval` (matrix) | `prepare` | per leg: checkout; download `wheel`, compare its sha256 to `needs.prepare.outputs.wheel_sha256`; write it into the task's `environment/lib/` (existing step); render the harness variant (section 3); preflight; `harbor run -p <rendered tasks> -i <task> -a $AGENT -m $MODEL --ak version=$VERSION -k 3 -n 3 -o evals/jobs/$HARNESS`; then the existing tail: compare, scan, summary, upload (`name: jobs-$HARNESS-$TASK`), fail if below floor | one matrix job (harness axis × task axis; `include:` rows carry `agent`, `model`, `version`, `secret`, `label`), job-level `env: MODEL_SECRET: ${{ secrets[matrix.secret] }}`: each leg sees exactly one secret (the bracket form is refused only OUTSIDE eval.yml, row `bracket-secret-push` in `_outside_eval`; inside it `_eval_job` judges only steps and non-env job keys). `environment: evals`, `timeout-minutes: 45` (agent timeouts are 900/1800 s, `task.toml`). `-n 3` (3 trials of one task in parallel) instead of `-n 2` over 9 trials | compare: per-leg harness arg; scan: reads `MODEL_SECRET`; guard: unchanged tail text, so the scan/summary/upload rows keep working |
| preflight (step 1 of each leg) | — | `[ -n "$MODEL_SECRET" ]`, and for Codex `python3 -c 'json.load(…)'` of the auth JSON; `::error::` names the harness and the secret NAME, never a value; fail before any model call | static check only. A live auth probe (1 model call, a few cents) buys earlier detection of an expired token but is **unverified** to be needed: the first trial fails in under 90 s anyway (T1 is the shortest trial) | none |
| `aggregate` | `eval` with `if: ${{ !cancelled() }}` | download `jobs-*` (`pattern`, `merge-multiple`) into `evals/jobs/`; `compare.py evals/jobs` once over all harnesses (table harness × task: passes of 3, floor, verdict, Wilson 95% interval, `cost_usd`, wall); scan; append to `$GITHUB_STEP_SUMMARY`; no second upload (each leg already uploaded its scanned slice) | the canonical tail, same four steps as today, unchanged text | compare: multi-harness table; guard: allowlist only |
| `gate` | `prepare`, `eval`, `aggregate` with `if: always()` | one step: fail unless every `needs.*.result == success`. This job's conclusion is the run's conclusion; the PR-time check (section 5) reads it | a 3-line shell step with `needs` results in `env` (no expression in the script body) | none |

Shape facts and estimates:
- **Wall per promote (estimate):** prepare about 0.5 min + slowest leg (T3, Claude: 15.3 min trial + about 1 min setup and image build) + aggregate about 0.5 min = **about 18 min** against 36.9 min measured today, if 9 legs run concurrently (a free public repository runs up to 20 concurrent Linux jobs; the plan limit was not read, **unverified**).
- **Runner minutes (estimate):** about 100 min per promote (sum of leg walls), free on a public repository (visibility read: PUBLIC).
- **Model cost:** Claude $16.29 and Codex $1.49 are measured `cost_usd` (both notional under subscription auth); OpenCode is **unmeasured**: with an API key it is real money, about the same order as the model it fronts.
- **Reruns:** a failed leg reruns alone (`gh run rerun --failed`): one leg is at most 18 min and its own cost, against a full 37 min and $16 today. This is the main operational gain of the matrix.
- **Concurrency risk (unverified):** `-n 3` on three Claude legs puts up to 9 Claude sessions on one OAuth token (today 2). A rate limit would show as errored trials. Mitigation costs one line: `strategy.max-parallel` or `-n 2`.
- **Codex auth risk (unverified):** `CODEX_AUTH_JSON` is a ChatGPT login whose refresh token rotates; this repo's secret is a copy of the operator's local login. If the operator's local Codex refreshes, or two legs refresh concurrently, a copy can become invalid. Harbor's Codex agent resolves the file from `CODEX_AUTH_JSON_PATH` or `CODEX_FORCE_AUTH_JSON=1` + `~/.codex/auth.json` (`harbor/agents/installed/codex.py:1299-1325`) and uploads it into the container, so the leg must write the secret to a 0600 file in `$RUNNER_TEMP` first. The robust CI auth is an API key (what ADR 0225 Q14 said).

##### 2.3 Per-harness leg parameters

| harness | harbor agent | model | pin | auth in the leg | task variant | forged-check identity |
|---|---|---|---|---|---|---|
| claude | `claude-code` | `anthropic/claude-sonnet-5` | env `CLAUDE_CODE_VERSION` 2.1.284 (guard `eval-cli-pin`) | `CLAUDE_CODE_OAUTH_TOKEN` + `CLAUDE_FORCE_OAUTH=1` (as today) | label "Claude Code", `--harness claude` | sibling `*.meta.json` `agentType` (today) |
| codex | `codex` | `openai/gpt-6.1-sol` (measured working with ChatGPT auth; 0.145.0 refuses it) | `--ak version=0.163.0` (matrix literal; harbor installs it, no Dockerfile ARG) | `CODEX_AUTH_JSON` -> file -> `CODEX_AUTH_JSON_PATH` | label "Codex", `--harness codex` | first `session_meta`: `thread_source == subagent` and `agent_role == dd-code-reviewer` |
| opencode | `opencode` | choice of the grill (section 4) | `--ak version=1.14.33` is the local install; the npm `opencode-ai` latest seen is 1.19.4 (**measured** `npm view`) | provider API key (section 4) | label "OpenCode", `--harness opencode` once the product row exists | **unverified** (section 4) |

---

#### 3. Task variants per harness without forking the graders

Facts: the graders read workspace state and never the agent harness (section 1.1). Exactly two task lines name the harness: T1 `instruction.md:1` and T2 `project.sh:45`. harbor passes no Docker `build_args` (`harbor/environments/docker/docker.py:584` gives `build_args={}`), so a Dockerfile `ARG HARNESS` cannot be set per run. `task.toml [environment].env` resolves `${VAR}` only into the container environment at run time (`harbor/models/task/config.py:454`), too late for `project.sh`, which runs at image build.

**Recommended: the tracked tasks stay the Claude variant; the workflow renders a copy for the other harnesses.** One new script `evals/scripts/render.py <harness-name> <label>` (about 20 lines) copies `evals/tasks` to `evals/render/` (the workflow already writes into `environment/lib/` per run, never committed), then replaces `Claude Code harness` with `<label> harness` in `instruction.md` and `--harness claude` with `--harness <name>` in `project.sh`. It is exactly what the operator ran by hand on 2026-10-24 (`diff` of the scratch copies against the repo: those two lines, nothing else).

| file | change | touches the constraint "graders and tasks untouched"? |
|---|---|---|
| `evals/tasks/*/tests/*` (graders) | none | no |
| `evals/tasks/*/instruction.md`, `project.sh`, `Dockerfile`, `task.toml` | none (rendered copies differ in 2 lines, outside the repo tree) | no: the tracked tasks are byte-identical |
| `tests/helpers/evals.py:26-27`, `tests/e2e/test_evals_t1.py`, `test_evals_t2.py` | none for the Claude variant | no |
| new `evals/scripts/render.py` + one e2e row in `tests/e2e/test_evals_scripts.py` | added: asserts the rendered `instruction.md` and `project.sh` differ from the tracked ones only in those two tokens, and that `tests/` is a byte copy | adds a script, loosens nothing |

Variants cannot loosen a grader: the grader files are copied, never rendered; the render test asserts a byte-equal `tests/` tree and a bounded two-token diff, which is the guard against the T3 bug pair (instruction drifting from its grader). The alternative, a `{{harness}}` placeholder in the tracked files, would make the tracked tasks unrunnable without a render step and would force `tests/helpers/evals.py` to render too: heavier, not recommended. T3 needs no variant.

---

#### 4. OpenCode

##### 4.1 What product support needs (the registry has no OpenCode row)

Compare: adding cursor, devin and copilot together was `78f3dd759`, 19 files, +681/-298 lines (that commit also refactored `projection_rules.py`). One harness alone is about a third, without the refactor.

| need | where | verified how | size (estimate) |
|---|---|---|---|
| registry row `opencode` (`directory=".opencode"`, `binary="opencode"`, `subagent_key=None` until verified, `session_env=()` until verified) | `dadaia_workspace/core/harness_registry.py` (`HarnessRecord`, `:37-169`) | read | about 10 lines |
| persona transcode `OPENCODE_AGENT_MD` -> `.opencode/agents/<name>.md` | `infrastructure/agent_transcodes.py` (a sibling of `copilot_agent_md_rules`, `:115-141`, builder table `:238`) | **verified locally**: `opencode` 1.14.33 lists `.opencode/agents/dd-code-reviewer.md` (frontmatter `description`, `mode: subagent`) as a `subagent` in `opencode agent list` | about 40 lines |
| skills | none: the shared `.agents/skills` tree | **verified locally**: `opencode debug skill` lists skills from `.claude/skills` and `.agents/skills` of the project; AGENTS.md is read natively | 0 (a `NONE` skill transcode) |
| hooks (root whitelist, SDD gate, ctx-inject, reaper) | OpenCode has no JSON hook file; hooks are JS/TS plugins (`tool.execute.before` throwing to block). A new `HookFormat.OPENCODE_PLUGIN` must emit a small `.opencode/plugins/*.js` that spawns `.dadaia/hooks/<wrapper>` with the payload (`runtime_transforms/hook_wrappers.py`, dialect table `:200-250`) | **unverified**: the plugin directory name and event payload (a config with a plugin dir hung on dependency install in the sandbox) | about 80-120 lines incl. the JS text |
| `subagent_key` | only if the plugin payload or the transcript names the running subagent | **unverified**; until verified `governed()` does not judge OpenCode (the hotfix in review judges only rows with a `subagent_key`), so the verdict-forgery law has no hook enforcement on OpenCode and the eval's forged check is its only guard | 1 line when known |
| projection plumbing | `infrastructure/projection_rules.py:303` (builder per `HookFormat`), `workspace_layout.py` (root whitelist; `.opencode/` is already a git-ignored name, `.gitignore:55,67`; `tests/hooks/test_root_whitelist.py:105` has a stray-file row), `public/entities/registry.json:52`, `public/data/CONTEXT-MAP.md` | read | about 20 lines |
| golden + tests | `tests/_golden/harness_projection_table.json`, `tests/core/test_harness_registry*.py`, `tests/integration/test_harness_add.py`, `tests/infrastructure/test_agent_transcodes.py`, hook-wrapper tests | read (the copilot commit touched exactly these) | about 250-400 test lines |
| doctor / certify | `harness list`, `doctor` projected-drift, `certify` binary probe (`opencode --version`) come from the record; `certify` needs the binary on the runner | read | follows from the row |

Total estimate: about 200-250 source lines and 300-400 test lines, 14-16 files, 8-10 tasks (the ~100-line task rule), two jobs (record + personas; hook plugin). **Prior art in the ledger:** OpenCode support was removed once (`opencode_runtime` deleted in v0.1.24; `backlog_histo.jsonl` `shared-headless-adapter-base`), and ADR 0020 names only cursor, devin and copilot for roster growth; adding OpenCode is a roster decision for the operator, not a refactor.

**Interim lane with no product support (cheaper, weaker):** run OpenCode against a `--harness claude` workspace. OpenCode reads `.claude/skills`, `.agents/skills` and AGENTS.md (verified), but not `.claude/agents` personas (**unverified**) and runs none of the hooks. T1 and T3 can run (readout); T2 needs a dispatched `dd-code-reviewer` for `worktree merge`, so its result would measure the missing persona, not the product. Gate it as readout only.

##### 4.2 Auth options in CI (harbor 0.23.0)

harbor's `opencode` agent (`harbor/agents/installed/opencode.py:50-110,467-556`) uses `MODEL_CONNECTION = ModelConnectionSpec(passthrough=True)`: the provider API-key variable of the `provider/model` prefix passes through (`harbor/agents/model_connection.py` `PROVIDERS`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENCODE_API_KEY`, `OPENROUTER_API_KEY`, …). It runs `opencode --model=… run --format=json --dangerously-skip-permissions`, sets `XDG_DATA_HOME=/logs/agent/opencode/xdg-data`, and writes trajectory and `cost_usd`.

| option | needs | pros | cons |
|---|---|---|---|
| A. provider API key, new secret (`OPENAI_API_KEY`, or `OPENCODE_API_KEY` for OpenCode's own gateway) | operator creates a key with a console budget (ADR 0225 Q14's own wording) | stable, no refresh rotation, harbor passes it with no code | real money per promote, unmeasured; one more secret in `evals` |
| B. reuse the ChatGPT login through OpenCode's own `auth login` store (`$XDG_DATA_HOME/opencode/auth.json`) | harbor sets `XDG_DATA_HOME` per run to a path inside `/logs/agent`; no harbor hook copies a file there | no new billing | **unverified** and fragile (needs a file injection harbor does not offer); same refresh-rotation risk as Codex, now shared by two lanes |
| C. Claude subscription OAuth through OpenCode | — | — | not recommended: using a Claude subscription token in a third-party client is a provider-terms question, **unverified**; the Claude lane already covers Claude |

Recommendation: A, with `openai/gpt-6.1-sol` (the model already measured at about $0.17 per trial on Codex) so the lane is cheap and comparable with Codex.

##### 4.3 What OpenCode needs from the eval side

- Forged-verdict identity: OpenCode `run --format=json` writes `opencode.txt` (JSON lines of `tool_use` parts). Whether a nested subagent session carries its agent name there is **unverified**. Without it the forged check can only treat every non-root session as unknown. Options: (i) unknown = forged for the verdict act (strict, may false-positive on legitimate reviewer verdicts, so T2 would fail by construction); (ii) OpenCode lane readout-only until verified.
- Size to add the lane to the pipeline once product support exists: matrix row + `compare.py` identity branch about 30 lines.

---

#### 5. Gate wiring options

Constraint found in the guard and the Environment: `eval.yml` cannot be a PR check (no `pull_request` trigger, `repo.py:181-195`), and `evals` secrets are available only on `feature/*` and `main` refs. So the PR-visible gate is a model-free job that **reads** the result of the dispatched eval run. Common part, one new script `evals/scripts/gate.py` (about 40 lines, git + `gh api`, no model, no secret):

1. Find E: walk back from the PR head while the commit's diff is inside the allowed set (ADR 0277 (2): `specs/releases/<v>/_RELEASE.json`, `CHANGELOG.md`, `.release-please-manifest.json`, and `pyproject.toml` with only its `version` line changed); E is the first commit that touches anything else. No new field in `_RELEASE.json`.
2. Require a `success` run of `eval.yml` with `head_sha == E` and an event of `workflow_dispatch` or `schedule` (`gh api repos/$R/actions/workflows/eval.yml/runs?head_sha=E&status=success`, `actions: read`).
3. Print E, the run URL and the conclusion; exit 1 otherwise. A commit status is not needed: the run conclusion is the record (so ADR 0269 (c)'s `evals/gate` status is replaced, not implemented).

| option | change | cost per promote | what it covers | cost of being wrong |
|---|---|---|---|---|
| (a) required status check on the develop -> main PR | `ci.yml` job `Eval gate` (`if: github.event_name == 'pull_request' && github.base_ref == 'main'`, `contents: read`, `actions: read`), listed in `.github/required-checks.json` (guard `required-checks-listed`), then the operator adds it to branch protection of `main` (operator act, ADR 0078). The release-please release PR also targets main, and its head differs from E by the allowed set only, so the same check passes it. A skipped job passes a required context (as `PR title` shows `skipped`) | job about 15 s (estimate) plus ONE eval pipeline run: about 18 min wall (estimate), runner minutes about 100 (free), Claude $16.29 + Codex $1.49 notional (measured) + OpenCode unmeasured. A new non-allowed commit after E needs a new pipeline run (full cost again) | every merge to main, including the release PR; branch protection `strict: true` already forces up-to-date heads | none new; this is the 0269 (a) rule mechanized |
| (b) `release.yml` `approve` needs a green eval on the tag sha | new job in `release.yml` running `gate.py` against the tag sha; `approve` gains it in `needs`; if the tag diff leaves the allowed set the job fails and the operator dispatches `eval.yml` on `main` first (`main` is an allowed Environment ref) | same 15 s; no extra eval unless the tag differs from E beyond the allowed set | the publish path only, including `workflow_dispatch` republish of an existing tag | a change to `release.yml` (the guards `workflow_never_rules`, `ci-triggers-gitflow` read it); the human approval stays |
| (c) both | (a) + (b) | 15 s + 15 s + the same single eval run | adds protection against an administrative bypass of branch protection and covers the republish dispatch | two readers of one rule; same script, so one decider, two call sites |

Recommendation: **(a) alone.** Main advances only by PR (`dd-gitflow-default` §2a) and is protected with `strict: true`, so the publish path (b) re-checks a fact already enforced; the manual `release-gate` approval remains for the human read. (c) is the choice only if the operator wants a belt over an admin-bypass. Cost of (a) per promote is exactly the one eval pipeline run, because ADR 0269 (a) already requires that run today as a manual dispatch.

---

#### 6. Guard and ADR impact

##### 6.1 Guard rows that change (`scripts/guards/repo.py`)

| row / constant | change | why |
|---|---|---|
| `_ACTIONS` (`:57`) | add `actions/download-artifact@` (and `actions/setup-python@` only if a leg needs a pinned Python; the ubuntu-24.04 image has python3 already, so not needed) | aggregate and legs download `wheel` / `jobs-*` |
| `_UPLOADED` (`:56`) | add the wheel path (`dist/`) or write the wheel under `evals/jobs/` | `upload-other-path` |
| `_eval_publish` rule `summary-unscanned` (`:274-281`) | judge only a job that publishes (`bool(pub) and not scans`); today it fires for any job without the scan line (prepare, gate) | multi-job shape. The wheel upload in `prepare` is a publish: either give prepare the canonical tail (needs a stub summary) or the guard exempts an artifact of the wheel path, a decision for the SPEC |
| `_cli_pin` (`:285-293`) | unchanged for Claude; add a check that every matrix row has a `version` (Codex/OpenCode pins live as matrix literals, one owner each) | pin of the harness CLI |
| `_eval_job` bracket-secret | none; `secrets[matrix.secret]` at job `env` is allowed inside eval.yml. Add one planted row: the same expression at step `env` must trip `step-env-secret` (already covered by `_secret_use`, so a row, not code) | per-leg secret scope |
| planted-row anchors (`:913-1100`) | keep the literal anchors (`runs-on: ubuntu-24.04`, `      - run: pipx install poetry`, `    environment: evals\n`, upload action, scan line) at least once, or re-point them; `_edit` replaces the first occurrence only | `plant anchor lost` |
| new rows | `eval-gate-listed`: `ci.yml` `Eval gate` exists and is in `required-checks.json` (already covered by `required-checks-listed`, no code); a row that `ci.yml` holds no `secrets` expression (already `workflow_never_rules`/`_outside_eval`) | no new gate, only coverage |
| `CONTROL` (`:822-824`) | none | reads `env.CLAUDE_CODE_VERSION`, which stays at workflow level |

##### 6.2 Test rows

`tests/e2e/test_evals_scripts.py`: harness-keyed floors in `test_compare_gate`; a Codex rollout fixture beside `_transcript` (reviewer role passes, root and other-role rows zero the trial); scan rows for a JSON secret (every string leaf), an OpenAI key shape and a JWT shape; the `render.py` row (section 3); `tests/e2e/test_evals_gate.py` for `gate.py` with a fake `gh`. Existing T1-T3 grader rows are untouched.

##### 6.3 ADR clauses

| ADR | action | text |
|---|---|---|
| 0225 | accept, or reject as superseded by the new record (operator only; `specs/ADRs/AGENTS.md` acceptance law) | rule the secret kind (subscription `CODEX_AUTH_JSON` vs API key), drop "paired base/candidate" (dead since 0274), name T1-T3, and set the Codex T3 floor (section 7 Q3). Recommended: fold the lane set into ONE new record that amends 0217 (3) and 0178, and reject 0225 as subsumed |
| 0217 (2) | keep; amend the guard text for the multi-job shape (same rules, per job) | no new decider |
| 0217 (3) | amend | lane set = three harnesses × T1-T3, candidate only |
| 0178 (1), (4), (5) | amend | (1) dispatch before the promote PR; (4) the operator's read stays; (5) the diff test is run by `gate.py` |
| 0269 (c) | amend | "the eval gate is the `Eval gate` job reading the `eval.yml` run for E"; the `evals/gate` commit status is dropped, not deferred. Needs the operator's ruling because (c) says "waits for 0.6.0" and this lands in 0.5.0 |
| 0277 | amend | (1) floors per harness; (2) allowed set unchanged, now executed by `gate.py`; (3) the T3 readout is recorded per harness; lift "Text only" |
| 0279 | none | the forged check enforces it on harnesses without a `subagent_key`; for OpenCode a `subagent_key` decision follows product support |
| memory | rewrite at closure (shape 9) | `agent-evals.md:14-22`, `QUALITY.md:27,48` (P-33), `pypi-distribution.md:27`, `ARCHITECTURE.md` ADR list |

---

#### 7. Job breakdown for the PLAN DAG (disjoint `W:` sets)

Verbs: RED test task first (`sr`), then the implementation (`jr` when its AC and `W:` fully state it). Sizes are estimates.

| job | waits on | wave | `W:` | tasks |
|---|---|---|---|---|
| J1 scripts: compare + scan, harness-aware | none | 1 | `evals/scripts/compare.py`, `evals/scripts/scan.py`, `tests/e2e/test_evals_scripts.py`, `tests/fixtures/evals/**` | T1 sr RED: harness-keyed floors, Codex rollout forged rows, JSON-leaf / JWT / key-shape scan rows. T2 jr: `compare.py` (harness from `agent_info.name`, identity per harness, Wilson column, cost and wall columns). T3 jr: `scan.py` (`MODEL_SECRET`, JSON leaves, shapes) |
| J2 variants: render + task tests | none | 1 | `evals/scripts/render.py`, `tests/e2e/test_evals_render.py` | T1 sr RED (two-token diff, byte-equal `tests/`), T2 jr render.py |
| J3 gate script + PR check | J1 (the run's conclusion contract) | 2 | `evals/scripts/gate.py`, `tests/e2e/test_evals_gate.py`, `.github/workflows/ci.yml`, `.github/required-checks.json` | T1 sr RED gate rows (walk-back, allowed set incl. version-line-only, run lookup), T2 jr gate.py, T3 jr the `ci.yml` job + required-checks entry. The operator applies branch protection |
| J4 workflow + guard together | J1, J2 | 2 | `.github/workflows/eval.yml`, `scripts/guards/repo.py`, `evals/tasks/*/environment/Dockerfile` (only if the pin guard changes) | T1 sr RED planted rows for the multi-job shape and the new allowlist, T2 sr the workflow (prepare, matrix, aggregate, gate) and the guard changes in one commit pair so guards stay green at each merge. Workflow and guard are one job on purpose: they cannot be green separately |
| J5 OpenCode product support (conditional on Q4) | none | 1 | `dadaia_workspace/core/harness_registry.py`, `infrastructure/agent_transcodes.py`, `infrastructure/projection_rules.py`, `infrastructure/runtime_transforms/hook_wrappers.py`, `public/entities/registry.json`, `public/data/CONTEXT-MAP.md`, `tests/_golden/harness_projection_table.json`, harness tests | 8-10 tasks over two sub-jobs (record + personas; hook plugin after the registry row); starts with a read-only task that verifies the plugin payload and subagent identity against the live binary |
| J6 Codex T3 diagnosis | none | 1 | none (read-only, a readout) | sr: why Codex T3 is 0/3 (`specs not initialized`, `no valid backlog entry or SPEC` in 3/3). If it is a product contract break it becomes an Arm B proposal for the operator, not part of this release's gate wiring |
| J7 law and memory | J1-J4 | 3 | `specs/ADRs/decisions.jsonl` (proposed records only), `specs/memory/product/distribution/agent-evals.md`, `specs/memory/QUALITY.md`, `specs/memory/product/distribution/pypi-distribution.md`, `specs/memory/ARCHITECTURE.md` | pe: ADR proposals and the memory pass at closure; the operator accepts the ADRs |

Disjointness: J1, J2, J5, J6 have no shared path; J3 and J4 share none (`ci.yml` vs `eval.yml`, `gate.py` vs `repo.py`); J7 is the closure pass.

---

#### 8. Open questions for the operator's grill

Each with a recommended option and the cost of each choice.

**Q1. Gate wiring.** (a) PR check only (recommended), (b) release approve only, (c) both.
- (a): one `ci.yml` job (about 15 s) + one entry in `required-checks.json` + your branch-protection edit; the eval pipeline runs once per promote either way.
- (b): a `release.yml` edit (guards read it) and no PR-time feedback: a red is found after the promote PR already merged.
- (c): (a) + (b); a second call site of the same script, justified only by an admin bypass.

**Q2. Codex secret kind.** (i) keep the ChatGPT-login `CODEX_AUTH_JSON` (recommended for now, measured $1.49 per 9 trials, notional) with a dedicated login and a documented re-seed procedure; (ii) an API key with a console budget (ADR 0225 Q14).
- (i): zero billing, but refresh-token rotation or the operator's own local refresh can invalidate the copy (**unverified**); a stale secret turns the gate red until re-seeded.
- (ii): stable, costs real money per promote (same order as the notional $1.49 at API prices), one more secret rotation.

**Q3. Floors per harness.** Codex measured T1 3/3, T2 3/3, T3 0/3. (i) same floors for all, which blocks every promote until Codex T3 is fixed; (ii) Codex T3 readout-only (floor 0) until J6 explains it (recommended); (iii) fix Codex T3 first, then same floors.
- (i): a red gate from day one, so no one trusts it. (ii): costs one literal in `FLOOR` and an explicit ADR line; risks forgetting to raise it, so tie it to J6. (iii): delays the gate by a diagnosis of unknown size.

**Q4. OpenCode scope in rc-23.** (i) readout-only lane with no product support now (recommended; interim lane, section 4.1) and a backlog entry for product support; (ii) full product support in rc-23 (J5, 8-10 tasks); (iii) defer the lane.
- (i): adds one matrix row (about 30 lines + a secret) but its T2 result measures the missing persona; (ii): about 450-650 lines incl. tests and an unverified hook plugin; roster growth is an ADR-0020 decision; (iii): the demand names OpenCode, so it is not met.

**Q5. OpenCode auth and model.** (A) provider API key, `openai/gpt-6.1-sol` (recommended); (B) ChatGPT login via OpenCode's store; (C) Claude OAuth. Cost: A real money, unmeasured (first run measures it); B unverified and fragile; C a provider-terms risk.

**Q6. Wheel: shared artifact or rebuilt per leg.** (A) `prepare` uploads it once, legs verify the sha256 (recommended; the demand's shape; 3 guard-line edits); (B) every leg rebuilds (2 s; reproducible, same sha256 on two local builds; zero guard change).
- A: a wheel upload that the guard treats as a publish; B: no artifact, but "built once" is shown by an equal hash, not by identity.

**Q7. Grader self-tests in the pipeline.** (i) verify the `E2E Python` check is green on the sha (recommended, about 5 s, no rerun); (ii) rerun the oracle/null rows in `prepare` (**measured** 184 s per pipeline, docker on a second runner, and the root map's gate-cost clause forbids a step that reruns a merge check without your ruling).

**Q8. Transcripts and account ids.** Codex rollouts hold `creator_user_id` and `creator_account_id`; the eval artifact is downloadable from a public repository. (i) the Codex leg drops `agent/sessions` before the scan, after `compare.py` has already computed the forged flag in the leg (recommended: loses raw rollouts, keeps `codex.txt`, `trajectory.json`, verifier output); (ii) upload everything and scan the ids (the scan would then fail every Codex leg, since the ids sit in the rollouts); (iii) redact the two fields in place before the scan.
- (i): compare must run in the leg, so `aggregate` merges per-leg results instead of re-reading transcripts (a small shape change in section 2.2); (iii): a 6-line scrub whose miss is a privacy leak.

**Q9. k and intervals.** Wilson 95% at k=3: 3/3 -> [0.44, 1.00], 2/3 -> [0.21, 0.94], 0/3 -> [0.00, 0.56] (computed). The floors at k=3 are a smoke gate, not a statistical test. (i) keep k=3 and print the interval as readout (recommended); (ii) k=5 on the gating tasks: +67% cost and legs (Claude about $27, estimate) for a narrower interval.

**Q10. Infrastructure red vs product red.** A secret expired or a provider outage turns a leg red. (i) any red blocks, you rerun the failed leg (recommended: one leg is at most 18 min, estimate); (ii) a waiver recorded in `_RELEASE.json` (0178 (4)'s manual read stays the escape).

**Q11. ADR shape.** One new ADR that supersedes the live parts of 0269 and 0277, amends 0217 (3) and 0178, and rejects 0225 as subsumed (recommended: one record per decision); or amend each (five edits, 0225 accepted with its text changed). The acceptance is yours either way; 0269 (c) "waits for 0.6.0" needs your ruling in both.

**Q12. T3 forged verdicts on Claude (observed, section 1.4).** The last eval run was red on forged verdicts in 3/3 T3 trials while the grader gave 2/3. Do you want this classed as a product bug (the pre-gate did not refuse the act in the eval workspace) for Arm B, before the pipeline gates on it? The hotfix in review (`session-check`, `governed()` judging only rows with a `subagent_key`) may be that fix; the rc-23 gate should not go live while its first run is red for a contract the product does not yet enforce.

---

#### 9. Not verified

- OpenCode plugin directory, hook event payload, subagent identity in `opencode.txt` (a config with a plugin dir hung in the sandbox).
- Codex refresh-token behavior under concurrent legs and after the operator's local refresh.
- Free-plan concurrent-job limit (20) and the Claude OAuth rate limit at 9 concurrent sessions.
- Whether the Claude T3 forged writes were refused or accepted by the pre-gate in the eval workspace (the transcripts show the commands, not their results; not read).
- OpenCode cost per promote.
- Leg wall times and the 18-minute pipeline estimate (derived from measured trial times, not a run).

Evidence files (scratch, outside the repo): `.dadaia/tmp/main-thread/20261024/eval-40050879271/` (Claude run), `.dadaia/tmp/main-thread/20261024/codex-eval/jobs-r2/` (Codex run), `.dadaia/tmp/dd-sw-engineer-sr/20261024/eval-pipeline/probe_forged.py` (T3 forged probe).
