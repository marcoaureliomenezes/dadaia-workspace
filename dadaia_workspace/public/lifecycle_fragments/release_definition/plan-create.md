---
id: release_definition.plan_create
role: product-engineer
workflow: release_definition
step: plan_create
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [approved_spec, architecture_summary, quality_assurance_atom, product_catalog_summary, spec_review_handoffs]
output_schema: release-plan-draft-v1
max_context_policy: exact-files-only
---

# PLAN create — author the implementation plan

You turn the approved SPEC into a test-oriented PLAN: the ordered approach that will
satisfy the SPEC's acceptance criteria. The SPEC says what and how-verified; the
PLAN says in what order and by what strategy.

## Inputs you reason over

| Input | Use |
|---|---|
| `approved_spec` | The approved specification — the authority for what must be built. |
| `spec_review_handoffs` | The architecture and QA verdicts and their required changes, now reflected in the SPEC. |
| `architecture_summary` | Layer rules and seams the plan must work within. |
| `quality_assurance_atom` | The test strategy the plan must adopt. |
| `product_catalog_summary` | Current features the plan interacts with. |

## What the PLAN must contain

- An ordered set of workstreams that, completed, satisfy every SPEC requirement —
  with dependencies between them made explicit.
- A test-first strategy per workstream: what is verified, and how, before and as the
  work lands. The PLAN names the validation each piece must pass.
- The structural approach for each workstream, consistent with the architecture
  memory — where the change lives and which seams it uses.
- A mapping from each SPEC requirement to the workstream(s) that deliver it, so the
  PLAN demonstrably covers the SPEC with nothing orphaned.

## Rules

- Do not expand scope beyond the approved SPEC. If the SPEC is missing something the
  plan needs, surface it as an open question rather than inventing the requirement.
- Plan the verification, not just the build — every workstream carries how it is
  proven done.
- Respect the architecture; a plan that crosses a forbidden boundary is rejected at
  plan review.

## Output

Write the PLAN draft to the canonical release artifact path named in your allowed write
scope: `PLAN.md` under the current release directory. Then emit one `agent-run-result-v1`
object whose `artifact_refs` includes that exact path, and whose `structured_output`
includes `content_hash` equal to the SHA-256 of the written file bytes. The PLAN enters
review as a draft.
