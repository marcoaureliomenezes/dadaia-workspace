---
slug: pypi-distribution
title: pypi-distribution
tldr: The PyPI package on one version axis, two console-script names, the OIDC pipeline, the wheel contract and the derived docs.
summary: dadaia-workspace publishes to PyPI under OIDC trusted publishing from the release-please workflow; release-please owns the version, the CHANGELOG and the tag, and pyproject carries the published floor.
tags: [distribution, pypi, release, packaging]
sources:
  - .github/workflows/**
  - release-please-config.json
  - dadaia_workspace/cli/main.py
  - dadaia_workspace/__main__.py
  - pyproject.toml
  - scripts/**
---

## Pipeline

- `pip install dadaia-workspace` installs the library and one CLI under two console-script names, `dadaia` and `dadaia-workspace`, so `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` runs without an install (`tests/cli/test_main__console_scripts.py`).
- `pyproject.toml` `version` and `.release-please-manifest.json` carry the last published number — the floor release-please bumps from, stated nowhere else.
- `.github/workflows/release.yml` runs on every push to `main`: the `release-please` job maintains one release PR proposing the next version from the Conventional Commits since the floor, and merging it writes the CHANGELOG section and creates the tag ([[release-lifecycle]]).
- The publish side runs in the same workflow, every job gated on `release_created`: `ci` (the whole `ci.yml` check set, called as a reusable workflow), `build`, `approve` (blocking on the `release-gate` environment), `publish` under OIDC trusted publishing with no long-lived token, and `smoke-test` against the live index.
- The `e2e-python` leg, in CI on every PR and before publish, installs `uv` and runs the onboarding journey (`tests/e2e/test_onboarding_journey.py`: `uvx --from <built wheel>` over `file://` bare repos — greenfield, dadaia v6 specs, foreign specs, a second project with an associated repo, a failed then corrected create, a re-init upgrade) with `DADAIA_REQUIRE_UVX=1`, so an absent `uvx` fails instead of skipping.
- `ci.yml`'s Linux jobs call one stdlib script, `scripts/ci.py [<job>…]`, which runs the named jobs' steps (all when none is named), prints `PASS`/`FAIL <step>: <command>` per step and exits 1 on any failure; its `guards` job runs `scripts/guards/run.py`, plain and `--planted` ([[QUALITY]]).
- The tracked `verify:` line runs `python scripts/ci.py job`; `job`, `stage` and an empty invocation share the focused repository verification set, while task merges enforce RED/implementation separation without a repository command ([[worktrees]]).
- `.github/workflows/eval.yml` is the one workflow that calls a model (dispatch or the weekly schedule, GitHub-hosted, the model secret read at job level in the `evals` environment, every upload scanned first); the `no-model-api-in-ci` guard (`scripts/guards/repo.py`) judges every line of it and no other workflow (ADR 0217, [[QUALITY]] P-33; [[agent-evals]]).
- Poetry is CI and release tooling, never a dependency: every workflow installs it as one `pipx install poetry==<version>` pin, and the `poetry-below-the-floor` guard refuses a pin below the CVE floor `_POETRY_FLOOR` (`scripts/guards/repo.py`).
- The `guards` job refuses a subprocess call with `text=True` or `universal_newlines=True` and no `encoding` over `dadaia_workspace/` and `scripts/` (`scripts/guards/slop.py`): the locale would decode its output, and CI's `PYTHONUTF8=1` hides the gap; a `**` spread is not judged.
- Coverage data lands outside the checkout: `-p scripts.covdata` is its one decider, a temp directory removed when pytest exits, and coverage follows subprocesses (`patch = ["subprocess"]`), so the hook entrypoints count.
- `smoke-test` walks the three onboarding levels from the published wheel: `uvx dadaia-workspace==<version> init --repo <file:// bare repo>`, `specs init --context`, then `doctor --context`.

## One version axis, two positions

- `pyproject.toml` and the manifest hold the published floor; the release PR holds the number proposed next; nothing else states a version.
- A `v<version>` tag exists only for numbers release-please released; withholding the `release-gate` approval leaves the tag and CHANGELOG section without an upload, and the number is never reused.
- Consumer-validation candidate wheels are throwaway and never mint a published version.
- `CHANGELOG.md` is written by release-please; a hand-written legacy section is never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` needs no asset download; the workspace venv's dependencies still resolve from PyPI ([[public-asset-distribution]]).
- The wheel does not ship the consumer-validation recipe: it lives in `scripts/CONSUMER_VALIDATION_RECIPE.md`, the developer's matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- A venv bootstrap installs the running distribution (editable from a checkout, else its re-packed wheel); `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes it install a named candidate wheel instead.

## Discovery surfaces

- `pyproject.toml` `description` is the tagline, byte-equal to `README.md`'s first non-badge paragraph and to `llms.txt`'s `> ` line; `readme = "README.md"` makes the derived README the long description; `[tool.poetry.urls]` carries `Homepage`, `Repository`, `Documentation` (`https://github.com/marcoaureliomenezes/dadaia-workspace/tree/main/docs`, the repository's `docs/` folder — no separate site is published), `Changelog` and `Issues`; every README link is absolute, so it resolves on the PyPI page; every keyword names something the README says — pinned by `tests/contract/test_docs_derived_from_memory.py` ([[QUALITY]]).
- Every command's `--help` states behaviour in the reader's words — no requirement, task, audit or ADR id and no code seam name — and every example line spells the absolute venv CLI through the one renderer (`tests/cli/commands/test_help.py`); `docs/cli.md` is derived from it.
- The `Development Status` classifier stays `3 - Alpha` until a released wheel passes the consumer-validation recipe ([[consumer-agent-support]]).
- Channels: PyPI; the GitHub repository description, topics and homepage; `llms.txt` as the agent index; and the repository's `docs/` folder on the principal branch, with no separate site. Authored documents are reconciled from current product memory; no prose hash marker participates in correctness.

## Dependencies

[[QUALITY]], [[release-lifecycle]], [[public-asset-distribution]], [[cross-platform-portability]], [[consumer-agent-support]].
