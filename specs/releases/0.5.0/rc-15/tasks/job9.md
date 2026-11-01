# Job 9 — no fixed cap on open task trees (FR9)

**Status:** Draft

Wave 3. ADR 0250 (accepted 2026-10-13) amends 0191: parallelism is the approved PLAN's schedule. `TASK_CAP`, the sixth-task refusal and the law clause leave; the job-branch refusal of `_refuse_task` stays. ADR 0250's `measured_by` is the AC9.1 case of this job.

- **Seams closed.**
  - `_refuse_task` keeps only the "no job branch" check; `_exit` and the `ours` import leave if nothing else uses them (a grep in the commit body).
  - **Ordered change (AC9.1).** In `test__worktree_new.py:138-152` the sixth-task refusal and its `clean` fix assert, and the final "the cap counts tasks only" line, become "the sixth task opens" (and a different job's first task still opens). The orphan and job-branch asserts stay unedited. The `test(J9.T1)` commit names the operator's order of 2026-10-13: "Trocar o assert (Recommended)"; the test is renamed to its contract and `_word` leaves if nothing else uses it.
  - The instance copy `worktrees/AGENTS.md` follows by the main thread's reprojection after the merge, not by a task.
- Test-side first: T1. Then T2, T3 (disjoint `W:`).
- Commit bodies carry `git grep -nE 'TASK_CAP|task worktrees are open|at most 5' -- dadaia_workspace tests` (hits before, 0 after).
- Pre-review checklist: parallelism has one decider, the PLAN; sweep line; net lines about −12.

Tasks: 3 (2 jr, 1 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J9.T1 | sr | AC9.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py` | the ordered assert change of the intro, quoting the order. RED: the sixth task refuses today |
| J9.T2 | jr | AC9.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py` | `TASK_CAP`, its refusal, `_exit` and the `ours` import leave as the intro says. Owner T1. After T1 |
| J9.T3 | jr | AC9.2 | `dadaia_workspace/public/data/worktrees-AGENTS.md` | the clause "at most 5 task worktrees are open per rc" leaves line 15; the rest of the line stays. No test, reviewer sweep |
