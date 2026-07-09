# Context bind success is not reflected in context show JSON

- Bug ID: `context-bind-success-not-reflected-in-context-show`
- Severity: MEDIUM
- Context observed: `dd-chain-capture`
- Surface: `dadaia context bind` / `dadaia context show --json`
- Component: context/session observability
- Reported here: 2026-07-09T00:38Z

## Symptom

`dadaia context bind dd-chain-capture --mode implementation --release v0.2.0` prints a
successful bind with a new session id, but both generic and named context inspection still
show no active session.

Observed:

```text
✓ Bound to 'dd-chain-capture' (mode: implementation, session id: sess_e445b1eb)
```

Then:

```bash
<workspace>/.dadaia/.venv/bin/dadaia context show --json
```

returns the default `dadaia-workspace` context with:

```json
"session": null
```

And:

```bash
<workspace>/.dadaia/.venv/bin/dadaia context show dd-chain-capture --json
```

returns `dd-chain-capture` but still:

```json
"session": null
```

## Repro

```bash
<workspace>/.dadaia/.venv/bin/dadaia context bind dd-chain-capture \
  --mode implementation \
  --release v0.2.0

<workspace>/.dadaia/.venv/bin/dadaia context show --json
<workspace>/.dadaia/.venv/bin/dadaia context show dd-chain-capture --json
```

## Expected

After a successful bind, context inspection should expose the active/bound session, mode,
release, and context. Operators need this to verify that lifecycle workflow commands will
target the correct context before mutating a release.

## Impact on dd-chain-capture releases

The lifecycle commands default to `--context dadaia-workspace` unless `--context` is
passed explicitly. Because `context show` does not reflect the bind, an operator cannot
trust the usual context-inspection surface and must pass `--context dd-chain-capture`
manually on every workflow command.

## Notes

No repo bug was filed. This local report is intentionally kept under
`z_dadaia-workspace-BUGs` for export to the operator's local dadaia-workspace worktree.
