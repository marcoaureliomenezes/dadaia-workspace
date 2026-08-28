---
slug: academy
title: academy
category: product
tldr: Packaged knowledge-base modules browsable in the panel's Academy tab, with a copy-from-template CLI for derived courses.
summary: The panel's Academy tab browses the shipped `knowledge_basis` modules directly; `dadaia academy create/update/delete` manages copies derived from them under `.dadaia/academy/`.
tags:
- academy
- onboarding
- courses
---

## Purpose

Internal course system for onboarding and study, with two surfaces:

1. **Browsing the knowledge base (primary).** The panel's Academy tab lists every module
   shipped in `dadaia_workspace/features/academy/knowledge_basis/` via `GET /api/academy`
   (title + lesson count). A lesson renders through the read-only route
   `GET /academy/<module>/<lesson>`, traversal-guarded by a single-segment check plus
   `Path.resolve()` and `is_relative_to`. No CLI call is a precondition for content.
2. **Copy-from-template management (CLI).** `dadaia academy create` copies a
   knowledge-base module to `.dadaia/academy/<slug>/`, registered in `academy.json`;
   `list`, `update` and `delete` manage those derived courses.

Shipped modules: `00_dadaia_workspace`, `01_spec_driven_development`, `03_multi_agents`,
`06_claude_code`, `07_codex` — each a README plus numbered lessons.

## Usage flow

1. `dadaia academy modules` lists the knowledge-base modules; the panel tab shows the same
   set.
2. `dadaia academy create "my-course" --module <n>` copies a module and registers it.
3. `dadaia academy {list|update|delete}` manages derived courses.

## Runtime state touched

- `dadaia_workspace/features/academy/knowledge_basis/<NN_module>/` — read-only source,
  rendered through `features/panel/views/_md_render.py`.
- `.dadaia/academy/academy.json` — index of derived courses.
- `.dadaia/academy/<slug>/` — the derived course directory.

## Dependencies

[[workspace-init]] creates `academy.json`; [[panel]] injects `AcademyService` optionally at
its composition root and serves the tab.
