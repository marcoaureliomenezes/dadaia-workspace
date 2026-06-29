---
name: codex-release-definition-spec_create-does-not-create-canonical-spec.md-artifact
status: Open
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# Codex release-definition spec_create does not create canonical SPEC.md artifact

**Symptom:** Codex release-definition spec_create does not create canonical SPEC.md artifact

## Details

After PI and fake release-definition workers blocked at spec_create, the Codex Layer-2 harness was tried for v0.1.40. It also accepted release_scope but blocked at spec_create because specs/releases/v0.1.40/SPEC.md was missing. This leaves release-definition unusable for the current scope across all attempted workflow harnesses.

## Repro

.dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2-codex --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --bug pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence --bug fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact --harness codex --model gpt-5.5:medium --json

## Expected

Codex spec_create writes canonical SPEC.md artifact evidence or the workflow provides a deterministic artifact materialization path.

## Actual

Workflow returned BLOCKED at spec_create: spec_create missing canonical release artifact SPEC.md.
