---
name: v0110-cross-test-session-state-pollution-order-sensitive
status: Closed
severity: LOW
reported: 2026-06-10
resolved_in: v0.1.10
surface: tests/contract/cli/test_cli_context.py + tests/unit/hooks/test_sdd_post_gate.py (v0.1.10 in-progress working tree)
session_id: null
---

**Resolution (v0.1.10) — verified NOT REPRODUCIBLE on the integrated tree:**
This was a transient symptom of the in-flight working tree (T-010-04/05/08 still
`[-]` and partially integrated). On the current integrated v0.1.10 tree the
exact failing-case repro now passes with zero failures, confirming the
order-sensitivity is gone — the shared `.dadaia/states/` session/lease state is
properly isolated per-test (harness-env fixture T-010-10 / R5 fixture matrix
T-010-11 / session-identity consolidation T-010-07). Verification commands run
2026-06-10:

```bash
# bug's failing-case repro — now PASSES:
pytest -p no:cacheprovider -q --ignore=tests/unit/public/test_pre_push_gate_venv_probe.py
#   => 2772 passed, 8 skipped, 1 xpassed, 0 failed

# the two named victim files WITH the doctor file collected first — PASSES:
pytest -p no:cacheprovider -q tests/unit/features/public/test_model_registry_doctor.py \
  tests/contract/cli/test_cli_context.py tests/unit/hooks/test_sdd_post_gate.py
#   => 51 passed, 0 failed

# full suite — PASSES:
pytest -p no:cacheprovider -q
#   => 2779 passed, 8 skipped, 1 xpassed, 0 failed
```

The separate `test_pre_push_gate_venv_probe.py` collection-time blocker noted
below was also resolved by T-010-26 (the full suite now includes that file and
is green). No regression test is owned by this bug — its acceptance is the full
suite being order-independent, proven above. File retained (not deleted) per
release-governance.


**Symptom:** In the v0.1.10 feature branch working tree (with T-010-04 /
T-010-05 / T-010-08 changes uncommitted and still `[-]`), the full suite is
**collection-order sensitive**: 14 tests in `tests/contract/cli/test_cli_context.py`
and `tests/unit/hooks/test_sdd_post_gate.py` FAIL under one collection order but
PASS in isolation.

```
# Full suite WITH tests/unit/features/public/test_model_registry_doctor.py collected:
14 failed, 2649 passed   (the 14 are all in test_cli_context.py + test_sdd_post_gate.py)

# Same production tree, that one new test file DESELECTED:
2658 passed, 0 failed

# The 14 "failing" suites run in isolation (alone, or even with the new file first):
45–51 passed, 0 failed
```

**Repro:**

```bash
# fails:
pytest -p no:cacheprovider -q --ignore=tests/unit/public/test_pre_push_gate_venv_probe.py
# passes (same code, my test file out):
pytest -p no:cacheprovider -q --ignore=tests/unit/public/test_pre_push_gate_venv_probe.py \
  --deselect tests/unit/features/public/test_model_registry_doctor.py
# passes (victims in isolation):
pytest -p no:cacheprovider -q tests/contract/cli/test_cli_context.py tests/unit/hooks/test_sdd_post_gate.py
```

**Expected:** Test outcomes are independent of collection order. A suite that
passes in isolation must not fail when a state-neutral test module (only
`tmp_path` + `monkeypatch`, no `.dadaia/states` writes — verified to leave no
global residue) is added to the collection.

**Root cause (hypothesis):** The order-sensitivity points to shared mutable
session/lease state under `.dadaia/states/` (sessions runtime ptr / lease record
/ context bind record) that the T-010-04/05/08 tests read or write without full
per-test isolation; collection order changes which test seeds that state first.
This is **not** caused by T-010-24 (model-resolution doctor) — that task only
adds a pure read-only check; its test merely shifts ordering and exposes the
latent pollution. Owner of the real fix: the Track-K/R4 tasks' test isolation
(harness-env fixture T-010-10 / R5 fixture matrix T-010-11), or a conftest
session-state reset.

**Notes:** Filed by software-engineer during T-010-24. Discovered while running
the mandated full suite. Separate pre-existing collection-time blocker in
`tests/unit/public/test_pre_push_gate_venv_probe.py` (module-level
`assert shutil.which("poetry") is None`) trips whenever `poetry` is installed in
the active venv — that is a T-010-26 test-environment assumption, also not in
scope here.
