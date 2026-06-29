---
name: release-definition-spec-create-overselects-context-budget
status: Closed
severity: HIGH
reported: 2026-06-29
surface: lifecycle release_definition context selector
session_id: codex-2026-06-29-v0139
release: v0.1.39
resolved: 2026-06-29
---

# Release-definition `spec_create` over-selects context and exceeds headless prompt budget

**Symptom:** A workflow-first release definition for the picked backlog item
`sdd-governance-v2-agents-lifecycle` blocked before launching the `spec_create` worker
because the assembled prompt exceeded the PI headless runtime budget.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.39 \
  --run-id v0139-define-sdd-governance \
  --intent "Pick sdd-governance-v2-agents-lifecycle and define a focused alpha-1 release using dadaia workflows. Scope the first implementable slice with attention: classify per-class specs archive directories as FROZEN, scaffold/doctor the accepted archive taxonomy, and leave JSONL bug-events plus audit-disposition law as explicit residuals unless the workflow proves they fit safely." \
  --backlog sdd-governance-v2-agents-lifecycle \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

**Expected:** `spec_create` should inject only bounded context required for the selected
backlog item and stay under the headless runtime prompt budget.

**Actual:** The run blocked before launch:

```text
worker prompt exceeds headless runtime budget before launch (1056699 > 900000 chars)
```

The run state at `.dadaia/states/lifecycle/v0139-define-sdd-governance.json` shows
`spec_create` refs included broad backlog and bug corpus rather than only the picked
backlog item and the release-scope handoff.

**Workflow reporting note:** The bug-report workflow was attempted first:

```bash
.dadaia/.venv/bin/dadaia lifecycle bug report --context dadaia-workspace --release-id v0.1.39 ...
```

It produced intake and dedupe handoffs, then timed out before writing the bug file. This
Markdown file is the emergency fallback required when the bug-report workflow is itself
unavailable or blocked.

**Acceptance:** Bound `release_definition.spec_create` dynamic context so a selected
backlog release definition does not include the entire live backlog/bug corpus. Add
regression coverage that `spec_create` context refs are limited to the selected backlog,
upstream release-scope handoff, and explicitly required review inputs.

## Resolution - v0.1.39 alpha-1

`ContextSelector` now accepts explicit selected backlog, bug, and audit identifiers. The
release-definition composition root threads `ReleaseDefinitionScopeInput` into the
selector, so `spec_create` receives exactly the operator-picked items while `release_scope`
keeps its broad discovery context.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py::test_release_definition_spec_create_injects_only_selected_scope -q
```
