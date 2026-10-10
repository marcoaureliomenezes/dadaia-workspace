# Job 5 — the jr sweep and the retired-name test row (AC2.5)

**Status:** Draft

Wave 4. Waits on Job 4 because T4's row asserts the whole library clean. Renames only: `Owner:` docstring lines and sample agent names in tests that Jobs 1 and 2 did not touch. Behaviour and asserts are unchanged; the sweep line goes in each commit body: `git grep -c 'dd-software-engineer' -- <the task's files>` before (counts) and 0 after, and `git grep -n 'dd-software-engineer' -- dadaia_workspace tests` printing nothing after T4.

- All tasks have disjoint `W:`; T1–T3 run in parallel, T4 last.

Tasks: 4 (0 sr, 4 jr).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | jr | AC2.5 | `tests/e2e/features/test_cli_uninitialized_workspace.py`, `tests/e2e/features/test_ctx_inject_bind_boundary.py`, `tests/e2e/features/test_handoff_pipeline.py`, `tests/e2e/features/test_specs_upgrade_e2e.py`, `tests/e2e/test_evals_scripts.py`, `tests/e2e/test_evals_t1.py` | rename: `Owner: dd-software-engineer` becomes `Owner: dd-sw-engineer-sr` (and the sample agent name in `test_handoff_pipeline.py:70`) |
| J5.T2 | jr | AC2.5 | `tests/e2e/test_evals_t2.py`, `tests/e2e/test_onboarding_journey.py`, `tests/e2e/test_one_line_bootstrap.py`, `tests/e2e/test_push_denylist_journey.py`, `tests/e2e/test_push_gate_check.py`, `tests/fixtures/test_previous_release.py`, `tests/public/scripts/test_pre_push_ci_gate.py` | rename: `Owner: dd-software-engineer` becomes `Owner: dd-sw-engineer-sr` |
| J5.T3 | jr | AC2.5 | `tests/cli/commands/test_reports.py`, `tests/core/test_handoff_index.py`, `tests/core/test_handoff_index__handoff_schema_contract.py`, `tests/hooks/test_root_whitelist.py`, `tests/fixtures/handoffs/v1.2-deepening-audit-self-pull.handoff.json` | rename: sample agent names in handoff, report and hook fixtures become `dd-sw-engineer-sr` (the fixture JSON still validates) |
| J5.T4 | jr | AC2.5 | `tests/infrastructure/test_privacy_check.py` | literal test: one more row of `test_public_source_names_no_retired_surface` over every `public` glob for the retired persona name, written so the test file itself does not contain the literal; fails if any shipped file still names it. After T1–T3 and Job 4 |
