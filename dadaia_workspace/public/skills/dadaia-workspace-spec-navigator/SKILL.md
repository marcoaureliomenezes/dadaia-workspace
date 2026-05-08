---
name: dadaia-workspace-spec-navigator
description: "Use when: loading dadaia-workspace specs in canonical order for implementation, review, or planning. Supports both the repository itself and an active runtime context discovered via `dadaia context show --json`, and stops implementation when required artifacts are not explicitly approved."
---

# dadaia-workspace-spec-navigator

## Goal

Resolve the active Spec Context Project using the stable JSON contract and load the correct specs for the current task.

## Workflow

1. If the task is about the `dadaia-workspace` repository itself, load local repository specs in this order and stop:
   - `specs/constitution.md`
   - `specs/memory/architecture.md`
   - `specs/memory/product.md`
   - `specs/memory/tech-stack.md`
   - `specs/foundation/SPEC.md`
   - `specs/SPEC.md`
   - the relevant feature spec
   - `specs/PLAN.md` and `specs/TASKS.md` when planning or implementation is in scope
   - if implementation is in scope, verify every required artifact for that scope contains the explicit marker `**Status:** Aprovado`; otherwise stop before implementation
2. Otherwise run `dadaia context show --json`.
3. Parse the JSON result.
4. If `context` is `null`, stop and tell the user to activate a context first.
5. Read `<specs_dir>/constitution.md`.
6. Read `<specs_dir>/memory/architecture.md`.
7. Read `<specs_dir>/memory/product.md`.
8. Read `<specs_dir>/memory/tech-stack.md`.
9. Read `<specs_dir>/foundation/SPEC.md`.
10. Read `<specs_dir>/SPEC.md`.
11. Read the feature spec relevant to the current task.
12. If planning or implementation is in scope, read `<specs_dir>/PLAN.md` and `<specs_dir>/TASKS.md`.
13. If implementation is in scope, verify every required artifact for that scope contains the explicit marker `**Status:** Aprovado`; otherwise stop before implementation.
14. If required files are missing, report that the context is incomplete and stop before implementation.

## Guardrails

- Do not parse `dadaia context list` as the canonical source for automation.
- Do not assume specs exist if `specs_dir` is present but required files are missing.
- Do not treat `Em revisão`, `Draft`, or missing status markers as approval for implementation.
- For dadaia-workspace itself, always load the foundation spec when the task can affect architecture, state machine, CLI, schema, or agent assets.
- If the task affects bootstrap, Python execution, or automation hygiene, always load `specs/memory/architecture.md` and `specs/memory/tech-stack.md`.