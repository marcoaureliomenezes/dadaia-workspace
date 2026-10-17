# Job 5 — the 9-metric readout: `verdict.py stats` REBUILT (FR9)

**Status:** Draft

Wave 3, waits on Job 2, Job 4. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1, §1.2 and §4 (the stated reason for the net ADD).

- **REBUILD of `_stats`.** `verdict.py` is the verdict writer (one job); the reader moves to `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py` and `verdict.py stats <M.m.p>-rc<N>` stays the entry. The count selects verdicts by the candidate's `produced_at` window, not by an rc-named branch prefix (the prefix filter is the defect and is deleted), so lane trees (`wt/<v>/wt-backlog-<slug>`, `wt-hotfix-<bug>`) and free-named trees count. It reads the handoff zone and `.dadaia/reaped/**` through `_handoffs.reviewer_records` (unchanged, shared with `_worktree_end.py`), and prints the oldest record it read (retention is about 8 days).
- **Rows printed (rulings).** Local metrics 1, 2, 4, 6, 7, 9 with the SPEC §2 target beside each; metrics 3 (merge `verify:` wall time) and 5 (CI red share) only when `gh` answers, otherwise `unread` and exit 0 (fail open); metric 8 prints the pointer to the one-grep test (Job 1), `pre-push-ci-gate.sh:32` being its one named exception. Absent data prints `n/a`, never a failure. Metric 9 asks the sibling reader of Job 4 by running `bugs.py` (no import across components); metric 7 runs `release.py drift --json` as a subprocess. Grep for an existing reader first (`_bugs_store.read_records`, `reviewer_records`).
- **Keeps passing.** `test_verdict.py:309` (counts per tree, `produced_at` order) and `:457` (fix line outside a workspace, literal text) stay; the old counters (`sequences`, `verdicts`, `rejected`, `first_pass_rejected`) are replaced by the table.
- **Net lines.** ADD of about +40 (`_stats.py` +75, `verdict.py` -33): the readout the operator ordered at Q9. Offsets searched: only the moved `_stats` (counted); no other deletion exists.

**Gate law (rc-17).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured). An implementer's definition of done is that run, plus the touched test directory (`tests/public/skills/dd_handoff_emitter`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line, no added skip/xfail, and the sweep greps. No preflight, no full CI line; CI on push is the net.

**Sweep greps.** `git grep -n 'first_pass_rejected' -- dadaia_workspace .agents` prints nothing outside the tests that pin the new table; `git grep -n 'startswith(f"wt/' -- dadaia_workspace/public/skills/dd-handoff-emitter` prints nothing; `git grep -nE 'import (verdict|bugs|release)\b' -- dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py` prints nothing (components are reached by running their script).

Tasks: 3 (1 jr, 2 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: T1 then T2; T3 starts with T1.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | sr | AC9.1, AC9.2 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, unit, over fixture ledgers and handoffs: each local metric value and its target; a lane-tree and a free-named-tree verdict counted; a record under `.dadaia/reaped/` read; the oldest record printed; metrics 3 and 5 read `unread` with no `gh` and exit 0 (and print values from a stub `gh`); absent data reads `n/a`; the existing `:309` and `:457` tests keep passing |
| J5.T2 | sr | AC9.1, AC9.2 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/_stats.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py` | `_stats` moves out of `verdict.py` and becomes the readout; `verdict.py stats` stays the entry. Owner: T1. After T1 |
| J5.T3 | jr | AC9.3 | `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md` | the three places that cite `verdict.py stats` name the table and its targets; the closure summary carries it (RC-FLOW step 4); text only |
