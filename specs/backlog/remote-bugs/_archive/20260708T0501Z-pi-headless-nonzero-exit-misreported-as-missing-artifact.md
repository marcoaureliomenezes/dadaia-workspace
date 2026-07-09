# Pi headless non-zero exit is misreported as missing artifact evidence

- Severity: HIGH
- Surface: `dadaia lifecycle pipeline --harness pi`
- Component: `dadaia_workspace.infrastructure.pi_runtime`
- Context observed: `dd-chain-capture`
- Event stream mirror: `repos/dd-chain-capture/specs/bugs/20260708T05Z-00.jsonl`

## Symptom

When `pi` exits non-zero before producing a `message_end` event, lifecycle reports:

```text
agent result missing artifact evidence
```

instead of surfacing the real Pi setup failure.

## Repro

With `pi` installed but no provider API key configured:

```bash
PATH=/home/ubuntu/workspace/.dadaia/tools/pi/node_modules/.bin:$PATH \
  /home/ubuntu/workspace/.dadaia/.venv/bin/dadaia lifecycle pipeline \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --harness pi \
  --json
```

Direct Pi smoke command:

```bash
PATH=/home/ubuntu/workspace/.dadaia/tools/pi/node_modules/.bin:$PATH \
  pi --mode json --tools read --model gpt-5.3-codex -p 'Return exactly {"ok":true}'
```

The direct command exits `1` and reports:

```text
No API key found for azure-openai-responses.
```

The lifecycle command instead blocks as though the worker succeeded without artifact refs.

## Expected

`PiHeadlessAdapter` should return `AgentRunStatus.FAILED` whenever the subprocess return
code is non-zero, preserving the redacted stderr/stdout failure even if stdout contains
session/event text but no usable `message_end` payload.

## Impact

This masks the real setup problem and blocks `dd-chain-capture` v0.2.0 implementation
because the release requires real secondary Layer-2 Pi workflow execution.
