# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §2. The release has OPEN scope; each
CANDIDATE is one closed-scope cycle below; version and branch never change between
candidates. `WT` is `.dadaia/.venv/bin/dadaia worktree` (`worktrees/AGENTS.md`).

## Gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Task | `WT merge <task path>`: git hygiene and RED/implementation test-path separation | the task's fast-forward onto its `wt-main` |
| Job | `dd-code-reviewer` `APPROVED` naming the job's HEAD; the `verify:` line at `WT merge` | the job's merge into `wt-rc` |
| Candidate close | `dd-code-reviewer` `APPROVED` naming the `wt-rc` HEAD; the `verify:` line and ledger checks at `WT merge` | the rc's merge into the work branch |
| Promote (ship) | `dd-code-reviewer` APPROVED on the integration tip (`dd-gitflow-default` §3b) | the integration -> principal PR |

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the job back to its tree.
- One review per job, never per task (`worktrees/AGENTS.md` §2).

## The candidate arc, step by step

An rc is a DAG of jobs the PLAN draws, Job 1 first. Its `wt-rc` carries the define as its first commits and the reconcile as its last.

**Step 1 — Open a job.**
- `WT new <repo> <M.m.p>/rc-<N>/job-<n>/wt-main` once its PLAN edges are merged; its tasks live in `rc-<N>/tasks/job<n>.md` (`dd-release-definition` §5).
- Each task opens `WT new <repo> <M.m.p>/rc-<N>/job-<n>/wt-task-<kkk>` from its `wt-main` (`kkk` is the `T<k>` in 3 digits); a sub-agent works it; it is `running` while its tree exists.
- Done when: the tree exists.

**Step 2 — Tasks.**
- Every task commits under its id and lands by `WT merge` after its task gate.
- Done when: every job-file task has merged and no `wt-task-<kkk>` tree remains open.

**Step 3 — Job merge.**
- The reviewer's one verdict names the job's HEAD; `WT merge` runs the job gate and fast-forwards `wt-rc`.
- The merge commit and job/task git history record job progress; the merge writes no release-state bookkeeping. [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md) is the current state-entry contract.
- Done when: the job is on its `wt-rc`.

**Step 4 — Reconcile.**
- The rc's last commits, on its `wt-rc`, taken once every other job merged. Order: `release.py phase CLOSURE --sha <sha>` first (it refuses while any job, task or lane tree is open; the rc's own `wt-rc` is exempt). Then complete `measured_by` repairs, the rc's independent measurement, the disposition sweep and artifact GC. Last, run `release.py drift` and the memory pass (`MEMORY-UPDATE.md`) with its derived docs and generated catalog in the same merge.
- Closure scope: after `phase CLOSURE`, only a block-list bug (`specs/bugs/AGENTS.md` §2) lands on this `wt-rc`; any other bug, REBUILD or operator demand becomes a job of the next rc, which opens at once.
- Persist the closure narrative only through the summary and a closure memory entry per reconcile pass, described by [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md). The underlying ledgers and artifacts remain the records of their own disposition and GC work. The rc's independent measurement, the goal readouts and the `verdict.py stats` table (local metrics 1, 2, 4, 6, 7 and 9, each beside its SPEC §2 target, and the oldest record read) are recorded only in the `summary` entry; a closed SPEC and PLAN are not written.
- Disposition sweep: a picked backlog entry exits by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition …`, once; an audit finding moves by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding> --disposition …`, and `audit.py close <dir> --sha <window-end>` closes an audit with none `open`; ledger dispositions follow `.agents/skills/dd-backlog-definition/scripts/schemas/histo-record-v1.schema.json`; `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive` ages terminal records.
- Artifact GC: `.dadaia/.venv/bin/dadaia doctor` dry, then `--fix`; resolve or hold every reported artifact through the doctor's own procedure.
- Done when: the reconcile commits are on `wt-rc`; `.dadaia/.venv/bin/dadaia doctor` is clean.

**Step 5 — Candidate PR.**
- `WT merge` of the `wt-rc` into the work branch, then the work -> integration PR (`dd-gitflow-default` §3b).
- Done when: the PR merges.

The arc ends here. Promote and what follows it: `dd-gitflow-default` steps 9-12.
