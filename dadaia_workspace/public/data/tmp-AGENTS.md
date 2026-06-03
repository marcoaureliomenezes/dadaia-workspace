# .dadaia/tmp/AGENTS.md — Temporary Files

Scope: this file governs `.dadaia/tmp/**`.

This directory is for disposable agent scratch files, screenshots, command
captures, generated probes, and intermediate data. Nothing here is product
source or an approval artifact.

## Rules

- Use task/agent-scoped subdirectories, for example:
  `.dadaia/tmp/<agent>/<YYYYMMDD>/<slug>/`.
- Prefer small text, JSON, screenshots, or logs that support a report.
- Do not store secrets, credentials, tokens, private keys, or production dumps.
- Do not import files from here as application/runtime dependencies.
- Do not use this directory for `SPEC.md`, `PLAN.md`, `TASKS.md`, source code,
  committed tests, or persistent state.

## Cleanup

Files here may be deleted after their evidence is summarized in a report. If a
temporary artifact is required for traceability, move the evidence reference to
`.dadaia/reports/<context>/<agent>/` and mention it in the report sidecar.

## Validation

Reports that cite temporary files must include enough detail to reproduce the
evidence if the temp file is later removed.
