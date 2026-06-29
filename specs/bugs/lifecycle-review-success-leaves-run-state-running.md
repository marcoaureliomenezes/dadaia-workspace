---
name: lifecycle-review-success-leaves-run-state-running
status: Open
severity: MEDIUM
reported: 2026-06-29
surface: lifecycle review security / LifecycleRunStore
session_id: codex-goal-v0.1.37-pi-smoke
---

# Successful lifecycle review leaves persisted run state as `running`

**Symptom:** A bounded real PI security-review workflow completed successfully and emitted
an APPROVED handoff, but the persisted lifecycle run record still showed
`status: running`.

**Repro:**

```bash
timeout 420 .dadaia/.venv/bin/dadaia lifecycle review security \
  --context dadaia-workspace \
  --release-id v0.1.37 \
  --run-id v0137-security-pi-smoke-2bdf57b7 \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

Command result:

```json
{"accepted": true, "blocked": null, "phase": "security_review", "runtime": "pi_headless", "status": "OK"}
```

The emitted handoff
`.dadaia/handoff/dadaia-workspace/2026-06-28T153000Z-security-reviewer-v0137-security-pi-smoke-2bdf57b7.handoff.json`
has `verdict: APPROVED` and `metrics.commit_sha:
2bdf57b773d25a0a94a725055e366028b854d0fe`.

Persisted state:

```json
{
  "run": {
    "run_id": "v0137-security-pi-smoke-2bdf57b7",
    "phase": "security_review",
    "status": "running",
    "blocked": null,
    "active_worker": null
  }
}
```

**Expected:** A successful lifecycle review command should persist a terminal successful
run state, not leave an apparently-running record.

**Actual:** The command returns OK but the state remains `running`, polluting
`dadaia lifecycle status` and making completed review runs look live.

**Root cause hypothesis:** The single-step review workflow returns a
`PhaseWorkflowResult` from the accepted transition, but the target phase remains the same
review phase and the persisted `LifecycleRunStatus` is not normalized to `COMPLETED` for
same-phase review commands.

**Impact:** Operators debugging PI workflow runs see stale running review records even
after successful completion. This weakens the status improvements in v0.1.37 and should be
fixed before declaring PI workflow execution smooth.
