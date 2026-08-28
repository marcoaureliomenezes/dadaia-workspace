---
slug: academy
title: academy
category: product
tldr: Packaged knowledge-base modules browsable in the panel's Academy tab, with a copy-from-template CLI for derived courses.
summary: The panel's Academy tab browses the shipped knowledge_basis modules directly, while the academy CLI manages copies derived from them under the workspace state tree.
tags: [academy, onboarding, courses]
---

## Surfaces

- The panel's Academy tab lists every module shipped in `features/academy/knowledge_basis/` via `GET /api/academy`, and no CLI call is a precondition for content.
- A lesson renders through the read-only route `GET /academy/<module>/<lesson>`, traversal-guarded by a single-segment check plus `Path.resolve()` and `is_relative_to`.
- `dadaia academy create "<name>" --module <n>` copies a knowledge-base module to `.dadaia/academy/<slug>/`, registered in `academy.json`; `modules`, `list`, `update` and `delete` manage those derived courses.
- Shipped modules are `00_dadaia_workspace`, `01_spec_driven_development`, `03_multi_agents`, `06_claude_code` and `07_codex`, each a README plus numbered lessons rendered by the panel's Markdown renderer.
- The `knowledge_basis/` tree is read-only packaged source, and `.dadaia/academy/academy.json` indexes the derived courses beside their directories.

## Dependencies

[[workspace-init]] creates `academy.json`; [[panel]] injects `AcademyService` optionally and serves the tab.
