# Lifecycle diagnostic commands reject explicit context/release options

- Bug ID: `lifecycle-diagnostic-commands-missing-context-options`
- Severity: HIGH
- Context: `dd-chain-capture`
- Release: `v0.2.0`
- Component: `dadaia lifecycle` CLI option surface
- Reported: 2026-07-09T00:42Z

## Symptom

Some lifecycle commands needed to operate and diagnose a release do not accept the same
explicit context contract as `pipeline` and `implement-review`.

These commands rejected `--context dd-chain-capture --release-id v0.2.0`:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle preflight \
  --context dd-chain-capture --release-id v0.2.0 --json

<workspace>/.dadaia/.venv/bin/dadaia lifecycle status \
  --context dd-chain-capture --release-id v0.2.0 --json

<workspace>/.dadaia/.venv/bin/dadaia lifecycle handoffs doctor \
  --context dd-chain-capture --release-id v0.2.0 --json
```

Observed for each:

```text
No such option: --context
```

`dadaia specs doctor --context dd-chain-capture --json` also rejects `--context`; it only
offers `--specs-dir`.

## Why this blocks dd-chain-capture

The `dd-chain-capture` release tasks require every workflow command to be explicit:

```text
dadaia lifecycle ... --context dd-chain-capture --release-id v0.2.0
```

That is necessary because `dadaia context show --json` currently resolves the wrong
default context (`dadaia-workspace`) in this workspace. Commands without explicit context
are therefore unsafe for this release.

## Expected

All lifecycle release-facing commands should accept a consistent context/release option
surface, or the CLI should provide an equivalent explicit selector. Diagnostic commands
must not require implicit session binding when explicit release operation is the release
law.

