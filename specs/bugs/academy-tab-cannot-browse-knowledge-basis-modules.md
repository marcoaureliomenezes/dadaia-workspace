---
name: academy-tab-cannot-browse-knowledge-basis-modules
status: Closed
severity: HIGH
session_id: null
reported: 2026-06-11
surface: panel Academy tab (/api/academy + academy.js + lesson serving)
---

**Symptom:** In the live panel, the Academy tab does not teach. It shows at most a
single "Module 7" card (or none), and clicking a card opens nothing — no lessons, no
content. The tab is effectively dead.

**Repro:**
1. `dadaia panel`, open the Academy tab.
2. Observe: only the modules previously created via `dadaia academy create` appear
   (often exactly one, e.g. a copy of module 07), never the seven shipped
   `knowledge_basis` modules.
3. Click a card → `renderDetail` shows only static metadata (module number, name,
   created_at). There is no lesson list and no lesson content.

**Expected:** The Academy tab browses the shipped course content
(`dadaia_workspace/features/academy/knowledge_basis/`): all modules with titles and
lesson counts, expand a module to its lessons, click a lesson to read its rendered
Markdown in the panel.

**Root cause:**
- `GET /api/academy` (`views/api.py::render_api_academy`) returns
  `AcademyService.list_all()` — i.e. `CourseStore` records, which are *user-created
  course copies* produced by `dadaia academy create`, NOT the `knowledge_basis`
  modules. With no/one course created, the tab is empty / shows one stale module.
- `assets/js/academy.js::renderDetail` renders only course metadata; there is no
  lesson-serving route, so no lesson Markdown is ever fetched or shown.

**Fix (this wave):** repoint `/api/academy` at the knowledge_basis module catalog
(modules + lesson lists), add a read-only path-traversal-guarded
`GET /academy/<module>/<lesson>` route that renders the lesson `.md` to HTML via the
existing `views/_md_render.py` seam, and rewrite `academy.js` to browse
modules → lessons → rendered lesson.

**Notes:** Surfaced by operator live panel review. The shipped content (7 modules,
3-5 lessons each) was always present; only the panel wiring read the wrong source.


**Resolution (2026-06-11, same-day fix):** academy module/lesson browsing + in-panel rendered lessons (views/academy.py, academy.js, traversal-guarded lesson route); verified live in browser + unit suites green.
