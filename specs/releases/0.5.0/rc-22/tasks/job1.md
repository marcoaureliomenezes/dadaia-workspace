# Job 1 — the agentic scorecard final round (FR8)

**Status:** Draft

Wave 1, no job edge. It opens only after every lane of PLAN §3 that writes `dadaia_workspace/public/**` has merged on `feature/0.5.0` and `worktree sync <wt-rc path>` has brought them in; the lanes are not jobs. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §2, §3. The rubric is `.dadaia/reports/dadaia-workspace/agentic-scorecard/20261017T0519Z/rubric.md` (R1-R8, P1-P3, S1-S12, C1-C6); the judges are two independent read-only `dd-code-reviewer` sessions, each scoring every cell with `path:line` for every cell below 9; the main thread never scores.

- **Round 1 (AC8.1).** Run by the main thread as the define's last act on the tip that holds every lane (PLAN §3, act S1). Its record lists the cells below 9; each becomes one fix row `J1.T2..T<k>` (one row per file group, no file in two rows), inserted into this file and into PLAN's DAG `W:` by a shape-5 amendment in the `wt-rc` before this job's `wt-main` opens, as rc-21's Job 5 did. Until then the job holds its closing row only.
- **Fix rule (AC8.2).** A fix deletes or corrects text before it adds any; it adds no mechanism, no file, no gate. A cell that stays below 9 because the law and the code disagree is a finding for the main thread (Arm B), never a new rule. A scaffold edit re-pins its canon digest in `shipped-hashes.json` and the byte-identical repo copy; those files then join that row's `W:`.
- **Final round (AC8.3).** The closing row runs after every fix row has merged and the job's `wt-main` is merged into the `wt-rc`: that head is the frozen tip for `dadaia_workspace/public/**` (the closure writes only `specs/memory`, `README.md`, `docs`, `llms-full.txt` and `_RELEASE.json`, none scored). Two judges re-score every cell at that sha; the loop is score, fix, re-score, and stops only when both put every cell at 9 or above. A fix after a round re-opens the job (a new row), so the last round names the sha the closure starts from. Round files land under `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/`, never in the repo.

**Gate law.** `verify:` is `python scripts/ci.py job`, unchanged; no preflight, no new gate. A fix row's Definition of done is that run, the directories `python scripts/impact.py <the row's W:>` prints at its base, and the own-diff self-check. The closing row has no code; the main thread cites the record path and both judges' totals.

**Sweep greps.** `git diff --numstat <base>...HEAD -- dadaia_workspace/public` shows a net at or below 0; `git grep -nE "ADR [0-9]{4}|dadaia_workspace/" -- dadaia_workspace/public` prints no new line.

**Seeded fix rows.** The pre-mortem's open law-text hits (PLAN §1.2: R1 `worktrees-AGENTS.md:22` holding only where a subagent key exists; R4 the map §3 Operator-action classes against Q11) are judged by round 1, not pre-assigned: a cell they leave below 9 becomes a fix row.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J1.T1 | cr | AC8.1, AC8.2, AC8.3 | `.dadaia/reports/dadaia-workspace/agentic-scorecard/` | CLOSING ROW, runs after every fix row: the final round at the frozen tip, two judges, every cell >= 9; no test: the record is the evidence (the round directory named in the closure report) |
