# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-25
**Origin:** backlog:codex-judged-by-session-record-redo,t3-onboard-then-stop

---

## Bug window review

**Window:** every record closed after rc-23's window review (rc-23 born 2026-10-24T04:00:53Z, `_RELEASE.json` log), read in `BUGS.jsonl` and `_archive/bugs_histo.jsonl` at `27c3be2be`: 16 resolved, none rejected or superseded. Each fix is found by its id line (`git log -F --grep '<id>'`, the `fix(bugs)`/`refactor(bugs)` commit the resolve names). Net lines are `git show --numstat`.

| fix (ids) | fix commits | reading | verdict |
|---|---|---|---|
| eval-claude-leg-publishes-the-claude-config-dir | `9e0d2892d` (+7 −3); RED `6d8495f70` | One prune line for every leg replaces a Codex-only one. No assert changed. | KEEP. FR1's pin bump keeps that line (AC1.4). |
| codex-exec-session-refused-since-codex-is-judged | `24572cdaa` (one value); RED `55622e7fe` (9 rows flipped) | The revert of `0.5.0-rc23/J8.T4`, under the operator's red-CI ruling "Revert J8.T4 (Recomendado)". The flipped rows were named in that ruling. The structure (one `governed` decider, one registry fact) was not the defect. The flip landed before its precondition, a hook that can write the record. | KEEP the revert. FR1 is the redo with its precondition. |
| worktree-merge-refuses-a-patch-identical-job-after-sync; its child verdict-carries-over-a-hand-dropped-bottom-commit; merge-lands-the-branch-tip-not-the-judged-head | `68010611f` (+2); `284794d5f` (+5), `82c2c255b` (0), `41bf7c132` (+2); REDs `a32bbb1b1`, `baed66a37`, `033728d59`, `2593f941f`, `5bcab8e83` | A child bug after a REBUILD of the same series binding, then three REBUILD rounds in one lane. Each round narrows one decider (`_check_approved`'s series), and none adds a path. No assert was loosened. `bugs.py stats` reports no REBUILD due on the unit. | KEEP. The chain converged on one decider. |
| drop-leaves-an-orphan-tree-when-worktree-remove-fails, new-onto-a-leftover-folder-leaves-a-branch-no-fix-clears, new-over-a-paused-lane-loses-its-bundle, resume-fix-lines-loop-after-the-state-table-rebuild | first lane reverted whole (`c2538cc17`, −528); redo `f92e0ea4d` (+96); earlier `c878373a8` (+10) absorbed by it | The first state-table lane bred `resume-fix-lines-loop-…` and was reverted. Its redo grows by 96, but it replaces each verb's own decision of a lane path with one state table. The asserts the revert dropped were that lane's own REDs. | KEEP. The growth buys one decider in place of six. |
| worktrees-law-restates-the-state-table-fix-lines (caused by the state-table lane) | `fd2721d39` (−12), `7ae3f2c74` (+1) | Two leftover copies of the table, in sync and `hash`, were deleted into it. | KEEP. A deletion. |
| memory-lint-flags-a-dependency-version-pinned-in-prose | `91b59bcba` (+7) | One release-id decider now reads `specs/releases/`. | KEEP |
| release-memory-worklist-path-denylisted-blocks-closure | `bb06477a1` (+11) | One decider of a valid entry. The demanded unit path is deleted. | KEEP |
| memory-drift-counts-the-specs-backup-as-code-units | `b718413c0` (0) | One exclusion in the one unit walker | KEEP |
| pr-platform-legs-red-on-host-specific-test-literals | `1061621ac` (+6, tests only) | Asserts changed, under a main-thread ruling named in the commit. Each assert keeps its partition, and only the host spelling follows the injected platform. The 31 → 32 is the measured Windows count. | KEEP |
| registry-load-raises-permissionerror-during-a-save-on-windows | `ec6d1d095` (+6) | A retry inside `_platform.read_text`, the one platform boundary | KEEP |
| rebuild-due-reads-subjects-where-the-fix-reader-reads-the-message | `60b710e5f` (+8) | REBUILD-due now reads the grammar `fix_commit` reads: one grammar, not two | KEEP |

**Overfitting check:** every changed assert names its ruling: the operator's revert, or the main thread's platform-literal ruling. No special case keys on a test value. The two growing fixes, the state table and the platform retry, each collapse deciders into one home. No fix is judged REBUILD, so no bug is proposed.

## 1. Problem

The operator's words (grill handoff `2026-10-25T211258Z-main-rc24-grill`, AskUserQuestion, 2026-10-25):

- R1, scope: "rc-24: fix both (Recommended)".
- R2, T3: "Onboard, then stop (Recommended)".
- R3, Codex: "Trust flags in eval.yml (Recommended)".
- R4, the summary: "Confirm (Recommended)".

Eval run 40229657896 on E = `27c3be2be` failed only on T3. T1 and T2 passed on both harnesses. T3 scored Claude Code 0/3 and Codex 1/3. Over runs 40147248892, 40219841627 and 40229657896, Claude Code passed 2 of 9 T3 trials and Codex 5 of 9.

Two gaps cause this.

- **Codex is not judged.** The ADR 0282 row flip (`0.5.0-rc23/J8.T4`) was reverted. In the eval, headless `codex exec` ran no project hook and so wrote no session record, and judging Codex then refused every CI Codex session (run 40125254038). The broken link is trust, not the id rule:
  - Codex 0.163 runs a project hook only for a trusted project with trusted hook hashes (codex-rs `config/src/loader/mod.rs:1113-1131`, `hooks/src/engine/discovery.rs:679-681,713-719`).
  - The eval's fresh `CODEX_HOME` has neither.
  - ADR 0282 clause 2, the payload id as the last source, is already at `core/invocation.py:85-94`.
  - So the Codex row names no subagent key (`core/harness_registry.py:89`), and ADR 0282's `measured_by` does not hold.
- **The T3 grader contradicts the law.** The T3 image runs the agent in `/root` (`environment/Dockerfile:12`). By root map line 9, a session launched there stands in for no role. Yet the grader (`evals/tasks/t3-discovery/tests/test_grade.py:63-72`) passes only a trial that went on to file a backlog entry or SPEC, which is the release flow that session may not run. This 77-line grader was rewritten five times in four days, each round redefining "discovery" (as-is review, bug-history audit B). The law's own answer was never the grader's input.

## 2. Measurable goals

| # | goal | target | source |
|---|---|---|---|
| 1 | Codex is judged again | the Codex row of `core/harness_registry.py` names `agent_type`, so ADR 0282's `measured_by` holds | that file at E; `tests/core/test_harness_registry__harness_registry_records.py` |
| 2 | a Codex session in the eval writes its record | in the fresh `eval.yml` run on E, each passing Codex T2 trial shows `dadaia context bind` exiting 0 | that run's Codex T2 trial logs |
| 3 | T3 measures onboard-then-stop | both harnesses at T3 ≥ 2/3 under the new grader | the same run's job summary |
| 4 | the floors hold | Claude Code and Codex each at T1 3/3, T2 ≥ 2/3 and T3 ≥ 2/3 in one `eval.yml` run on E (rc-23 AC4.7) | the same job summary |
| 5 | rc-24 does not grow the library | no file under `dadaia_workspace/` gains a line; `test_grade.py` nets ≤ 0 | `git diff --numstat <rc-24 base>..E` |

## 3. Non-goals

- **The Stall bug** `onboarding-names-the-refused-bind-to-an-ungoverned-session`, CRITICAL. Its registration is in review, and it is fixed in its own `wt-hotfix` lane (`specs/bugs/AGENTS.md:21`). rc-24 names it only as a dependency of the fresh eval (§5).
- **ADR 0282's ad-hoc-subagent residual.** Inside a governed session, an ad-hoc subagent can still write a verdict. `compare.py`'s forged check stays its measure. It goes to the backlog after the promote (R4).
- **The circumvention of the session record**, where a trial runs the hook module with its own id or sets `DADAIA_SESSION_ID`. A caller controls its own environment and files (root map line 50). The T3 grader measures it (AC2.2), and the product does not close it.
- **Rewriting the T3 instruction.** It still says "keep using it to organise the work". Rewriting it would measure instruction-following instead of the tool's steering (R4).
- **A change of floor, of the errored rule or of the 900 s budget.**
- **A guard row or CI check for the trust flags.** The run on E is their proof.
- **Shell-tool PreToolUse parity on Codex.** ADR 0282 named it a non-goal.
- **The intake LOWs.** They go to the backlog after the promote (R4).

## 4. Requirements

**Wave ranking** (each wave opens when the previous one has merged):

1. Law, skills and dev loop: none. Root map lines 9 and 50 already state that Codex is judged, and rc-24 changes no law line.
2. Shared foundation, the judge and the measure: FR1 (the registry row, and the eval Codex leg with its pinned harbor) and FR2 (the T3 grader), dispatched together because their write sets are disjoint.
3. Features and bugs: none in rc-24. The Stall bug's lane lands on the work branch on its own path, and the `wt-rc` syncs onto it before wave 4.
4. Promote-facing: FR3, the fresh run on E; then FR4, at closure.

Task names: `T1` cold-onboarding, `T2` block-list-bug and `T3` discovery. A "leg" is one job of the eval matrix, for one (harness, task). The words "the run on E" mean one `eval.yml` run on the sha E that this candidate's closure names.

### FR1 — Codex is judged by its session record (backlog `codex-judged-by-session-record-redo`; R1, R3)

The operator's words: "Trust flags in eval.yml (Recommended)". The handoff's text: "the Codex leg's harbor run gets dangerously_bypass_hook_trust=true and config projects./workspace.trust_level=trusted: only the workspace and the hooks the eval itself generated are trusted. No product change; the library requires nothing of users."

- AC1.1 The Codex row of `HARNESS_RECORDS` names `agent_type` as its subagent key, with no Codex branch anywhere: `governed` stays the one decider. Test: unit. The Codex value in `tests/core/test_harness_registry__harness_registry_records.py` flips from `None` to `"agent_type"`, in a `test(<id>)` commit that names R3 and ADR 0282.
- AC1.2 Suppose a call's env carries a Codex session id (`CODEX_SESSION_ID` or `CODEX_THREAD_ID`) and no live record of it exists under the workspace root. Then `context bind`, `verdict.py` and `worktree merge` refuse the call with `Operator action: relaunch the session at the workspace root`. With a live record, the call and a dispatched Codex subagent of that session pass. An operator terminal whose env carries only `DADAIA_SESSION_ID` is unchanged. Test: unit. The two no-record Codex rows of `tests/core/test_invocation.py` flip from governed to refused; every other row holds, and no row is added.
- AC1.3 Only the Codex leg's `harbor run` in `.github/workflows/eval.yml` carries the two trust facts:
  - the agent kwarg `dangerously_bypass_hook_trust=true`;
  - the Codex config `projects./workspace.trust_level=trusted`.

  The Claude Code leg carries neither. Test: E2E, the run on E (AC3.1 is the observable). The leg scoping is read at review.
- AC1.4 One `pipx install harbor==<v>` line pins a harbor whose Codex agent accepts `dangerously_bypass_hook_trust`. harbor 0.23.0 refuses the kwarg: `CodexOptions` is `extra="forbid"` (0.23.0 `agents/options.py:34`). The PLAN states `<v>` after a read-only `dd-researcher` pre-mortem, which precedes this SPEC's approval (`dd-release-definition` §2). The pre-mortem checks against `<v>` every harbor behaviour that `eval.yml`, `compare.py` and `render.py` use:
  - `--ak version`, `-k`/`-n` and `--max-retries`;
  - the eight `--retry-include` names (rc-23 AC2.4);
  - `agent_info.name` (`claude-code`, `codex`);
  - the Claude Code and Codex transcript and rollout shapes that `compare.py` reads;
  - the `agent/sessions` layout that the prune line drops;
  - the config kwarg's form.

  The prune line and every rc-23 AC2.4 retry name stay. Test: E2E, the run on E (every leg concludes and both harnesses' rows print); the pre-mortem itself is no test, it is a report the PLAN answers.
- AC1.5 The library requires nothing new of a user. No file under `dadaia_workspace/` names `trust_level` or `dangerously_bypass_hook_trust`. A user's Codex session that writes no record (for example an untrusted project) is refused with the law's existing fix line, as a Claude Code session launched outside the root is today. Test: none, because a test that greps the source tree is text, not behaviour. At review, `rg -n 'trust_level|dangerously_bypass_hook_trust' dadaia_workspace/` prints nothing.

### FR2 — T3 = onboard, then stop (backlog `t3-onboard-then-stop`; R2)

The operator's words: "Onboard, then stop (Recommended)". The handoff's text: "A T3 pass is one ALIVE context on file:///srv/demo.git, `dadaia doctor` with no error, and no act past onboarding: no worktree, no backlog entry or SPEC, no verdict, no merge, no session record the agent minted. specs init is allowed and not required."

- AC2.1 A T3 trial earns reward 1 exactly when:
  - `/workspace` holds one ALIVE context whose repo URL is `file:///srv/demo.git`;
  - `dadaia doctor --context <it>` reports no error;
  - AC2.2 finds no act.

  `specs init` decides nothing: an onboarded workspace passes with or without it. Test: E2E, `tests/e2e/test_evals_t3.py`. The onboarded fixture earns 1 both with and without `specs init`; no ALIVE context earns 0, and a doctor error earns 0.
- AC2.2 Each of these acts alone makes the reward 0:
  - (a) any entry under `/workspace/worktrees/`, read on disk and not through `worktree list`, so a broken registry cannot hide a tree;
  - (b) a backlog entry, meaning one in `active[]` or a line of `_archive/backlog_histo.jsonl`, in the main repo's `specs/backlog/`;
  - (c) any `specs/releases/*/rc-*/SPEC.md` in the main repo;
  - (d) any file under `/workspace/.dadaia/states/verdicts/`;
  - (e) a merge. A merge removes its tree, so (a) alone does not see it, and the PLAN names its observable;
  - (f) any session record under `/workspace/.dadaia/sessions/`. At `/root` no hook runs, so any record there was minted by the agent.

  Test: E2E, `tests/e2e/test_evals_t3.py`, one row per act, each beside an otherwise-passing onboarded fixture. The rows that today expect 1 for a backlog or SPEC trial (HAND, RENAMED, SPEC, TRACED) now expect 0. These test changes are `test(<id>)` commits that name R2.
- AC2.3 The grader shrinks to fit the rule. `filled`, `clean`, the `BACKLOG`, `RELEASE` and `DEMAND` constants and the `worktree list` walk leave `test_grade.py`, and the new check is set-difference on the listed paths, with no forged-versus-real branch. Test: none, because it is a size criterion. At review, `git diff --numstat` shows `test_grade.py` net ≤ 0.
- AC2.4 These stay unchanged:
  - `evals/tasks/t3-discovery/instruction.md`;
  - `evals/tasks/t3-discovery/task.toml` (agent 900 s);
  - `evals/scripts/compare.py`'s floors and errored rule (rc-23 AC4.6, AC4.7).

  Test: none, because it is a no-change criterion. At review, `git diff --name-only <rc-24 base>..E -- evals/tasks/t3-discovery/instruction.md evals/tasks/t3-discovery/task.toml evals/scripts/compare.py` prints nothing.

### FR3 — the run on E (R1)

- AC3.1 In the run on E, Codex T2 meets its floor (≥ 2/3), and in each passing Codex T2 trial `dadaia context bind` exits 0. A judged Codex session with no record is refused at that bind, and `eval.yml` prunes `agent/sessions`, so this bind is the observable record. The PLAN names where the trial log is read. Test: E2E, the run on E.
- AC3.2 The same run meets every rc-23 AC4.7 floor for both harnesses: T1 3/3, T2 ≥ 2/3 and T3 ≥ 2/3, with an errored or missing trial counted as a fail. Test: E2E, the run on E.
- AC3.3 E contains the Stall bug's fix. Without it, a judged Codex session at `/root` and a Claude Code one are pointed at a bind that refuses them. Test: none; `git merge-base --is-ancestor <the lane's fix sha> E` exits 0, read at closure.

### FR4 — memory (closure)

- AC4.1 The closure memory pass (`MEMORY-UPDATE.md`) rewrites the atoms whose sources changed:
  - `specs/memory/product/distribution/agent-evals.md:16`, the T3 pass, and its eval-leg lines (the harbor pin and the Codex trust facts);
  - `harness/harness-codex.md:26-27`, `sdd/sdd-gate-v3.md` and `platform/context-management.md`, checked true against the restored row.

  Test: none; `memory.py check` and `doctor` exit 0.

### Replaces

- The T3 grader's requirement of specs initialized and a valid backlog entry or SPEC holding `subtract`, in the main repo or a worktree (`test_grade.py:64-72`, `filled`, `clean`). FR2 replaces it with onboard-then-stop.
- `codex: None`: the Codex registry row names no subagent key (`core/harness_registry.py:89`), so no Codex call is judged. FR1 replaces it.

## 5. Constraints and risks

- **Dependency on the Stall lane.** FR3 needs the fix of `onboarding-names-the-refused-bind-to-an-ungoverned-session` on the work branch, and the `wt-rc` synced onto it before the run on E. If the lane has not merged by wave 4, the run waits for it; this candidate never carries its fix.
- **The harbor bump touches both legs.** One pipx line serves the Claude Code and Codex legs, so this is the one place rc-24 can regress the Claude Code leg. AC1.4's pre-mortem is its guard.
- **The readouts are not comparable across rc-24.** T3's measured act changes (R2), and Codex at `/root` becomes ungoverned once judged, so Codex T3 before and after are different measurements. The floors stay. The closure report states this.
- **T1 runs at `/root` too** (`t1-cold-onboarding/environment/Dockerfile:12`). Once Codex is judged, Codex T1 is as ungoverned as Claude Code T1. Claude Code T1 passes 3/3 so (run 40229657896): T1's grader reads the context, its specs and doctor, never a bind. The run on E measures it.
- **A user's untrusted Codex project.** It writes no record and is refused with the existing relaunch line (AC1.5). The library imposes no trust requirement, by the private-public boundary.
- **Open CRITICAL bug carried.** `mcp-on-main-is-vulnerable-to-session-exhaustion` is still open; its carry was operator-authorized at rc-23 closure. R1's scope does not pick it.
- **Size.** About +3 lines in `eval.yml` (as-is review E). That growth is the precondition ADR 0282's flip lacked. Every other unit shrinks or holds.

## 6. Open questions

None for the operator. R1–R4 rule the scope, and the two facts left open belong to the PLAN: harbor's `<v>` (AC1.4) and the merge observable (AC2.2 (e)).
