---
name: lifecycle-review-qa---harness-fake-blocks-with-missing-approved-verdict
status: Open
severity: "MEDIUM"
surface: lifecycle bug report workflow
session_id: null
---

# lifecycle review qa --harness fake blocks with missing APPROVED verdict

**Symptom:** lifecycle review qa --harness fake blocks with missing APPROVED verdict

## Repro

python -m dadaia_workspace.cli.main lifecycle review qa --release-id v0.1.40 --run-id v0140-alpha1-qa --harness fake --json

## Expected

Fake lifecycle review worker emits an APPROVED verdict or the CLI documents the required approving fake path

## Actual

Command returned BLOCKED at qa_review: agent result missing APPROVED verdict
