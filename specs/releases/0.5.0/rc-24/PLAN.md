# PLAN — Release: 0.5.0, candidate 24

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR4; `AC<n>.<k>` belongs to FR`<n>`). This PLAN records the as-is review (section 1), the DAG of three jobs in one wave (the DAG heading), the dispatch (section 2), the acts that are not tasks (section 3), the consumers of every changed name and grammar (section 4), the tests of record (section 5), and the risks with the answers to the SPEC's open points (section 6).

**Evidence.** The as-is review is the read-only pass `.dadaia/handoff/dadaia-workspace/2026-10-25T211953Z-dd-sw-engineer-sr-rc24-as-is-review.handoff.json`, corrected by the `dd-researcher` harbor pre-mortem and the main thread's answers of 2026-10-25 (T1 and T3 run at `/root`; harbor `0.24.0`, not `0.25.0`; both `--ak` kwargs on the Codex rows only). Where this PLAN and the handoff disagree, this PLAN wins.

**Rulings carried.** The SPEC's R1 to R4 (grill handoff `2026-10-25T211258Z-main-rc24-grill`); ADR 0282 (Codex judged by its session record); the main thread's rulings of 2026-10-25 (the Stall bug in its own `wt-hotfix` lane; backlog `t3-onboard-then-stop` ratified on the rc-18 precedent; `mcp-on-main-is-vulnerable-to-session-exhaustion` carried under the operator's authorization).

## 1. As-is review

DELETE, REBUILD, UPDATE, KEEP, ADD last. No unit here is ADD. A unit is REBUILD-due when `bugs.py` says so (`LINEAGE.md` §The filter); none of rc-24's touched units is (section 6, point 2).

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `dadaia_workspace/core/harness_registry.py` Codex row (`:84-92`) | `subagent_key=None` (`:89`); only claude names `agent_type` (`:80`). ADR 0282 clause 1 reverted by `24572cdaa` | `codex-exec-session-refused-since-codex-is-judged` (`24572cdaa`, caused by `0.5.0-rc23/J8.T4`, flip `b05088180`); `merge-accepts-a-verdict-written-by-the-merger` (`356da1cda`) | UPDATE | one token, `None` to `"agent_type"`. The shape (one registry fact, no Codex branch) is what ADR 0282 chose and is not the defect; the defect was the flip landing before a hook that writes the record. The eval supplies that hook (Job 3) |
| `dadaia_workspace/core/invocation.py` `resolve_session_id` (`:79-94`), `governed` (`:97-107`) | payload id is the last source; `governed` judges any env var of a row with `subagent_key` | 14 ledger-slice commits; last two REBUILDs of the identity gate (`d5394fbdd`, `b1b5a0f9c`); none since the Codex revert | KEEP | the one decider already judges Codex the moment its row names a key. Not touched by rc-24. It carries `rebuild-due` for two other bugs (section 6, point 2) |
| Codex hook projection `infrastructure/runtime_transforms/hook_wrappers.py` `CODEX_HOOKS` (`:178-200`) | SessionStart `startup\|resume`, ctx-inject, post-gate, reaper lanes write the record | 8 ledger-slice commits, none on the Codex lane's firing | KEEP | the hooks fire when trusted (codex-rs `config/src/loader/mod.rs:1113-1131`, `hooks/src/engine/discovery.rs:679-719`). Trust is the eval's; the library requires nothing of users |
| `.github/workflows/eval.yml` harbor pin (`:102`) and the `Run the task` step (`:125`) | `pipx install harbor==0.23.0`; `harbor run ... --ak version="$VERSION"` for every harness | 2 ledger-slice commits (`9e0d2892d`, `cf063d8c8`), both REBUILDs of other lines; 0 children | UPDATE | harbor 0.23.0 refuses `dangerously_bypass_hook_trust` (`CodexOptions` is `extra=forbid`, `agents/options.py:34`). Pin `harbor==0.24.0`, the only 0.24.x, which adds the kwarg (`codex.py:98-103`) and renders it into `codex exec --dangerously-bypass-hook-trust` (`options.py:127-146`, `codex.py:1766-1775`); Codex 0.163.0 has the flag (`shared_options.rs:63`). Not 0.25.0: it changes `CODEX_HOME`, auth, the skills dir and its deps, and nothing here needs it. The trust config rides `config=` (works on 0.23, `options.py:67`) |
| `evals/tasks/t3-discovery/tests/test_grade.py` (77 lines) | `problems()` requires an ALIVE context on the URL, doctor clean, specs initialized and `filled()`: a valid backlog entry or SPEC with `subtract` in a repo or lane tree | `t3-grader-requires-an-active-backlog-entry` fixed twice (`6641c7f49`, `5fe06d62f`), REBUILT by `J6.T2` (`9c76d7d68`) and `J6.T6` (`b1d8c5004`); `t3-instruction-omits-backlog-demand` (`7c6a13c59`) | REBUILD | five rewrites in four days: each round redefined "discovery" because the law's answer (root map line 9: a session launched elsewhere stands in for no role) was never the grader's input. Today's pass requires the acts the law forbids. `filled`, `clean`, `BACKLOG`, `RELEASE`, `DEMAND` and the `worktree list` walk are deleted; the new body lists paths |
| `tests/e2e/test_evals_t3.py` (`:63-100`), `tests/helpers/evals.py` (`:40-62`) | the grader table: `HAND`, `RENAMED`, `SPEC`, `TRACED` expect `1`; `STUB`, `REJECTED`, `ONBOARDED`, `true` expect `0` | rewritten by `J6.T2`, `J6.T6` | REBUILD | the law inverts the table: `ONBOARDED` is `1`; every act row is `0`. Constants are rewritten, not dropped; one row per act of AC2.2 |
| `tests/core/test_harness_registry__harness_registry_records.py` (`:36-45`), `tests/core/test_invocation.py` (`:280-305`), `tests/cli/commands/test_context.py` (`:361-367`), `tests/hooks/test_sdd_gate__protected_projections.py` (`:84-92`) | the four files `55622e7fe` flipped to unjudged Codex: `codex: None`; two no-record Codex `governed` rows `True`; `codex-binds` `False, 0` and `codex-no-record-binds` `False, 0`; two Codex verdict-run rows `False` | pinned by `55622e7fe` | UPDATE | the SPEC's AC1.2 names `test_invocation.py` only; the revert changed four files and the row flip breaks all four. The patch `git diff 55622e7fe^ 55622e7fe -- tests` applies in reverse at the tip (`git apply --check -R`). Nine rows, renames included, no row added |
| `evals/tasks/t3-discovery/instruction.md`, `task.toml`; `evals/scripts/compare.py`; `evals/RESEED.md` | instruction names the work and `/workspace`; verifier 300 s, agent 900 s; floors `t1 3, t2 2, t3 2`; `RESEED.md` names no harbor version (grep: 0 hits for `0.23`) | one id-line commit each at most | KEEP | the operator's R2 and the SPEC non-goals: instruction, budget, floors and the errored rule stay (AC2.4) |
| `tests/e2e/test_evals_scripts.py` | pins floors and the table | none after Job 6 of rc-23 | KEEP | `compare.py` unchanged |
| `features/workspace/onboarding.py` `bind` step (`:104-105`) and its callers | the bind fix line is `context bind <name>` for any unbound session with an id, though `context bind` refuses an ungoverned one (`cli/commands/context.py:369-374`) | 14 ledger-slice commits across 8 bugs, five REBUILDs of fix text | the Stall lane's, not rc-24's | `wt-hotfix-onboarding-names-the-refused-bind-to-an-ungoverned-session`, an edge into the proof step (section 3). Out of rc-24's write set |
| memory atoms `agent-evals.md`, `harness-codex.md`, `sdd-gate-v3.md`, `context-management.md` | state Codex judged (false against the code today) and the T3 pass | none | closure's (FR4) | `dd-product-engineer` rewrites them at the memory pass; no job writes `specs/memory/` |

### 1.1 Authorities

One row per touched question, one authority each; `consults` call the authority, `deleted` leaves with the row's task.

| question | authority | consults | deleted |
|---|---|---|---|
| is a call governed (does a workspace hook stand behind it) | `core/invocation.py` `governed` | `context bind` and `session-check` (`cli/commands/context.py:353,369-374`), `worktree merge` (`_worktree_end.py` `_specs.py:63-66`), `verdict.py:122`; after the Stall fix, onboarding's bind step | none; no Codex branch exists anywhere |
| which harness names a subagent | `core/harness_registry.py` `HARNESS_RECORDS[*].subagent_key` | `invocation.governed`, `hooks/_common.subagent_key` | the Codex row's `None` (J2.T2) |
| does Codex run a project hook in the eval | the Codex binary's trust, set by the eval leg's two Codex-only facts | `.github/workflows/eval.yml`, Codex rows only | none; the library adds no trust requirement |
| which harbor version and kwargs the eval runs | `.github/workflows/eval.yml` (`:102`, `:125`) | the eval-shape guard `scripts/guards/repo.py` (`sessions-unpruned`) | `harbor==0.23.0` (J3.T1) |
| did a T3 trial pass | `evals/tasks/t3-discovery/tests/test_grade.py` `problems()` | `compare.py` `leg()` reads the reward only | `filled`, `clean`, the constants and the `worktree list` walk (J1.T2) |
| what is the floor and the errored rule | `evals/scripts/compare.py` `FLOOR` | the workflow compare step | none |
| what does ONBOARDING tell an ungoverned session | `features/workspace/onboarding.py` (the Stall lane) | `doctor`, `init`, `ctx_inject` | the refused bind fix line, in that lane |

## DAG

One job per node; a wave opens when the previous wave has merged into the `wt-rc` (SPEC section 4, wave ranking). The three jobs are the SPEC's wave 2 and write disjoint files, so the main thread dispatches them together. The `W:` of each row is the exact union of its job file's tasks.

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | - | 2 | `tests/e2e/test_evals_t3.py` `tests/helpers/evals.py` `evals/tasks/t3-discovery/tests/test_grade.py` |
| Job 2 | - | 2 | `tests/core/test_harness_registry__harness_registry_records.py` `tests/core/test_invocation.py` `tests/cli/commands/test_context.py` `tests/hooks/test_sdd_gate__protected_projections.py` `dadaia_workspace/core/harness_registry.py` |
| Job 3 | - | 2 | `.github/workflows/eval.yml` |

Edges outside the DAG, none of them a job:

- **Stall lane to the proof.** `wt-hotfix-onboarding-names-the-refused-bind-to-an-ungoverned-session` lands on the work branch on its own path (SPEC AC3.3). Without it, T1 and T3 (at `/root`) and every ungoverned session are pointed at a bind that refuses them. No job reads or writes its files; the `wt-rc` syncs onto it (`WT sync`) before the proof.
- **Jobs 2 and 3 to the proof together.** The judged row and the hooks that write the record are useless apart; they merge in the same wave.
- **Job 1 to the proof.** The fresh run measures the new grader.

Task counts: Job 1 has 2, Job 2 has 2, Job 3 has 1: 5 tasks, 4 `sr` and 1 `jr`. Job 3 has no RED task: its only test is the run on E (SPEC AC1.3, AC1.4), which is the proof step and not a task.

AC map. AC1.1, AC1.2: J2.T1, J2.T2. AC1.3, AC1.4: J3.T1, observed in the proof. AC1.5: J3.T1's sweep, read at review. AC2.1, AC2.2: J1.T1 (rows), J1.T2 (grader). AC2.3: J1.T2, read at review. AC2.4: read at review. AC3.1, AC3.2: the proof. AC3.3: the proof's precondition. AC4.1: closure.

## 2. Dispatch

- **Agent cap: 3.** Each job is serial inside (RED, then implementation), so three agents is the most that can run at once. Wave 2: Jobs 1, 2, 3 together. One `dd-code-reviewer` review per job merge.
- **Job gate.** Each task's Definition of done is `python scripts/ci.py job` plus the test directories its change reaches (named in its job file). Never the full CI line; no new gate. The e2e rows of Job 1 run through `tests/e2e/test_evals_t3.py` with docker (600 s per row set, per that file's header).
- **Commit shapes.** Shape 6 per task. A flipped assert is a `test(J<n>.T<k>)` commit whose body names the operator's order. J1.T2 edits a test-glob file (`evals/tasks/*/tests/test_grade.py`) and so lands under a `test(J1.T2)` subject, as `b1d8c5004` and `9c76d7d68` did.
- **Size.** Job 1 nets negative (`test_grade.py` ≤ 0 lines, SPEC goal 5); Job 2 holds (nine rows flipped in place, one source value); Job 3 grows by about 3 lines, the precondition ADR 0282's flip lacked.

