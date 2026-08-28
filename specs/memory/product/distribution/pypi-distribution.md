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

## Pipeline

`pip install dadaia-workspace` installs the library and its `dadaia` CLI. `pyproject.toml` `version`
is the single source of the number, restated in no other file. Publication is fully automated by
`.github/workflows/release.yml` under **OIDC trusted publishing**: no long-lived PyPI token exists
in the repository or its secrets, and the `pypi` GitHub environment carries the trust binding. PyPI
descriptions are immutable per release, so a documentation-only fix to the project page requires a
version bump.

A version bump landing on `main` fires the workflow: `check` (an existing `v*` tag skips every
downstream job), five test legs re-run on the release commit, `build`, `approve` (blocking on the
**`release-gate` GitHub environment** for human approval), `publish` (uploading under the `pypi`
environment, then creating and pushing the `v<version>` tag) and `smoke-test` (installing the exact
version from the live index and running `dadaia --help` plus a real `dadaia init` in a tmpdir).

## One version axis, two positions

A release id *is* the version it mints, so `pyproject.toml`, the release directory and the CHANGELOG
section carry the same digits. `pyproject.toml` on `main` is the newest **minted** number; PyPI
shows the newest **published** one; a `v<version>` tag exists only for published numbers, because
the publish job creates it. Withholding the release-gate approval is a supported outcome: the code
still shipped to `main`, no tag exists, and the number is minted-unpublished — it keeps its
CHANGELOG section and archived release directory and is retired rather than reused, though
publication stays available on a later operator order. Consumer-validation candidates are throwaway
wheels and never mint a published version; numbers advance only at deploy time, on the operator's
order. `CHANGELOG.md` carries one `## [x.y.z]` section per published version, each traceable to a
`git log` range cited inline; sections are never renamed, renumbered or deleted.

## Wheel content contract

The wheel ships `dadaia_workspace/` with the full `public/` asset tree, so `dadaia init` works
offline from a bare pip install with no network fetch. It also ships
`public/data/CONSUMER_VALIDATION_RECIPE.md`, the matrix a validator runs against every candidate
wheel before deploy ([[consumer-agent-support]]). `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes
workspace-venv bootstraps install a candidate instead of pinning from PyPI.

## Dependencies

[[quality-assurance]], [[public-asset-distribution]], [[cross-platform-portability]].
