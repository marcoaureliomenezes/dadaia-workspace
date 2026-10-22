# Job 6 — eval graders (FR13)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/`, `K/` = `S/dd-bug-resolution/scripts/`, `PP/` = `dadaia_workspace/public/`, `P/` = `dadaia_workspace/`. Design and evidence: PLAN section 1 (the row each task names), section 4 (consumers), section 5 (hazards). The job opens when Job 5 has merged into the `wt-rc`; tasks with disjoint `W:` run together, at most 4 agents; a task whose `waits on` names another shares a file with it or consumes its output.

Wave VI. k=3 and the local Codex readout stay (operator). The process check lives once, in `evals/scripts/compare.py` (Q8); the implementer reads the harbor trial artifact format before writing the RED.

**Definition of done (each task).** `python scripts/ci.py job` passes; the test directories `python scripts/impact.py <the task's W:>` prints pass; for a fix, the first-pass sweep grep with its hit count (ADR 0280 clause 2); the own-diff self-check of `dd-release-implementation` section 3. The gate is the repo `verify:` line, unchanged: no preflight, no new gate, never the full CI line. A task that finds a pin its `W:` does not name stops and amends this file in a shape-5 commit, then continues; it never edits outside its `W:`. Net production lines are at most 0 per task, or the outcome states the reason.

**Sweep greps.** `git grep -n "def filled" -- evals` prints one definition; `git grep -n "verdict" -- evals/scripts/compare.py evals/tasks` prints the one process check, in `compare.py`, and none in a grader.

| task | who | AC | `W:` | waits on | outcome |
|---|---|---|---|---|---|
| J6.T1 | sr | AC13.1 | `tests/helpers/evals.py` `tests/e2e/test_evals_t3.py` | - | R70 RED: the bare `release.py new` stub is a negative fixture and the grader gives it 0; a SPEC whose Origin or entry carries the demand text of the container's brief passes |
| J6.T2 | sr | AC13.1 | `evals/tasks/t3-discovery/tests/test_grade.py` | J6.T1 | R70: `filled()` requires the demand text in the SPEC Origin or the entry; the grader reads the checkers' exit status |
| J6.T3 | sr | AC13.2 | `tests/e2e/test_evals_scripts.py` `tests/e2e/test_evals_t1.py` `tests/e2e/test_evals_t2.py` `tests/e2e/test_evals_t3.py` | J6.T1 | R71 RED: a trial whose verdict was written outside the dispatched reviewer reads reward 0 in `compare.py`, one row per task |
| J6.T4 | sr | AC13.2 | `evals/scripts/compare.py` `evals/tasks/t2-block-list-bug/tests/test_grade.py` | J6.T2, J6.T3 | R71: `compare.py` reads the trial transcript and zeroes a trial with an outside verdict (one owner, no copy in a grader); the t2 grader reads bug ids through the shipped ledger reader, not a hand parse |
