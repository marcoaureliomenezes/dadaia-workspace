---
name: pi-headless-masks-nonzero-auth-failure-as-missing-artifact
status: Closed
severity: HIGH
reported: 2026-06-27
surface: lifecycle PI Layer-2 runtime adapter / release-definition workflow
session_id: sess_43ddcbfb
---

**Symptom:** Running a release-definition workflow with PI Layer-2 and an explicit
model failed as a workflow gate error (`agent result missing artifact evidence`) instead
of surfacing the actual PI CLI failure.

**Observed command:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dd-chain-capture \
  --release-id v0.1.2 \
  --run-id pi-dd-chain-capture-v0.1.2-define \
  --harness pi \
  --model gpt-5.3-codex:medium \
  --json
```

**Observed workflow result:**

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "release_scope",
    "reason": "agent result missing artifact evidence"
  },
  "steps": [
    {"label": "release_scope", "runtime": "pi_headless", "accepted": false}
  ]
}
```

**Inspection:** A direct PI CLI reproduction with the same explicit model exits non-zero
and prints a provider/login error on stderr while still emitting a `session` event on
stdout:

```bash
printf '%s' 'Return JSON.' | pi --mode json --tools read -p --model gpt-5.3-codex
# exit code: 1
# stdout: {"type":"session", ...}
# stderr: No API key found for azure-openai-responses. Use /login ...
```

`dadaia_workspace/infrastructure/pi_runtime.py` calls `_result_from_output(stdout,
returncode)`. In the `message is None` fallback, non-empty stdout is treated as a
successful `AgentRunResult` even when `returncode != 0`, so the lifecycle gate later
blocks on missing artifact evidence and hides the real provider/auth failure.

**Expected:** If PI exits non-zero and no `message_end` is available, the adapter should
return `FAILED` and surface redacted stderr/stdout as the error. The workflow should
block with an actionable PI runtime failure, not a misleading artifact-evidence gate.

**Impact:** Operators testing PI as Layer-2 cannot distinguish harness/model auth
failures from worker non-compliance. This wastes debugging time and obscures the real
configuration problem.

**Acceptance:** Add a unit test for non-zero PI return code + stdout session event +
stderr error + no `message_end`; assert `AgentRunStatus.FAILED` with a redacted error
containing the PI failure message.

## Resolution

Fixed in `v0.1.35`.

`PiHeadlessAdapter` now treats a non-zero `pi --mode json` exit with no terminal
`message_end` as a runtime failure even when PI emitted partial session JSON on stdout.
The adapter surfaces redacted stderr/stdout as the error, so workflow users see the real
provider/auth/configuration failure instead of a later generic artifact-evidence block.

Evidence:

- `dadaia_workspace/infrastructure/pi_runtime.py#PiHeadlessAdapter._result_from_output`
- `tests/contract/test_headless_runtime_security.py::test_pi_nonzero_without_message_end_surfaces_runtime_failure`
- Focused validation: `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py` -> `10 passed`
