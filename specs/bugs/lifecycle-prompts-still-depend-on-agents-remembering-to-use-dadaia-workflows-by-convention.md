---
name: lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention
status: Closed
severity: "HIGH"
surface: lifecycle bug report workflow
session_id: null
---

# Lifecycle prompts still depend on agents remembering to use dadaia-workflows by convention

**Symptom:** Lifecycle prompts still depend on agents remembering to use dadaia-workflows by convention

## Details

Operator feedback: release definition, release implementation, review, closure, and other supported development lifecycle phases must default to dadaia-workflows. Manual lifecycle execution should be the exception and must be recorded as an exception when workflow tooling is broken.

## Repro

Ask an agent to define or implement a release; observe that it may inspect/edit specs manually before invoking dadaia lifecycle workflow verbs, requiring operator reminders.

## Expected

Agentic instructions and release governance state that dadaia-workflows are the default lifecycle path for every supported phase; fallback/manual execution is exceptional and must be justified with a registered workflow bug.

## Actual

The workflow-first expectation is present in some skills, but not sufficiently canonical across the governing memory/rules/agentic surfaces, so operators still need to repeat it.

## Resolution

Closed in v0.1.40 alpha-1 T4. The always-on `release-governance` rule now defines
workflow-first lifecycle execution as the default for release definition,
implementation, review, audit, bug reporting, closure, and shipping. The root
AGENTS source and lifecycle reference skills now require the matching
`dadaia lifecycle ...` workflow first, with manual fallback only after a registered
workflow bug.
