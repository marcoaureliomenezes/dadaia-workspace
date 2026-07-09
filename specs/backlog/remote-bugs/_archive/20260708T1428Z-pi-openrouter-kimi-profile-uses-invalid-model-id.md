# pi-openrouter-kimi-high profile uses invalid OpenRouter model id

- Bug ID: `pi-openrouter-kimi-profile-uses-invalid-model-id`
- Severity: HIGH
- Context: `dd-chain-capture`
- Surface: `dadaia lifecycle pipeline --step-model implement=pi-openrouter-kimi-high`
- Component: `dadaia_workspace` workflow model profiles / Pi OpenRouter model mapping
- Reported: 2026-07-08T14:28Z

## Symptom

The built-in profile `pi-openrouter-kimi-high` resolves to model `kimi-2.7`.
Direct Pi/OpenRouter execution with that model ID fails because OpenRouter does not
recognize it as a valid model ID.

## Reproduction

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle workflow profiles list --json

PATH=<workspace>/.dadaia/tools/pi/node_modules/.bin:$PATH \
pi --provider openrouter --model kimi-2.7 --mode json --tools read -p smoke
```

The first command shows:

```json
{
  "id": "pi-openrouter-kimi-high",
  "harness": "pi",
  "model_id": "kimi-2.7"
}
```

The second command is rejected by OpenRouter unless a local Pi model alias is manually
configured.

## Expected

The governed profile should resolve to a Pi/OpenRouter-valid model ID, or the lifecycle
profile layer should install/declare the alias it depends on. A clean OpenRouter key
configuration should not require hidden per-user alias state.

## Workaround Used

A local Pi alias was added outside the workspace:

```text
name: kimi-2.7
id: moonshotai/kimi-k2.5
provider: openrouter
```

No API key values are included here.

## Valid Model IDs Observed

`pi --list-models kimi --provider openrouter` lists valid OpenRouter Kimi IDs including:

- `moonshotai/kimi-k2`
- `moonshotai/kimi-k2-0905`
- `moonshotai/kimi-k2-thinking`
- `moonshotai/kimi-k2.5`
- `moonshotai/kimi-k2.6`
