---
slug: pypi-distribution
title: pypi-distribution
tldr: The PyPI package on one version axis, two console-script names, the OIDC pipeline, the wheel contract and the docs site.
summary: dadaia-workspace publishes to PyPI under OIDC trusted publishing from the release-please workflow; release-please owns the version, the CHANGELOG and the tag, and pyproject carries the published floor.
tags: [distribution, pypi, release, packaging]
sources:
  - .github/workflows/**
  - release-please-config.json
  - dadaia_workspace/cli/main.py
  - dadaia_workspace/__main__.py
  - docs/**
---

## Pipeline

- `pip install dadaia-workspace` installs the library and one CLI under two console-script names, `dadaia` and `dadaia-workspace`, so `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` runs without an install (`tests/unit/cli/test_console_scripts.py`).
- `pyproject.toml` `version` and `.release-please-manifest.json` carry the last published number — the floor release-please bumps from, stated nowhere else.
- `.github/workflows/release.yml` runs on every push to `main`: the `release-please` job maintains one release PR proposing the next version from the Conventional Commits since the floor, and merging it writes the CHANGELOG section and creates the tag ([[release-lifecycle]]).
- The publish side runs in the same workflow, every job gated on `release_created`: four test legs (`unit-fast`, `contract-coverage`, `integration`, `e2e-python`), `build`, `approve` (blocking on the `release-gate` environment), `publish` under OIDC trusted publishing with no long-lived token, and `smoke-test` against the live index.

## One version axis, two positions

- `pyproject.toml` and the manifest hold the published floor; the release PR holds the number proposed next; nothing else states a version.
- A `v<version>` tag exists only for numbers release-please released; withholding the `release-gate` approval leaves the tag and CHANGELOG section without an upload, and the number is never reused.
- Consumer-validation candidate wheels are throwaway and never mint a published version.
- `CHANGELOG.md` is written by release-please; a hand-written legacy section is never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` works offline from a bare install ([[public-asset-distribution]]).
- It ships `dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md`, the matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes a venv bootstrap install a candidate wheel instead of the PyPI release.

## Discovery surfaces

- `pyproject.toml` `description` is the tagline, byte-equal to `README.md`'s first non-badge paragraph and to `llms.txt`'s `> ` line; `readme = "README.md"` makes the derived README the long description; `[tool.poetry.urls]` carries `Homepage`, `Repository`, `Documentation` (the docs site), `Changelog` and `Issues`; every keyword names something the README says — pinned by `tests/contract/test_docs_derived_from_memory.py` ([[QUALITY]]).
- The `Development Status` classifier stays `3 - Alpha` until a released wheel passes the consumer-validation recipe ([[consumer-agent-support]]).
- Channels: PyPI; the GitHub repository description, topics and homepage, set from the same tagline and keywords; `llms.txt` at the repository root, an index whose every line links to a derived document, the law, the CLI reference or the memory catalog; the docs site, GitHub Pages serving `docs/` from `main` with no build toolchain, every page derived under its markers. `docs/distribution.md` is derived from this list.

## Dependencies

[[QUALITY]], [[release-lifecycle]], [[public-asset-distribution]], [[cross-platform-portability]], [[consumer-agent-support]].
