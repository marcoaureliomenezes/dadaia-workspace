---
id: audit.triage
role: project-auditor
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
Audit output is never a deletion — it is a status token plus a routing decision.

## Inputs you reason over

| Input | Use |
|---|---|
| `selected_audit_findings` | The findings from the drift scan to dispose. |
| `candidate_backlog` | Existing backlog so a finding folds into an item rather than duplicating it. |

## Procedure

1. **Dispose every finding.** Assign each finding exactly one disposition:
   `bug` (file an additive bug record), `backlog` (route to a backlog item),
   `accepted-risk` (record and accept, no action now), or `resolved` (already fixed,
   evidence cited). Nothing is dropped silently.
2. **Route, never delete.** A finding becomes a bug or backlog entry by status token
   and routing; the audit itself deletes nothing.
3. **Cite the evidence.** Every disposition carries the finding's severity and the
   evidence behind it so the routing is auditable.

## Output

A disposition handoff naming, per finding, its disposition token and route, the
severity, and the evidence. This output is disposition-ready: the operator or a
downstream workflow acts on the tokens directly.
