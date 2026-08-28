---
slug: pypi-distribution
title: pypi-distribution
category: product
tldr: The published PyPI package on one version axis, the OIDC publish pipeline, and the wheel content contract.
summary: dadaia-workspace publishes to PyPI from the release workflow under OIDC trusted publishing; pyproject version is the single source of the number, and minting is separate from publishing.
tags: [distribution, pypi, release, packaging]
---

## Pipeline

- `pip install dadaia-workspace` installs the library and its `dadaia` CLI, and `pyproject.toml` `version` is the single source of the number, restated in no other file.
- Publication is automated by `.github/workflows/release.yml` under OIDC trusted publishing: no long-lived PyPI token exists, and the `pypi` GitHub environment carries the trust binding.
- A version bump landing on `main` fires the workflow: `check` (an existing `v*` tag skips everything downstream), five test legs, `build`, `approve` (blocking on the `release-gate` environment), `publish` (upload, then push the `v<version>` tag) and `smoke-test` against the live index.

## One version axis, two positions

- A release id is the version it mints, so `pyproject.toml`, the release directory and the CHANGELOG section carry the same digits.
- `pyproject.toml` on `main` is the newest minted number and PyPI the newest published one; a `v<version>` tag exists only for published numbers, because the publish job creates it.
- Withholding release-gate approval is supported: the code shipped, no tag exists, and the minted-unpublished number keeps its CHANGELOG section and archived directory, retired rather than reused.
- Consumer-validation candidates are throwaway wheels and never mint a published version; numbers advance only at deploy, on the operator's order.
- `CHANGELOG.md` carries one `## [x.y.z]` section per published version, each citing a `git log` range, never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` works offline from a bare pip install ([[public-asset-distribution]]).
- It also ships `CONSUMER_VALIDATION_RECIPE.md`, the matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes a venv bootstrap install a candidate instead of pinning from PyPI.

## Dependencies

[[quality-assurance]], [[public-asset-distribution]], [[cross-platform-portability]].
