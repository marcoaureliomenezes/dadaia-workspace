# worktrees/AGENTS.md — Worktree Rules

Scope: this file governs only `worktrees/**`. It is the one home of the worktree rules;
a skill points here, never restates them.

- `WT` below is `python3 .agents/skills/dd-gitflow-default/scripts/worktree.py` — the one tool that opens, lists, merges and cleans a worktree.
- A harness-native worktree (`.claude/worktrees/**`, a scratchpad) is not ours: never opened for SDD work, never merged by `WT`.

## 1. The tree

- One worktree per job, flat at `worktrees/<repo>/<M.m.p>-rc<N>-<job>`, on the branch `wt/<M.m.p>-rc<N>/<job>`, cut from the repo's work branch; a job needs its rc's Approved `SPEC.md`.
- Two more names inside an rc: `<M.m.p>-rc<N>-define` (the candidate's definition) and `<M.m.p>-rc<N>-reconcile` (the Reconciliation job: memory, derived docs, `measured_by` repairs, the rc's measurement, closure).
- Outside an rc only `backlog-<slug>`, on `wt/backlog/<slug>`; a bug is a job.
- A job's tasks share its tree; a stage is a barrier inside it, never a tree. One change — code, tests, specs, memory, derived docs — lands in one job.
- `WT new <repo> <name>` opens a tree; any other name is refused.

## 2. Three gates, one review

1. Task: `scripts/ci.py task <files>` — ruff and mypy on the touched files, the task's owner tests; then the task's commit, its subject opening with its id.
2. Stage: `scripts/ci.py stage` — lint, mypy, guards, unit, integration — green before the next stage opens; the closing commit carries `stage: <id> — unit+integration green`.
3. Job: push `wt/<M.m.p>-rc<N>/<job>` (the one pushable `wt/` branch) and let its CI matrix run; `dd-code-reviewer` reviews `git diff <work branch>...HEAD` once and names that green run (`…/actions/runs/<id>`) in its verdict, a handoff whose `scope` names HEAD.
4. `WT merge <path>` lands HEAD as it is, by fast-forward, only when the tree is clean, HEAD contains the work branch, a valid APPROVED verdict names HEAD (or a reflog sha with the same patch-id and message series) and the CI-matrix run, and `scripts/ci.py job` passes on HEAD as one argv list; it then removes the tree and `branch -d`s it.
5. A `define` or `backlog` tree lands `specs/` only: its merge needs its one review pass and the bugs, backlog and release checks, and runs no test.

- One review per job, plus one per stage past 400 added lines (`git diff --numstat`, column 1); none per task.
- A moved work branch refuses with `fix: git -C <tree> rebase <work>`; the rebase runs inside the worktree. A ledger conflict is redone by the ledger's own writer on the rebased tree, never hand-merged. `WT merge` re-runs cleanly after any stop.

## 3. Hotfix and parallel jobs

- A block-list bug's fix is a hotfix: its own job, outside the rc's DAG.
- Jobs run in parallel only with disjoint envelopes or an edge in the PLAN's DAG.

## 4. Environment and hygiene

- A worktree never holds its own `.venv`, `.dadaia` or tool cache; caches go where the harness env points; the flat name keeps the one venv at `../../../.dadaia/.venv`.
- A subagent works only inside the worktree path it was given, bound to the context; only the main thread opens and merges.
- Never `git stash` in a worktree: every worktree of a repo shares one stash stack; set work aside as a WIP commit.
- Never merge by hand, never `git worktree remove --force`, never `git branch -D` a `wt/` branch.
- An empty or merged worktree leaves by `WT clean <path>`; ignored files are kept (`--keep`) or dropped (`--drop`) by the operator's word.
- `WT list` shows every open worktree: name, age, commits ahead, dirty or clean.
- Never close a candidate or `context dead` a context while one of its `wt/*` branches exists, the closing tree's own aside: merge or clean it first.
- Nothing lives under `worktrees/` but `<repo>/<name>` worktrees and this file.
