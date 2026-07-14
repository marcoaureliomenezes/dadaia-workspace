---
slug: quality-assurance
title: quality-assurance
category: core
tldr: Layered pytest/contract/browser validation, strict CI, live-worker opt-ins, and zero repo-local test artifacts.
summary: >-
  Defines test layers, safety fixtures, workflow validation, browser evidence, CI gates,
  coverage, cross-platform checks, and anti-slop requirements.
tags:
- testing
- pytest
- ci
- quality
- test-architecture
token_estimate: 460
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

Tests prove public behavior and failure handling at the cheapest reliable layer. The
suite must be hermetic by default and must never invoke a paid/live worker without an
explicit opt-in.

## Layers

| Layer | Scope |
|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes. |
| Contract | Public API/schema, architecture, security, projection, and invariant checks. |
| Integration | CLI plus real temporary filesystem/state and composed services. |
| E2E | Complete Python journeys and browser-backed panel behavior. |
| Live opt-in | Explicit Codex/PI binary and provider validation outside default CI. |

`tests/conftest.py` blocks accidental real PI/Codex invocation unless the corresponding
live flag is set. Temporary workspaces use pytest `tmp_path` or workspace `.dadaia/tmp/`;
they never bootstrap the source repo as a consumer workspace.

## Workflow Validation

Each of the four dadaia-workflows has deterministic fake-worker coverage and real
phantom journeys through Codex and PI. Tests assert step order, fragment/persona
injection, provider/model resolution, immutable attempt payloads, exact dependency
consumption, rejection/retry behavior, task-marker closure gating, diagnostics, and
terminal state.

Live PI GPT validation must use provider-qualified `openai-codex/...` profiles when the
campaign is intended to use the Codex subscription. Optional OpenRouter profiles require
an explicit operator choice and are never selected implicitly.

## Browser Validation

Panel changes are checked through unit DOM/static-asset contracts and Chromium journeys.
Responsive features are exercised at desktop and mobile viewports. Canvas features
require nonblank pixel evidence and a state/pixel change after real keyboard or touch
input. Screenshots and Playwright outputs go outside the repository.

## CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with
80% coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E,
repository hygiene, backlog doctor, branch/PR governance, and security verdict jobs.
Release publication repeats the relevant quality ladder before build, approval, publish,
and package smoke test.

## Anti-Slop

pytest uses `-p no:cacheprovider`; mypy incremental state is disabled; Ruff, coverage,
and Playwright outputs are redirected. Forbidden repo-local artifacts include
`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `.coverage`,
`coverage/`, `test-results/`, `playwright-report/`, `.venv/`, and `.dadaia/`.

## Dependencies

[[tech-stack]], [[architecture]], [[dadaia-workflows]], [[panel]].
