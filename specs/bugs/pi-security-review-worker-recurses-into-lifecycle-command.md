---
name: pi-security-review-worker-recurses-into-lifecycle-command
status: Open
severity: HIGH
reported: 2026-06-29
surface: lifecycle review security / PI_HEADLESS worker prompt-tool behavior
session_id: codex-goal-v0.1.36-push
---

# PI security-review worker recursively invokes `dadaia lifecycle review security`

**Symptom:** Attempting to produce the pre-push `security-reviewer` handoff with the real
PI Layer-2 worker did not return a handoff. Instead, the PI process spawned another
`dadaia lifecycle review security --harness pi --json` process from inside the worker run.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle review security \
  --context dadaia-workspace \
  --release-id v0.1.36 \
  --run-id v0136-security-pi-1563a27e \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

Observed process tree before interrupting the run:

```text
dadaia,2969043 .dadaia/.venv/bin/dadaia lifecycle review security ...
  |-pi,2969091
  |   |-dadaia,2972814 .dadaia/.venv/bin/dadaia lifecycle review security ...
```

The run state existed at `.dadaia/states/lifecycle/v0136-security-pi-1563a27e.json`, but
while the parent command was still alive it showed `active_worker: null` and `status:
running`. The command was interrupted with Ctrl-C to avoid an uncontrolled recursive
worker chain.

**Expected:** A PI worker running a lifecycle review step should inspect the scoped prompt
and emit one `agent-run-result-v1` object with an APPROVED/REJECTED verdict and artifact
evidence. It must not launch the same `dadaia lifecycle` command recursively.

**Actual:** The worker used its available bash/tool surface to start another lifecycle
review command, creating recursive orchestration instead of returning the result object to
the parent workflow.

**Root cause hypothesis:** The review prompt and/or PI tool allowance is too permissive for
workflow-review steps. PI sees a command-shaped task and can use `bash` to run the CLI
instead of acting as the bounded worker behind `AgentRuntimePort`. This is especially risky
for lifecycle verbs because recursion can spend credits, leave stale `running` lifecycle
state, and never produce the pre-push security handoff.

**Impact:** PI cannot yet be trusted as a seamless Layer-2 worker for `dadaia lifecycle
review security`. This blocks the goal of using PI reliably across dadaia-workflows and
should be picked into the next PI workflow-hardening release.

**Fix direction:**

- Make review-step prompts explicitly forbid invoking `dadaia lifecycle ...` from inside
  the worker and require direct emission of the result object.
- Consider restricting PI review-step tools to exclude `bash` unless a step's write scope
  truly requires shell execution.
- Add a deterministic PI-headless test with a fake runner that attempts a nested lifecycle
  command and assert the workflow blocks or the adapter/tool policy prevents it.
- Ensure interrupted lifecycle review runs either clear `active_worker`/status or become
  visible as blocked/stale for cleanup.

**Bug-report workflow note:** Direct Markdown fallback used because
`bug-report-fake-bug-write-emits-stub-and-discards-fields` is still open.
