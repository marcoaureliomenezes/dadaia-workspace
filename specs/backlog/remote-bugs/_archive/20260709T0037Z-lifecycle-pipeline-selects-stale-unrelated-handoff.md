# Lifecycle pipeline selects stale unrelated handoff as current implement evidence

- Bug ID: `lifecycle-pipeline-selects-stale-unrelated-handoff`
- Severity: HIGH
- Context observed: `dd-chain-capture`
- Surface: `dadaia lifecycle pipeline`
- Component: lifecycle handoff/evidence selection
- Reported here: 2026-07-09T00:37Z

## Symptom

A fresh lifecycle pipeline run for `dd-chain-capture` `v0.2.0` blocks at the
`implement` step with:

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "implement",
    "reason": "agent result missing artifact evidence",
    "detail": {
      "validated_handoff_path": ".dadaia/handoff/dd-chain-capture/2026-07-08T235900Z-software-engineer-t24-services-audit.handoff.json"
    }
  }
}
```

The referenced handoff is an old `T-2.4` services-audit handoff. It is unrelated to the
current `T-3.1` workflow run.

## Repro

From the workspace root:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle pipeline \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --run-id v020-t31-workflow \
  --harness codex \
  --write-scope docker/hermes-capture/workspace/scripts/telegram_listener.py \
  --write-scope docker/hermes-capture/scrapers/tests/test_telegram_listener.py \
  --write-scope docker/hermes-capture/supervisord.conf \
  --json
```

The same issue reproduces with the fake harness:

```bash
<workspace>/.dadaia/.venv/bin/dadaia lifecycle pipeline \
  --context dd-chain-capture \
  --release-id v0.2.0 \
  --run-id zbug-fake-pipeline-smoke \
  --harness fake \
  --write-scope docker/hermes-capture/workspace/scripts/telegram_listener.py \
  --json
```

## Expected

The workflow must validate evidence produced by the current run and current step, or fail
with a clear "no current implement artifact" error. It must never select an unrelated
older handoff from a previous task as the implement-step evidence.

## Impact on dd-chain-capture releases

This blocks use of `dadaia lifecycle pipeline` for progressing `dd-chain-capture`
releases. Since both `codex` and `fake` harnesses hit the same stale-handoff path, this is
a core lifecycle evidence-selection problem, not a model/harness problem.

## Notes

No repo bug was filed. This local report is intentionally kept under
`z_dadaia-workspace-BUGs` for export to the operator's local dadaia-workspace worktree.
