---
title: "Test artifact hygiene — panel E2E writes artifacts no one ever consumes"
status: consumed
consumed_by: bug panel-e2e-artifacts-no-consumer (operator ruling 2026-08-12 — badly built tests are bugs, fixed on the spot, no release)
opened: 2026-08-11
description: >-
  The panel E2E suite writes artifacts with no consumer: 6 unconditional
  success-path full-page screenshots accumulate locally and are never uploaded in
  CI; the Playwright HTML report is written to the runner tmpdir and discarded
  every CI run, even on failure. Artifacts that will never be consumed must not be
  written; artifacts useful on failure must actually be uploaded.
intents:
  - subject:
      kind: catalog
      ref: panel
    change: >-
      Panel E2E artifact hygiene — (1) tests/e2e/panel/*.spec.ts: remove the 6
      unconditional success-path full-page screenshots
      (spec-context-tab.spec.ts:41, tab-navigation.spec.ts:42,
      theme-switcher.spec.ts:56/85/112/133) or gate them behind an env flag with a
      documented consumer; (2) .github/workflows/ci.yml + release.yml e2e-panel
      jobs: add upload-artifact on failure for report+screenshots, OR set reporter
      to line-only in CI — today neither job uploads the Playwright HTML report
      even on failure, so failure evidence is paid for and thrown away; (3)
      tests/e2e/panel/playwright.config.ts: retention policy for local outputs so
      screenshots/reports do not accumulate indefinitely.
---

# Test artifact hygiene — panel E2E writes artifacts no one ever consumes

## Description

The panel E2E suite writes artifacts with NO consumer: 6 unconditional success-path
full-page screenshots (spec-context-tab.spec.ts:41, tab-navigation.spec.ts:42,
theme-switcher.spec.ts:56/85/112/133) landing in `tests/e2e/panel/screenshots/`
(gitignored, accumulating locally, never uploaded in CI — pure write cost); the
Playwright HTML report is written to the runner tmpdir and discarded every CI run
(neither job uploads it, even on failure — ci.yml e2e-panel and release.yml e2e-panel
have no upload-artifact step), so failure evidence is paid for and thrown away.

## Motivation

Operator ruling: artifacts that will never be consumed must not be written; artifacts
that would be useful on failure must actually be uploaded.

## Evidence

- Report: `.dadaia/reports/tauan-games/qa-engineer/2026-08-11T180616Z-test-runtime-efficiency-both-repos.html`
- Handoff: `.dadaia/handoff/tauan-games/2026-08-11T180616Z-qa-engineer-test-runtime-efficiency-both-repos.handoff.json`

## Acceptance criteria

A green local run leaves zero new files outside the gitignored output dir; a red CI run
yields downloadable failure evidence; a green CI run writes no report that is discarded.
