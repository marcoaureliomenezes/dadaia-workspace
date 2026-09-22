---
slug: pypi-distribution
title: pypi-distribution
tldr: The PyPI package on one version axis, two console-script names, the OIDC pipeline that also publishes the skills repo, the wheel contract and the docs site.
summary: dadaia-workspace publishes to PyPI under OIDC trusted publishing from the release-please workflow; release-please owns the version, the CHANGELOG and the tag, and pyproject carries the published floor.
tags: [distribution, pypi, release, packaging]
sources:
  - pyproject.toml
  - .github/workflows/**
  - release-please-config.json
  - .release-please-manifest.json
  - dadaia_workspace/cli/main.py
  - dadaia_workspace/__main__.py
  - docs/**
---

## Pipeline

- `pip install dadaia-workspace` installs the library and its CLI under two console-script names for one callable — `dadaia` and `dadaia-workspace`, the second so that `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` resolves without an install (0.4.7 c9; `tests/unit/cli/test_console_scripts.py` pins the identity); `pyproject.toml` `version` and `.release-please-manifest.json` carry the LAST PUBLISHED number — the floor release-please bumps from, restated nowhere else.
- Publication is automated by `.github/workflows/release-please.yml` under OIDC trusted publishing: no long-lived PyPI token exists, and the `pypi` GitHub environment carries the trust binding.
- Every push to `main` runs the `release-please` job: it maintains one release PR proposing the next version from the Conventional Commits since the floor, and merging that PR is the promote act — it writes the CHANGELOG section and creates the tag.
- The publish side runs in the same workflow, every job `needs` `release-please` and gated on `release_created == 'true'`: five test legs, `build`, `approve` (blocking on the `release-gate` environment), `publish`, `smoke-test` against the live index, and `publish-skills-repo` — the built `dadaia-skills` repository force-pushed with the version as the commit subject, failing closed with one `::error::` when its token is absent ([[public-asset-distribution]]).

## One version axis, two positions

- One axis, two positions: `pyproject.toml` and the manifest hold the published floor, and the release PR holds the number proposed next; nothing else states a version.
- A `v<version>` tag exists only for published numbers, because release-please creates it when its PR merges.
- Withholding release-gate approval is supported: the tag and the CHANGELOG section exist, the upload does not, and the number is never reused.
- Consumer-validation candidate wheels are throwaway and never mint a published version; numbers advance only at deploy, on the operator's order.
- `CHANGELOG.md` is written by release-please from the commit history; a hand-written section is legacy, never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` works offline from a bare pip install ([[public-asset-distribution]]).
- It also ships `CONSUMER_VALIDATION_RECIPE.md`, the matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes a venv bootstrap install a candidate wheel instead of pinning from PyPI.

## Discovery surfaces

- The metadata contract: `pyproject.toml` `description` is the tagline, byte-equal to `README.md`'s first non-badge paragraph and to `llms.txt`'s `> ` line; `readme = "README.md"` makes the derived README the long description, under a 10 KB budget; `[tool.poetry.urls]` carries exactly `Homepage` (the PyPI project page), `Repository`, `Documentation` (the docs site, `https://marcoaureliomenezes.github.io/dadaia-workspace/`), `Changelog` and `Issues`; `keywords` are the GitHub topic set, and a keyword naming nothing the README says is deleted — all pinned by `tests/contract/test_docs_derived_from_memory.py` ([[QUALITY]]).
- The `Development Status` classifier is a claim, not decoration: `3 - Alpha` until a post-release wheel passes the consumer-validation recipe ([[consumer-agent-support]]).
- The channels and their state: PyPI (live — the long description follows the README at the next publish); the GitHub repository description, topics and homepage (set from the same tagline and keyword set by `gh repo edit`, settings no file carries, each run recorded in the release `log`); `llms.txt` at the repository root (live — an llmstxt.org index whose every line links to a derived document, the law, the CLI reference or the memory catalog); the docs site — GitHub Pages serving `docs/` from `main` (`index.md`, `quickstart.md`, `positioning.md`, `bug-loop.md`, `bug-ledger-lessons.md` beside the four earlier pages, every page derived under its markers, no build toolchain; enabling Pages is an operator act); the `dadaia-skills` repository (built, published by the release workflow, installable by `npx skills add marcoaureliomenezes/dadaia-skills` and as a Claude Code marketplace — the marketplace submission and the awesome-list PRs are operator acts, none made). `docs/distribution.md` is the one page derived from this list.

## Dependencies

[[QUALITY]], [[public-asset-distribution]], [[cross-platform-portability]], [[consumer-agent-support]].
