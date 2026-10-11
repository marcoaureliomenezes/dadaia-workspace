# Job 11 — backlog skill: one slug grammar owned by the backlog schema; kernel owners adopted (FR13, FR11)

**Status:** Draft

Wave 3, after Job 1 (the owners and the moved schema) and Job 5 (it removes `--ts` and the ADR-number comments from the same files). One skill, one job. The slug owner is `$defs.slug` of `backlog-v1.schema.json`, now in this skill's `scripts/schemas/`; the worktree name parser (Job 13) and `verdict.py` (Job 14) read it through `_ledger.load_schema('backlog-v1')` and add their own `a--b` case, so the three jobs need no order among themselves.

- The three slug patterns inside the schema (`:28`, `:44`, `:64`) become one `$defs.slug` referenced thrice; `_backlog_write.py:17` reads the pattern from the schema instead of keeping a literal.
- `_backlog_store.py` loses `Refusal`, `serialize`, `_validated` and the commit loop to the kernel's `_refusal`, `_jsonl`, `_commit`; `_backlog_check.py` loses `finding()`, `histo_findings` and its JSONL line parser; `backlog.py` loses `_values`; vocabularies (`_backlog_schema.py:15,17`) are read from the schema; the clock helper (`_backlog_write.py:23`) is `_clock`.
- radon: no function of this skill is rank D to F (measured at `99a522b3d`), so no refactor task.
- Test-side first: T1. Then T2, T3 in parallel (disjoint `W:`).
- Sweep lines in commit bodies: `git grep -n 'class Refusal\|def serialize\|def _values\|def commit\|def _validated' -- dadaia_workspace/public/skills/dd-backlog-definition` (5 before, 0 after); `git grep -n '\[a-z0-9\]' -- dadaia_workspace/public/skills/dd-backlog-definition` (slug literals: 1 before the schema's, 0 after).
- Pre-review checklist: one reader per rule (each copy deleted); the only cross-skill edge is the kernel's; sweep lines above; no platform fact; net production lines ≤ 0 (est. −120).

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J11.T1 | sr | AC13.1 | `tests/public/skills/dd_backlog_definition/scripts/test__backlog_schema.py` | RED, unit: the slug `a--b` is accepted or refused identically by (a) `backlog.py new`, (b) the schema validation of an entry carrying it, (c) every other `$ref` of the slug definition (intents, histo); the three schema patterns are one `$defs.slug`. Owner this file |
| J11.T2 | sr | AC13.1 | `dadaia_workspace/public/skills/dd-backlog-definition/scripts/schemas/backlog-v1.schema.json`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_write.py` | one `$defs.slug` referenced by all three places; `_backlog_write` reads it. Owner T1. Fix commit of the slug bug; Phase 0 block `caused_by: none`, `prior diffs read: the four slug patterns`, `rebuild: the slug grammar`. After T1 |
| J11.T3 | sr | AC11.4 | `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_check.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_exit.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_schema.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/backlog.py`, `tests/public/skills/dd_backlog_definition/scripts/test_backlog.py`, `tests/public/skills/dd_backlog_definition/scripts/test__backlog_exit.py` | adopt the kernel owners as the intro says; delete the copies. The existing backlog suites stay green unedited (the two test files are listed because their imports of `Refusal`/`serialize` follow the move, imports only). After Job 1. Also deletes the `cast` in `_backlog_check.py` that existed only because mypy could not follow the `sys.path` edges (absorbed `task-gate-mypy-follows-cross-skill-imports`) |
