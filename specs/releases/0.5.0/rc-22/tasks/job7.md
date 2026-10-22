# Job 7 — the agentic scorecard final round (FR14)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/`, `K/` = `S/dd-bug-resolution/scripts/`, `PP/` = `dadaia_workspace/public/`, `P/` = `dadaia_workspace/`. Design and evidence: PLAN section 1 (the row each task names), section 4 (consumers), section 5 (hazards). The job opens when Job 6 has merged into the `wt-rc`; tasks with disjoint `W:` run together, at most 4 agents; a task whose `waits on` names another shares a file with it or consumes its output.

Wave VII. It opens when Jobs 1-6 have merged and the memory pass is not yet written: the closure writes only `specs/memory`, `README.md`, `docs`, `llms-full.txt` and `_RELEASE.json`, none scored, so the head of the `wt-rc` after this job is the frozen tip for `dadaia_workspace/public/**`. The rubric is `.dadaia/reports/dadaia-workspace/agentic-scorecard/20261017T0519Z/rubric.md` (R1-R8, P1-P3, S1-S12, C1-C6); the judges are two independent read-only `dd-code-reviewer` sessions, each scoring every cell with `path:line` for every cell below 9; the main thread never scores.

- **Round 1 (AC14.1).** Run by the main thread as act S1 (PLAN section 3) on the tip that holds Jobs 1-6. Its record lists the cells below 9; each becomes one fix row `J7.T2..T<k>` (one row per file group, no file in two rows), inserted into this file and into PLAN's DAG `W:` by a shape-5 amendment in the `wt-rc` before this job's `wt-main` opens. Until then the job holds its closing row only.
- **Fix rule.** A fix deletes or corrects text before it adds any; it adds no mechanism, no file, no gate. A cell that stays below 9 because the law and the code disagree is a finding for the main thread (Arm B), never a new rule. A scaffold edit re-pins its canon digest in `shipped-hashes.json` and the byte-identical repo copy; those files then join that row's `W:`, and the fix rows own `CANON_AT[13]` through one row only.
- **Final round.** The closing row runs after every fix row has merged and the job's `wt-main` is merged into the `wt-rc`: that head is the frozen tip for `dadaia_workspace/public/**`. Two judges re-score every cell at that sha; the loop is score, fix, re-score, and stops only when both put every cell at 9 or above. A fix after a round re-opens the job (a new row), so the last round names the sha the closure starts from. Round files land under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/`, never in the repo.

**Gate law.** `verify:` is `python scripts/ci.py job`, unchanged; no preflight, no new gate. A fix row's Definition of done is that run, the directories `python scripts/impact.py <the row's W:>` prints at its base, and the own-diff self-check. The closing row has no code; the main thread cites the record path and both judges' totals.

**Sweep greps.** none: the round record is the evidence.

| task | who | AC | `W:` | waits on | outcome |
|---|---|---|---|---|---|
| J7.T1 | cr | AC14.1 | `.dadaia/reports/dadaia-workspace/agentic-scorecard/` | - | CLOSING ROW, runs after every fix row: the final round at the frozen tip, two judges, every cell at 9 or above; no test: the record is the evidence (the round directory named in the closure report) |
