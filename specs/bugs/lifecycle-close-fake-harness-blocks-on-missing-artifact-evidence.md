---
name: lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence
status: Closed
severity: "MEDIUM"
reported: 2026-06-30
surface: lifecycle bug report workflow
session_id: null
---

# lifecycle close fake harness blocks on missing artifact evidence

**Symptom:** lifecycle close fake harness blocks on missing artifact evidence

## Repro

/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia lifecycle close --context dadaia-workspace --release-id v0.1.41 --run-id close-v0141 --harness fake --json

## Expected

The fake harness closure path should either emit valid closure artifact evidence or be documented/rejected before the workflow starts.

## Actual

The workflow accepted fake, then blocked at closure with reason agent result missing artifact evidence.

## Resolution

- **Release:** v0.1.42 (task T-D).
- **Root cause:** `lifecycle close` targets phase `CLOSURE`, which is a *create* step
  (not a review phase), so the evidence gate in
  `LifecycleAgentRunner._blocked_result` requires only populated `artifact_refs` +
  in-scope paths. `FakeAgentRuntime` had writers for create (`SPEC/PLAN/TASKS`), bug, and
  review handoffs, but **no closure writer** — the close step matched none of them and
  fell through to the no-op result with empty `artifact_refs`, so the gate blocked on
  "agent result missing artifact evidence".
- **Fix:** added `_write_allowed_close_artifact` to
  `dadaia_workspace/infrastructure/fake_runtime.py`, the closure sibling of
  `_write_allowed_review_handoff`. It detects the create-step close prompt
  ("Run the close step") and, when a `.dadaia/handoff/<context>/**` path is allowed,
  writes a deterministic closure handoff document and returns it as `artifact_refs`, so
  the evidence gate passes and `lifecycle close --harness fake` advances to `CLOSURE`.
- **Validation:** new regression test
  `tests/integration/cli/test_lifecycle_cli.py::test_lifecycle_close_fake_harness_emits_evidence_and_advances`
  runs the close verb against the real default `FakeAgentRuntime` and asserts the run
  reaches `CLOSURE` (`COMPLETED`, not blocked) with a closure handoff artifact on disk.
  `ruff`, `ruff format`, and `mypy` clean on the changed files.

