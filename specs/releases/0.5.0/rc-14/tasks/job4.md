# Job 4 — gitflow skill: one declared-line reader, worktree rows of a repo that left, the specs-revert row (FR6, FR14, FR17)

**Status:** Draft

Wave 1. Two REBUILDs in `dd-gitflow-default` (PLAN §1 rows 17 and 18) and the §3a row. ADR 0220 P3 already bans shlex for Windows, so the one splitter is `str.split()`; the documented behaviour (a verify line is one argv command with no shell, `;` and `$(...)` are plain words) is unchanged.

- Test-side first: T1, T2, T3 in parallel; then T4, T5; then T6; T7 and T8 any time.
- `_worktree_git.rows` reports a tree of a repo outside every gitflow with state `unregistered` and `registered: false`; the one filter, "rows of this context's repos plus rows no context owns", lives in `ledger_scripts.worktree_rows(root, repos)`; the two inline `r['repo'] in repos` filters (doctor and `ctx_inject`) leave. The two renders stay for Wave 3's `context-show-derives-worktrees`.
- The §3a row takes the free number 7: tree `wt/hotfix/<bug-id>`, writes the reverted `specs/` paths, message `Revert "<subject>"` with the `block: <item>` body.
- Commit bodies carry `git grep -n 'shlex' -- dadaia_workspace/public/skills/dd-gitflow-default` (2 hits before, 0 after) and the ADR-number comment count of `_worktree_end.py` and `_worktree_git.py` (7 before, 0 after).
- Net production lines ≤ 0 for the job (measured: the three helpers `_declared`, `_gate`, `_is_test_path` are 56 lines; `rows` is 53).
- Ledger transitions of this job's bugs (`bugs.py resolve`) are made at the Reconciliation, which owns `specs/bugs/BUGS.jsonl`; this job's fix commits echo the Phase 0 block.

Tasks: 8 (2 jr, 6 sr). `who` names the dispatched role (SPEC FR5 of rc-13, `dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | sr | AC14.1 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` | RED, unit: the declared line `python scripts\ci.py job` runs as `['python', 'scripts\\ci.py', 'job']` and a `tests:` glob line splits by the same function; the existing `;` and `$(...)` words case stays. Also deletes the dead `verify-task:` and `verify-stage:` lines of the fixture (`:426`, `:557`). Owner `test__worktree_end.py` |
| J4.T2 | sr | AC17.1 | `tests/features/spec_context/test_doctor__worktree_rows.py` | RED, integration: a linked worktree under `worktrees/gone/` of a repo registered in no context is a doctor finding with exactly one fix line, and the `ctx_inject` bind block shows it; a registered repo's rows are unchanged. Owner `test_doctor__worktree_rows.py` |
| J4.T3 | sr | AC17.1 | `tests/infrastructure/test_ledger_scripts.py` | RED, unit: `worktree_rows(root, repos)` returns rows whose repo is in `repos` plus rows with `registered: false`, and no row of another context's repo. Owner `test_ledger_scripts.py` |
| J4.T4 | sr | AC14.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` | REBUILD: one `_declared_argv(tree, work, key)` reads and splits a declared line; `_gate` and `_refuse_implementation_tests`/`_is_test_path` call it; delete both `shlex.split` calls and the import; delete the ADR-number comment lines. Owner T1. Fix commit of the shlex bug; body echoes the Phase 0 block (`prior diffs read: 9d608bba8, cb5cc3fde`, `rebuild: the declared-line reader`) |
| J4.T5 | sr | AC17.1 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py` | REBUILD `rows`: also walk `worktrees/<repo>/` of repos with no gitflow record, report their trees as `unregistered` with `registered: false` and an empty `exit`; delete the ADR-number comment lines. Owner T2, T3. Fix commit of the doctor bug |
| J4.T6 | sr | AC17.1 | `dadaia_workspace/infrastructure/ledger_scripts.py`, `dadaia_workspace/features/spec_context/doctor.py`, `dadaia_workspace/hooks/ctx_inject.py` | `worktree_rows(root, repos)` owns the one filter; `check_worktrees` and `_worktrees` pass their repos and drop their inline filters. Owners T2, T3. After T5 |
| J4.T7 | jr | AC6.1 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` | the §3a row 7 for a hotfix that reverts `specs/` text; row 9 stops naming `llms.txt`. No test; reviewer sweep: the table keeps one shape per write |
| J4.T8 | jr | AC9.2 | `tests/helpers/worktree_ws.py` | delete the dead `verify-task:` and `verify-stage:` lines the fixture writes (`:120`); owner the gitflow script tests, green unedited |
