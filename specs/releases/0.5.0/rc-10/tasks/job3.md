# TASKS — 0.5.0 rc-10, Job 3 — evals: the first run

**Status:** Approved — by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

`W:` paths are relative to `repos/dadaia-evals`. Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

- Edge: Job 2 on `dadaia-evals` `main`. The run is the driver's act; a tree (`worktrees/dadaia-evals/0.5.0-rc10/job3`) opens only for a grader fix (PLAN agent default 2); its `W:` paths are relative to `repos/dadaia-evals`.

## Stage J3.S1 — RED (none: AC3.1 has no test)

- Contract: no acceptance test exists for AC3.1 (one model run, observed); no task rows.

## Stage J3.S2 — the run

- Contract: exit tests: the run's verdict per 0178 (2) read; a grader fix, if any, keeps `tests/` green; envelope `tasks/*/tests/test_grade.py`, `tasks/*/tests/test.sh`; ACs AC3.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J3.S2.T1 | AC3.1 | — (driver: `gh workflow run eval.yml -f lib_ref=<feature/0.5.0 tip>`, T1 + T2, k=3, `-n 2`; confirms `dadaia capabilities --json` names the stamped candidate and no rate-limit error in `jobs/`) | check: the `_RELEASE.json` `kind: note` names the run URL, verdict, tokens, wall time |
| J3.S2.T2+ | AC3.1 | the failing task's `tests/test_grade.py` / `tests/test.sh` | born per failing grader; its Job 2 test row green; one rerun of that task |
| J3.S2.T9 | — | — (close commit in `dadaia-evals`, only if a tree opened) | close task: `test-audit:` and `mutation:` lines; with no tree Job 3 logs only its `kind: note`; this file's `done` is written by Reconciliation |
