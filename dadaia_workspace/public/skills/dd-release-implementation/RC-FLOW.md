# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §2. The release has OPEN scope; each
CANDIDATE is one closed-scope cycle below; version and branch never change between
candidates.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Task | `WT merge <task path>`: the repo's `verify-task:` line | the task's fast-forward onto its job branch |
| Stage | `WT stage <job path>`: no task open, the `verify-stage:` line | the next stage |
| Job | `dd-code-reviewer` `APPROVED` carrying the job's green CI-matrix run as `ci_run`; the `verify:` line at `WT merge` | the job's merge |
| Candidate close | the Reconciliation job's merge | the candidate's work -> integration PR |
| Promote (ship) | pre-staged security verdict naming the integration tip | the integration -> principal PR |

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the job back to its tree.
- One review per job, never per task (`worktrees/AGENTS.md` §2).

## The candidate arc, step by step

An rc is an Implement: a DAG of jobs the PLAN draws, Job 1 first, the Reconciliation job last.

**Step 1 — Open a job.**
- `WT new <repo> <M.m.p>-rc<N>/<job>` once its PLAN edges are merged; its tasks live in `rc-<N>/tasks/<job>.md` (`dd-release-definition` §5).
- Each task opens `WT new <repo> <M.m.p>-rc<N>/<job>--<task-id>` from the job branch; a sub-agent works it; it is `running` while its tree exists; there is no reservation commit.
- Done when: the tree exists.

**Step 2 — Stages and tasks.**
- Stage 1 writes every acceptance test RED, each failing by assertion and carrying the repo's RED marker; each later stage turns its rows green by deleting that marker line alone — past the RED stage's close a test is never edited (`worktrees/AGENTS.md` §2).
- Each task commits under its id and lands by `WT merge` after its task gate; each stage closes by `WT stage`.
- Done when: the last stage closed green and the close task wrote the job file's `done`.

**Step 3 — Job merge.**
- Push the job branch; the reviewer's one verdict names its green CI-matrix run; `WT merge` runs the job gate and fast-forwards.
- Append the job's `kind: merge` entry to `_RELEASE.json`'s `log` (`RELEASE-EVENTS.md`).
- Done when: the job is on the work branch and its entry passes `release.py check`.

**Step 4 — The Reconciliation job.**
- The bug batch runs first: one job outside the DAG, after its last job merges, fixing every open bug `found_in` the rc, grouped by cause (`specs/bugs/AGENTS.md` §2); a bug found in the Reconciliation job is fixed inside it.
- The last job, one tree (`<M.m.p>-rc<N>/reconcile`): memory (`MEMORY-UPDATE.md`), the derived docs in the same merge, `measured_by` repairs, the rc's measurement, the closure narrative, the disposition sweep, the artifact GC.
- Closure narrative: the `log` entries `RELEASE-EVENTS.md` describes — `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`.
- Disposition sweep: a picked backlog entry exits by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition …`, once; an audit finding moves by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding> --disposition …`, and `audit.py close <dir> --sha <window-end>` closes an audit with none `open`; a bug is never silently dropped; `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive` ages the ledger once the sweep is terminal.
- Artifact GC: `.dadaia/.venv/bin/dadaia doctor` dry, then `--fix`; the `kind: artifact-gc` entry records the exit code and what the operator holds.
- Done when: the Reconciliation job merged; `.dadaia/.venv/bin/dadaia doctor` is clean.

**Step 5 — Candidate PR.**
- Open the work -> integration PR (branch names: the constitution's `gitflow:`) (security verdict covering the head, `dd-gitflow-default` §2a); watch CI to green; merge.
- Done when: it merges green.

The arc ends here. Gate -> promote -> record -> branch cut: `dd-gitflow-default` steps
9-12.

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) — gate-blocked for any other agent/phase.
- Minting a version, writing a CHANGELOG section or moving a closed trio on disk — the project's release pipeline owns the first two, git owns the third.
