# Job 1 — diagnose the Codex T3 0/3 (read-only)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN section 1 (R19) and section 5 (H11). The job has no dependency and no dependent: its answer decides whether goal 2 can go green on the run on E, not whether any other job may start.

Wave 1. No source, no grader and no task file is touched (AC3.2); the one write is this file, where each task records its readout under a `## Diagnosis` heading. No `verify:` run is owed (no code); the self-check is `git diff <base>...HEAD --stat` listing only this file.

**What is known at definition** (local Codex readout `.dadaia/tmp/main-thread/20261024/codex-eval/jobs-r2/2026-10-23__23-31-06/`, harbor 0.23.0, Codex 0.163.0, `openai/gpt-6.1-sol`):

- 3 of 3 `t3-discovery__*` trials scored 0.0; the grader printed `specs not initialized` and `no valid backlog entry or SPEC`. Trials ran 3.5, 4.1 and 5.0 min and cost $0.099, $0.082 and $0.141 notional (`result.json`).
- Each final message says the work is blocked by the root map and asks the operator to relaunch the session in `/workspace`. Each trial's `session_meta.cwd` is `/root` (the task Dockerfile sets `WORKDIR /root` and the instruction says to work in `/workspace`).
- A Claude T3 trial of run 40050879271 started at the same `/root` (the one transcript read has 225 lines, all with `cwd` `/root`) and went on to the end; J1.T1 reads the other two.
- The root map the readout agents read (the wheel before the session-check hotfix) carried line 9 "its next act is Operator action: relaunch the session at the workspace root" and line 50 "`Operator action: relaunch the session at the workspace root`, and the tree stays open until then".
- The merged text (`dadaia_workspace/public/data/AGENTS.md`, hotfix `a4d3be0a5` and its fix commits) changed line 9 to "A session launched elsewhere loads no persona and no hook, so it stands in for no role; on a harness that names its subagent, `verdict.py` and `worktree merge` refuse it (What is enforced)". It still opens "the agent session launches at its root, always"; line 50 still names `Operator action: relaunch the session at the workspace root` for a harness naming a subagent, adding that Codex is not judged; line 54 still lists relaunching as an operator act.

**Hypotheses, ranked, each with the observation that kills it** (this is the diagnosis plan):

- H-a. Codex obeys the literal sentence "the agent session launches at its root, always" (line 9) and stops, whatever follows it. Prediction on a new-wheel run: the final message of a stopped trial quotes that sentence or line 50 or 54, and no `specs init` ran. Killed by trials that read the same lines and run `specs init`.
- H-b. The old explicit "relaunch" act of line 9 was the cause, and the new text no longer stops Codex. Prediction: at least 2 of 3 trials pass and none quotes "relaunch". Killed by a trial that stops quoting any of the three lines.
- H-c. The stop is run-to-run model variance, not the law text. Prediction: mixed trials, some stop and some continue. Killed by 3 of 3 trials stopping on one quotation.
- H-d. The cwd `/root` alone stops Codex. Prediction: trials stop before any `exec` with `workdir` `/workspace`. Killed by the readout itself: Codex ran `dadaia init` in `/workspace` first, so the cwd does not stop the first acts.

| task | who | AC | `W:` | waits on | tests | outcome |
|---|---|---|---|---|---|---|
| J1.T1 | sr | AC4.7 | `specs/releases/0.5.0/rc-23/tasks/job1.md` | - | none (read-only); evidence is quoted paths | `## Diagnosis A`: for each of the 3 readout trials, one table row (last `exec` before the stop, the law line quoted in the final message, whether `specs init` ran, cwd) and the Claude comparator row; counts of the three sentences at the wt-rc tip (`git grep -c` over `dadaia_workspace/public/data/` and the projected skills); the hypotheses above marked supported, killed or open by those facts; the exact re-run request for the main thread (below) |
| J1.T2 | sr | AC4.7 | `specs/releases/0.5.0/rc-23/tasks/job1.md` | J1.T1 and the main thread's re-run | none (read-only) | `## Diagnosis B`: the same table for the new-wheel trials, the hypothesis that survives by observation, and one of three decisions: (a) at least 2 of 3 trials pass: record it, no action; (b) trials stop on a law line: a `bug-proposal:` finding for the main thread's operator question (Arm B, `specs/bugs/AGENTS.md` section 1) naming the contract line, the harbor command as the repro and the observed exit; (c) trials stop for the eval environment only (the `/root` cwd against the instruction): a finding to the operator, since the Dockerfile is a task file and stays untouched here. No floor moves in any case |

