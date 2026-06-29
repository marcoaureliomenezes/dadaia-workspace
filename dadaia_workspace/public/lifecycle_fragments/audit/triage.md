---
id: audit.triage
role: project-manager
workflow: audit
step: triage
static_inputs: []
dynamic_inputs: [selected_audit_findings, candidate_backlog]
output_schema: audit-disposition-handoff-v1
max_context_policy: summary
---

# Triage — turn findings into disposition-ready output

You take the drift-scan findings and produce the audit's disposition-ready output:
each finding assigned a disposition so the operator can act without re-deriving it.
Audit output is never a deletion. It is a lifecycle disposition token plus a
routing decision.

## Inputs you reason over

| Input | Use |
|---|---|
| `selected_audit_findings` | The findings from the drift scan to dispose. |
| `candidate_backlog` | Existing backlog so a finding folds into an item rather than duplicating it. |

## Procedure

1. **Dispose every finding.** Assign each finding exactly one canonical lifecycle
   disposition: `fixed`, `superseded`, `deferred`, or `rejected`. Nothing is dropped
   silently.
2. **Route, never delete.** A disposition is not a route label. A finding may route to
   an additive bug record, backlog item, accepted risk note, or release evidence while
   retaining one of the canonical disposition tokens above.
3. **Cite the evidence.** Every disposition carries `finding_id`, severity, route, and
   the evidence behind it so the routing is auditable.
4. **Archive only when complete.** Do not archive audit output until every
   `finding_id:` entry has a canonical `disposition:` token.

## Output

A disposition handoff naming, per finding, `finding_id`, canonical disposition token,
route, severity, and evidence. This output is disposition-ready: the operator or a
downstream workflow acts on the tokens directly.
