# Job 2 — law text: self-check, gate-cost wording, closure order, commit rows, scorecard line (FR3, FR4, FR5, FR7, FR8, FR10, FR11)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and §1.2 consumers.

- Law and skill text only: no behaviour, so no RED test. The checks are `dadaia public doctor` printing `[ok] public-privacy`, the entity and doctor tests, and the AI-surface lens (`AUTHORING.md`, 15 rules) at review. A rewording deletes words before it adds any.
- **Moved out of this job.** The closure-scope line of the bugs law, its mirror, its `shipped-hashes.json` digest and the `CANON_AT` re-pin are Job 7's (`shipped-hashes.json` and `core/specs_version.py` have one owner, no parallel sharing).
- **T1.** One self-check, written once in `dd-release-implementation/SKILL.md` §3: `python scripts/ci.py job`, the touched test directories, the own-diff self-check (removed `assert` lines, added skip/xfail, the platform-literal greps, the PLAN's sweep greps) over `git diff <base>...HEAD`, and the REBUILD-due check. The sr persona §3 points to it and restates nothing; the jr persona already reads the sr file first, so no jr edit. The `verify:` line and the merge checks do not change (`git diff <base>...HEAD -- AGENTS.md` shows no `verify:` change).
- **T2.** Root map line on gate cost: the cap compares a changed `verify:` with the `verify:` it replaces, never with itself; the line that says a gate change states its measured cost agrees; `Agent action: <one act>` agrees with the ruled SeveralWork form. `dd-grill-me/SKILL.md:32`: Recommended never marks a heavier gate. `public/data/AGENTS.md` projects to the instance root `AGENTS.md` by `public install`; never hand-edit the instance copy.
- **T3.** `RC-FLOW.md` step 4 and `MEMORY-UPDATE.md` steps 1, 2, 9 and Done-when: after `release.py phase CLOSURE`, only block-list bugs land on the `wt-rc` and the next rc is born at once; the memory pass (`release.py drift`, atoms, doctor) is the last step before the `wt-rc` merge, after the `measured_by` repairs, measurement, disposition sweep and GC. The 2026-10-08 ruling (staleness judged by existence) stands.
- **T4.** `dd-gitflow-default` §3a gains a `docs(law)` row (pure law or doc text, in the job tree that found it, one review, no ledger record; text a program prints stays Arm B) and a `chore(bugs): update` row; `dd-code-review` gains the scratch-only probe recipe (`DADAIA_FENCED_ROOTS`); `dd-cli-library` names the `pkill -f` and `pgrep -f` waiters under the kill-by-PID line. Commit shapes are discipline: no script reads the §3a table.
- **T5 (`pe`).** `specs/constitution.md` §5 gains the Q5 line: the agentic scorecard is the final rc's last implementation job before the promote, never after the closure summary. Delete this task if the SPEC update already carries the line.

**Gate law (rc-17).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured). An implementer's definition of done is that run, plus the touched test directories (`tests/infrastructure`, `tests/features/specs`, `tests/core/test_template_history.py`), plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line, no added skip/xfail, and the sweep greps. No preflight, no full CI line; CI on push is the net.

**Sweep greps.** `git diff <base>...HEAD -- AGENTS.md | grep -E '^[-+]verify:'` prints nothing; `grep -n 'one run of the job' dadaia_workspace/public/data/AGENTS.md` shows the reworded cap; `git diff <base>...HEAD --stat` touches only this job's `W:`.

Tasks: 5 (3 jr, 1 sr, 1 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: all five tasks have disjoint `W:` and start together.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J2.T1 | sr | AC3.1, AC3.2 | `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/agents/dd-sw-engineer-sr.md` | the self-check written once in SKILL §3; sr §3 points to it; wording is a design choice (the first pass was 71 of 110 trees); no test |
| J2.T2 | jr | AC4.1, AC4.2, AC10.2 | `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/skills/dd-grill-me/SKILL.md` | text only: cap compared with the verify it replaces; measured-cost line agrees; `<one act>` wording matches SeveralWork; grill item 7 also bars a heavier gate |
| J2.T3 | jr | AC5.1, AC5.2, AC8.1 | `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md` | reorder step 4 (memory pass last) and add the closure-scope sentence; MEMORY-UPDATE steps 1, 2, 9 and Done-when follow; `MEMORY-UPDATE.md` step 1 "no memory write before CLOSURE" stays true |
| J2.T4 | jr | AC7.1, AC11.1 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-code-review/SKILL.md`, `dadaia_workspace/public/skills/dd-cli-library/SKILL.md` | two §3a rows, the probe recipe, the kill-by-PID wording; text only |
| J2.T5 | pe | AC5.3 | `specs/constitution.md` | the Q5 scorecard-placement line in §5, in the file's language; no test |
