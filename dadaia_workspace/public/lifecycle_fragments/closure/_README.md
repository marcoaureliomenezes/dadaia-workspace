# closure — scaffolded, deferred

This workflow directory is scaffolded but carries no step fragments yet. The
`closure` workflow is deferred to a follow-up release; only its directory and this
stub ship now.

When implemented, this workflow collects evidence, writes the closure record,
updates memory, and archives the release. Planned steps (see the epic, §6.4):
`closure_evidence_collect`, `closure_write` (product-engineer), `memory_update`
(product-engineer), `archive_release`, `closure_verify`. Memory writes are permitted
only in the closure phase and are Python-gated; archive and verify are
Python-decided from doctor evidence.

Do not reference fragments from this directory in any shipped workflow until the step
fragments exist — the loader and workflow checks will fail on a dangling fragment id.
