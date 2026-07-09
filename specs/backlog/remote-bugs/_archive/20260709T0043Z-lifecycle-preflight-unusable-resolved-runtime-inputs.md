# Lifecycle preflight blocks on unresolved runtime inputs with no CLI way to provide them

- Bug ID: `lifecycle-preflight-unusable-resolved-runtime-inputs`
- Severity: MEDIUM
- Context: `dd-chain-capture`
- Release: `v0.2.0`
- Component: `dadaia lifecycle preflight`
- Reported: 2026-07-09T00:43Z

## Symptom

`dadaia lifecycle preflight` cannot be run for the active `dd-chain-capture` release.
The command does not accept `--context` or `--release-id`, and even with
`DADAIA_CONTEXT=dd-chain-capture` it blocks on unresolved inputs.

Command:

```bash
DADAIA_CONTEXT=dd-chain-capture \
<workspace>/.dadaia/.venv/bin/dadaia lifecycle preflight --json
```

Observed:

```json
{
  "status": "BLOCKED",
  "message": "lifecycle preflight requires resolved runtime inputs",
  "blocked": {
    "blocked_at_step": "preflight",
    "reason": "lifecycle preflight requires resolved runtime inputs",
    "resume_token": "unresolved:preflight",
    "operator_command": null
  }
}
```

Help output exposes no option to provide the missing runtime inputs:

```text
Usage: dadaia lifecycle preflight [OPTIONS]
Options:
  --json
  --help
```

## Why this blocks dd-chain-capture

Preflight is a core diagnostic command for determining whether a release can proceed
through the lifecycle workflows. If it cannot resolve the active context/release and
does not tell the operator how to supply the missing inputs, it cannot be used to
validate readiness before progressing `v0.2.0`.

## Expected

Preflight should either:

- accept explicit `--context` and `--release-id`, like `pipeline` and
  `implement-review`; or
- resolve them reliably from the bound session; or
- emit the exact command/options needed to supply the missing inputs.

