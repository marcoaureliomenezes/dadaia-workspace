# TASKS — 0.5.0 rc-10, Job 5 — HOOKS-DRIFT-1 states what it observed

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

## Stage J5.S1 — RED

- Contract: exit tests the AC5.1 rows RED as strict xfail; envelope `tests/unit/features/spec_context/test_hooks_drift.py`, `tests/integration/test_workspace_fix_lines_clear_their_finding.py`; ACs AC5.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J5.S1.T1 | AC5.1 | `tests/unit/features/spec_context/test_hooks_drift.py` | RED: an absent hook reads "absent", an edited one "differs"; one code, one fix line |
| J5.S1.T2 | AC5.1 | `tests/integration/test_workspace_fix_lines_clear_their_finding.py` | RED: a deleted projected hook; its fix line, run, restores it and clears the finding |

## Stage J5.S2 — the message

- Contract: exit tests J5.S1's rows green, unit + integration green; envelope `f/spec_context/doctor.py`, this file; ACs AC5.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J5.S2.T1 | AC5.1 | `f/spec_context/doctor.py` (`check_installed_hooks`: the observed state, absent or differing; the `OSError` arm stops reading as "differs") | `test_hooks_drift.py`, `test_workspace_fix_lines_clear_their_finding.py` |
| J5.S2.T2 | — | this file | close task, last: behavior map; `test-audit:`, `mutation:`; `done` |
