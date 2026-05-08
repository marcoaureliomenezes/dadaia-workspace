---
description: "Use when: modifying specs, rules, skills, or mirrored public governance assets for dadaia-workspace. Enforces canonical review order, single-source-of-truth ownership, and z_bug_specs logging."
paths:
  - "specs/**"
  - "dadaia_workspace/public/**"
  - "z_bug_specs.md"
  - "report-specs-review.md"
---

# dadaia-workspace-spec-governance

This rule governs every change under `specs/` and `dadaia_workspace/public/`.

## Mandatory review order

Load and compare documents in this order before finishing the task:

1. `specs/constitution.md`
2. `specs/memory/architecture.md`
3. `specs/memory/product.md`
4. `specs/memory/tech-stack.md`
5. `specs/foundation/SPEC.md`
6. `specs/SPEC.md`
7. Every feature spec affected by the change
8. `specs/PLAN.md` and `specs/TASKS.md` if implementation planning is in scope
9. `z_bug_specs.md`

## Owner document map

- `specs/memory/architecture.md` owns the runtime workspace template and `.dadaia/` semantics.
- `specs/memory/product.md` owns the product definition, user roles, and conceptual model.
- `specs/memory/tech-stack.md` owns toolchain policy, `.dadaia/.venv`, and Python execution policy.
- `specs/foundation/SPEC.md` owns implementation architecture and anti-drift rules.
- `specs/SPEC.md` owns product behavior and top-level CLI contracts.
- `specs/features/*/SPEC.md` own feature-specific behavior only.
- `specs/PLAN.md` and `specs/TASKS.md` are derived documents and must not override owner documents.

## Mandatory checks

- `.dadaia` template consistency.
- `.dadaia/.venv` policy consistency.
- `.dadaia/tmp/python` and `.dadaia/tmp/json` policy consistency.
- Architecture consistency.
- State machine consistency.
- Frozen CLI consistency.
- Data model support for approved feature behavior.
- Agent asset model consistency between `dadaia_workspace/public/` and the workspace runtime `.claude/` installation target.
- Traceability from approved requirements to plan and tasks.

## Derived document policy

- Edit the owner document first.
- Align affected feature specs second.
- Regenerate or realign `PLAN.md` and `TASKS.md` last.
- Do not let `PLAN.md` or `TASKS.md` redefine contracts owned by higher-level documents.

## Approval marker policy

- A canonical artifact is implementation-ready only when its header contains the exact marker `**Status:** Aprovado`.
- If unresolved issues remain, keep affected artifacts marked `Em revisão` and record the gaps in `z_bug_specs.md`.
- Only mark affected canonical artifacts `Aprovado` after the refinement pass finishes with no unresolved gaps.

## Historical context files

- `report-specs-review.md` is historical context only.
- `z_bug_specs.md` is the live unresolved-gap registry.

## Unresolved issues

If any inconsistency, weak behavior description, or unresolved conflict remains after the refinement pass:

- update `z_bug_specs.md`;
- describe only the remaining gaps;
- do not claim the specs are ready for implementation.