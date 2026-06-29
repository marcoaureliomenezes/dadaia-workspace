---
name: pi-handoff-recovery-skips-valid-handoff-when-final-message-has-verdict-but-no-artifact_refs
status: Closed
severity: "MEDIUM"
surface: lifecycle bug report workflow
resolved: 2026-06-29
release: v0.1.37
session_id: null
---

# PI handoff recovery skips valid handoff when final message has verdict but no artifact_refs

**Symptom:** PI handoff recovery skips valid handoff when final message has verdict but no artifact_refs

## Repro

Run dadaia lifecycle review security with PI where the worker writes an APPROVED handoff but the final message exposes verdict without artifact_refs; inspect run v0137-security-pi-final-e7ffd4c1

## Expected

PI adapter recovers the written matching handoff whenever artifact_refs are missing, even if verdict is already present

## Actual

Run blocked with agent result missing artifact evidence although .dadaia/handoff/dadaia-workspace/2026-06-28T173000Z-security-reviewer-v0137-security-pi-final-e7ffd4c1.handoff.json was APPROVED and had the full commit SHA

## Root Cause

`PiHeadlessAdapter._with_written_handoff_result` skipped disk handoff recovery whenever the
parsed final message already contained a verdict, even if `artifact_refs` were empty. A PI worker
can emit a verdict in the final message while relying on the written handoff for artifact evidence.

## Fix

The adapter now skips recovery only when both required pieces are already present: non-empty
`artifact_refs` and a verdict. If either piece is missing, it looks for the newest matching
handoff written during the run and recovers artifact refs plus verdict metadata from it.

## Validation

- `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py -q` -> `15 passed`
- `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/dadaia_workspace/infrastructure/pi_runtime.py repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py` -> `All checks passed!`
- `.dadaia/.venv/bin/python -m mypy --strict repos/dadaia-workspace/dadaia_workspace/infrastructure/pi_runtime.py` -> `Success`
