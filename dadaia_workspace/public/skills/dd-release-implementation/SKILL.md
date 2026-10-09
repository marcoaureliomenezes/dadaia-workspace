---
name: dd-release-implementation
description: >
  Run an Approved candidate to its PR: job and task worktrees, the RED-test then implementation task pair,
  the job review and merge, the Reconciliation job (phase CLOSURE, memory pass, disposition sweep, doctor)
  and _RELEASE.json entries. Use when working a task or job, closing a candidate, or writing release state.
  Defining a candidate is dd-release-definition's; PRs, promote and branch cut are dd-gitflow-default's.
---

# dd-release-implementation

> Not hook-enforced. No engine advances gates or drives closure — implementers, the reviewer, `dd-product-engineer` and the main thread uphold it directly.

## 1. When

- `dd-software-engineer` working a task inside an `Approved` candidate.
- `dd-product-engineer` at each candidate's closure (memory, `_RELEASE.json`).
- From the first task through the candidate PR; the gate after it: `dd-gitflow-default` §2 steps 9-12.

## 2. Steps

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the live release: `dd-spec-navigator` Phase 3.
3. The live candidate's job files sit at `releases/<v>/rc-<N>/tasks/job<n>.md`, the highest `rc-<N>/`; a lower one is closed history.
4. Full navigation protocol: `dd-spec-navigator`.
5. Read `RC-FLOW.md` for the candidate arc and gate cadence before acting past opening a task.
6. Change `_RELEASE.json` through `release.py` verbs (`phase`, `memory`, `ship`); only `summary` and the authorization `note` are hand-written (`RELEASE-EVENTS.md`).
7. At `RC-FLOW.md` step 4, run `MEMORY-UPDATE.md`'s full protocol before touching any memory atom.
8. A test enters the suite only under the root map §1 test basics.
9. Before growing any module, run the deletion test (delete it: does complexity vanish or reappear across callers?) — a diff that only adds justifies itself against replace-don't-layer.
10. Implement each task inside its own task worktree, cut from its job's worktree branch per `worktrees/AGENTS.md` §1.

## 2a. Push green

- Every work-branch push (`<work>M.m.p`, the constitution's `gitflow:`) runs the repo's `verify:` line first, green.
- Pre-push: `.dadaia/AGENTS.md` §3.
- Commits flow freely; a full scan lives only in the audit lane.
- Fix a red `verify:` line at its cause, since a rerun hides the defect it reports.
- A flaky test is quarantined by the repo's own mechanism, bug-gated; an unregistered pass-on-retry is a failure.

## 3. Done when

- Live release resolved (`dd-spec-navigator` Phase 3).
- Task committed under its id in its task worktree; the main thread runs its `WT merge` (`worktrees/AGENTS.md` §2).
- Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- `verify:` line green before any push; the reviewer's `APPROVED` on the work-branch head before its PR (`dd-gitflow-default` §3b).
- At candidate closure: the Reconciliation job merged (`RC-FLOW.md` step 4) -> candidate PR -> the promote-or-continue gate.

## 4. References

- [`RC-FLOW.md`](RC-FLOW.md) — gate cadence table, the candidate arc.
- [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md) — `_RELEASE.json` shape, milestone ownership, `log` conventions.
- [`MEMORY-UPDATE.md`](MEMORY-UPDATE.md) — closure memory protocol.
