---
name: live-pi-review-e2e-fixture-stale-cli-architecture
status: Closed
severity: MEDIUM
reported: 2026-06-28
surface: tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py
session_id: sess_8cdf6cce
---

# Live PI review e2e fixture was stale and got correctly rejected by the real reviewer

**Symptom:** After the canonical-hash authority fix, the real PI review-path e2e reached
`spec_arch_review` but the reviewer returned `REJECTED`.

Observed reason:

```text
agent result verdict REJECTED (expected APPROVED)
verdict_reason: the SPEC makes an unfounded root-callback claim and a test-placement
requirement that violates the repository's test architecture.
```

**Root cause:** The synthetic review fixture proposed adding `dadaia --version` but
claimed the root app lived in `dadaia_workspace/cli/app.py` and assumed an existing root
callback. The current code defines the root Typer app in `dadaia_workspace/cli/main.py`
and has no root callback. The fixture also prescribed a too-specific unit-test placement
instead of asking for a CLI-level test consistent with existing test layout.

**Expected:** The opt-in live PI e2e fixture should be reviewable and architecturally
true. The test is supposed to validate the PI Layer-2 review gate, not rely on a reviewer
approving stale or false architecture claims.

## Resolution — v0.1.36 alpha-1

Updated the live e2e fixture SPEC and architecture context to name
`dadaia_workspace/cli/main.py`, to allow introducing a root callback if absent, and to
ask for CLI-level tests without dictating an invalid location.

Validation:

```bash
DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" timeout 900 \
  .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q -s \
  repos/dadaia-workspace/tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py::test_real_pi_worker_review_step_emits_approved_and_gate_passes
```

Evidence: `1 passed in 340.50s`; the run printed
`spec_arch_review accepted with gate verdict 'APPROVED'`.
