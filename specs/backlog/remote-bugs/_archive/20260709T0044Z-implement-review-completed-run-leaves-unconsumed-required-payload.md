# Implement-review completed run leaves required payload unconsumed

- Bug ID: `implement-review-completed-run-leaves-unconsumed-required-payload`
- Severity: HIGH
- Context: `dd-chain-capture`
- Release: `v0.2.0`
- Component: `dadaia lifecycle implement-review` / `dadaia lifecycle handoffs doctor`
- Reported: 2026-07-09T00:44Z

## Symptom

A deterministic fake `implement-review` run completed successfully, but the workflow-step
handoff doctor then blocked on a required payload from that same terminal run.

Command:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle implement-review \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --run-id zbug-fake-implement-review \
  --harness fake \
  --json
```

Observed result:

```json
{
  "attempts": 1,
  "completed": true,
  "final_verdict": "APPROVED"
}
```

Then:

```bash
DADAIA_CONTEXT=dd-chain-capture \
<workspace>/.dadaia/.venv/bin/dadaia lifecycle handoffs doctor --json
```

Observed:

```json
{
  "ok": false,
  "status": "blocked",
  "findings": [
    {
      "kind": "unconsumed_required",
      "message": "terminal run zbug-fake-implement-review: required payload review_qa#0 is produced, not consumed_all",
      "ref": ".dadaia/runs/lifecycle/zbug-fake-implement-review/steps/review_qa-attempt-0.step-payload.json"
    }
  ]
}
```

The run state itself records `status: completed`, but the `review_qa` payload has:

```json
{
  "producer_step": "review_qa",
  "declared_consumers": ["implement"],
  "retention_mode": "promote_to_evidence",
  "consumptions": []
}
```

## Why this blocks dd-chain-capture

This makes `handoffs doctor` fail after a successful terminal workflow. A release flow
that uses `implement-review` can leave lifecycle state that its own doctor considers
invalid, blocking diagnosis and possibly later workflow gates.

## Expected

For a terminal successful `implement-review` run, the final approved review payload
should either be marked consumed/promoted correctly or should not declare a required
consumer that can never run after terminal completion.

