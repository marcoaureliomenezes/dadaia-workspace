# Job 11 — backlog skill: kernel owners adopted, no import of the release skill (FR11)

**Status:** Draft

Wave 3, after Job 1 (the owners, the moved schema with its one `$defs.slug`, and the `release.py origin` verb) and Job 5 (it removes `--ts` and the ADR-number comments from the same files). One skill, one job.

- `_backlog_store.py` loses `Refusal`, `serialize`, `_validated` and the commit loop to the kernel's `_refusal`, `_jsonl`, `_commit`; `_backlog_check.py` loses `finding()`, `histo_findings` and its JSONL line parser; `backlog.py` loses `_values`; vocabularies (`_backlog_schema.py:15,17`) are read from the schema; the clock helper (`_backlog_write.py:23`) is `_clock`.
- The surviving edge to the release skill (`_backlog_exit.py:21`, `from _release_schema import origin`) is deleted: `exit` runs `release.py origin <spec> --json` through the sibling script path (PLAN §1.5); the `sys.path` line that served it leaves with it.
- radon: no function of this skill is rank D to F (measured at `54c85077b`), so no refactor task.
- Test-side first: none (behaviour-preserving). T1 and T2 are disjoint.
- Sweep lines in commit bodies: `git grep -nE 'class Refusal|def serialize|def _values|def commit|def _validated' -- dadaia_workspace/public/skills/dd-backlog-definition` (5 before, 0 after); `git grep -n '_release_schema' -- dadaia_workspace/public/skills/dd-backlog-definition` (1 before, 0 after).
- Pre-review checklist: one reader per rule (each copy deleted); no cross-component import or cycle beyond the kernel edge; sweep lines above; no platform fact; net production lines ≤ 0 (est. −110).

Tasks: 2 (0 jr, 2 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J11.T1 | sr | AC11.4 | `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_check.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_schema.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/backlog.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_write.py`, `tests/public/skills/dd_backlog_definition/scripts/test_backlog.py` | adopt the kernel owners as the intro says; delete the copies. The existing backlog suites stay green unedited (`test_backlog.py` is listed for its import follow only). Also deletes the `cast` in `_backlog_check.py` that existed only because mypy could not follow the `sys.path` edges (absorbed `task-gate-mypy-follows-cross-skill-imports`). After Job 1 |
| J11.T2 | sr | AC11.4 | `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_exit.py`, `tests/public/skills/dd_backlog_definition/scripts/test__backlog_exit.py` | `exit` reads the Origin ids by running `release.py origin <spec> --json`; delete the import, the `sys.path` line and the `Refusal`/`serialize` copies of this file. Owner `test__backlog_exit.py` unedited. After Job 1 |
