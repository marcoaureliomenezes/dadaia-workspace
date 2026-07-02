---
name: panel-memory-view-unreachable-and-incomplete
status: Closed
severity: HIGH
session_id: sess_4f3a2384
reported: 2026-06-11
resolved_in: v0.1.13
surface: panel Projects tab memory feed (views/index.py chips, views/memory.py root, handler route classes)
---

**Symptom:** Project memory in the Projects tab has NEVER been viewable from the
browser, in any panel version. Clicking any memory chip (Architecture / Tech
Stack / Product) renders a raw `{"error": "unauthorized"}` page. Additionally the
chip set itself is wrong: `quality-assurance.md` (present in every spec context's
`specs/memory/`) is not linked at all, and `constitution.md` — the main file of a
project, at `specs/constitution.md` — is not exposed anywhere in the panel.

**Root causes:**
1. `/memory-view/<slug>/<path>` is `BEARER_SECOND_LOOP` (Authorization header
   required) but the chips are plain `<a href>` full-page navigations — a browser
   navigation can never carry a Bearer header, and (since v0.1.11) the session
   cookie that does ride along is never read by the server. Unreachable by
   construction in every version.
2. `views/index.py:247-249` hardcodes exactly three chips
   (architecture.md / tech-stack.md / product/index.md). `quality-assurance.md`
   exists in all 6 live contexts and is omitted.
3. `views/memory.py` resolves only under `repos/<slug>/specs/memory/`;
   `constitution.md` lives one level up (`repos/<slug>/specs/constitution.md`)
   and is unservable through the current root + traversal guard.

**Repro:** open panel (authenticated launch) → Projects → any project →
"Architecture" → raw unauthorized JSON. Grep `views/index.py` for
`quality-assurance`/`constitution` → zero hits.

**Expected:** memory views render for an authenticated browser session (depends
on the cookie-auth fix in `panel-cookie-auth-theater-browser-apis-unreachable`);
the chip set covers Architecture, Tech Stack, Quality Assurance, Product, and
Constitution; constitution served through an explicit, traversal-guarded
extension of the memory root (allowlisted single file, not a blanket `specs/`
exposure).

**Notes:** operator-reported during live panel review 2026-06-11; confirmed in
code and live with Playwright. No operator-local data in this record.
