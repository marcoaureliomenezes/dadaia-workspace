# backlog_definition — scaffolded, deferred

This workflow directory is scaffolded but carries no step fragments yet. The
`backlog_definition` workflow is deferred to a follow-up release; only its directory
and this stub ship now.

When implemented, this workflow turns an operator demand into an accepted, additive
backlog item. Planned steps (see the epic, §6.2): `intake_grill` (project-manager),
`architecture_probe` (software-architect), `domain_probe` (optional specialist),
`backlog_author` (product-engineer / PM per governance), `backlog_review`.

Do not reference fragments from this directory in any shipped workflow until the step
fragments exist — the fragment loader and workflow checks will fail on a reference to
a fragment id with no source.
