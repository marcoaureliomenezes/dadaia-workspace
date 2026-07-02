---
name: legacy-surface-retirement
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: operator architectural deep-review 2026-07-02 (lane B — no-legacy-code law)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/newartifacts.py#bug_new_cmd" }
    change: "delete the legacy `dadaia bug new` Markdown bug scaffolder (superseded by the v0.1.46 JSONL `dadaia bugs append` canon): remove the bug_app registration from cli/main.py, delete the command and its spec_artifacts backing, and update the architecture atom's CLI inventory at the disposing release (the atom currently documents the dual path as coexisting)"
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/server.py#dashboard" }
    change: "remove the deprecated `dadaia server dashboard` command — its removal was promised for the release after deprecation and is overdue at v0.1.48"
  - subject: { kind: code, ref: "dadaia_workspace/container.py#build_orchestration_service" }
    change: "retire features/orchestration: run/status/resume are inert compat stubs (dispatch moved to `dadaia lifecycle`); delete the stubs and the feature package, folding any surviving read-only list/show reference into features/workflows"
  - subject: { kind: code, ref: "dadaia_workspace/core/exceptions.py#ReviewBlockedByImplementationError" }
    change: "delete ReviewBlockedByImplementationError and ImplementationBlockedByReviewError (zero raisers, zero catchers; they exist only for the unused review->implementation backtrack transitions whose reconciliation is owned by lifecycle-verb-governance-uniformity)"
---

# BACKLOG — Legacy surface retirement

**Priority:** HIGH. The operator's law: no dead, stale, or past-representing code.
Also owns (prose scope): audit `features/migrate` — keep only migrations still
required for supported consumer upgrade paths reachable from `dadaia specs upgrade`;
archive or delete completed one-time internal migrations. Also retire
`features/lifecycle/workflows/_deferred.py` (2026-07-02): an empty
`DEFERRED_WORKFLOWS` tuple wrapped in a release-history docstring, kept only as a
"declared seam" — inline the empty concept into its two consumers (workflows
`__init__` re-export + `dadaia_catalog`) and delete the module. Going forward, every
deprecation must carry a release-stamped expiry that the disposing release honors —
"removed next release" promises that outlive two releases are themselves a doctor-able
smell.

Small same-family dead code (unreachable panel telemetry fallback, dead re-exports)
stays owned by `hygiene-and-dead-code-cleanup` (cross-ref).
