---
slug: pypi-distribution
title: pypi-distribution
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
- Consumer-validation candidate wheels are throwaway and never mint a published version; numbers advance only at deploy, on the operator's order.
- `CHANGELOG.md` carries one `## [x.y.z]` section per published version, each citing a `git log` range, never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` works offline from a bare pip install ([[public-asset-distribution]]).
- It also ships `CONSUMER_VALIDATION_RECIPE.md`, the matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes a venv bootstrap install a candidate wheel instead of pinning from PyPI.

## Discovery surfaces

- The metadata contract: `pyproject.toml` `description` is the tagline, byte-equal to `README.md`'s first non-badge paragraph and to `llms.txt`'s `> ` line; `readme = "README.md"` makes the derived README the long description, under a 10 KB budget; `[tool.poetry.urls]` carries exactly `Homepage` (the PyPI project page — no documentation site exists), `Repository`, `Documentation` (`docs/getting-started.md`), `Changelog` and `Issues`; `keywords` are the GitHub topic set, and a keyword naming nothing the README says is deleted — all pinned by `tests/contract/test_docs_derived_from_memory.py` ([[QUALITY]]).
- The `Development Status` classifier is a claim, not decoration: `3 - Alpha` until a post-release wheel passes the consumer-validation recipe ([[consumer-agent-support]]).
- The channels and their state: PyPI (live — the long description follows the README at the next publish); the GitHub repository description, topics and homepage (set from the same tagline and keyword set by `gh repo edit`, settings no file carries, each run recorded in the release `log`); `llms.txt` at the repository root (live — an llmstxt.org index whose every line links to a derived document, the law, the CLI reference or the memory catalog); awesome-lists of agentic tooling (an operator submission, none made); the Claude Code skills/plugin registry (blocked until the skill corpus is packaged as a plugin, a backlog item). `docs/distribution.md` is the one page derived from this list.

## Dependencies

[[QUALITY]], [[public-asset-distribution]], [[cross-platform-portability]], [[consumer-agent-support]].