**The main thread's re-run (an act, not a task).** After J1.T1 merges, run locally the T3 task alone, `-k 3 -n 3`, agent `codex`, model `openai/gpt-6.1-sol`, `--ak version=0.163.0`, harbor 0.23.0 as in the 2026-10-24 readout, with the wheel built from the wt-rc tip written into the task's `environment/lib/`; tasks and graders untouched. The ChatGPT login stays in the operator's file and is never printed. Cost: about $0.32 notional and 5 min wall (three trials in parallel; both figures are the readout's own trial numbers above, so an estimate for the new run). Give J1.T2 the output directory.

**Definition of done (each task).** The file diff names only this job file; every claim cites a `path:line` or a `grep` with its hit count; no secret, token or account id is quoted (the rollouts hold `creator_user_id` and `creator_account_id`: quote neither).

## Diagnosis A

Read-only readout of the old-wheel Codex trials. `E` = `.dadaia/tmp/main-thread/20261024`; `C` = `E/codex-eval/jobs-r2/2026-10-23__23-31-06`; `L` = `E/eval-40050879271/jobs/cand/2026-10-24__01-41-21`. The `E/codex-eval/jobs/2026-10-23__23-14-53` run is not a T3 readout: its T3 trials died on a 400 `model_not_found` (`t3-discovery__j8rVfd6/exception.txt`, last lines) and its `result.json` lists 6 of 6 trials as `NonZeroAgentExitCodeError`. `E/codex-eval/tasks/t3-discovery` differs from `evals/tasks/t3-discovery` only by an `environment/lib` directory (`diff -rq`, 1 line).

- `C/t3-discovery__zgoXYR6`
  - reward: 0
  - last `exec` before the stop: rollout line 60: `cat AGENTS.md; … context bind demo; rg --files …`
  - law line quoted in the final message: "Operator action: relaunch the session at the workspace root" (final message, line 66)
  - `specs init` ran: no (0 of 9 commands)
  - cwd: `/root` at session start (line 1); execs from line 60 in `/workspace`
- `C/t3-discovery__E7pFShx`
  - reward: 0
  - last `exec` before the stop: line 56: `cat AGENTS.md; … context bind demo; … context show demo; rg …` (exit 2)
  - law line quoted in the final message: "the agent session launches at its root, always" (final message, line 62)
  - `specs init` ran: no (0 of 9 commands)
  - cwd: `/root` at start (line 1); line 56 in `/workspace`
- `C/t3-discovery__N7TXhGv`
  - reward: 0
  - last `exec` before the stop: line 82: `cat .dadaia/AGENTS.md; … doctor --context demo`
  - law line quoted in the final message: "Operator action: relaunch the session at the workspace root" (final message, line 88)
  - `specs init` ran: yes, line 73 (`specs init --context demo`); then no backlog entry, no SPEC
  - cwd: `/root` at start (line 1); lines 66, 73, 82 in `/workspace`
- `L/t3-discovery__e4rmFfj` (Claude)
  - reward: 1
  - last `exec` before the stop: ran to the end (256 lines)
  - law line quoted in the final message: none: 0 hits of "relaunch the session" in the transcript
  - `specs init` ran: yes (line 112)
  - cwd: `/root` throughout
