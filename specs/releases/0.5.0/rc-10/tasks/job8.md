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
- Offender list: produced at the stage's open by the new guard's dry run; each offender is one task row (pure core extracted, or the test turns `medium`), disjoint `W:`.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J8.S3.T1 | AC8.1 | `scripts/guards/isolation.py` (check `small-spawns-no-process`: red on a planted subprocess in a small test) | guard plant |
| J8.S3.T2+ | AC8.1 | per offender | born from the list |
| J8.S3.T9 | — | this file | close task, last: readout (share of small items under 100 ms) for `_RELEASE.json`; behavior map; `test-audit:`, `mutation:`; `done` |
