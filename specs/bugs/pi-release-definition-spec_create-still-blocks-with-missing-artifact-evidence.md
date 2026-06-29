---
name: pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence
status: Open
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# PI release-definition spec_create still blocks with missing artifact evidence

**Symptom:** PI release-definition spec_create still blocks with missing artifact evidence

## Details

While defining v0.1.40 through dadaia lifecycle release define with --harness pi and model gpt-5.3-codex-spark:medium, the workflow accepted release_scope but blocked at spec_create with reason 'agent result missing artifact evidence'. This repeats the previously claimed-fixed class and prevents PI from being the default release-definition worker for this SDD governance release.

## Repro

timeout 900 .dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2 --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --harness pi --model gpt-5.3-codex-spark:medium --json

## Expected

PI spec_create emits canonical SPEC artifact evidence or a recoverable matching handoff so the release-definition workflow advances.

## Actual

Workflow returned BLOCKED at spec_create: agent result missing artifact evidence.
