---
description: "Use when: working in dadaia-workspace implementation, bootstrap, specs, or runtime automation. Enforces native SDD, workspace-root .dadaia usage, isolated .dadaia/.venv, and no ephemeral files outside .dadaia/tmp."
paths:
  - "**"
---

# dadaia-workspace-sdd-enforcer

This rule is always active for dadaia-workspace.

## Mandatory behavior

- Never implement code without the required approved spec artifacts for the current scope.
- Respect the SDD phase order: `SPEC.md` -> `PLAN.md` -> `TASKS.md` -> implementation.
- Do not skip human approval gates between phases.
- If implementation and spec diverge, update the specs first.
- If the task is about refining `specs/`, do not mix that work with implementation unless the user explicitly asks for both and the specs are already consistent.
- Treat the runtime dadaia workspace as `<workspace-root>/.dadaia/`, outside the `dadaia-workspace/` repository root.
- After workspace bootstrap exists, use `<workspace-root>/.dadaia/.venv/bin/python` and `<workspace-root>/.dadaia/.venv/bin/pip` for Python execution.
- Write ephemeral Python scripts only in `<workspace-root>/.dadaia/tmp/python/`.
- Write transient JSON or temporary structured data only in `<workspace-root>/.dadaia/tmp/json/`.
- Keep product agent assets only under `dadaia_workspace/public/` in this repository.
- Do not create or rely on `dadaia-workspace/.claude/`; runtime installation target is `<workspace-root>/.claude/`.
- Do not create temporary automation artifacts under the library repository root, `specs/`, or `tests/`.

## Explicit approval marker

- A required canonical artifact counts as approved only when its header contains the exact marker `**Status:** Aprovado`.
- Artifacts marked `Em revisão`, `Draft`, or without an explicit status marker are not approved for implementation.

## Before writing code

1. Load `specs/constitution.md`.
2. Load `specs/memory/architecture.md`.
3. Load `specs/memory/product.md`.
4. Load `specs/memory/tech-stack.md`.
5. Load `specs/foundation/SPEC.md`.
6. Load `specs/SPEC.md`.
7. Load the feature spec relevant to the task.
8. Confirm that `PLAN.md` and `TASKS.md` exist and are aligned when the scope requires implementation.

## Stop conditions

- Missing spec artifact.
- Required artifact not explicitly marked `Aprovado`.
- Missing owner document for the concern being edited.
- Conflicting behavior between specs.
- Python automation being attempted outside `.dadaia/.venv` after bootstrap exists.
- Temporary automation artifact being written outside `.dadaia/tmp/`.
- Frozen CLI surface being changed without explicit spec update.
- State machine or schema being changed only in code.