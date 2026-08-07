---
slug: quality-assurance
title: quality-assurance
category: core
tldr: Layered pytest/contract/browser validation, strict CI, consumer-side release gate, and zero repo-local test artifacts.
summary: >-
  Defines test layers, safety fixtures, browser evidence, CI gates, coverage,
  cross-platform checks, the consumer-side approval boundary, and anti-slop requirements.
tags:
- testing
- pytest
- ci
- quality
- test-architecture
token_estimate: 520
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

Tests prove public behavior and failure handling at the cheapest reliable layer. The
suite must be hermetic by default and must never invoke a paid/live binary without an
explicit opt-in.

## Layers

| Layer | Scope |
|---|---|
| Unit | Pure behavior, validators, rendering, adapters with fakes. |
| Contract | Public API/schema, architecture, security, projection, and invariant checks. |
| Integration | CLI plus real temporary filesystem/state and composed services. |
| E2E | Complete Python journeys and browser-backed panel behavior. |
| Live opt-in | Explicit Codex/PI binary validation outside default CI. |

`tests/conftest.py` carries two autouse safety backstops: it blocks accidental real
PI/Codex invocation unless the corresponding live flag is set
(`DADAIA_E2E_REAL_WORKER` / `DADAIA_PI_LIVE` / `DADAIA_CODEX_LIVE` /
`DADAIA_CLAUDE_LIVE`), and it fakes `ensure_workspace_venv` so no test ever builds a
real venv (disk/time protection). Temporary workspaces use pytest `tmp_path` or
workspace `.dadaia/tmp/`; they never bootstrap the source repo as a consumer
workspace. The suite is ~2,100 collected tests, green-serial in a few minutes.

## Root Cause, Always

A defect is reproduced on the executed path, pinned by a test that fails for the real
reason, fixed at the causal site, and proven green. Workarounds and symptom patches are
not acceptable outcomes. The recurrence evidence is unambiguous: structural fixes that
**delete** surface stay quiet, while additive fixes reproduce the next defect in the same
family within a day. Removal is the preferred remedy; an additive-only fix carries an
explicit justification of why removal was impossible.

## Browser Validation

Panel changes are checked through unit DOM/static-asset contracts and Chromium journeys.
Responsive checks currently run at desktop widths (1024/1440) only — no mobile viewport
is exercised yet. Canvas games are asserted as DOM contracts in unit tests; the
nonblank-pixel-after-input journey is a normative requirement for new canvas work, not
yet enforced by an existing Playwright test. Screenshots and Playwright outputs go
outside the repository.

## CI

CI runs importability, Ruff format/lint, import-linter, mypy strict, unit, contract with
80% coverage, Windows/macOS cross-platform subsets, integration, Python E2E, panel E2E,
repository hygiene, backlog doctor, branch/PR governance, security verdict, and a
gitleaks secret-scan job on every push/PR. Release publication repeats the relevant
quality ladder before build, approval, publish, and package smoke test.

Internal gates never approve a deploy by themselves: every candidate wheel must pass the
consumer-side validation matrix shipped in the package
(`public/data/CONSUMER_VALIDATION_RECIPE.md`) with an APPROVED verdict from the
operator's consumer-side validator. A green internal gate that diverges from real
consumer behavior is itself a bug.

## Anti-Slop

pytest uses `-p no:cacheprovider`; mypy incremental state is disabled; Ruff, coverage,
and Playwright outputs are redirected. Forbidden repo-local artifacts include
`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `.coverage`,
`coverage/`, `test-results/`, `playwright-report/`, `.venv/`, and `.dadaia/`.

## Dependencies

[[tech-stack]], [[architecture]], [[panel]], [[consumer-agent-support]].
