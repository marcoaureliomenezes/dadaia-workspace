---
slug: academy
title: academy
category: product
tldr: browsable knowledge_basis in the panel's Academy tab + copy-from-template management via CLI.
summary: the panel's Academy tab browses the knowledge_basis modules directly
  (GET /api/academy lists all modules with titles and lesson counts; the read-only
  traversal-guarded route GET /academy/<module>/<lesson> renders the lesson in
  Markdown). The copy-from-template CLI (dadaia academy create/update/delete)
  remains the management surface for derived courses.
tags:
- academy
- onboarding
- courses
last_updated: '2026-07-02'
release_origin: v0.1.48
---

CLI surface: `dadaia academy {modules|list|create|update|delete}` · Panel: `Academy` tab at `http://127.0.0.1:4999/#academy` · Closure: dadaia-workspace-panel-r5-v1 · 2026-05-21

## Purpose

Internal course system for onboarding and study, with two surfaces:

1. **Direct knowledge_basis browsing (primary access).** The panel's Academy tab
   (`http://127.0.0.1:4999/#academy`) lists ALL modules shipped in
   `dadaia_workspace/features/academy/knowledge_basis/` via `GET /api/academy`
   (titles + lesson counts). Clicking a module expands its lessons; clicking a
   lesson renders the Markdown in the panel via the read-only route
   `GET /academy/<module>/<lesson>` — traversal-guarded (single-segment +
   `Path.resolve()` + `is_relative_to`). No `dadaia academy create` is a
   precondition for the tab to have content.
2. **Copy-from-template management (CLI).** `dadaia academy create` copies a
   knowledge-basis module to `.dadaia/academy/<slug>/`, registered in the
   `academy.json` index; update/delete manage those derived courses.

The `07_codex` module is a complete English-language course on the Codex runtime
(README + numbered lessons + exercises + example + references), with live-verified
Codex-contract facts annotated by evidence-level.

Useful for accelerating the onboarding of new (human) contributors or producing structured reference material that agents can consult.

## Usage flow

  1. `dadaia panel` → **Academy** tab: `GET /api/academy` lists all knowledge_basis modules with title and lesson count.
  2. Clicking a module expands the lesson list; clicking a lesson loads `GET /academy/<module>/<lesson>` and renders the Markdown inline with the `[← Back to Academy]` breadcrumb.
  3. `dadaia academy modules` — lists the modules available in the knowledge basis (numbered) via CLI.
  4. `dadaia academy create "my-course" --module 1` — copies module 1 to `.dadaia/academy/my-course/` and registers it in `academy.json`.
  5. `dadaia academy list` / `update` / `delete` — management of derived courses via CLI.



## Typical trigger

Onboarding of a new contributor or agent; creation of structured reference material. The operator opens the panel and accesses the Academy tab to browse the available modules without leaving the window.

## Differentiator

Templated learning — accelerates onboarding by offering structured knowledge instead of scattered documentation. Each course is a versionable folder the operator can edit. The integration as a panel tab eliminates the need to leave the control window to consult onboarding content.

## Runtime state touched

  * `dadaia_workspace/features/academy/knowledge_basis/<NN_module>/` — read-only source of the shipped modules (read by `GET /api/academy` for the catalog and by `GET /academy/<module>/<lesson>` for the content; rendered via `views/_md_render.py`).
  * `.dadaia/academy/academy.json` — index of derived courses (read by `AcademyService.list_all()`; written by the `dadaia academy create/update/delete` CLI).
  * `.dadaia/academy/<slug>/` — copy-from-template course directory (copied by the CLI).
  * `GET /api/academy` — lists the knowledge_basis modules (titles + lesson counts).
  * `GET /academy/<module>/<lesson>` — read-only traversal-guarded route (single-segment + resolve + `is_relative_to`) that renders the lesson Markdown.



## Dependencies

  * Depends on [[workspace-init]] (creates `academy.json` and installs modules via `public-asset-distribution`).
  * [[panel]]: `AcademyService` is injected as optional DI in `PanelService(academy=None)` at the composition root of `panel.py`. The panel's Academy tab consumes `GET /api/academy` via `academy.js`, which registers the module via `window.Panel.register('academy', Academy)` and uses `window.authedFetch` and `window.escHtml` (globals from `core.js`; `authedFetch` is a residual name — it is a thin alias of plain `fetch` that sends NO credential, per the panel's no-auth model).
