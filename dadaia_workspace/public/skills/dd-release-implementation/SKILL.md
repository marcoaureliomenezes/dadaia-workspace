---
name: dd-release-implementation
description: >
  Run an Approved candidate to its PR: job and task worktrees, the RED-test then implementation task pair,
  the job review and merge, the reconcile on the rc's `wt-rc` (phase CLOSURE, memory pass, disposition sweep, doctor)
  and _RELEASE.json entries. Use when working a task or job, closing a candidate, or writing release state.
  Defining a candidate is dd-release-definition's; PRs, promote and the next work branch are dd-gitflow-default's.
---

# dd-release-implementation

## 1. When

- `dd-sw-engineer-sr` or `dd-sw-engineer-jr` working a task inside an `Approved` candidate.
- `dd-product-engineer` at each candidate's closure (memory, `_RELEASE.json`).
- From the first task through candidate closure (`dd-gitflow-default` step 8); the gate after it: steps 9-12.

## 2. Steps

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the live release: `dd-spec-navigator` Phase 3.
3. The live candidate's job files: `dd-release-definition` §The job file — tasks; a lower `rc-<N>/` is closed history.
4. Full navigation protocol: `dd-spec-navigator`.
5. Read `RC-FLOW.md` for the candidate arc before acting past opening a task.
6. Change `_RELEASE.json` only through `release.py` verbs; its hand-written entries are `RELEASE-EVENTS.md`'s.
7. At `RC-FLOW.md` step 4, run `MEMORY-UPDATE.md`'s full protocol before touching any memory atom.
8. A test enters the suite only under the root map §The flow test basics.
9. Before growing any module, run the deletion test (`dd-code-review` SLOP.md) — a diff that only adds justifies itself against replace-don't-layer.
10. Implement each task inside its own `wt-task-<kkk>` tree (`worktrees/AGENTS.md` §The tree), cut from its job's `wt-main` (`dd-gitflow-default` §The branch contract).
11. Before claiming a bug, unused code or done, cite file:line or a grep; reproduce from a clean state; done needs user-side evidence.
12. After any tool error, re-read the real state; return a deferral to the main thread as an intake proposal carrying its design, never written into the backlog.
13. A red not caused by the change is proven at the merge-base before it is called pre-existing; an env-sensitive change is reproduced in a clean environment first.

## 2a. Push green

- Pre-push: `.dadaia/AGENTS.md` §Git chokepoints.
- Commits flow freely; a full scan lives only in the audit (`dd-audit-project`).
- Fix a red `verify:` line at its cause, since a rerun hides the defect it reports.
- A flaky test is quarantined by the repo's own mechanism, bug-gated; an unregistered pass-on-retry is a failure.

## 3. Done when

- Live release resolved (`dd-spec-navigator` Phase 3).
- Task committed under its id in its `wt-task-<kkk>` tree; the main thread runs its `WT merge` (`worktrees/AGENTS.md` §Merges, gates, review).
- The implementer hands back with no process of its own still running (no background command, `jobs` empty).
- Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- Self-check before every hand-back: run the repo's `verify:` line and the test directories the change reaches, then read your own `git diff <base>...HEAD` for removed assertions, newly skipped tests, hand-typed fix-line labels, platform literals in assertions and the sweep greps the job file names; a hit is fixed or reported, never handed back silently.
- The hand-back carries evidence per item, extending the engineer's evidence line: the consumer sweep for a changed grammar, format, public name or fix line (other repos as a count, never by name) and evidence for each QA-lens item of `dd-code-review` §The six lenses; old asserts follow the root map §The flow test line; a bare PASS goes back unreviewed.
- At candidate closure: the `wt-rc` carrying the reconcile merged (`RC-FLOW.md` step 4) -> the promote-or-continue gate (`dd-gitflow-default` steps 8-9); the main thread's closure report to the operator carries the batch of `dd-manager-orchestration` (Conflict resolution, step 4) and the readout table of `python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py stats <M.m.p>-rc<N> --specs <specs-dir>`.

## 4. References

- [`RC-FLOW.md`](RC-FLOW.md) — the gate pointers and the candidate arc.
- [`RELEASE-EVENTS.md`](RELEASE-EVENTS.md) — `_RELEASE.json` shape, milestone ownership, `log` conventions.
- [`MEMORY-UPDATE.md`](MEMORY-UPDATE.md) — closure memory protocol.