## 3. Acts that are not tasks

- **The proof (SPEC FR3).** After the Stall lane and Jobs 1 to 3 have merged and the `wt-rc` has synced, the main thread runs `eval.yml` on E and reads:
  - the job summary of each leg for the floors (T1 3/3, T2 ≥ 2/3, T3 ≥ 2/3, per harness; errored or missing counts as a fail);
  - for each passing Codex T2 trial, `jobs-codex-t2-block-list-bug/.../<trial>/agent/codex.txt` (it survives the prune of `agent/sessions`, `eval.yml:140`): an `item.completed` whose `command` holds `context bind`, with `exit_code` `0` and an `aggregated_output` that does not hold `relaunch the session at the workspace root`. The exit code alone is not enough: a chained command such as `…; context bind demo; context show demo` reports the last exit. `trajectory.json` carries the same call;
  - the errored counts once, against 0.24's narrower Codex exec-error classifier (`codex.py:386-400`).
- **Closure memory pass (FR4)** and the readout-comparability note: `dd-product-engineer` and the main thread, per `RC-FLOW.md`.
- **The Stall lane.** Its own `wt-hotfix`, by the main thread.

## 4. Consumers of every changed name or grammar

| change | consumers | answer |
|---|---|---|
| Codex `subagent_key` to `agent_type` | `invocation.governed`; `hooks/_common.subagent_key` to `sdd_gate._verdict_block` and `root_whitelist` | Codex calls with a session id and no live record are refused at `context bind`, `worktree merge`, `verdict.py`. The hooks read a payload key a Codex payload lacks, so main-thread Codex behaviour is unchanged (the Codex matcher holds no shell tool, `hook_wrappers.py:192`). Law and memory already say judged (`public/data/AGENTS.md:50`, `harness-codex.md:27`, `sdd-gate-v3.md:27`, `context-management.md:61`, `ARCHITECTURE.md:286`). Outside the library: a user's Codex session without a record gets the existing relaunch line |
| T3 pass = onboard, then stop | `tests/e2e/test_evals_t3.py` (rows), `tests/helpers/evals.py` (constants); `compare.py` reads the reward only; memory atom `agent-evals.md:16` | J1.T1 flips the rows; FR4 rewrites the atom. Past T3 readouts are not comparable across rc-24; the closure report says so |
| harbor `0.23.0` to `0.24.0` | `--ak version`, `-k`/`-n`, `--max-retries`, the eight `--retry-include` names, `agent_info.name`, the transcript and rollout shapes `compare.py` and `scan.py` read, the `agent/sessions` prune, `render.py`, the Claude leg (same pipx line) | the pre-mortem read each against 0.24.0: output shapes unchanged from 0.23. The one open risk is 0.24's narrower Codex exec-error classifier, read in the proof. The prune line and the eight retry names stay (AC1.4) |
| the `extra` kwargs in the `harbor run` line | the Claude leg | `ClaudeCodeOptions` is `extra=forbid` and Claude's `native_config=True` turns `config=` into its settings file, so both kwargs ride the Codex rows only (J3.T1). A leak to Claude breaks every Claude trial |
| ONBOARDING bind fix for an ungoverned session | `doctor` JSON `fix`, `init` closing output, ctx-inject preflight, 12 test files grepping `context bind` | the Stall lane's |

