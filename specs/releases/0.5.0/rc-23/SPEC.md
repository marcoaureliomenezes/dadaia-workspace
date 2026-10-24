# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-24
**Origin:** operator-demand

---

## Bug window review

**Window:** every record closed after rc-22's birth (2026-10-21T00:28:07Z, `_RELEASE.json` log), read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `f00331174`: 17 resolved, 1 superseded. rc-22's window review already judged 13 of them (closed by 2026-10-21T12:53:49Z); they are not re-judged here. This table judges the 5 closed after that review and the eval graders' line, which this candidate builds on. Each fix is found by its id line (`git log -E --grep '^(fix|refactor)\(bugs\): …<id>'`).

| fix (ids) | fix commits | reading | verdict |
|---|---|---|---|
| a-session-outside-the-workspace-root-merges-on-its-own-verdict (the session-check hotfix) | `d5394fbdd`, `b1b5a0f9c`, `1857ae8ba`; test `a4d3be0a5` | Structural. The verdict rule had one decider, the pre-gate hook, and a session outside the root loads no hook. Now `core.invocation.governed` is the one decider, and the writer and `worktree merge` both ask it through `context session-check`. One test contract changed (`touch_last_seen_at`'s absent-record `None`), by the operator's order of 2026-10-24, named in the commit. Residual by ruling: only a harness whose registry row names a subagent key is judged, so on Codex nothing in the product refuses a forged verdict. | KEEP. The residual makes FR4's Codex forged check the only guard on that harness. |
| t3-instruction-omits-backlog-demand | `7c6a13c59` | Text-only; rc-22 already ruled it KEEP | KEEP |
| t3-grader-requires-an-active-backlog-entry | `6641c7f49`, `5fe06d62f` | Loosened twice after a 0/3 (rc-22 F026). The REBUILD was rc-22 FR13 (`9c76d7d68`: the demand text earns the reward, a stub earns nothing). | KEEP the REBUILD; no grader changes here (AC3.2) |
| compare.py forged-verdict zeroing (rc-22 FR13, not a bug) | `ea8875e8b` | It reads only Claude Code transcripts: a Codex trial has no `assistant` line, so it is never zeroed. Within its stated contract (Claude-only eval.yml) this is not a defect. A new harness axis is new behaviour. | KEEP; FR4 extends it per harness |
| verdict-act-gate-lexer-lets-an-ampersand-redirection-or-a-midword-hash-hide-the-writer, verdict-act-gate-lexer-misses-the-module-name-attached-to-dash-m | `bf0c4cee4` | rc-22 FR7's REBUILD: a token test with the lexer deleted, net −12 | KEEP |
| init-no-terminal-fix-line-nests-one-act-label-inside-another | `91c9ec15a` | rc-22 FR8's REBUILD: every act sentence takes a plain command | KEEP |
| resolve-names-only-the-fix-bugs-label | `349aed920`, `2cfc0d373`, `830088b7c` | Three string REBUILDs of one refusal in one lane, after review rounds. No assert loosened. | KEEP |

**Overfitting check:** no fix in the window changed an assert without a named ruling. No special case keys on a test value. The one behaviour narrowed, governed judging only a subagent-keyed harness, is a stated ruling with its residual, and FR4 covers it on the eval side. No fix is judged REBUILD, so no bug is proposed.

## 1. Problem

The operator's words (grill handoff `2026-10-24T035818Z-main-thread-grill-eval-pipeline`, Portuguese, insults removed):

- R0: "coloque um pipeline decente, busque referencias de AI engineers ... cadê outros jobs de preparação, eval em diferentes harnesses, pelo menos openCode Claude code e codex ... é para colocar na ... pipeline de deploy ... não tem sumario no final, não tem preparação"; and "we will not deploy with no passing to the eval. and Don't do tricks".
- R1: "claude e codex bloqueiam. Open Code vamos configurar depois que eu sentir que vc sabe construir ... um pipeline de eval seguindo algum material de referencia de experts, AI engineers. não um job ... sem sumário".
- R2: "Check obrigatório no PR de promote (Recomendado)".
- R3: "Suportar OpenCode no 0.5.0 (Recomendado)", sequenced by R1 after the operator validates the pipeline.
- R4: "Manter o login ChatGPT".
- R5: "isso vai ser o gate de deploy do produto".
- R6: "Confirmo (Recomendado)".

The gap: `.github/workflows/eval.yml` is one job, `eval`. It runs one harness with one secret, builds the wheel in-job, prints a table with no harness axis and no interval, and scans for one secret. Nothing in the deploy flow reads its result: ADR 0178 (4) makes the gate the operator's manual read, and ADR 0269 (c) deferred an `evals/gate` status to 0.6.0. The last run, 40050879271, was red, and only a human could see it.

The references (each a URL in the grill's research notes):
- Anthropic, "Demystifying evals for AI agents": clean environment per trial, pass^k for consistency.
- Anthropic, "Quantifying infrastructure noise": infra errors counted apart.
- UK AISI Inspect: fail on error, retry opt-in.
- The promptfoo action: one required status.

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | the pipeline's stages exist and run on E | `prepare`, one leg per (harness, task) for Claude Code and Codex × T1–T3, `aggregate`, and the final result job each conclude in one `eval.yml` run on E | that run's job list |
| 2 | both gating harnesses meet their floors | Claude Code and Codex each at T1 3/3, T2 ≥ 2/3, T3 ≥ 2/3 on E, in one `eval.yml` run | that run's job summary |
| 3 | the summary | one row per (harness, task) printing passes of 3, pass^3 and the Wilson 95% interval | the same job summary |
| 4 | the deploy gate | `Eval gate` (ci.yml) is a required check on the develop → main PR, and goes red without a green `eval.yml` run on E | `.github/required-checks.json`; that PR's checks |
| 5 | privacy | zero secret values and zero account ids in any uploaded artifact | each leg's scan exit 0; the artifact files |

## 3. Non-goals

- The OpenCode lane and OpenCode product support: a backlog entry, R3. Its lane follows the operator's validation of this pipeline (R1).
- LLM judges; every grader stays a script.
- k > 3. The floors are a smoke gate at k=3; the interval is a readout.
- A change to `release.yml`: the `release-gate` approval stays the human read (R2 chose the PR check alone).
- An image cache, a PR-triggered or nightly eval run, and a rerun of the grader self-tests.

## 4. Requirements

**Wave ranking** (each wave opens when the previous one has merged):

1. Law: FR7, the ADR proposal, which the operator accepts before wave III merges.
2. Shared foundation: FR4's scripts (compare, scan) and FR3's render.
3. Features: FR1, FR2, FR6 and FR8 together, since the workflow and its guard cannot go green apart; then FR5, the gate.
4. Promote-facing: the run on E (goals 1–3, 5), the operator's branch-protection act (goal 4), and FR9 at closure.

The task ids below are `T1` cold-onboarding, `T2` block-list-bug and `T3` discovery. A "leg" is one job of the matrix, for one (harness, task).

### FR1 — prepare

- AC1.1 `prepare` builds the candidate wheel once from the run's checkout, uploads it, and outputs its sha256. Each leg downloads it and compares its sha256 to that output before writing it into a task's `environment/lib/`. On a mismatch the leg fails before any model call. Test: E2E (the `eval.yml` run on E); unit (the FR8 guard rows that allow the download and the wheel path).
- AC1.2 `prepare` reads the `E2E Python (pytest)` check run on the run's sha. Unless it concluded `success`, `prepare` fails and no leg starts. The grader self-tests are never rerun in the pipeline (root map §1: no step reruns a check the merge runs; 184 s measured, CI run 40049028058). Test: E2E (the run on E shows that step); the no-rerun clause has no test and is read at review.
- AC1.3 Each leg runs a secret preflight before any model call. Its one secret must be non-empty, and for Codex it must parse as JSON. On failure it prints one `::error::` line naming the harness, the secret's NAME and the re-seed doc (AC6.2), and it never prints a value. Test: E2E, the preflight's rows in `tests/e2e/test_evals_scripts.py` (an empty secret and a non-JSON secret exit 1, and the output holds neither value).

### FR2 — matrix

- AC2.1 There is one job per (harness, task): Claude Code and Codex × T1–T3, six legs. Each leg runs in the `evals` environment, at `-k 3`, with its output under its own `evals/jobs/<harness>/` slice and its own artifact name. Test: unit (FR8's planted rows judge each leg); E2E (the run on E).
- AC2.2 Each leg sees only its own harness's secret, at job level: the Claude legs `CLAUDE_CODE_OAUTH_TOKEN` and the Codex legs `CODEX_AUTH_JSON`. A secret at step `env` is refused. The reason is that harbor's agent env falls back to all of `os.environ` (harbor 0.23.0 `agents/installed/base.py:642-649`). Test: unit (planted row: a leg secret at step `env` trips `no-model-api-in-ci`).
- AC2.3 The per-harness pins:

  | harness | model | CLI version | pin owner |
  |---|---|---|---|
  | Claude Code | `anthropic/claude-sonnet-5` | 2.1.284 | `env.CLAUDE_CODE_VERSION`, as eval.yml has today |
  | Codex | `openai/gpt-6.1-sol` | 0.163.0 | its matrix row (measured working on the local readout; 0.145.0 refuses the model) |

  Every matrix row carries its model and CLI version. Test: unit (`eval-cli-pin` planted rows, AC8.2).
- AC2.4 Harbor retries only these infra and provider exception types:
  - infra: `EnvironmentStartTimeoutError`, `SandboxBuildFailedError`, `SandboxLikelyOutOfMemoryError`, `VerifierTimeoutError`;
  - provider: `ApiRateLimitError`, `ApiOverloadedError`, `ApiInternalServerError`, `ApiConnectionError`.

  An agent-side error is never retried. A red leg is rerun alone (`gh run rerun --failed`), never by a full rerun of every leg. Test: no test, because retry behaviour is harbor's; review reads the include list against this AC.

### FR3 — task variants

- AC3.1 A render script writes each non-Claude harness's copy of `evals/tasks/` outside the tracked tree. It changes only the harness label: the harness words on T1 `instruction.md:1` and `--harness claude` on T2 `environment/project.sh:45`. Every `tests/` folder is a byte copy, and the tracked tasks stay the Claude Code variant, unchanged. Test: E2E, a render row in `tests/e2e/` (the copy differs from the tracked tree in exactly those two tokens, and `tests/` is byte-equal).
- AC3.2 No grader changes in this candidate: `git diff --name-only <rc-23 base>..E -- 'evals/tasks/*/tests/'` prints nothing. Test: none; git, at review.

### FR4 — aggregate

- AC4.1 Each leg computes its own compare result, in-leg, and uploads it with its scanned slice; there is one path for every harness. `aggregate` merges the per-leg results into one table and reads no transcript. Test: E2E, `tests/e2e/test_evals_scripts.py` (aggregation of two harnesses' results).
- AC4.2 The forged-verdict check runs per harness. On both harnesses, the act is a shell command whose text holds `verdict.py` and `--verdict`. It zeroes the trial whatever its grader said, unless the dispatched `dd-code-reviewer` ran it.
  - Claude Code (unchanged): the reviewer is a transcript under `subagents/` whose sibling `*.meta.json` has `agentType` `dd-code-reviewer`.
  - Codex: the reviewer is a rollout file whose first `session_meta` has `thread_source` `subagent` and `agent_role` `dd-code-reviewer`. The act is an `exec` `custom_tool_call` whose `input` holds the command text.

  Test: E2E, `tests/e2e/test_evals_scripts.py`. A Codex rollout fixture: the reviewer's act passes; the act from the root (`thread_source` `user`) and from another role zero the trial.
- AC4.3 A trial of a harness with no identity rule makes compare exit 1. It is never a silent pass. Test: E2E (an unknown-harness row).
- AC4.4 The Codex leg removes its raw rollouts (`agent/sessions/**`, which hold `creator_user_id` and `creator_account_id`) after its in-leg compare, and before the scan and the upload. Test: E2E (the run on E: no Codex artifact holds `agent/sessions`); AC4.5's rows.
- AC4.5 Each leg's scan reads its own secret. When the secret parses as JSON, every string leaf is a needle (the id, access and refresh tokens and the account id); otherwise the whole value is one needle. Further needles: the Anthropic token shape, an OpenAI key shape, a JWT shape, and any value of `creator_user_id` or `creator_account_id`. A hit exits 1 and uploads nothing, and the output names the file, never the needle. Test: E2E, `tests/e2e/test_evals_scripts.py` (one row per needle kind, and a row whose output holds no needle).
- AC4.6 The job summary prints one row per (harness, task), with these columns:
  - passes of 3, the floor and the verdict;
  - errored trials, in their own column: an errored or missing trial is a fail for the floor;
  - pass^3 = C(c,3)/C(n,3);
  - the Wilson 95% interval.

  `aggregate` appends the table to `$GITHUB_STEP_SUMMARY`. Test: E2E, `tests/e2e/test_evals_scripts.py`, with the literals 3/3 → pass^3 1, [0.44, 1.00]; 2/3 → pass^3 0, [0.21, 0.94]; 0/3 → pass^3 0, [0.00, 0.56].
- AC4.7 The floors are the same for both harnesses (R1): T1 3/3, T2 ≥ 2/3, T3 ≥ 2/3. If any (harness, task) is below its floor, `aggregate` exits 1. The run is green only when `prepare`, every leg and `aggregate` succeeded. Test: E2E, `tests/e2e/test_evals_scripts.py` (harness-keyed floor rows); the run on E.

### FR5 — the gate

- AC5.1 `ci.yml` gains a model-free `Eval gate` job: no secret expression, no model CLI, permissions `contents: read` and `actions: read`. It runs on a `pull_request` whose base is `main` and is skipped on every other event. Test: unit (the existing outside-eval rows of `no-model-api-in-ci` refuse a secret in `ci.yml`).
- AC5.2 `Eval gate` passes only when there is a `success` run of `eval.yml`, with event `workflow_dispatch` or `schedule`, on a sha E such that `git diff --name-only E <PR head>` lists only these paths (ADR 0277 (2)):
  - `specs/releases/<live>/_RELEASE.json`;
  - `CHANGELOG.md`;
  - `.release-please-manifest.json`;
  - `pyproject.toml`, with only its `version` line changed.

  On a pass it prints E and the run URL. Otherwise it exits 1 with one fix line naming the dispatch of `eval.yml` on the PR head's work branch. The rule is a tree diff, not a first-parent walk, because develop advances by merge commits. Test: E2E, the gate script's rows, with a fake `gh` and a git fixture:
  - an allowed diff passes;
  - a code change after E fails;
  - a `pyproject.toml` change beyond the version line fails;
  - a red run, a missing run and a non-dispatch, non-schedule run each fail.
- AC5.3 `Eval gate` is listed in `.github/required-checks.json`. The operator applies it to `main`'s branch protection (ADR 0078). Test: unit (`required-checks-listed`).

### FR6 — Codex auth

- AC6.1 The Codex leg authenticates with the `CODEX_AUTH_JSON` ChatGPT login (R4). It writes the secret to a 0600 file under `$RUNNER_TEMP` and passes that path as `CODEX_AUTH_JSON_PATH`. The file never lies under `evals/jobs/`. Test: E2E (the run on E; AC4.5's scan is the proof of absence).
- AC6.2 A re-seed procedure is written in one doc home, which AC1.3's error names. It covers a dedicated login, the secret set from a real terminal and never printed, and a re-dispatch of the red legs. Test: none (doc text).

### FR7 — the ADR (R5)

- AC7.1 One ADR record is proposed (`docs(adr): propose …`) with the text below; its acceptance is the operator's (`specs/ADRs/AGENTS.md` §2). Test: none; `doctor` `LEDGER-ADR-SCHEMA`.
  - **Title:** "The deploy gate is the multi-harness eval pipeline: Claude Code and Codex legs at k=3 on sha E, read by a required Eval gate check on the promote PR".
  - **Decision:**
    1. `eval.yml` is `prepare` → one leg per (harness, task) → `aggregate`. The Claude Code and Codex legs gate at T1 3/3, T2 ≥ 2/3 and T3 ≥ 2/3 each, candidate-only (ADR 0274).
    2. A model is called only in `eval.yml`, on dispatch or schedule, with each leg's one secret at job level and the scan before any upload: 0217 (2), applied per job.
    3. The model-free `Eval gate` job in `ci.yml`, required on every PR into `main`, passes only with a green `eval.yml` run on a sha E whose diff to the PR head lies in 0277 (2)'s allowed set. It replaces 0178's and 0269 (c)'s `evals/gate` status rather than deferring it, and it lands in 0.5.0.
    4. Codex authenticates with the `CODEX_AUTH_JSON` ChatGPT login and a written re-seed procedure.
    5. No uploaded artifact holds a secret or an account id. Codex raw rollouts are dropped after the in-leg compare.
    6. The OpenCode lane follows the operator's validation of this pipeline.
  - **Relations:** it supersedes the live parts of 0269 and 0277, amends 0217 (3) (the lane set) and 0178 ((1), (5) mechanized; (4) stays the human read), rejects 0225 as subsumed, and rules 0269 (c)'s 0.6.0 deferral into 0.5.0.

### FR8 — guards

- AC8.1 `no-model-api-in-ci` changes only as the multi-job shape needs:
  - `actions/download-artifact@` is allowed;
  - the wheel artifact path is allowed;
  - `summary-unscanned` judges only a job that publishes.

  Every other rule holds unchanged, per job. Test: unit, planted rows: a non-allowlisted action, an upload of another path, and a publishing job without the scan line each still trip.
- AC8.2 `eval-cli-pin`: the Claude Code pin stays `env.CLAUDE_CODE_VERSION`, equal to every Dockerfile `ARG`. A matrix row without a CLI version trips the guard. Test: unit (a planted row).
- AC8.3 No planted row is deleted or loosened. A re-pointed anchor still trips its rule. Test: unit (every pre-existing planted-row id is present and trips); the reviewer reads the diff.

### FR9 — law and memory (closure)

- AC9.1 The closure memory pass (`MEMORY-UPDATE.md`) rewrites the atoms whose sources changed:
  - `specs/memory/product/distribution/agent-evals.md`: the stages, the harness axis, the per-harness forged rule and the gate;
  - `QUALITY.md` P-33, `pypi-distribution.md` and `ARCHITECTURE.md`'s ADR list;
  - the atoms the session-check hotfix left stale: `specs/memory/product/platform/context-management.md:59` (the session store creates the record), `specs/memory/product/philosophy/product-vision.md:15`, and the rest of the main-thread intake's list.

  Test: none; `memory.py check` and `doctor`.

### Replaces

- The single `eval` job: one harness, one secret, the wheel built in-job, and `-n 2` over nine trials. FR1, FR2 and FR4 replace it.
- `compare.py`'s Claude-only forged check, and its floors and table with no harness axis. FR4 replaces them.
- `scan.py`'s one plain-text secret needle. AC4.5 replaces it.
- The manual-read gate: ADR 0178 (4) as the gate, and 0269 (c)'s deferred `evals/gate` status. FR5 replaces it; the operator's read stays a human read at `release-gate`.

## 5. Constraints and risks

- **ChatGPT refresh rotation (R4).** A CI refresh can invalidate the operator's local login or the secret copy (measured: `last_refresh` renewed by age after 8 days). The gate is then red until the secret is re-seeded (AC6.2). OpenAI's docs recommend an API key for CI; the operator was told this and kept the login.
- **PUBLIC artifacts.** The repo is public, so every uploaded artifact is downloadable. Codex rollouts carry account ids, which is why AC4.4 and AC4.5 exist and the scan precedes every upload.
- **Cost per run.** Claude Code $16.29, measured on run 40050879271 (harbor's `cost_usd`, notional under subscription auth). Codex $1.49 notional, on the local readout. A rerun of one red leg costs that leg alone.
- **Wall time.** 31–37 min today (runs 39462036716 and 40050879271). About 18 min is estimated for the matrix: the slowest leg, T3 Claude at 15.3 min plus setup. This is unverified, as are the runner concurrency limit and the Claude OAuth rate limit across concurrent legs.
- **Codex T3, measured 0/3 on the local readout.** The grader reported `specs not initialized` and `no valid backlog entry or SPEC`. Under R1's floors, goal 2 stays red until the cause is known. The PLAN carries a read-only diagnosis. A product contract break goes to the operator as an Arm B proposal, and no floor moves.
- **Claude T3 on run 40050879271** was red on forged verdicts: 3/3 trials wrote a verdict outside the reviewer. The session-check hotfix now refuses that act outside the workspace root, and the first run on E measures T3 after it.
- **The hotfix's residual.** On Codex, the product refuses no forged verdict, so AC4.2 is that harness's only guard.
- **Operator acts.** The operator accepts the ADR (FR7) and applies branch protection (AC5.3); the PLAN batches them into one question.

## 6. Open questions

None open at approval. R0–R6 rule the scope, and the grill handoff's agent defaults (shared wheel, no self-test rerun, privacy, statistics, reds, task variants, ADR shape) land as FR1, FR4, AC2.4, FR3 and FR7.
