---
name: dadaia-workspace-spec-navigator
description: "Use when: loading dadaia-workspace specs in canonical order for implementation, review, planning, or release closure. Resolves the active release via specs/releases/ACTIVE.md and reads memory Markdown + the active release's SPEC/PLAN/TASKS. Supports both the dadaia-workspace repository itself and any active runtime context discovered via spec_contexts.json (v2 registry) or `dadaia context show --json`."
---

# dadaia-workspace-spec-navigator

## Goal

Resolve the active Spec Context Project, the active release, and load the right specs in
canonical order for the current task.

## Directory reference

```
specs/
├── constitution.md              ← absolute laws of the product — read first, always
├── memory/
│   ├── architecture.md        ← layer rules, modules, dependency contracts
│   ├── tech-stack.md          ← approved technologies and constraints
│   └── product/                 ← FOLDER catalog (functional view)
│       ├── index.md             ← entry point: vision, users, ordered feature catalog with links
│       ├── catalog.json         ← generated machine-readable feature catalog
│       └── <feature-slug>.md    ← one Markdown atom per feature in production
├── assets/<scope>/<id>.png      ← screenshots referenced by memory Markdown
├── releases/
│   ├── ACTIVE.md                ← which release is active and in which phase
│   └── <release-id>/{SPEC,PLAN,TASKS,CLOSURE}.md
├── backlog/
│   ├── BACKLOG.md                ← single source: ## ACTIVE (candidates) + ## LEDGER (closed)
│   └── _archive/                 ← superseded entry files, historical (git mv only)
└── _archive/                    ← archived releases, legacy features/memory/root (read-only)
```

Status-token lifecycle (`Draft` → `Em revisão` → `Aprovado`): `DADAIA.md` §6 —
referenced, not restated.

## Workflow

1. **Resolve workspace context.**
   - If the task is about the `dadaia-workspace` repository itself, treat its local
     `specs/` as the target spec context.
   - Otherwise, resolve exactly as the law (DADAIA.md §3) does:
     - **a) `DADAIA_CONTEXT` env var** — if set, use
       `<workspace-root>/repos/<DADAIA_CONTEXT>/specs/`.
     - **b) your own session binding** — `dadaia context show --json` reports it (the
       live session record; never scan for a "first alive" context).
     - **c) the repo containing the working directory** — a cwd under
       `repos/<slug>/` selects that context.
   - Context resolves automatically from the registry — never halt to ask the
     operator to bind or rebind. Binding is optional. Only if the workspace has no
     ALIVE context at all is there nothing to navigate.

2. **Read constitution and atomic memory (Markdown).**
   - `<specs-dir>/constitution.md`
   - `<specs-dir>/memory/architecture.md`
   - `<specs-dir>/memory/product/catalog.json` — preferred machine-readable feature catalog when present.
   - `<specs-dir>/memory/product/index.md` — entry point for product catalog. Load
     specific `<specs-dir>/memory/product/<area>/<feature-slug>.md` files (per
     `catalog.json`'s `path` field) on demand when the
     task requires functional depth on a particular feature (avoids overloading context
     with all features at once).
   - `<specs-dir>/memory/tech-stack.md`

   Read Markdown atoms directly. Use `catalog.json` to select the 1-3 feature
   atoms relevant to the task; do not load every product atom by default.

3. **Resolve the active release (and segment).**
   - Read `<specs-dir>/releases/ACTIVE.md`. Format (schema v2, ADR-1/ADR-5):
     ```
     release: <release-id>
     segment: <alpha-N|rc-N>   # optional — present for segmented releases
     phase: <DISCOVERY|DEFINITION|SPEC|PLAN|TASKS|IMPLEMENTATION|CLOSURE|ARCHIVED>
     ```
   - If file is missing or `release: none`: no active release. Inform the operator and
     stop before implementation.
   - Let `<rel-path>` = `<release-id>/<segment>` when a `segment:` is present, else
     `<release-id>`.

4. **Read the active release's specs in order** (under `releases/<rel-path>/`):
   - `<specs-dir>/releases/<rel-path>/SPEC.md`
   - `<specs-dir>/releases/<rel-path>/PLAN.md` (if planning/implementation in scope)
   - `<specs-dir>/releases/<rel-path>/TASKS.md` (if implementation in scope)
   - `<specs-dir>/releases/<rel-path>/CLOSURE.md` (only if phase = `CLOSURE` or
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
  DEFINITION and CLOSURE phases (constitution, Memory Canon). Reading is always allowed.
