---
name: release-definition-spec-create-overinjects-context-exceeds-codex-input-limit
status: Closed
severity: HIGH
reported: 2026-06-29
resolved: 2026-06-29
release: v0.1.37
surface: lifecycle release define / spec_create / CodexExecAdapter context injection
session_id: codex-goal-v0.1.36-push
---

# Release-definition `spec_create` over-injects context and exceeds Codex input limit

**Symptom:** Defining the next PI workflow-hardening release blocked at `spec_create`
before creating `specs/releases/v0.1.37/SPEC.md`.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.37 \
  --run-id v0137-pi-workflow-hardening-define \
  --intent "Make PI a reliable Layer-2 worker for dadaia-workflows. Focus on preventing PI workers from recursively invoking dadaia lifecycle commands, making workflow bug registration trustworthy, and fixing lifecycle status inspection so operators can safely run and debug PI-driven workflows." \
  --backlog pi-agent-fourth-harness \
  --bug pi-security-review-worker-recurses-into-lifecycle-command \
  --bug bug-report-fake-bug-write-emits-stub-and-discards-fields \
  --bug lifecycle-status-no-args-hangs-100pct-cpu \
  --harness codex \
  --model gpt-5.5:medium \
  --json
```

**Expected:** The release-definition workflow should pass a bounded, step-relevant prompt
to `codex exec`, create the requested SPEC artifact, and continue to PLAN/TASKS or return
an actionable workflow-level rejection.

**Actual:** The run state recorded a rejected `spec_create` worker with this Codex error:

```text
Error: turn/start: turn/start failed: Input exceeds the maximum length of 1048576 characters.
actual_chars: 1082420
```

The rejected step's injected references included broad historical handoff lists, backlog
files, many bug files, and large static documents. The total prompt crossed the Codex
transport limit by about 34k characters, so no release artifact was produced.

**Root cause hypothesis:** `release_definition.spec_create` accepts the broad
`release_scope` context set without a transport-aware token/character budget. The step
injects whole artifacts where a summarized scope handoff plus the selected backlog/bug
records should be sufficient.

**Impact:** Release definition can dead-end when the backlog/bug catalog grows. This blocks
advancing the PI workflow-hardening release through the normal workflow and forces manual
SPEC repair or a narrower retry.

**Fix direction:**

- Add a character/token budget to lifecycle worker prompt assembly before invoking
  headless runtimes.
- For `spec_create`, prefer the approved release-scope handoff plus the explicitly
  selected backlog/bug files over the entire open backlog/bug and historical handoff set.
- Fail earlier with a workflow-owned blocked result that names the over-budget fragment and
  suggested retry, instead of surfacing a raw transport exception.
- Add a regression test using an oversized synthetic backlog/bug catalog.

**Bug-report workflow note:** Direct Markdown fallback used because
`bug-report-fake-bug-write-emits-stub-and-discards-fields` is still open.

## Resolution

Closed in `v0.1.37/alpha-1`.

Root cause: release-definition model steps assembled the full worker prompt and launched the
headless runtime without a transport-aware prompt budget. When the selected context grew,
`codex exec` rejected the request with its raw `input_too_large` transport error.

Fix: `ReleaseDefinitionWorkflow` now checks the fully assembled worker prompt before
starting the runtime. Prompts over the headless budget block inside the lifecycle workflow
with a structured `BlockedState` naming the step and prompt character count, instead of
spawning Codex/PI and surfacing a raw transport failure.

Validation:

- Oversized prompt regression in `tests/integration/cli/test_release_definition_workflow.py`.
- `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py -q` -> `12 passed`.
- Included in focused v0.1.37 deterministic suite -> `41 passed`.
