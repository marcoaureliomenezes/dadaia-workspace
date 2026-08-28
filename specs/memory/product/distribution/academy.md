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

## Surfaces

Internal course system for onboarding and study, with two surfaces. **Browsing the knowledge base**
is primary: the panel's Academy tab lists every module shipped in
`dadaia_workspace/features/academy/knowledge_basis/` via `GET /api/academy`, and a lesson renders
through the read-only route `GET /academy/<module>/<lesson>`, traversal-guarded by a single-segment
check plus `Path.resolve()` and `is_relative_to`. No CLI call is a precondition for content.
**Copy-from-template management** is the CLI half: `dadaia academy create "<name>" --module <n>`
copies a knowledge-base module to `.dadaia/academy/<slug>/`, registered in `academy.json`, and
`modules`, `list`, `update` and `delete` manage those derived courses.

Shipped modules: `00_dadaia_workspace`, `01_spec_driven_development`, `03_multi_agents`,
`06_claude_code`, `07_codex` — each a README plus numbered lessons, rendered through the panel's
Markdown renderer. The `knowledge_basis/` tree itself is read-only packaged source;
`.dadaia/academy/academy.json` indexes the derived courses beside their directories.

## Dependencies

[[workspace-init]] creates `academy.json`; [[panel]] injects `AcademyService` optionally at its
composition root and serves the tab.
