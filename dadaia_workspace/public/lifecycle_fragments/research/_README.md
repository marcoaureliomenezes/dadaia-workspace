# research — scaffolded, deferred

This workflow directory is scaffolded but carries no step fragments yet. The
`research` workflow is deferred to a follow-up release; only its directory and this
stub ship now.

When implemented, this workflow scopes research questions, runs bounded
investigations, and synthesizes a recommendation. Planned steps (see the epic,
§6.6): `research_scope_grill` (project-manager), `researcher_run`
(researcher / specialist), `synthesis` (project-manager). Synthesis output points to
a recommended backlog or release action.

Do not reference fragments from this directory in any shipped workflow until the step
fragments exist — the loader and workflow checks will fail on a dangling fragment id.
