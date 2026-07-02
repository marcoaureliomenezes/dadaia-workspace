---
title: panel-theme-switcher-broken-ugly
severity: High
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-theme-switcher-broken-ugly

## Description

The bottom theme switcher is visually poor and does not work. Operator report
(2026-06-07): "The ugly bottom Theme. very ugly, don't work, must be totally
improved." Corroborated by a headless-browser probe: clicking the theme control
produced no theme options and `document.documentElement.dataset.theme` did not
change (no console errors — it silently does nothing).

## Steps to reproduce

1. Open the panel.
2. Click the theme switcher (bottom of the page).
3. **Expected:** theme options appear; selecting one applies and persists the
   theme.
   **Actual:** no functional change observed; no theme applied.

## Environment

- dadaia version: 0.1.5 + current `main`
- Probe: Chromium headless against `dadaia panel` on 127.0.0.1.

## Notes

- Existing theme e2e (`tests/e2e/panel/theme-switcher.spec.ts`) is reported as
  "thorough" yet the operator sees it not working — re-verify the test exercises
  the real shipped control and isn't asserting against mocked/synthetic state
  (cross-reference [[panel-e2e-shallow-coverage-no-deploy-gate]]).
- Two scopes: (a) **functional** — make selection apply + persist; (b) **visual
  redesign** — "totally improved" is a UX/design task (panel UI surface; per the
  `plugin-scope` rule this is frontend-design plugin territory).

## Fix direction

Diagnose `dadaia_workspace/features/panel/views/assets/js/themes.js` +
`themes` CSS; confirm the control markup, option rendering, apply + localStorage
persistence path. Pair functional fix with a deep-interaction regression test
(click → option visible → theme dataset changes → persists across reload).
Visual redesign tracked alongside the tab-merge UX work.