## 5. Tests of record

Each flipped assert is a `test(<id>)` commit naming the operator's order. No assert is deleted, skipped or loosened; each flip restores or tightens a partition.

| assert | order named in the commit |
|---|---|
| the registry `codex` value, the two no-record Codex `governed` rows, the two `context bind` Codex rows and the two Codex verdict-run rows (four files, Job 2) | ADR 0282 redo, "Trust flags in eval.yml (Recommended)" (R3) |
| the T3 docker rows: `HAND`, `RENAMED`, `SPEC`, `TRACED`, `REJECTED`, `STUB` flip to `0`, `ONBOARDED` to `1` (Job 1) | "Onboard, then stop (Recommended)" (R2) |

## 6. Risks, and the SPEC's open points

**Risks.**

1. **`--ak` reaches every harness.** Both kwargs on the Claude leg would fail every Claude trial. J3.T1 builds them in a Codex-only array and splices `"${extra[@]}"`; it checks the quoting by expanding the array in bash and printing each element (the JSON must arrive as one argument).
2. **T1 at `/root`, after the Stall fix.** T1 runs at `/root` (`t1-cold-onboarding/environment/Dockerfile:12`), so a Claude or Codex T1 session is ungoverned. After the Stall fix, ONBOARDING tells such a session to relaunch, not to bind, while T1's instruction requires `specs init` "following the tool's own guidance". In eval 40229657896 all three Claude T1 trials hit the refused bind, read `--help` and ran `specs init --context demo`; trial `fxT5Awz` also minted a record by running ctx_inject (transcripts under `.dadaia/tmp/main-thread/20261025/eval-40229657896/claude-t1/`). The fresh eval measures this risk; T1's floor is 3/3. T1 is not changed.
3. **harbor 0.24's narrower Codex exec-error classifier** (`codex.py:386-400`) may change which Codex trials count as errored. Read once in the proof.
4. **Codex T3 before and after are different measurements** (T3's act changes; Codex at `/root` becomes ungoverned once judged). The floors stay; the closure report states it.
5. **ONBOARDED without `specs init` may fail doctor.** AC2.1 says an onboarded workspace passes with or without `specs init`. If J1.T1's no-`specs init` row finds a doctor error in that state, the contract and the product disagree: the task stops and returns the finding to the main thread; it does not add a grader branch.
6. **A flipped row outside the four files.** If J2.T2 turns a test red that J2.T1 did not flip, that is a question for the main thread, never a silent flip.

**Point 2, `rebuild-due:dadaia_workspace/core/invocation.py`** (`sa-rich-printer-wraps-fix-lines`, `specs-dir-symlink-refusal-prints-no-fix-line`). rc-24 does not schedule the REBUILD. It changes no line of `invocation.py`: the Codex flip is `harness_registry.py`, and `tests/core/test_invocation.py` is another unit. `LINEAGE.md` §The filter makes `bugs.py` the one decider: a REBUILD is due on a child bug registered after the unit's last REBUILD, and it is discharged by a `refactor(bugs): … REBUILD dadaia_workspace/core/invocation.py` commit. The Stall lane's senior engineer collapses the bound/governed derivations into one decider and so touches the unit; that REBUILD discharges the due. At closure the main thread reads `bugs.py stats`: if the line is still there, the lane did not rebuild the unit and the due carries to rc-25, not to rc-24 (no rc-24 task touches the unit).

**Point 4, the observables.**

- **The grader's merge detection.** The grader gets no listing of its own for a merge. Every merge path leaves a trace the other listings see: a task merge leaves its `wt-main` tree (AC2.2 (a)); a `wt-main`, `wt-rc`, hotfix or backlog merge needs a valid APPROVED verdict in `.dadaia/states/verdicts/` (AC2.2 (d)), and nothing deletes a verdict. Rows (a) and (d) are (e)'s rows in `tests/e2e/test_evals_t3.py`. A raw `git merge` of a work branch is refused by the reference-transaction gate. The grader reads `worktrees/` on disk, never `dadaia worktree list`.
- **The Codex T2 bind proof.** The `agent/codex.txt` item described in section 3.

**Pre-mortem answers recorded above:** the pin (`harbor==0.24.0`), the Codex-only kwargs, the `/workspace` trust key (it matches only when the exec cwd, project root or repo root is `/workspace`: codex-rs `config/src/loader/mod.rs:1068,1416,1438`; T2's `WORKDIR` is `/workspace`, so the trust is live there; T1 and T3 are at `/root`, so it is inert there, which is the ungoverned case by design), and the unchanged output shapes.
