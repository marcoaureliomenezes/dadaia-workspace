---
name: release-define-pi-worker-long-running-no-progress-heartbeat
status: Closed
severity: HIGH
reported: 2026-06-28
surface: lifecycle release_definition PI worker orchestration
session_id: codex-2026-06-28-v0136
---

# `release define` PI worker can run opaquely for minutes with no lifecycle progress heartbeat

**Symptom:** After v0.1.36 PI model-routing fixes, scratch live workflow validations stayed
running for minutes while the persisted lifecycle run remained unchanged at
`release_scope`. The CLI emits no progress until the worker returns, so an operator cannot
distinguish a slow live worker from a deadlock from the lifecycle state alone.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.36-pi-smoke \
  --run-id v0136-pi-smoke-1 \
  --intent "Smoke-test PI Layer-2 release-definition after provider-qualified model routing and canonical artifact prompt fixes." \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

**Observed in the first run:**

- No stdout/stderr was emitted for more than 2 minutes.
- `ps` showed the lifecycle Python process sleeping in `poll_schedule_timeout`.
- `.dadaia/states/lifecycle/v0136-pi-smoke-1.json` remained:

```json
{
  "current_step": "release_scope",
  "phase": "release_definition",
  "status": "running",
  "blocked": null,
  "injected_context": [],
  "workflow_steps": []
}
```

The process was manually terminated with SIGTERM to avoid leaving a stuck worker. No scratch
release artifacts or handoffs were written.

**Strace correction:** A bounded `strace` repro (`v0136-pi-smoke-2`) showed that PI *did*
spawn and stream JSON events. The original "before worker spawn" hypothesis was wrong.
The parent process stays inside `subprocess.run(..., capture_output=True)` until PI exits,
while the lifecycle run record stays at `release_scope` with no injected context, heartbeat,
child pid, stdout tail, or "worker active" marker. The live PI worker also continued into
tool execution before the external timeout killed it.

**Second bounded repro:** A mixed-harness run intended to bound the workflow to one live PI
step also required manual termination:

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.36-pi-scope-smoke \
  --run-id v0136-pi-scope-smoke-1 \
  --intent "Smoke-test PI release_scope as a Layer-2 workflow step after v0.1.36 fixes; later steps are fake to bound runtime." \
  --harness fake \
  --step-harness release_scope=pi \
  --step-model release_scope=gpt-5.3-codex-spark:medium \
  --json
```

After roughly two minutes, the run state still showed `release_scope` / `running` with no
progress metadata.

**Expected:** While a live worker is running, the lifecycle state should expose a heartbeat
or active-worker marker (runtime, child pid when known, started_at, last stdout/stderr event
summary or byte counters). If the worker exceeds a bounded operator-visible threshold, the
CLI should provide actionable progress or a typed timeout/block, not a silent wait with
unchanged state.

**Known-good adjacent evidence:** A direct PI command using the same provider-qualified
model succeeds:

```bash
pi --mode json --model openai-codex/gpt-5.3-codex-spark --thinking low \
  --no-tools --no-session --no-context-files -p "Reply with exactly: OK"
```

PI returned `provider=openai-codex`, `model=gpt-5.3-codex-spark`, and final text `OK`.

**Acceptance:** Add instrumentation around live worker execution so `LifecycleRun` records
an active worker heartbeat before entering `runtime.run()`, and clears or completes it
after the worker returns. Add regression coverage that a long-running injected runtime
updates visible run state before blocking. Consider streaming PI stdout progress or adding
a shorter workflow-level watchdog distinct from the adapter's 900-second subprocess
timeout.

## Resolution — v0.1.36 alpha-1

`ReleaseDefinitionWorkflow._run_model_step()` now persists the run immediately after
`record_injected_context()` and before entering `runtime.run()`. This means a long-running
PI/Codex worker no longer leaves the run state with an empty `injected_context`; the
operator can at least see the selected context/prompt audit for the active step while the
worker is still running.

The lifecycle run model also now carries an additive `active_worker` marker with the active
step, runtime kind, start timestamp, and heartbeat timestamp. Release-definition sets this
marker immediately before entering the blocking worker call and clears it immediately after
the worker returns. That fixes the reported opaque state: a live PI worker no longer looks
like a stale unchanged run record.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py::test_release_definition_persists_injected_context_before_worker_returns
```

Future improvement: stream PI stdout progress or periodically refresh `active_worker` while
the subprocess is running. That is a richer progress UX, not required to close this bug's
opaque-state failure.

**Live validation:** A bounded scratch run with real PI on `release_scope` and fake for the
remaining steps showed the fixed state while PI was running:

```bash
timeout 60s .dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.36-pi-active-worker-smoke \
  --run-id v0136-pi-active-worker-smoke \
  --intent "Bounded smoke to verify active_worker marker while real PI release_scope runs." \
  --harness fake \
  --step-harness release_scope=pi \
  --step-model release_scope=gpt-5.3-codex-spark:medium \
  --json
```

During the run, `.dadaia/states/lifecycle/v0136-pi-active-worker-smoke.json` contained:
`current_step=release_scope`, `status=running`, `active_worker.step=release_scope`,
`active_worker.runtime_kind=pi_headless`, populated timestamps, and non-empty
`injected_context`. The command was intentionally bounded and exited via `timeout` after
the evidence was captured.

**Notes:** Registered via direct-Markdown fallback because
`bug-report-fake-bug-write-emits-stub-and-discards-fields` is currently open. No secrets or
operator-local auth material included.
