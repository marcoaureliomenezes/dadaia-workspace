---
name: backlog-definition-pi-intake-grill-artifact-evidence-gate
status: Open
severity: MEDIUM
reported: 2026-06-27
session_id: sess_5aabaf1d
surface: dadaia lifecycle backlog define --harness pi
---

**Symptom:** Running the `backlog_definition` dadaia-workflow with the real Layer-2 PI
worker blocks at the first model step:

```bash
.dadaia/.venv/bin/dadaia lifecycle backlog define \
  --context dadaia-workspace \
  --release-id v0.1.33 \
  --run-id backlog-definition-workflow-dedup-conflict-control \
  --harness pi \
  --model gpt-5.5:high \
  --json
```

The workflow returns `BLOCKED` at `intake_grill` with reason
`agent result missing artifact evidence`.

**Expected:** `intake_grill` should be able to advance on a schema-valid structured
`backlog-demand-v1` result. That step does not write a SPEC/PLAN/TASKS/report file; it
produces proposed intents for the following Python `subject_bind` step.

**Observed evidence:** `.dadaia/states/lifecycle/backlog-definition-workflow-dedup-conflict-control.json`
records `runtime_kind: pi_headless`, `output_schema: backlog-demand-v1`, and
`gate_result: REJECTED` at `intake_grill`. The generic create-step gate in
`features/lifecycle/agent_runner.py` blocks all non-review model steps with empty
`artifact_refs`, but `backlog_definition.intake_grill` is a structured-data producer, not
an artifact-writing create step.

**Notes:** The first sandboxed run also failed before PI started because PI needed to
create lock files under `/home/marco/.pi/agent`; rerunning with approved escalation allowed
PI to run and exposed the real workflow gate block above. No secrets included.
