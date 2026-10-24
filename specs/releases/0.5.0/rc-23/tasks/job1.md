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
