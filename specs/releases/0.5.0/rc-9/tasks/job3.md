# TASKS — 0.5.0 rc-9, Job 3 — the REBUILDs

**Status:** Draft

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

As built on `wt/0.5.0-rc9/job3` (its PLAN.md, carried here; it wins over the PE draft — SPEC §How rc-9 runs, Deviation).

Worktree `worktrees/dadaia-workspace/0.5.0-rc9-job3`, branch `wt/0.5.0-rc9/job3`, cut from 2ace25f28. One tree for the job; no TASKS markers. Ledger rows (rc-8 AC12.4 numbering) are resolved by the main thread at merge.

Task ids follow the SPEC (fold 4fa92dba5). There is one deviation: AC3.2 runs as J3.S3.T1, not J3.S2.T2. AC3.3's redo also writes `features/spec_context/service.py` (the hold loop's fix line, `worktree_git_dir`), so the two tasks cannot share a stage with disjoint `W:`. Envelopes are as built. Gates: per task, `ruff` + `mypy --strict` on the touched files and the owner tests (`-n 2`); per stage, unit + integration (`-n 2`); at job end, `scripts/ci.py` once.

## S1 — RED only (test files; acceptance tests as strict xfail)

| Task | AC | `W:` | RED tests |
|---|---|---|---|
| J3.S1.T1 | AC3.1 | `tests/unit/test_suite_env.py`, `tests/integration/test_suite_session_env.py`, `tests/conftest.py` (`pytest_plugins`) | `test_suite_env[operator-out-temp-home-in]`, `test_an_inner_run_under_an_operator_context_sees_the_temp_home`; `test_an_inner_run_writing_a_watched_pycache_exits_1` already passes (the tripwire exists) and guards the redo |
| J3.S1.T2 | AC3.2, AC3.3 r27, AC3.6 r24 | `tests/integration/test_context_dead_holds.py`, `tests/integration/test_context_dead_submodule.py` | `test_dead_refuses_a_dirty_checkout_one_fix_line_per_file`, `test_an_oserror_in_the_hold_loop_refuses_with_a_fix_line`, `test_dead_holds_a_repo_with_a_submodule_and_its_gitdir_resolves` |
| J3.S1.T3 | AC3.3 r6, r21–23, AC3.6 r25, r26 | `tests/unit/features/spec_context/test_sweep.py`, `tests/unit/test_workspace_service.py`, `tests/unit/features/spec_context/test_doctor_gc.py` | `test_a_surviving_target_is_refused_by_its_outcome[*]`, `test_a_refusal_is_falsy_and_no_str`, `test_move_returns_its_failure_as_a_refusal`, `test_a_permission_failure_names_the_recorded_entry`, `test_a_root_level_held_symlink_keeps_its_hold_clock`, `test_a_refused_hold_leaves_the_list_form_denylist_in_place`, `test_the_expire_lane_walks_each_expired_entry_once` |

## S2 — the REBUILDs and the own fixes but AC3.2

ACs: AC3.1, AC3.3–AC3.6.

| Task | AC | `W:` | Owner tests |
|---|---|---|---|
| J3.S2.T1 | AC3.1 | `tests/conftest.py`, `tests/fixtures/harness_env.py` (`base_env` kept as a wrapper on `suite_env` for Jobs 1 and 2), `tests/helpers/worktree_ws.py`, `tests/unit/test_conftest_pollution_guard.py` (deleted), `tests/contract/test_core_file_io_purity.py`, the four e2e files, the two gate integration files, `tests/integration/test_tool_caches_stay_in_the_tmp_zone.py`, the two S1.T1 files | `test_suite_env.py`, `test_suite_session_env.py` |
| J3.S2.T3 | AC3.3, AC3.6 r24, r25, r26 | `features/spec_context/{sweep,doctor}.py`, `features/spec_context/service.py` (hold loop, `worktree_git_dir`), `features/workspace/service.py`, `features/migrate/upgrade.py`, `cli/commands/specs.py`; the S1.T3 files, `test_context_dead_holds.py` (r27 and the AC2.11 row), `test_context_dead_submodule.py`, the `sweep.deleter` test call sites | `test_sweep.py`, `test_doctor_gc.py`, `test_workspace_service.py`, `test_context_dead_holds.py`, `test_context_dead_submodule.py`, `tests/unit/features/migrate` |
| J3.S2.T4 | AC3.4 | `core/specs_version.py`, `specs/constitution.md`, `tests/unit/core/test_specs_version.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py` | those two |
| J3.S2.T5 | AC3.5 | `tests/unit/cli/test_exitcode_truthfulness.py` | itself |
| J3.S2.T6 | AC3.6 r20 | `scripts/guards/isolation.py` | `scripts/guards/run.py --planted` |

## S3 — `context dead` never commits

AC: AC3.2.

| Task | AC | `W:` | Owner tests |
|---|---|---|---|
| J3.S3.T1 | AC3.2 | `features/spec_context/service.py`, `infrastructure/git_subprocess.py`, `cli/commands/context.py`, `features/certification/service.py`, `container.py`; dead's, `commit_all`'s and the refusal harness's tests | `test_context_dead_holds.py`, `test_refusal_fix_lines_clear_their_refusal.py`, `test_spec_context_service.py`, `test_one_secret_matcher.py`, the git-subprocess tests |
