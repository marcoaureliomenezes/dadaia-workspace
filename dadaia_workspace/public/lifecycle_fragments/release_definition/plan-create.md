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
- For every new or changed caller-facing surface, an explicit contract binding:
  exact public type/function/method names, parameter and return signatures, field
  names/types, and module/export path. These are PLAN design decisions derived from
  the approved behavior; do not leave them for TASKS or implementation to invent.
- A mapping from each SPEC requirement to the workstream(s) that deliver it, so the
  PLAN demonstrably covers the SPEC with nothing orphaned.
- A `## Validation Dependency Table` section — MANDATORY, a Python lint blocks the
  step without it. Copy this skeleton verbatim into the PLAN and fill one row per
  workstream (canonical ids `WS-1`, `WS-2`, …; write `None` for an empty cell; the
  validation-dependencies cell may name only the current or an earlier workstream):

  ```markdown
  ## Validation Dependency Table

  | Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
  |---|---|---|---|---|
  | WS-1 | <deliverable> | <command or check> | None | None |
  ```

## Rules

- Do not expand scope beyond the approved SPEC. If the SPEC is missing something the
  plan needs, surface it as an open question rather than inventing the requirement.
- Naming and binding the implementation contract for an approved public behavior is
  required planning, not scope expansion. If existing source determines the naming
  convention, follow it; if no defensible binding can be derived, surface the gap as
  an open question and do not present the PLAN as implementable.
- Plan the verification, not just the build — every workstream carries how it is
  proven done.
- Keep validation dependency-safe: a workstream's own validation may use only the
  product surfaces created before or within that workstream. When end-to-end evidence
  needs a later integration/orchestration surface, assign that evidence to the later
  workstream and validate the earlier unit through its direct public or internal
  contract. Never require an earlier workstream to prove behavior through work that has
  not been built yet.
- Foundational value objects and data contracts must be validated through direct
  construction, equality, serialization, or invariant tests. Do not validate them
  through an orchestration, replay, UI, or integration surface scheduled later.
- Respect the architecture; a plan that crosses a forbidden boundary is rejected at
  plan review.

## Output

A PLAN draft plus its SPEC-requirement coverage mapping, emitted per the output
contract. The PLAN enters review as a draft.
