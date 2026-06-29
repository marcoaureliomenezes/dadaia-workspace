---
name: fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact
status: Open
severity: "HIGH"
surface: lifecycle bug report workflow
---

# Fake release-definition spec_create does not create canonical SPEC.md artifact

**Symptom:** Fake release-definition spec_create does not create canonical SPEC.md artifact

## Details

After PI release-definition blocked at spec_create, the documented deterministic fallback was tried with --harness fake. The workflow still blocked at spec_create because specs/releases/v0.1.40/SPEC.md was missing. This prevents even fake release-definition from producing canonical release artifacts.

## Repro

.dadaia/.venv/bin/dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 --run-id v0140-define-sdd-governance-v2-fake --backlog sdd-governance-v2-agents-lifecycle --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict --bug backlog-doctor-blocks-consumed-item-refactor-commit --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention --bug pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence --harness fake --json

## Expected

Fake release-definition remains a deterministic workflow driver and creates the canonical SPEC/PLAN/TASKS artifacts required by gates.

## Actual

Workflow returned BLOCKED at spec_create: spec_create missing canonical release artifact SPEC.md.

