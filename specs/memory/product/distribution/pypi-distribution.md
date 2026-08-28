---
slug: pypi-distribution
title: pypi-distribution
category: product
tldr: The published PyPI package on one version axis, the OIDC publish pipeline, and the wheel content contract.
summary: '`dadaia-workspace` publishes to PyPI from `.github/workflows/release.yml` under OIDC trusted publishing; `pyproject.toml` `version` is the single source of the number, and minting a number and publishing it are separate acts.'
tags:
- distribution
- pypi
- release
- packaging
---

## Purpose

`pip install dadaia-workspace` installs the library and its `dadaia` CLI.
`pyproject.toml` `version` is the single source of the number, restated in no other file.

Publication is fully automated by `.github/workflows/release.yml` with **OIDC trusted
publishing**: no long-lived PyPI token exists in the repository or its secrets; the `pypi`
GitHub environment carries the trust binding. PyPI descriptions are immutable per release —
a documentation-only fix to the project page requires a version bump.

## Usage flow

1. A version bump lands on `main`.
2. `release.yml` fires on the push. The `check` job compares the pyproject version against
   existing `v*` tags: an existing tag skips every downstream job (idempotent).
3. Five test legs re-run on the release commit: `unit-fast`, `contract-coverage` (80 %
   gate), `integration`, `e2e-python`, `e2e-panel`.
4. `build` produces sdist + wheel and uploads them as a versioned artifact.
5. `approve` blocks on the **`release-gate` GitHub environment** — a human approval before
   anything reaches PyPI.
6. `publish` uploads via `pypa/gh-action-pypi-publish` under the `pypi` environment (OIDC
   `id-token: write`), then creates and pushes the `v<version>` tag.
7. `smoke-test` waits for index propagation, installs the exact version from the live
   index, and runs `dadaia --help` plus a real `dadaia init` in a tmpdir.

## Current behavior

**One version axis, two positions on it.** A release id *is* the version it mints, so
`pyproject.toml`, the release directory and the CHANGELOG section carry the same digits.
`pyproject.toml` on `main` is the newest **minted** number; PyPI shows the newest
**published** one; a `v<version>` tag exists only for published numbers, because the publish
job creates it. Withholding the release-gate approval is a supported outcome: the code still
shipped to `main`, no tag exists, and the number is minted-unpublished.

A minted-unpublished number keeps its CHANGELOG section and its archived release directory,
and is **retired rather than reused**. Publication of an already-minted number stays
available on a later operator order.

Consumer-validation candidates are throwaway wheels and never mint a published version;
numbers advance only at deploy time, on the operator's order.

`CHANGELOG.md` carries one `## [x.y.z]` section per published version, each traceable to a
`git log` range cited inline, plus annotations on the headings that match no published
version. Sections are never renamed, renumbered or deleted.

**Wheel content contract.** The wheel ships `dadaia_workspace/` with the full `public/`
asset tree, so `dadaia init` works offline from a bare pip install with no network fetch.
It also ships `public/data/CONSUMER_VALIDATION_RECIPE.md`, the consumer-side validation
matrix a validator runs against every candidate wheel before deploy
([[consumer-agent-support]]). `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes workspace-venv
bootstraps install a candidate instead of pinning from PyPI.

## Runtime state touched

- `pyproject.toml` — `version` and the PyPI OS classifiers.
- `CHANGELOG.md` — one section per published version.
- `.github/workflows/release.yml` — the release pipeline.
- GitHub environments `release-gate` (human approval) and `pypi` (OIDC binding).
- Git tags `v<version>`, created by the publish job.

## Dependencies

[[quality-assurance]] (the test legs the pipeline re-runs),
[[public-asset-distribution]] (the asset tree the wheel carries),
[[cross-platform-portability]] (the OS classifiers the 3-OS matrix backs).
