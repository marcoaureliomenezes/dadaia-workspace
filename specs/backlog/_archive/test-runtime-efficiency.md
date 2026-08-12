---
title: "Test runtime efficiency — CI long-pole and local xdist tail"
status: consumed
consumed_by: bug test-suite-real-venv-and-ci-longpole (operator ruling 2026-08-12 — badly built tests are bugs, fixed on the spot, no release)
opened: 2026-08-11
description: >-
  CI wall avg 222 s is healthy; levers: contract-coverage is the only pytest job
  without -n auto and is the CI long pole (windows 2:55); e2e-panel reinstalls
  Chromium every run; two outlier tests block the local xdist tail (measured via
  --durations=40, host-loaded upper bound 9:38 for the quick suite).
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#CI
    change: >-
      .github/workflows/ci.yml — add -n auto to the contract-coverage matrix jobs
      (the only pytest job without it; CI long pole, windows 2:55; estimate −40–60%
      job / −20–30% CI wall). Also ci.yml:299-301 + release.yml:120-122 — e2e-panel
      reinstalls Chromium every run; add actions/cache for ~/.cache/ms-playwright
      keyed on the @playwright/test version (estimate −15–20 s/run × 2 workflows).
  - subject:
      kind: code
      ref: tests/integration/test_cli_export.py#test_export_list_create_archive_excluding_mnt_and_import_round_trip
    change: >-
      242 s round-trip outlier blocks the local xdist tail — split/parametrize or
      loadgroup-first scheduling. Estimate (with the scaffold outlier): −15–30%
      local quick suite.
  - subject:
      kind: code
      ref: tests/contract/test_claude_scaffold_is_loadable.py#projected
    change: >-
      159 s setup fixture outlier blocks the local xdist tail — split/parametrize
      or loadgroup-first scheduling (same lever as the export round-trip outlier).
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Browser Validation
    change: >-
      tests/e2e/panel/playwright.config.ts — workers>1 with the 2 shared-state spec
      files isolated serial; bounded waits instead of networkidle; webServer.timeout
      30→60 s validity fix. tmpfs TMPDIR is a further −10–20% lever (low confidence,
      measure first).
---

# Test runtime efficiency — CI long-pole and local xdist tail

## Description

CI wall avg 222 s is healthy; levers: contract-coverage is the ONLY pytest job without
`-n auto` and is the CI long pole (windows 2:55); e2e-panel reinstalls Chromium every
run (no actions/cache of `~/.cache/ms-playwright` — ci.yml:299-301,
release.yml:120-122); two outlier tests (242 s test_cli_export round-trip; 159 s setup
in test_claude_scaffold_is_loadable) block the local xdist tail (measured via
`--durations=40`, host-loaded upper bound 9:38 for the quick suite).

## Motivation

Estimates: contract-coverage −40–60% job / −20–30% CI wall; browser cache −15–20 s/run
× 2 workflows; outlier split −15–30% local quick suite; tmpfs TMPDIR −10–20% (low
confidence, measure first).

## Evidence

- Report: `.dadaia/reports/tauan-games/qa-engineer/2026-08-11T180616Z-test-runtime-efficiency-both-repos.html`
- Handoff: `.dadaia/handoff/tauan-games/2026-08-11T180616Z-qa-engineer-test-runtime-efficiency-both-repos.handoff.json`

## Acceptance criteria

Before/after timing against the baseline report; no test removed.

## Disposition (2026-08-12, bug test-suite-real-venv-and-ci-longpole)

Root cause found beneath both outliers: the suite's no-real-venv backstop
(`_no_real_venv_in_tests`) was function-scoped and in-process only, so real venvs were
still built (a) inside any fixture scoped above `function` (the 159 s scaffold fixture)
and (b) inside the `dadaia init` subprocess spawned by `ImportService.bootstrap` (the
242 s export round-trip) and by `run-panel-e2e-server.sh` (which also made the panel
webServer blow its own 30 s timeout locally). Fixes, all measured unloaded:

- conftest backstop session-scoped + `dadaia init` subprocess intercepted in-process:
  export round-trip 19.9 s → 0.6 s; scaffold fixture setup 17.4 s → 0.3 s; guarded by
  `tests/unit/test_no_real_venv_backstop.py` and an assertion in the round-trip test.
- ci.yml + release.yml contract-coverage jobs: `-n auto` added (was the only pytest job
  without xdist).
- ci.yml + release.yml e2e-panel: `~/.cache/ms-playwright` cached keyed on the resolved
  `@playwright/test` version; system deps still install on cache hit.
- `run-panel-e2e-server.sh` pre-seeds a stub workspace venv (~20 s off the bootstrap);
  `webServer.timeout` 30 s → 60 s (validity fix — bootstrap measured 44 s pre-fix, the
  suite could not even start locally).
- `playwright.config.ts`: workers 1 → 2 (CI) / 4 (local), files parallel; the two
  mutating specs (`agent-policy`, `spec-context-operation-journey`) isolated serial via
  dependent single-file projects. The one UNbounded `networkidle` (tab-navigation
  E2E-TAB-05) is now bounded; the remaining `networkidle` waits were measured NOT to
  burn their timeouts (full guard tour 3.9 s + 2.3 s) and were left alone.
- tmpfs TMPDIR lever: not taken (low confidence, unmeasured — as the entry itself said).

Quick suite after: 2031 passed in 2:38 wall (`-n auto`, host-loaded), xdist tail item
now 16 s. No test removed; the journey spec still skips locally by design.
