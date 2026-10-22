# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` (Steps). The release has OPEN scope; each
CANDIDATE is one closed-scope cycle below; version and branch never change between
candidates. `WT` is `.dadaia/.venv/bin/dadaia worktree` (`worktrees/AGENTS.md`).

## Gate cadence

Each gate is owned elsewhere: task, job and candidate close at `WT merge` (`worktrees/AGENTS.md` §Merges, gates, review; one review per job, never per task); promote at `dd-gitflow-default` §The PR gate.

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the job back to its tree.

## The candidate arc, step by step

An rc is a DAG of jobs the PLAN draws, Job 1 first. Its `wt-rc` carries the define as its first commits and the reconcile as its last.

**Step 1 — Open a job.**
- `WT new` opens the job's `wt-main` once its PLAN edges are merged (leaf grammar: `worktrees/AGENTS.md` §The tree); its tasks live in its job file (`dd-release-definition` §The job file — tasks).
- Each task opens its `wt-task-<kkk>` tree from its `wt-main`; a sub-agent works it.
- Done when: the tree exists.

**Step 2 — Tasks.**
- Every task commits under its id and lands by `WT merge` after its task gate.
- Done when: every job-file task has merged and no `wt-task-<kkk>` tree remains open.

**Step 3 — Job merge.**
- The reviewer's verdict names the job's HEAD; `WT merge` fast-forwards `wt-rc`.
- The merge commit and job/task git history record job progress; the merge writes no release-state bookkeeping. [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md) is the current state-entry contract.
- Done when: the job is on its `wt-rc`.

**Step 4 — Reconcile.**
- The rc's last commits, on its `wt-rc`, taken once every other job merged. Order: `release.py phase CLOSURE --sha <sha>` first (its refusals: `worktrees/AGENTS.md` §Merges, gates, review). Then complete `measured_by` repairs, the rc's independent measurement, the disposition sweep and artifact GC. Last, run `release.py drift` and the memory pass (`MEMORY-UPDATE.md`) with its derived docs and generated catalog in the same merge.
- Closure scope: after `phase CLOSURE`, only what `specs/bugs/AGENTS.md` §Resolution admits lands on this `wt-rc`.
- Persist the closure narrative only through the summary and a closure memory entry per reconcile pass, described by [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md). The underlying ledgers and artifacts remain the records of their own disposition and GC work. The rc's independent measurement and the goal readouts are recorded only in the `summary` entry; a closed SPEC and PLAN are not written.
- Disposition sweep: a picked backlog entry exits by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition …`, once; an audit finding moves by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding> --disposition …`, and `audit.py close <dir> --sha <window-end>` closes an audit with none `open`; ledger dispositions follow `.agents/skills/dd-backlog-definition/scripts/schemas/histo-record-v1.schema.json`; `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive` ages terminal records.
- Artifact GC: `.dadaia/.venv/bin/dadaia doctor` dry, then `--fix`; resolve or hold every reported artifact through the doctor's own procedure.
- Done when: the reconcile commits are on `wt-rc`; `.dadaia/.venv/bin/dadaia doctor` is clean.

**Step 5 — Candidate PR.**
- `WT merge` of the `wt-rc` into the work branch, then the work -> integration PR (`dd-gitflow-default` §The PR gate).
- Done when: the PR merges.

The arc ends here. Promote and what follows it: `dd-gitflow-default` Steps, steps 9-12.
