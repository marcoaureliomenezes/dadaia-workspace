---
title: panel-e2e-shallow-coverage-no-deploy-gate
severity: High
opened: 2026-06-07
session_id: null
status: Closed
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-e2e-shallow-coverage-no-deploy-gate

## Description

The panel e2e suite passed green while a critical first-tab feature (memory
document viewer) was completely broken in 0.1.5
([[panel-memory-doc-links-broken-html]]). The tests are label-deep and there is
no deploy gate with teeth. This is the meta-defect: the test strategy cannot
catch broken panel features, so broken panels ship.

## Three stacked blind spots

1. **Label-deep assertions.** `tests/e2e/panel/spec-context-tab.spec.ts:29-37`
   asserts the memory chips *exist with the right text labels* — it never clicks
   them, never loads the document, never checks for a failed response.
2. **No global failed-response guard.** The only "no-4xx" check
   (`tab-navigation.spec.ts`) watches the *initial page load only*, not
   tab/chip interactions. A 404 fired by a tab click or an iframe is invisible.
3. **Fresh-workspace blindness.** CI (`.github/workflows/{ci,release}.yml`
   e2e-panel job) bootstraps a workspace with **no spec context**, so there are
   no project cards and the broken memory path is never exercised.

## Impact

A broken iframe does not fail page navigation, so `page.goto`-style assertions
stay green. Combined with the fresh-workspace fixture, no data-dependent panel
path is covered. Result: broken panel features pass CI and ship to PyPI.

## Environment

- dadaia version: 0.1.5 + current `main`

## Fix direction

- Add deep-interaction regression tests: click each memory chip and assert the
  iframe content returns 200 with real body (E2E-SCP-03/04/05), plus a memory
  API contract test (E2E-SCP-06).
- Add a **global zero-tolerance guard** (E2E-GUARD-01/02): fail the run on ANY
  4xx/5xx response or console error during a full tab tour + key interactions.
- Seed the CI panel workspace with a real spec context (memory atoms) so
  data-dependent paths run.
- The `e2e-panel` job already gates `build → publish` in `release.yml`; with the
  guard in place it actually blocks broken panels. Optionally extend the
  post-publish smoke test to hit a memory endpoint.
