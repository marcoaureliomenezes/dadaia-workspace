# Releases

This directory contains all release directories for this Spec Context Project.

## Structure

```
releases/
  ACTIVE.md                  — points to the currently active release
  <release-id>/
    SPEC.md                  — release specification (Status: Draft → Aprovado)
    PLAN.md                  — implementation plan (added after SPEC is approved)
    TASKS.md                 — task checklist with [ ]/[-]/[x] markers
    CLOSURE.md               — closure report (added after all tasks are done)
  legacy/                    — deprecated artifacts migrated from old tree layout
```

## Authoring Rules

- Each release directory is named with a slug matching `^[a-z][a-z0-9-]+$`.
- Release directories are created with `dadaia release new <id>` — do NOT create them
  manually to ensure canonical SPEC.md frontmatter.
- SDD lifecycle order: `SPEC.md` (Status: Draft) → operator approval → `PLAN.md` →
  `TASKS.md` → implementation → `CLOSURE.md`.
- Only one release may be in IMPLEMENTATION phase at a time. The active release is
  declared in `ACTIVE.md`.
- The `ACTIVE.md` format:
  ```
  release: <release-id>
  phase: <DISCOVERY|SPEC|PLAN|TASKS|IMPLEMENTATION|CLOSURE|ARCHIVED>
  ```

## ACTIVE.md Management

`ACTIVE.md` is managed by `product-engineer`. Agents must read it at the start of every
session to resolve the active release before touching any implementation file. When no
release is active, `ACTIVE.md` must contain `release: none`.

## Legacy Directory

The `legacy/` subdirectory is populated by `dadaia migrate tree-v2` when migrating
existing consumer repos from the old layout. Do not create files there manually.
