# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`. It is the one home of the worktree rules;
a skill points here, never restates them.

- `WT` below is `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py` — the one tool that opens, lists, merges and cleans a worktree.
- A harness-native worktree (`.claude/worktrees/**`, a scratchpad) is not ours: never opened for SDD work, never merged by `WT`.

## 1. The tree

- One worktree per job, nested at `worktrees/<repo>/<M.m.p>-rc<N>/<job>/`, on the branch `wt/<M.m.p>-rc<N>/<job>`, cut from the repo's work branch; a job needs its rc's approved SPEC (`specs/AGENTS.md`).
- Two more trees inside an rc folder: `define/` (the candidate's definition) and `reconcile/` (the Reconciliation job: memory, derived docs, `measured_by` repairs, the rc's measurement, closure).
- Outside an rc only `worktrees/<repo>/backlog/<slug>/`, on `wt/backlog/<slug>`, and `worktrees/<repo>/hotfix/<bug-id>/`, on `wt/hotfix/<bug-id>` (§3); a bug is a job.
- One worktree per task, `<M.m.p>-rc<N>/<job>--<task-id>/` on `wt/<M.m.p>-rc<N>/<job>--<task-id>`, cut from its job branch: sub-agents work the tasks of one stage in parallel, one per task worktree; at most 5 task worktrees open per rc. A stage is a barrier on the job branch, never a tree. One change — code, tests, specs, memory, derived docs — lands in one job.
- `WT new <repo> <name>` opens a tree; any other name is refused.

## 2. Three gates, one review

1. Task: its commit, the subject opening with its id; `WT merge <task path>` runs the work branch's `verify-task:` line on the touched files and fast-forwards the job branch — no verdict, no review; a task behind its job branch rebases first (its disjoint `W:` keeps it conflict-free) and the gate reruns.
2. Stage: `WT stage <job path>` — refused while a task worktree of the job is open, then the work branch's `verify-stage:` line green before the next stage opens; the closing commit carries `stage: <id> — verify-stage green`.
3. Job: `dd-code-reviewer` reviews `git diff <work branch>...HEAD` once and writes its own verdict with `verdict.py` (`dd-handoff-emitter`), its only write; the main thread never writes one. The hash binds the verdict to a diff; authorship is discipline plus audit. A job branch may be pushed before its review (a push is never a merge).
4. `WT merge <path>` lands HEAD as it is, by fast-forward, only when the tree is clean, HEAD contains the work branch, no task worktree of the job is open, a valid APPROVED verdict names HEAD, or a reflog sha of HEAD's patch-id and message series (ADR 0168), by `reviewed_sha`, and its `diff_sha256` matches the range the merge lands, and the work branch's `verify:` line passes on HEAD, split by `shlex` and run as one argv list, never a shell; it then removes the tree and `branch -d`s it.
5. A `define` or `backlog` tree lands `specs/` only: its merge needs its one review pass and the bugs, backlog and release checks, and runs no test.

- One review per job, plus one per stage past 400 added lines (`git diff --numstat`, column 1); none per task.
- A moved work branch refuses with `fix: git -C <tree> rebase <work>`; the rebase runs inside the worktree. A ledger conflict is redone by the ledger's own writer on the rebased tree, never hand-merged. `WT merge` re-runs cleanly after any stop.

## 3. Hotfix and parallel work

- A hotfix (`specs/bugs/AGENTS.md` §2) is its own job, outside the rc's DAG: `WT new <repo> hotfix/<bug-id>` cuts it from the work branch with no rc `SPEC.md`, once the main repo's `specs/bugs/BUGS.jsonl` on the work branch holds that bug `open`; its gates, one review and merge are §2's.
- Jobs run in parallel only with disjoint envelopes or an edge in the PLAN's DAG; tasks of one stage run in parallel with disjoint `W:`. The CI cost is cut in the gates, never by sharing a tree.

## 4. Environment and hygiene

- A worktree never holds its own `.venv`, `.dadaia` or tool cache; caches go where the harness env points; the flat name keeps the one venv at `../../../.dadaia/.venv`.
- A subagent works only inside the worktree path it was given, bound to the context; only the main thread opens and merges.
- Never `git stash` in a worktree: every worktree of a repo shares one stash stack; set work aside as a WIP commit.
- Never merge by hand, never `git worktree remove --force`, never `git branch -D` a `wt/` branch.
- An empty or merged worktree leaves by `WT clean <path>`; ignored files are kept (`--keep`) or dropped (`--drop`) by the operator's word.
- Never close a candidate or `context dead` a context while one of its `wt/*` branches exists, the closing tree's own aside: merge or clean it first.
- Nothing lives under `worktrees/` but `<repo>/<name>` worktrees and this file.
