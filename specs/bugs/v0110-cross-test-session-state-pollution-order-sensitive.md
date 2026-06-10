---
name: v0110-cross-test-session-state-pollution-order-sensitive
status: Open
severity: LOW
reported: 2026-06-10
surface: tests/contract/cli/test_cli_context.py + tests/unit/hooks/test_sdd_post_gate.py (v0.1.10 in-progress working tree)
session_id: null
---

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
