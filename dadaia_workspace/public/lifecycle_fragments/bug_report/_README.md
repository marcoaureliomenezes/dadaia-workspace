# bug_report — scaffolded, deferred

This workflow directory is scaffolded but carries no step fragments yet. The
`bug_report` workflow is deferred to a follow-up release; only its directory and this
stub ship now.

When implemented, this workflow normalizes a reported symptom into an additive bug
record, deduplicating against existing bugs. Planned steps (see the epic, §6.7):
`bug_intake` (any / PM), `dedupe` (Python / product-engineer), `bug_write`
(Python / product-engineer). Bug records are additive and land in the bug channel.

Do not reference fragments from this directory in any shipped workflow until the step
fragments exist — the loader and workflow checks will fail on a dangling fragment id.
