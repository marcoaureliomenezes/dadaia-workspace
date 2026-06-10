---
title: panel-wikilink-slug-hardcoded
severity: High
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-wikilink-slug-hardcoded

## Description

The panel markdown renderer hardcodes the context slug `"dadaia-workspace"` when
building wikilink hrefs. Every `[[...]]` wikilink in **any** Spec Context
Project's memory atom resolves to the `dadaia-workspace` context, not to the
context the atom belongs to. Cross-context memory navigation is silently
misdirected the moment a second context with wikilinks exists.

## Steps to reproduce

1. Have two alive Spec Context Projects, each with memory atoms containing
   `[[other-atom]]` wikilinks.
2. Open the panel → click a memory doc of the *non*-dadaia-workspace context.
3. Click a wikilink inside it.
4. **Expected:** navigates to the target atom within the same context.
   **Actual:** href is `/memory-view/dadaia-workspace/<slug>` regardless of the
   active context.

## Environment

- dadaia version: 0.1.5 + current `main`
- Python: 3.12

## Root cause

`dadaia_workspace/features/panel/views/_md_render.py:85-86` —
`_MEMORY_VIEW_PREFIX` plus a literal `/dadaia-workspace/` in `_render_wikilink`.
The mistune renderer is built as a slug-agnostic singleton, so the active
context slug is never threaded into wikilink construction.

## Fix direction

Parameterize `build_renderer(slug)` and close over the active slug in the
wikilink plugin; cache renderers per slug. Route the href through the same
canonical memory-URL builder used to fix [[panel-memory-doc-links-broken-html]].
Same root cause: no single URL builder.
