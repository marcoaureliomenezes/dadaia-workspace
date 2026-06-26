# audit — scaffolded, deferred

This workflow directory is scaffolded but carries no step fragments yet. The `audit`
workflow is deferred to a follow-up release; only its directory and this stub ship
now.

When implemented, this workflow scopes an audit, runs the doctors, scans for drift,
and triages findings into dispositions. Planned steps (see the epic, §6.5):
`audit_scope` (project-auditor), `doctor_pass` (Python), `drift_scan`
(project-auditor), `triage` (project-manager / product-engineer). Audit output must
be disposition-ready and land in the audit channel.

Do not reference fragments from this directory in any shipped workflow until the step
fragments exist — the loader and workflow checks will fail on a dangling fragment id.
