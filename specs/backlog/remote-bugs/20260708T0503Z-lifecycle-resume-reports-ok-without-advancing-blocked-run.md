# lifecycle resume reports OK without advancing blocked run

- Severity: MEDIUM
- Surface: `dadaia lifecycle resume`
- Component: `dadaia_workspace.cli.commands.lifecycle resume`
- Context observed: `dd-chain-capture`
- Event stream mirror: `repos/dd-chain-capture/specs/bugs/20260708T05Z-00.jsonl`

## Symptom

`dadaia lifecycle resume pipeline` printed:

```text
OK resumed pipeline
```

but `.dadaia/states/lifecycle/pipeline.json` remained blocked at the same step:

```text
blocked_at_step: implement
reason: agent result missing artifact evidence
```

No workflow step advanced and no new handoff was produced.

## Repro

After a pipeline is blocked at `implement`, run:

```bash
PATH=/home/ubuntu/workspace/.dadaia/tools/pi/node_modules/.bin:$PATH \
  /home/ubuntu/workspace/.dadaia/.venv/bin/dadaia lifecycle resume pipeline
```

The command exits `0` and prints success, but the state file remains unchanged.

## Expected

Resume should either:

- re-run and advance the resumable step, or
- exit non-zero with a clear reason that the run cannot advance without operator setup.

## Impact

This makes automation unreliable because success output does not prove progress. In this
case the underlying release blocker remains missing Pi provider credentials.
