# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §2. The release has OPEN scope; each
CANDIDATE is one closed-scope cycle below; version and branch never change between
candidates.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Task | `WT merge <task path>`: git hygiene and RED/implementation test-path separation | the task's fast-forward onto its job branch |
| Job | `dd-code-reviewer` `APPROVED` naming the job's HEAD; the `verify:` line at `WT merge` | the job's merge |
| Candidate close | the Reconciliation job's merge | the candidate's work -> integration PR |
| Promote (ship) | pre-staged security verdict naming the integration tip | the integration -> principal PR |

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the job back to its tree.
- One review per job, never per task (`worktrees/AGENTS.md` §2).

## The candidate arc, step by step

An rc is an Implement: a DAG of jobs the PLAN draws, Job 1 first, the Reconciliation job last.

**Step 1 — Open a job.**
- `WT new <repo> <M.m.p>-rc<N>/<job>` once its PLAN edges are merged; its tasks live in `rc-<N>/tasks/<job>.md` (`dd-release-definition` §5).
- Each task opens `WT new <repo> <M.m.p>-rc<N>/<job>--<task-id>` from the job branch; a sub-agent works it; it is `running` while its tree exists.
- Done when: the tree exists.

**Step 2 — Tasks.**
- Each behavior starts with a RED-test task and continues in a fresh implementation task that cannot touch test paths. Every task commits under its id and lands by `WT merge` after its task gate.
- Done when: every job-file task has merged and no task worktree remains open.

**Step 3 — Job merge.**
- The reviewer's one verdict names the job's HEAD; `WT merge` runs the job gate and fast-forwards.
- The merge commit and job/task git history record job progress; the merge writes no release-state bookkeeping. [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md) is the current state-entry contract.
- Done when: the job is on the work branch.

**Step 4 — The Reconciliation job.**
- The last job, one tree (`<M.m.p>-rc<N>/reconcile`), cut once every other job merged and before any task tree is cut. Order: `release.py phase CLOSURE --sha <sha>` first (it refuses while another `wt/*` is open). Then run `release.py drift` and the memory pass (`MEMORY-UPDATE.md`) with its derived docs and generated catalog in the same merge. Then complete `measured_by` repairs, the rc's independent measurement, the disposition sweep and artifact GC.
- Persist the closure narrative only through the summary and exactly one closure memory entry described by [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md). The underlying ledgers and artifacts remain the records of their own disposition and GC work.
- Disposition sweep: a picked backlog entry exits by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition …`, once; an audit finding moves by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding> --disposition …`, and `audit.py close <dir> --sha <window-end>` closes an audit with none `open`; ledger dispositions follow `dadaia_workspace/public/schemas/histo/histo-record-v1.schema.json`; `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive` ages terminal records.
- Artifact GC: `.dadaia/.venv/bin/dadaia doctor` dry, then `--fix`; resolve or hold every reported artifact through the doctor's own procedure.
- Done when: the Reconciliation job merged; `.dadaia/.venv/bin/dadaia doctor` is clean.

**Step 5 — Candidate PR.**
- Open the work -> integration PR and merge it: `dd-gitflow-default` §3b.
- Done when: it merges.

The arc ends here. Gate -> promote -> record -> branch cut: `dd-gitflow-default` steps
9-12.

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) (`specs/memory/AGENTS.md`).
- Minting a version, writing a CHANGELOG section or moving a closed trio on disk — the project's release pipeline owns the first two, git owns the third.
