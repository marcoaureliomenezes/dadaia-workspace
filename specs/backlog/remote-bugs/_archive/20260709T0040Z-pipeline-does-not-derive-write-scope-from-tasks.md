# Lifecycle pipeline does not derive implementation write scope from TASKS.md

- Bug ID: `pipeline-does-not-derive-write-scope-from-tasks`
- Severity: HIGH
- Context observed: `dd-chain-capture`
- Surface: `dadaia lifecycle pipeline`
- Component: lifecycle write-scope assembly
- Reported here: 2026-07-09T00:40Z

## Symptom

The implementation pipeline does not automatically read the active task's declared
`Write set:` from `specs/releases/<release>/TASKS.md`. Instead, callers must manually pass
one or more `--write-scope` flags.

Current CLI help says:

```text
--write-scope TEXT
  Extra write-scope path glob for the implement step ONLY ...
  A full TASKS.md write-set parser is out of scope — supply the paths explicitly per invocation.
```

Current source confirms this is additive-only behavior:

```text
extra_allowed_paths: tuple[str, ...] = ()
```

and the CLI threads only the `--write-scope` values into non-review steps.

## Repro

Inspect the workflow CLI:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle pipeline --help
```

Then run a pipeline without manually duplicating the current task's write set:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle pipeline \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --run-id <fresh-run> \
  --harness codex \
  --json
```

The implement worker receives handoff output scope plus any manually passed extra scopes,
not the active task's declared write set from `TASKS.md`.

## Expected

For release implementation workflows, the lifecycle engine should resolve the active
`[-]` task from `TASKS.md`, parse its `Write set:`, and pass those paths to the implement
worker automatically. Manual `--write-scope` may remain as an escape hatch, but it should
not be required for the normal release pipeline.

## Impact on dd-chain-capture releases

This makes workflow-only progress brittle. The whole point of the SDD task file is to
declare the legal implementation surface once. If the workflow ignores it, every pipeline
invocation can accidentally under-scope the implementer, produce no-op implementation
handoffs, or push scope errors into QA.

## Current workaround

Every pipeline command must manually repeat the T-3.1 write set, for example:

```bash
--write-scope docker/hermes-capture/workspace/scripts/telegram_listener.py
--write-scope docker/hermes-capture/scrapers/tests/test_telegram_listener.py
--write-scope docker/hermes-capture/supervisord.conf
```

This workaround is not acceptable as the primary release strategy because it duplicates
the task contract by hand.
