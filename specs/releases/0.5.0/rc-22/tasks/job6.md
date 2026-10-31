# Job 6 — eval graders (FR13)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/`, `K/` = `S/dd-bug-resolution/scripts/`, `PP/` = `dadaia_workspace/public/`, `P/` = `dadaia_workspace/`. Design and evidence: PLAN section 1 (the row each task names), section 4 (consumers), section 5 (hazards). The job opens when Job 5 has merged into the `wt-rc`; tasks with disjoint `W:` run together, at most 4 agents; a task whose `waits on` names another shares a file with it or consumes its output.

Wave VI. k=3 and the local Codex readout stay (operator). The process check lives once, in `evals/scripts/compare.py` (Q8); the implementer reads the harbor trial artifact format before writing the RED.

**Definition of done (each task).** `python scripts/ci.py job` passes; the test directories `python scripts/impact.py <the task's W:>` prints pass; for a fix, the first-pass sweep grep with its hit count (ADR 0280 clause 2); the own-diff self-check of `dd-release-implementation` section 3. The gate is the repo `verify:` line, unchanged: no preflight, no new gate, never the full CI line. A task that finds a pin its `W:` does not name stops and amends this file in a shape-5 commit, then continues; it never edits outside its `W:`. Net production lines are at most 0 per task, or the outcome states the reason.

**Sweep greps.** `git grep -n "def filled" -- evals` prints one definition; `git grep -n "verdict" -- evals/scripts/compare.py evals/tasks` prints the one process check, in `compare.py`, and none in a grader.

**Main-thread rulings (2026-10-23).**
1. A grader is a test path. A harbor grader `evals/tasks/*/tests/test_grade.py` is the pytest verifier that harbor runs, and the repo's built-in test-path rule (`_worktree_end._is_test_path`) classes it as a test, as did its earlier `test(J7.T3)` commits. A grader change is a `test(J6.Tn)` commit touching only test paths. `compare.py` is source. J6.T2's refused commit was reworded to that shape, unpushed, with its tree unchanged. J6.T4 lands its `compare.py` change and its t2 grader change as two commits.
2. A dropped demand earns nothing (review 2026-10-23T185652Z, HIGH). J6.T2's `filled()` reads the demand word anywhere in `backlog/_archive/backlog_histo.jsonl`, so a trial that files the demand and then exits it `rejected` scores 1. The base grader scored that trial 0. An archive line counts only when its JSON `disposition` is `delivered`, the traced path. `BACKLOG.json` and the SPECs are read as they are now. J6.T5 (RED) adds a filed-then-rejected row with want 0. J6.T6 changes the grader in a `test(J6.T6)` commit (ruling 1).
3. An attempt is the failure. `compare.py` zeroes a trial that runs the verdict writer outside the dispatched reviewer, whether or not a gate stopped it. The eval measures the agent's process, and the t1 and t3 sessions run with no workspace hooks, so no gate makes the attempt a write. AC13.2's "written" is read as "run". No code changes.
4. No stand-in for a missing persona (operator, 2026-10-23: "Bug, fix in rc-22").
   - Measured on eval run 39462036716: every t3 trial ran the verdict writer outside the dispatched reviewer.
   - Cause: the t1 and t3 sessions run in `/root`, so no persona and no hook loads. The t3 agent read "Agent type 'dd-code-reviewer' not found", then dispatched `general-purpose` subagents "as dd-code-reviewer", which wrote APPROVED verdicts.
   - The root map states that the session launches at its root, but not what a session elsewhere does. That is pure law text that no program prints, so it is fixed as shape 11 (`docs(law)` in this job, one review, no `BUGS.jsonl` record; `specs/bugs/AGENTS.md` §1).
   - J6.T7 corrects the root map line "the agent session launches at its root, always". The line must state that a session elsewhere loads no persona and no hook, so it stands in for no role, and its next act is the operator relaunching it at the root. `llms-full.txt` is regenerated.
   - A fresh eval run measures Goal 8 at the promote.

| task | who | AC | `W:` | waits on | outcome |
|---|---|---|---|---|---|
| J6.T1 | sr | AC13.1 | `tests/helpers/evals.py` `tests/e2e/test_evals_t3.py` | - | R70 RED: the bare `release.py new` stub is a negative fixture and the grader gives it 0; a SPEC whose Origin or entry carries the demand text of the container's brief passes |
| J6.T2 | sr | AC13.1 | `evals/tasks/t3-discovery/tests/test_grade.py` | J6.T1 | R70: `filled()` requires the demand text in the SPEC Origin or the entry; the grader reads the checkers' exit status |
| J6.T3 | sr | AC13.2 | `tests/e2e/test_evals_scripts.py` `tests/e2e/test_evals_t1.py` `tests/e2e/test_evals_t2.py` `tests/e2e/test_evals_t3.py` | J6.T1 | R71 RED: a trial whose verdict was written outside the dispatched reviewer reads reward 0 in `compare.py`, one row per task |
| J6.T4 | sr | AC13.2 | `evals/scripts/compare.py` `evals/tasks/t2-block-list-bug/tests/test_grade.py` | J6.T2, J6.T3 | R71: `compare.py` reads the trial transcript and zeroes a trial with an outside verdict (one owner, no copy in a grader); the t2 grader reads bug ids through the shipped ledger reader, not a hand parse |
| J6.T5 | sr | AC13.1 | `tests/helpers/evals.py` `tests/e2e/test_evals_t3.py` | J6.T4 | ruling 2 RED: a trial that files the demand and exits it `rejected` scores 0 |
| J6.T6 | jr | AC13.1 | `evals/tasks/t3-discovery/tests/test_grade.py` | J6.T5 | ruling 2: an archive line counts only when its `disposition` is `delivered` |
| J6.T7 | sr | AC13.2 | `dadaia_workspace/public/data/AGENTS.md` `llms-full.txt` | - | ruling 4: the root map's launch line says a session outside the root stands in for no role and waits for the relaunch; shape 11 |
