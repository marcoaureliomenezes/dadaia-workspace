---
name: dadaia-workspace-spec-reviewer
description: "Use when: reviewing or refining dadaia-workspace specs before implementation. Loads the canonical owner docs first, checks .dadaia and .venv policy, detects duplicated ownership, and records unresolved gaps in z_bug_specs.md."
---

# dadaia-workspace-spec-reviewer

## Goal

Run a disciplined consistency review over the relevant spec set before implementation or before declaring a refinement pass complete.

## Review workflow

1. Load `specs/constitution.md`.
2. Load `specs/memory/architecture.md`.
3. Load `specs/memory/product.md`.
4. Load `specs/memory/tech-stack.md`.
5. Load `specs/foundation/SPEC.md`.
6. Load `specs/SPEC.md`.
7. Load each feature spec affected by the current task.
8. If planning scope is affected, load `specs/PLAN.md` and `specs/TASKS.md`.
9. Load `z_bug_specs.md`.
10. Load `report-specs-review.md` only if the user explicitly asks for historical context.
11. Compare the spec set across these dimensions:
   - source-of-truth ownership by document;
   - `.dadaia` runtime template and folder semantics;
   - `.dadaia/.venv` policy and Python execution model;
   - `.dadaia/tmp/python` and `.dadaia/tmp/json` policy;
   - architecture and package structure;
   - state machine and lifecycle semantics;
   - frozen CLI surface and JSON contracts;
   - data model support for approved behavior;
   - public asset storage and workspace `.claude/` installation model;
   - traceability from approved requirements into `PLAN.md` and `TASKS.md`.
12. Report findings ordered by severity.
13. If unresolved issues remain, update `z_bug_specs.md`.

## Output rules

- Findings first.
- No implementation suggestions that bypass unresolved spec conflicts.
- Prefer owner-document fixes over derived-document patches.
- If no blocking issues remain, say so explicitly.