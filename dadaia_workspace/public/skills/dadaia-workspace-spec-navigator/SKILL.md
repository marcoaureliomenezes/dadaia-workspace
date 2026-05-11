---
name: dadaia-workspace-spec-navigator
description: "Use when: loading dadaia-workspace specs in canonical order for implementation, review, or planning. Supports both the repository itself and an active runtime context discovered via primary_context.json or `dadaia context show --json`."
---

# dadaia-workspace-spec-navigator

## Goal

Resolve the active Spec Context Project and load the correct specs for the current task.

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

2. Otherwise resolve the active context using one of these two mechanisms (in priority order):

   **a) `DADAIA_CONTEXT` env var** — if the env var is set, use `<workspace-root>/repos/<DADAIA_CONTEXT>/specs/` directly. This takes priority over the JSON file.

   **b) `primary_context.json`** — read `.dadaia/states/primary_context.json` directly. Parse the `specs_dir` field. As a fallback, run `dadaia context show --json` and parse the JSON output.

3. If no active context is found (env var unset and JSON file absent or `context: null`): stop and tell the user to activate a context first (`dadaia context activate <name>`).

4. Read `<specs_dir>/constitution.md`.
5. Read `<specs_dir>/memory/architecture.md`.
6. Read `<specs_dir>/memory/product.md`.
7. Read `<specs_dir>/memory/tech-stack.md`.
8. Read `<specs_dir>/foundation/SPEC.md`.
9. Read `<specs_dir>/SPEC.md`.
10. Read the feature spec relevant to the current task.
11. If planning or implementation is in scope, read `<specs_dir>/PLAN.md` and `<specs_dir>/TASKS.md`.
12. If implementation is in scope, verify every required artifact for that scope contains the explicit marker `**Status:** Aprovado`; otherwise stop before implementation.
13. If required files are missing, report that the context is incomplete and stop before implementation.

## Guardrails

- Do not parse `dadaia context list` as the canonical source for automation.
- Do not assume specs exist if `specs_dir` is present but required files are missing.
- Do not treat `Em revisão`, `Draft`, or missing status markers as approval for implementation.
- For dadaia-workspace itself, always load the foundation spec when the task can affect architecture, state machine, CLI, schema, or agent assets.
- If the task affects bootstrap, Python execution, or automation hygiene, always load `specs/memory/architecture.md` and `specs/memory/tech-stack.md`.
- Never reference `standby`, `context_dir`, `select`, or `is_selected` — these concepts do not exist in v3.0.
