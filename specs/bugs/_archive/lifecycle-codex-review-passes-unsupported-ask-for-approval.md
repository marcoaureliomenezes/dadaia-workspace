---
name: lifecycle-codex-review-passes-unsupported-ask-for-approval
status: Open
severity: HIGH
reported: 2026-07-01
surface: lifecycle review workflow, Codex Layer-2 runner
session_id: sess_d4657b09
---

## Summary

`dadaia lifecycle review qa --harness codex` blocks before the QA worker can run because
the lifecycle runner invokes `codex exec` with an unsupported `--ask-for-approval`
argument.

## Repro

```bash
.dadaia/.venv/bin/dadaia lifecycle review qa \
  --context tauan-games \
  --release-id v0.2.0 \
  --run-id review-qa-t-gis-06 \
  --harness codex \
  --json
```

Observed response:

```text
error: unexpected argument '--ask-for-approval' found
Usage: codex exec [OPTIONS] [PROMPT]
```

The workflow returns a blocked JSON result at `qa_review` with runtime `codex_exec`.

## Expected

The Codex lifecycle runner should use CLI flags supported by the installed Codex exec
surface, or capability-detect the approval/sandbox options before invocation. A QA review
gate should either run the Codex worker and extract its verdict, or fail with an actionable
configuration error that names the incompatible Codex CLI version/flag contract.

## Actual

The review workflow never reaches the worker. It blocks at command-line parsing with
`unexpected argument '--ask-for-approval'`, so release tasks that require QA/code/security
review cannot advance through the official Codex lifecycle gate.

## Notes

The documented bug-report workflow is not available in this CLI build:

```bash
.dadaia/.venv/bin/dadaia lifecycle bug --help
# No such command 'bug'
```

This file is therefore an additive fallback bug record. It was found while attempting to
review `tauan-games` release `v0.2.0`, task `T-GIS-06`.
