---
slug: pypi-distribution
title: pypi-distribution
category: product
tldr: The published dadaia-workspace 0.2.x PyPI package, the release.yml OIDC publish pipeline, the wheel content contract, and the SDD-vs-package version split.
summary: >-
  Owns PyPI distribution as product behavior — the live `dadaia-workspace` 0.2.x
  package (PyPI since PRs #112/#113, ratified v0.1.61), the `.github/workflows/release.yml`
  pipeline (version-vs-tag check → five test legs → build → release-gate approval →
  OIDC trusted publishing + tag → post-publish smoke), the wheel content contract
  (plugin packs and public assets ship in-package), and the documented version-scheme
  split: SDD releases `v0.1.x` version the SDD process while the package `0.2.x`
  versions the shipped library (ADR-2 — documented, never renumbered).
tags:
- distribution
- pypi
- release
- packaging
token_estimate: 800
last_updated: '2026-07-16'
release_origin: v0.2.5
---

## Purpose

`dadaia-workspace` is a published PyPI package: `pip install dadaia-workspace`
installs the library and its `dadaia` CLI. The last PUBLISHED version is
`0.2.2`; the next deploy version is `0.3.0` (`pyproject.toml` `version` is the single
source). Consumer-validation candidates are throwaway wheels — they NEVER mint
intermediate published versions; version numbers advance only at deploy time, on the
operator's order. PyPI descriptions are immutable per release: a
documentation-only fix to the project page requires a version bump, never an
in-place edit.

Publication is fully automated by `.github/workflows/release.yml` with **OIDC
trusted publishing** — no long-lived PyPI token exists in the repository or its
secrets; the `pypi` GitHub environment carries the trust binding.

## Usage flow

1. A version bump lands on `main` (`pyproject.toml` `version = "0.2.x"` — an
   operational-change-lane commit or a release merge).
2. `release.yml` fires on the `main` push. The `check` job compares the pyproject
   version against existing `v*` tags: tag exists ⇒ every downstream job skips
   (idempotent); new version ⇒ the pipeline proceeds.
3. Five test legs re-run on the release commit: `unit-fast`, `contract-coverage`
   (80% gate), `integration`, `e2e-python`, `e2e-panel` (Playwright against a
   bootstrapped panel workspace).
4. `build` produces sdist + wheel (`poetry build`) and uploads them as a
   versioned artifact.
5. `approve` blocks on the **`release-gate` GitHub environment** — a human
   approval step before anything reaches PyPI.
6. `publish` downloads the built artifact, publishes via
   `pypa/gh-action-pypi-publish` under the `pypi` environment (OIDC
   `id-token: write`), then creates and pushes the `v<version>` git tag.
7. `smoke-test` (ubuntu/py3.12) waits for PyPI propagation, `pip install
   dadaia-workspace==<version>` from the live index, runs `dadaia --help` and a
   real `dadaia init` in a tmpdir, asserting the state file exists. (The PyPI
   JSON index can lag the CDN right after publish — the smoke waits, then
   installs by exact version.)

## Typical trigger

The operator orders a package release (version bump on `main`), or an agent needs
to know how the shipped library reaches consumers and which version scheme a
number refers to.

## Differentiator

**Version-scheme split (ADR-2, documented — never renumbered):** SDD release ids
`v0.1.x` version the **SDD process** of this repository (specs, releases,
archive continuity); the package version `0.2.x` versions the **shipped
library** on PyPI. The two advance independently and both are correct in their
own domain. Renumbering SDD releases to match the package would falsify archived
history and break tag/PR continuity for zero information gain. When reading any
`v`-prefixed id in `specs/`, it is an SDD release; a bare `0.2.x` is the package.

**Wheel content contract:** the wheel ships the complete runtime product —
`dadaia_workspace/` with the full `public/` asset tree (agents, skills, rules,
workflows, scripts, schemas, templates, data, scaffold, runtime, personas,
lifecycle_fragments, pi) **including the in-package plugin packs**
(`public/plugins/{frontend-design,devops}/` — verified at the v0.1.60 audit), so
`dadaia init` and `dadaia plugin install` work offline from a bare pip install
with no network fetch of assets. The wheel also ships
`public/data/CONSUMER_VALIDATION_RECIPE.md` — the canonical consumer-side
validation matrix (statements F-01..F-23, verdict APROVADA / BLOQUEADA /
APROVADA COM EXCEÇÃO EXPLÍCITA) that a consumer-side validator runs against
EVERY candidate wheel before deploy; internal gates (`certify` included) never
approve a deploy by themselves. `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes
workspace-venv bootstraps install the candidate itself instead of pinning the
(possibly unpublished) version from PyPI.

## Runtime state touched

- `pyproject.toml` — `version` (single source of the package version) and the
  PyPI classifiers (`POSIX :: Linux + MacOS + Microsoft :: Windows`).
- `.github/workflows/release.yml` — the release pipeline (inventoried in
  [[quality-assurance]]).
- GitHub environments `release-gate` (human approval) and `pypi` (OIDC trusted
  publishing binding).
- Git tags `v<package-version>` — created by the publish job after a successful
  upload.

## Dependencies

- [[quality-assurance]] — the five test legs the pipeline re-runs, and the CI
  workflow inventory row for `release.yml`.
- [[public-asset-distribution]] — the `public/` asset tree the wheel carries.
- [[plugin-packs]] — the in-package packs whose wheel presence this contract pins.
- [[cross-platform-portability]] — the PyPI OS classifiers the 3-OS CI matrix backs.
