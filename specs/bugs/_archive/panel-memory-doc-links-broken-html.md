---
title: panel-memory-doc-links-broken-html
severity: Critical
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-memory-doc-links-broken-html

## Description

On the **first/default panel tab (Spec Context Projects)**, every memory
document link on every project card is **broken**. Clicking *Architecture*,
*Tech Stack*, or *Product* opens an empty/broken viewer.

The memory chips are generated with a stale `.html` extension that points at
files which **no longer exist** in the dadaia-workspace architecture — memory
atoms were migrated from `.html` to `.md` source (`memory-markdown-source-v1`),
but the panel link generator and the memory-view iframe were never updated.

This shipped in **PyPI 0.1.5** (confirmed against the published wheel) and
affects every real workspace that has at least one Spec Context Project with
memory atoms.

## Steps to reproduce

1. Run `dadaia panel` in a workspace that has at least one alive Spec Context
   Project (e.g. this workspace).
2. Open the panel → default *Spec Context Projects* tab.
3. Click *Architecture* (or *Tech Stack* / *Product*) on any project card.
4. **Expected:** the memory document renders in the viewer.
   **Actual:** the wrapper page loads (200) but its `<iframe>` requests
   `/memory/<slug>/architecture.html` → **404**, so the viewer is empty/broken.

Direct evidence (live):
- `GET /memory/dadaia-workspace/architecture.html` → **404**
- `GET /memory/dadaia-workspace/architecture.md`   → **200**

## Environment

- dadaia version: 0.1.5 (published wheel + current `main`)
- OS: Linux
- Python: 3.12

## Root cause

Stale `.html` extension from the markdown migration, in three+ uncoordinated
call sites:

- `dadaia_workspace/features/panel/views/index.py:231-233` — chip hrefs use
  `architecture.html` / `tech-stack.html` / `product/index.html`.
- `dadaia_workspace/features/panel/views/wrapper.py:36,86` — the `/memory-view/`
  wrapper sets `<iframe src="/memory/{slug}/{path}">` with the `.html` path
  forwarded verbatim.
- The raw `/memory/<slug>/<path>` route (`views/memory.py`) only resolves the
  on-disk `.md` atom; a `.html` request 404s.

Deeper root cause: there is **no single canonical memory-URL builder** — four
independent sites encode the URL shape, so the migration updated some and not
others. See related bug `panel-no-canonical-memory-url-builder` /
`panel-wikilink-slug-hardcoded`.

## Why the test suite missed it

`tests/e2e/panel/spec-context-tab.spec.ts:29-37` asserts the chips **exist with
the correct text labels** — it never clicks them, never loads the document,
never checks for a failed response. A 404-ing iframe does not fail page
navigation, so the test is green while the feature is dead. No panel spec has a
global "fail on any 4xx/5xx" guard across tab interactions, and CI bootstraps a
workspace with **no spec context** (no cards → nothing to click), so the broken
path is never exercised.

## Fix direction

1. Generate `.md` links (or make `/memory/` transparently map `.html`→`.md`).
2. Introduce a single canonical memory-URL builder used by the chip generator,
   the wrapper iframe, and the wikilink renderer.
3. Add regression tests that click each chip and assert the iframe content
   returns 200 with real body, plus a global zero-tolerance 4xx/5xx + console
   guard across a full tab tour (E2E-SCP-03/04/05/06, E2E-GUARD-01/02).
4. Seed the CI panel workspace with a real context so data-dependent paths run;
   the `e2e-panel` job already gates `build→publish` — give it teeth.