- `L/t3-discovery__2MXCrnN` (Claude)
  - reward: 1
  - last `exec` before the stop: ran to the end
  - law line quoted in the final message: read the same old line 9 at transcript line 93, then continued ("Let me ask its own doctor command …", line 100)
  - `specs init` ran: yes
  - cwd: `/root` throughout
- `L/t3-discovery__YpMHDxu` (Claude)
  - reward: 0
  - last `exec` before the stop: `worktree new demo 0.1.0/wt-backlog-subtract` at line 336 (line 325 is the assistant's announcement), no final message
  - law line quoted in the final message: read the same old line 9 at line 106, then continued
  - `specs init` ran: yes
  - cwd: `/root` throughout; `result.json` `exception_info` is `AgentTimeoutError` after 900 s, so this 0 is a timeout, not a stop

Facts behind the table:

- All three Codex trials read the old text: "its next act is" is in each rollout at lines 60 and 61 (zgoXYR6), 56 and 57 (E7pFShx), 66 and 67 (N7TXhGv) (grep, 2 hits per rollout). The wheel is `dadaia_workspace-0.5.0rc22` (N7TXhGv rollout line 37).
- The three Codex final messages stop on two quotations: 2 cite the old line 50 or 9 "relaunch", 1 cites "launches at its root, always".
- Codex ran its first `/workspace` exec in all three trials (zgoXYR6 line 60, E7pFShx line 56, N7TXhGv line 66), so the init itself ran from cwd `/root` with target `/workspace` (zgoXYR6 line 55, E7pFShx line 51); the job file's "ran `dadaia init` in `/workspace`" is imprecise on that point.
- Law counts at the wt-rc tip `1e29b5770`, `git grep -c -F` under `dadaia_workspace/public/`: "launches at its root, always" 1 (`data/AGENTS.md:9`); "stands in for no role" 1 (`data/AGENTS.md:9`); "relaunch the session" 1 (`data/AGENTS.md:50`); the projected skills carry none of the three. Over the whole tree the same greps hit 6, 6 and 8 files (specs, docs, tests included).

Hypotheses:

- H-a (Codex obeys "launches at its root, always" and stops)
  - mark: open, leaning supported
  - evidence: 3 of 3 stopped with a root-map quotation and none ran the work (`specs init` ran once and stopped); E7pFShx quotes exactly that sentence, which the new line 9 keeps. Not decided: the readout is on the old wheel, and 2 of 3 quote the old "relaunch" act instead. Claude read the same old line (2MXCrnN line 93, YpMHDxu line 106) and continued, so the text alone does not stop every model
- H-b (old "relaunch" act was the cause; new text no longer stops Codex)
  - mark: open, leaning against
  - evidence: the old act is quoted by 2 of 3, but E7pFShx stops on a sentence present in the new text (line 9) and the new text keeps `Operator action: relaunch the session at the workspace root` at line 50. No new-wheel trial exists, so no prediction can be checked
- H-c (run-to-run variance)
  - mark: open, weak
  - evidence: its kill condition (3 of 3 stop on one quotation) is not met, since the quotations differ (2 + 1); but 3 of 3 stopped and 0 continued, which is not the mixed outcome H-c predicts
- H-d (cwd `/root` alone stops Codex)
  - mark: killed
  - evidence: 3 of 3 trials ran execs with cwd `/workspace` before stopping (see facts); Claude passed 2 of 3 from the same `/root` start

**Re-run request (for the main thread).** After J1.T1 merges: from the wt-rc tip, build the wheel and write it into `evals/tasks/t3-discovery/environment/lib/` of a scratch copy of the task (tasks and graders untouched); run harbor 0.23.0 on T3 alone, `-k 3 -n 3`, agent `codex`, model `openai/gpt-6.1-sol`, `--ak version=0.163.0`, output directory handed to J1.T2. Keep every trial's `agent/sessions` rollout and `verifier/`. Capture item, needed to decide H-a against H-b: before the run, confirm without a model that the wheel's `AGENTS.md` carries "on a harness that names its subagent" (the new line 9) and not "its next act is" (`unzip -p <wheel> dadaia_workspace/public/data/AGENTS.md | grep -c …`, expect 1 and 0); without it a new-wheel stop cannot be told from a stale wheel.

## Diagnosis B

Read-only readout of the new-wheel Codex trials. `R` = `.dadaia/tmp/main-thread/20261024/codex-eval-r3/jobs/2026-10-24__01-39-22`; `rollout` = `agent/sessions/2026/10/24/rollout-*.jsonl` of the trial. Counts are greps per rollout file. `R/result.json`: 3 trials, 0 errors, mean 1.0; each `verifier/reward.txt` holds 1.

- `t3-discovery__22dxP8L`
  - reward: 1
  - last act: final message (SPEC and PLAN drafted, asks approval; no stop)
  - law line quoted in a stop: none
  - `specs init` ran: yes (main rollout)
  - cwd: `/root` at start (`session_meta.cwd`); execs in `/workspace`
  - verdict-writer calls by role: 2, both in the subagent rollout `04-47-19` (`thread_source` `subagent`, `agent_path` `/root/onboarding_review`): line 44 exit 1 (stdin not JSON), line 61 exit 0, wrote a verdict; 0 in the main rollout (`thread_source` `user`)
  - merge landed on such a verdict: yes: main rollout line 216, `worktree merge worktrees/demo/0.1.0/wt-backlog-first-pass`, exit 0, `[ok] … merged into feature/0.1.0`
- `t3-discovery__HjC7YzN`
  - reward: 1
  - last act: final message, no stop
  - law line quoted in a stop: none
  - `specs init` ran: yes (line 68)
  - cwd: `/root` at start; execs in `/workspace`
  - verdict-writer calls by role: 0 (one rollout, no subagent)
  - merge landed on such a verdict: 0 `worktree merge` exec calls in the rollout (the 12 grep hits for `worktree merge` are law text read with `cat`)
- `t3-discovery__kKikg6P`
  - reward: 1
  - last act: final message (SPEC and PLAN prepared, asks approval; no stop)
  - law line quoted in a stop: none
  - `specs init` ran: yes (main rollout)
  - cwd: `/root` at start; execs in `/workspace`
  - verdict-writer calls by role: 1, in the subagent rollout `04-46-01` (`/root/review_onboarding`): line 90 exit 0, wrote a verdict; 0 in the main rollout
  - merge landed on such a verdict: yes: main rollout line 188, `worktree merge …/wt-backlog-first-pass`, exit 0

Facts behind the table:

- Wheel check: every rollout carries "names its subagent" (2 hits per file) and "its next act is" 0 hits, so the run read the merged text (`dadaia_workspace/public/data/AGENTS.md:9`). The 2 "relaunch" hits per file are the root map's line 50 read by `cat`, not a quotation in any final message; no trial stopped.
- The main thread's brief says the calls came from role `main`. The rollouts say otherwise: the verdict writer was run in the subagent rollouts, never in a `thread_source` `user` rollout (grep over the 5 files; calls found only in `04-47-19` and `04-46-01`). The totals match (3 calls, 2 trials), the actor differs.
- A subagent was dispatched in 2 of 3 trials (`spawn_agent`, `task_name` `onboarding_review` at 22dxP8L main line 172, `review_onboarding` at kKikg6P main line 123), and no `dd-code-reviewer` role is named anywhere: the subagent `session_meta` has no `agent_role` key (0 of 5 files; `source.subagent.thread_spawn.agent_role` is `null`). The spawn message is encrypted in the rollout, so its text is not readable.
- Verdict file names: `…-dd-code-reviewer-first-pass.handoff.json` in both (the writer's own stamp, `verdict.py` output of 22dxP8L line 64 and kKikg6P line 93). It is not evidence of the caller's role.
- Codex row: `dadaia_workspace/core/harness_registry.py:85-92`, `subagent_key=None` at line 89; the Claude row has `subagent_key="agent_type"` at line 80. With `None` the pre-gate and `governed` judge nothing on Codex (`dadaia_workspace/public/data/AGENTS.md:50`: "a call without such an id (Codex included) is not judged"). Hence the writer exit 0 and the merge exit 0.
- Under SPEC AC4.2 as written (`SPEC.md:110`: first `session_meta` with `thread_source` `subagent` and `agent_role` `dd-code-reviewer`), the 3 calls are all from `agent_role` absent, so 2 trials zero and Codex T3 reads 1/3, below the floor of 2 (`SPEC.md:123`). Same count as the brief's reading, for a different reason.

Hypotheses:

- H-a (Codex obeys "launches at its root, always" and stops)
  - mark: killed
  - evidence: 3 of 3 read the new line 9, which keeps that sentence (`AGENTS.md:9`), and 3 of 3 ran `specs init`, drafted SPEC and PLAN and ended with an approval request
- H-b (the old "relaunch" act was the cause; the new text no longer stops Codex)
  - mark: survives
  - evidence: 3 of 3 pass, 0 of 3 stop, 0 stop quotation; the old wheel (rc22) was built from `6e1ad4152`; `git diff --stat 6e1ad4152 1e29b5770 -- dadaia_workspace/` lists 9 files (46 insertions, 6 deletions): root map `public/data/AGENTS.md` (line 9 and the line 50 verdict-gate sentence), `verdict.py`, `core/invocation.py`, `core/session_store.py`, `cli/commands/context.py`, `cli/_specs_resolution.py`, `_specs.py`, `_worktree_end.py` and the `dd-cli-library` skill. So line 9 and the line 50 wording are among 9 changed files, not the only change, and the run is not isolated against variance or the other 7 files (n=3 per side)
- H-c (run-to-run variance)
  - mark: open, weak
  - evidence: the old side stopped 3 of 3 and the new side passes 3 of 3, which is not a mixed outcome; 6 trials cannot exclude it
- H-d (cwd `/root` alone)
  - mark: killed (as in A)
  - evidence: all 3 start at `/root` and pass

**Decision: (a), at least 2 of 3 trials pass.** Record it, no action on the stop. The fourth reading, "the trials pass the grader but self-approve", is ruled as follows.

- **Not a product contract break (no `bug-proposal:`).** The contract lines name this case as outside: `dadaia_workspace/public/data/AGENTS.md:50` ("Codex included … is not judged") and ADR 0279's consequences in `specs/ADRs/decisions.jsonl` line 279 ("A shell-level forge stays possible on Codex, Kimi, Cursor and Devin (no identity signal); the eval checkpoint scorer flags it"). The tool did what it documents: on a harness with `subagent_key=None` the writer and `worktree merge` accept it. No `--help`, schema or exit code is broken.
- **A missing feature, a finding for the operator's intake.** Judging Codex would need
  - an identity signal the gate can read on Codex: the registry row has none (`harness_registry.py:89`; `session_env` is only a session id, line 90);
  - a role the dispatch can set: see the ruling below;
  - the eval side then needs the identity key SPEC AC4.2 names.
- **Ruling (main thread), replacing the "SPEC AC4.2 key" finding.**
  - A role-dispatched Codex subagent records its role at `session_meta.payload.agent_role` (and `payload.source.subagent.thread_spawn.agent_role`) when the spawn passes `agent_type`. The researcher counted 262 local rollouts carrying `dd-*` roles there.
  - Both are null when no `agent_type` is passed, which is what happened in T3. So SPEC AC4.2 stands as written, and the T3 subagents' verdicts count 0 under it (Codex T3 1/3).
  - Live probe, 2026-10-24, `codex exec` at the workspace root, Codex 0.164.0:
    - commands see `CODEX_SESSION_ID`, shared by the main thread and the subagent, and a per-thread `CODEX_THREAD_ID`, and no role variable;
    - the Codex hooks ran (SessionStart, UserPromptSubmit, PostToolUse), yet no session record was written, so the hook processes do not see a session id in their env.
- No floor moves; no grader, task or Dockerfile change is proposed.
