---
name: dadaia-workspace-spec-navigator
description: "Use when: loading dadaia-workspace specs in canonical order for implementation, review, planning, or release closure. Resolves the active release via specs/releases/ACTIVE.md and reads memory Markdown + the active release's SPEC/PLAN/TASKS. Supports both the dadaia-workspace repository itself and any active runtime context discovered via primary_context.json or `dadaia context show --json`."
---

# dadaia-workspace-spec-navigator

## Goal

Resolve the active Spec Context Project, the active release, and load the right specs in
canonical order for the current task.

## Workflow

1. **Resolve workspace context.**
   - If the task is about the `dadaia-workspace` repository itself, treat its local
     `specs/` as the target spec context.
   - Otherwise, resolve in priority order:
     - **a) `DADAIA_CONTEXT` env var** — if set, use
       `<workspace-root>/repos/<DADAIA_CONTEXT>/specs/`.
     - **b) `primary_context.json`** — read `.dadaia/states/primary_context.json` and
       parse `specs_dir`. Fallback: `dadaia context show --json`.
   - If neither resolves: stop and tell the operator to activate a context first
     (`dadaia context activate <name>`).

2. **Read constitution and atomic memory (Markdown).**
   - `<specs-dir>/constitution.md`
   - `<specs-dir>/memory/architecture.md`
   - `<specs-dir>/memory/product/catalog.json` — preferred machine-readable feature catalog when present.
   - `<specs-dir>/memory/product/index.md` — entry point for product catalog. Load
     specific `<specs-dir>/memory/product/<feature-slug>.md` files on demand when the
     task requires functional depth on a particular feature (avoids overloading context
     with all features at once).
   - `<specs-dir>/memory/tech-stack.md`

   Read Markdown atoms directly. Use `catalog.json` to select the 1-3 feature
   atoms relevant to the task; do not load every product atom by default.

3. **Resolve the active release.**
   - Read `<specs-dir>/releases/ACTIVE.md`. Expected format:
     ```
     release: <release-id>
     phase: <DISCOVERY|SPEC|PLAN|TASKS|IMPLEMENTATION|CLOSURE|ARCHIVED>
     ```
   - If file is missing or `release: none`: no active release. Inform the operator and
     stop before implementation.

4. **Read the active release's specs in order:**
   - `<specs-dir>/releases/<release-id>/SPEC.md`
   - `<specs-dir>/releases/<release-id>/PLAN.md` (if planning/implementation in scope)
   - `<specs-dir>/releases/<release-id>/TASKS.md` (if implementation in scope)
   - `<specs-dir>/releases/<release-id>/CLOSURE.md` (only if phase = `CLOSURE` or
     `ARCHIVED`)

5. **Approval verification.**
   - If implementation is in scope, every loaded SPEC/PLAN/TASKS must contain the explicit
     marker `**Status:** Aprovado`. Otherwise, stop before implementation and surface
     which artifact lacks approval.

6. **Legacy compat (migration window).**
   - If `specs/features/<name>/{SPEC,PLAN,TASKS}.md` exist, treat them as legacy. They do
     not authorize implementation unless explicitly referenced from the active release's
     SPEC. Report their presence as a migration warning.

## Guardrails

- **Ignore `_archive/`** by default. The archive is historical; agents do not use it as a
  source of approval. Read only when the operator asks for history.
- **Ignore `backlog/`** for implementation decisions. Backlog is informal; nothing there
  authorizes work.
- Do not parse `dadaia context list` as the canonical source for automation.
- Do not assume specs exist if `specs_dir` is present but required files are missing.
- Do not treat `Em revisão`, `Draft`, or missing status markers as approval.
- Never reference `standby`, `context_dir`, `select`, or `is_selected` — these concepts do
  not exist in v3.0.
- Markdown memory files are read-only for every agent except `product-engineer` during the
  CLOSURE phase. Reading is always allowed.
