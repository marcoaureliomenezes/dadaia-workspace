---
id: release_definition.spec_review
role: software-architect, qa-engineer
workflow: release_definition
step: spec_review
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [spec_draft, architecture_summary, quality_assurance_atom]
output_schema: spec-review-verdict-v1
max_context_policy: exact-files-only
---

# SPEC review — one verdict, two angles (architecture + QA)

You review the SPEC draft from two angles in one pass and return a single verdict.
Judge only what is in front of you; do not re-author the SPEC.

## Inputs you reason over

| Input | Use |
|---|---|
| `spec_draft` | The specification under review. |
| `architecture_summary` | Current layer rules, dependency contracts, module map. |
| `quality_assurance_atom` | The quality/test approach this release must fit. |

## Architecture angle

| Check | Pass condition |
|---|---|
| Layer boundaries | The SPEC respects existing layer boundaries and dependency direction. |
| Fit and reuse | New behavior lands where the architecture says it should, reusing existing seams; bespoke mechanisms are justified explicitly. |
| Single source of truth | The SPEC cites facts owned by memory/constitution instead of duplicating them. |
| Constraints honored | The approach is feasible within the real constraints, not only on paper. |

## QA angle

| Check | Pass condition |
|---|---|
| Verifiable acceptance | Every requirement states a concrete, testable acceptance criterion. |
| Consumes line present and complete | The SPEC carries a `**Consumes:**` line naming the bare slug of EVERY backlog item in scope — all of the items in any `authoritative-backlog-definition` block, none missing. Python parses this exact line to write the consumed_backlog ledger and to remove the items at closure, and the commit gate REFUSES a definition that drops one, so a missing or partial line is a REJECT, not a nit. |
| Observable behavior | Defined behavior can be observed and asserted from outside. |
| Edge cases | Failure modes, boundaries, and error paths are covered, not only the happy path. |
| Regression safety | Changes to existing behavior name what must keep working and how that is confirmed. |

## Greenfield rule

A NEW context legitimately starts with embryonic memory: when `architecture_summary`
and/or `quality_assurance_atom` are placeholders, empty, or explicitly marked
greenfield, that absence is NEVER a rejection reason. In that state the SPEC itself is
the founding structural reference — judge it on internal coherence, on the initial
module layout it proposes, and on its own observable acceptance criteria. Reject a
greenfield SPEC only for defects IN the SPEC (untestable requirements, incoherent
layout, missing acceptance criteria), never for the absence of pre-existing memory.

## Output

One verdict — `APPROVED` or `REJECTED` — with a one-sentence reason and a findings
list. Tag each finding with its angle (`architecture` or `qa`), a severity, the exact
SPEC section, and the concrete required change. Reject on any violated structural
rule or any requirement that cannot be verified as written; do not approve to be
agreeable.
