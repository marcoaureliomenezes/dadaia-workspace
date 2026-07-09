# Lifecycle Pi pipeline rejects valid handoff as missing artifact evidence

- Bug ID: `lifecycle-pi-valid-handoff-rejected-as-missing-artifact`
- Severity: HIGH
- Context: `dd-chain-capture`
- Surface: `dadaia lifecycle pipeline --harness pi --step-model implement=pi-openrouter-kimi-high`
- Component: `dadaia_workspace.features.lifecycle` / `dadaia_workspace.infrastructure.pi_runtime`
- Reported: 2026-07-08T14:25:59Z

## Symptom

The Pi worker implemented `v0.2.0` task `T-1.1`, changed
`docker/hermes-capture/Dockerfile`, reserved `T-1.1` in `TASKS.md`, wrote a handoff, and
validated it successfully:

```text
.dadaia/handoff/dd-chain-capture/2026-07-08T00-software-engineer-t11.handoff.json
VALID
```

The lifecycle pipeline still exited `rc=3` and recorded:

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "implement",
    "reason": "agent result missing artifact evidence",
    "detail": {}
  }
}
```

## Reproduction

Run the `v0.2.0` pipeline with Pi and the OpenRouter Kimi profile after Pi auth/model
aliasing is configured:

```bash
PATH=<workspace>/.dadaia/tools/pi/node_modules/.bin:$PATH \
<workspace>/.dadaia/.venv/bin/dadaia lifecycle pipeline \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --harness pi \
  --step-model implement=pi-openrouter-kimi-high \
  --step-model review_qa=pi-openrouter-kimi-high \
  --step-model review_security=pi-openrouter-kimi-high \
  --step-model review_code=pi-openrouter-kimi-high \
  --json
```

Evidence:

- Pipeline capture: `.dadaia/tmp/codex/20260708/v020-pipeline.jsonl`
- State file: `.dadaia/states/lifecycle/pipeline.json`
- Valid handoff: `.dadaia/handoff/dd-chain-capture/2026-07-08T00-software-engineer-t11.handoff.json`
- Pi session: `<home>/.pi/agent/sessions/--home-ubuntu-workspace--/2026-07-08T14-21-47-410Z_019f421b-3612-71b8-9f94-de03ff885e29.jsonl`

## Expected

Lifecycle should accept a valid worker handoff/artifact, or fail with a precise result
schema validation error that identifies the missing or invalid field and preserves the
handoff path.

## Notes

The handoff itself is valid `handoff-v1.1`. The final worker message emitted a fenced
`agent-run-result-v1` JSON object using `schema` rather than `schema_version`, which may
be the adapter extraction mismatch. No secrets were captured in this report.
