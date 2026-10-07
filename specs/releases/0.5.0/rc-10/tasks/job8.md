# TASKS — 0.5.0 rc-10, Job 8 — the unit tier spawns no processes

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Runs under today's law (before Job 6).

- Edge: Job 7. Test paths below are today's; the driver rewrites them to Job 7's mirror paths when the job opens (PLAN hot files).

## Stage J8.S1 — RED

- Contract: exit tests the AC8.2 rows RED as strict xfail; envelope `tests/unit/features/spec_context/test_service_rows.py`; ACs AC8.2
- AC8.3 has no RED row: its rows pass today through `run_hook_subprocess`; the rework is J8.S2.T4.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J8.S1.T1 | AC8.2 | `tests/unit/features/spec_context/test_service_rows.py` | RED: `SpecContextService` and `DoctorService` each built with a stub rows callable read its rows |

## Stage J8.S2 — DELETE the patches; inject the rows

- Contract: exit tests J8.S1 green, unit + integration green; envelope `f/spec_context/service.py`, `f/spec_context/doctor.py`, `dadaia_workspace/container.py`, `tests/conftest.py`, `tests/fakes.py`, `tests/contract/cli/test_cli_context.py`, `scripts/guards/isolation.py`, `tests/fixtures/harness_env.py`, `tests/unit/hooks/test_common.py`, `tests/unit/hooks/test_root_whitelist.py`, `dadaia_workspace/hooks/_common.py`; ACs AC8.2, AC8.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J8.S2.T1 | AC8.2 | `f/spec_context/service.py`, `f/spec_context/doctor.py`, `dadaia_workspace/container.py` (rows callable by constructor; the module-global read leaves) | `test_service_rows.py` |
| J8.S2.T2 | AC8.2 | `tests/conftest.py` (Job 7's bridge fixture leaves), `tests/fakes.py` (the stub rows), `tests/contract/cli/test_cli_context.py` (inline patch leaves) | `test_cli_context.py` |
| J8.S2.T3 | AC8.3 | `scripts/guards/isolation.py` (`hook-stdin-not-in-process` and its plants leave), `tests/fixtures/harness_env.py` (its comment pointer) | check: `grep -c hook-stdin-not-in-process scripts/guards/isolation.py` prints `0` |
| J8.S2.T4 | AC8.3 | `tests/unit/hooks/test_common.py`, `tests/unit/hooks/test_root_whitelist.py` (one row per hook lane through `run_hook_subprocess`; the `sys.stdin` patches leave), `dadaia_workspace/hooks/_common.py` (only if a row needs stdin injected at the entrypoint) | the two files |

## Stage J8.S3 — no process in a small test

- Contract: exit tests unit + integration green; guard plant red; envelope `scripts/guards/isolation.py`, the offenders' test files and sources named at stage open; ACs AC8.1
- Offender list: produced at the stage's open by the new guard's dry run (J8.S3.T1, 9 tests in 5 files, all hook-entrypoint tests through `run_hook_subprocess`); each offender file is one task row, disjoint `W:`.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J8.S3.T1 | AC8.1 | `scripts/guards/isolation.py` (check `small-spawns-no-process`: red on a planted subprocess in a small test) | guard plant |
| J8.S3.T2 | AC8.1 | `tests/core/test_workspace_resolver__one_workspace_root_rule.py` (`test_workspace_root_in_the_hook_env_never_opens_a_protected_write` drive the hook entrypoint through `run_hook_subprocess`: they turn `medium`, AC8.3) | the file; guard `small-spawns-no-process` |
| J8.S3.T3 | AC8.1 | `tests/hooks/test_pre_gate.py` (`test_non_object_envelope_fails_open`, `test_unreadable_stdin_fails_open` drive the hook entrypoint through `run_hook_subprocess`: they turn `medium`, AC8.3) | the file; guard `small-spawns-no-process` |
| J8.S3.T4 | AC8.1 | `tests/hooks/test_sdd_gate.py` (`test_gate_verdict`, `test_a_truncated_registry_is_no_context_at_the_gate` drive the hook entrypoint through `run_hook_subprocess`: they turn `medium`, AC8.3) | the file; guard `small-spawns-no-process` |
| J8.S3.T5 | AC8.1 | `tests/hooks/test_sdd_gate__classifier_symlink_canonicalization.py` (`test_a_symlink_into_protected_sessions_classifies_protected` drive the hook entrypoint through `run_hook_subprocess`: they turn `medium`, AC8.3) | the file; guard `small-spawns-no-process` |
| J8.S3.T6 | AC8.1 | `tests/hooks/test_sdd_post_gate.py` (the three `*_never_mutates_tasks_md*` tests drive the hook entrypoint through `run_hook_subprocess`: they turn `medium`, AC8.3) | the file; guard `small-spawns-no-process` |
| J8.S3.T9 | — | this file (it also added control shapes and two plants to the isolation check after hand mutants survived; J8.S4.T1 replaced that check) | close task, last: readout (share of small items under 100 ms) for `_RELEASE.json`; behavior map; `test-audit:`, `mutation:`; `done` |

- done: Job 8 — every task landed on `wt/0.5.0-rc10/job8`: J8.S1.T1 dd2a1d293; J8.S2.T1 9dd24140e, T2 0f9c7a128, T3 8e6c7209e, T4 812df47ed and 2aec51a27; J8.S3.T1 0b6cd9ecf, T2 87f5807a7, T3 ff45eb7a6, T4 84d4155bf, T5 82e5295bf, T6 bb7248291; closed by J8.S3.T9; review repair J8.S4.T1 c5978c967, T2 c050784f2, T3 0cd70c109, T4 8a2d36c85 (APPROVED on c5978c967). AC8.1 readout, gating nothing: 1,185 of 1,265 small items (93.3 %) run under 100 ms (setup + call + teardown, `-m "small and not slow and not quarantine"`, 85 items at or over).

## Stage J8.S4 — the review's two HIGH findings (CHANGES_REQUESTED on 1d1dfe3e1)

- Contract: exit tests unit + integration green, guard plant red; ACs AC8.1. One decider: `tests/conftest.py` sizes a test and, for a small test, refuses a process start at run time; the guard check plants a small test that spawns and expects the suite to fail it, so the AST spawn list and the restated seam list leave `scripts/guards/isolation.py`.
- Offenders: the reviewer's run-time spy at 1d1dfe3e1 (13 tests in 12 files); each turns `medium` (AC8.1).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J8.S4.T1 | AC8.1 | `tests/conftest.py` (a small test that starts a process fails), `scripts/guards/isolation.py` (`small-spawns-no-process` runs a planted small test through the suite; the AST list and `_PROCESS_MODULES` restatement leave) | guard plant |
| J8.S4.T2 | AC8.1 | `tests/cli/commands/test_context__cli_output_stability.py`, `test_doctor__cli_specs_doctor_fix.py`, `test_doctor__doctor_without_an_instance.py`, `test_init.py`, `test_specs__cli_specs_init_root_guard.py` | the files |
| J8.S4.T3 | AC8.1 | `tests/features/migrate/test_upgrade.py`, `test_upgrade__upgrade_fixed_sections.py`, `test_upgrade__upgrade_status_tokens.py`, `tests/features/specs/test_doctor_adr.py` | the files |
| J8.S4.T4 | AC8.1 | `tests/hooks/test_pre_gate.py` (`test_envelope_contract`, `test_non_write_and_protected_matrix`), `tests/hooks/test_venv_guard.py` | the files |
