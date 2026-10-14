# Job 3 — Retire the `.S<m>` task-id form (FR3)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1 and the as-is review it points to.

- ADR 0231 retired stages. `TASK_ID_RE` drops `(?:\.S\d+)?`; the `.S` form moves to `HISTORICAL_TASK_RE`, which lineage alone reads (36 ledger records carry `caused_by` ids such as `J1.S3.T1`, ASIS H6). `_release_schema.py:258,286` stop accepting the form in a current job file. T2 checks whether `stage_writes` and the `## Stage` parse (`_release_schema.py:273-300`) have a live caller: delete if none, else leave and report.
- `scripts/guards/slop.py:138` (`staged_task_id`) is a second reader of the `.S` form: KEEP, it refuses a leftover id of the retired form in a comment or docstring, which the retirement makes more right, not less; no edit. The bug-window note applies: `HISTORICAL_TASK_RE` (`_grammar.py:21`) is the second task grammar, finite history only; this job edits it in the same diff.

Tasks: 2 (1 jr, 1 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5). Parallelism: Sequential, two tasks.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | sr | AC3.1 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py` | RED (first assert fails today): `TASK_ID_RE.fullmatch("J1.S3.T1")` falsy and `fullmatch("J13.T6")` truthy; `bugs.py check` still accepts a resolved bug whose `caused_by` is `J1.S3.T1` when an archived `tasks/job1.md` carries it; `release.py check` refuses a current job file whose task id is `J1.S3.T1` and still exits 0 on the repo's own archived candidates |
| J3.T2 | jr | AC3.1 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_grammar.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` | `TASK_ID_RE` loses the group, `HISTORICAL_TASK_RE` gains `J[0-9A-Z]+\.S…\.T…`, `_release_schema.py:286` drops `(?:\.S\d+)?` (≈ −2 lines); owner T1. After T1 |
