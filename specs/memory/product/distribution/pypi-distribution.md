---
slug: pypi-distribution
title: pypi-distribution
tldr: The PyPI package on one version axis, two console-script names, the OIDC pipeline, the wheel contract and the derived docs.
summary: dadaia-workspace publishes to PyPI under OIDC trusted publishing from the release-please workflow; release-please owns the version, the CHANGELOG and the tag, the manifest carries the published floor, pyproject the label of the build under development, and every test, eval and smoke run validates only that build.
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

- `pip install dadaia-workspace` installs the library and one CLI under two console-script names, `dadaia` and `dadaia-workspace`, so `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` runs without an install (`tests/cli/test_main__console_scripts.py`); both names and `python -m dadaia_workspace` enter through one entry that makes stdout and stderr UTF-8 first.
- `.release-please-manifest.json` carries the last published number, the floor release-please bumps from. `pyproject.toml` `version` labels the code under development: `<release>rc<N>`, the live release's newest candidate, until that release ships, then the number release-please wrote; `release_workflow_canon`'s `version-label` and `version-shipped` clauses refuse any other value, the fix naming the expected one, and `version-equals-changelog` holds the CHANGELOG's top section to the manifest (`scripts/guards/repo.py`).
- `.github/workflows/release.yml` runs on every push to `main`: the `release-please` job maintains one release PR proposing the next version from the Conventional Commits since the floor, and merging it writes the CHANGELOG section and creates the tag ([[release-lifecycle]]).
- The publish side runs in the same workflow, every job gated on `release_created`: `ci` (the whole `ci.yml` check set, called as a reusable workflow with `actions: read` for the `Eval gate` job), `build`, `approve` (blocking on the `release-gate` environment), `smoke-test` on the built wheel, and `publish` under OIDC trusted publishing with no long-lived token, which waits on `smoke-test`.
- The `e2e-python` leg, in CI on every PR and before publish, installs `uv` and runs the onboarding journey (`tests/e2e/test_onboarding_journey.py`: `uvx --from <built wheel>` over `file://` bare repos — greenfield, dadaia v6 specs, foreign specs, a second project with an associated repo, a failed then corrected create, a re-init upgrade from this checkout's wheel to the same code rebuilt under the next `rc` label, and the quickstart's three shell blocks run as printed) with `DADAIA_REQUIRE_UVX=1`, so an absent `uvx` fails instead of skipping.
- `ci.yml`'s Linux jobs call one stdlib script, `scripts/ci.py [<job>…]`, which runs the named jobs' steps (`job` or no argument: the job level below), prints `PASS`/`FAIL <step>: <command>` per step and exits 1 on any failure, 2 on an unknown job; its `guards` job runs `scripts/guards/run.py`, plain and `--planted` ([[QUALITY]]).
- The tracked `verify:` line is `python scripts/ci.py job` — lint, typecheck, guards, the small tier and `doctor --specs-dir specs` — the job gate the merge runs once; the `not e2e` coverage run, the medium tier, Python E2E and repo hygiene run in CI only, and task merges enforce RED/implementation separation without a repository command ([[worktrees]]).
- `scripts/ci.py --changed` runs only the tests `scripts/impact.py` selects: a test is reached when it imports a changed module, directly or through others, and a changed skill script reaches its mirrored `tests/public/skills/dd_<skill>/` folder.
- `scripts/mutate.py --base <ref>` mutates only the lines a diff adds, a capped number of mutants per line, and prints each mutant's fate with its killing tests, the score and the diff's line and branch coverage; `--home` adds the kill matrix. It writes no bytecode into the checkout and builds its child environment through the kernel's scrubbed env. It is an optional review readout from the dev group, never a gate ([[QUALITY]]).
- `.github/workflows/eval.yml` is the one workflow that calls a model (dispatch or the weekly schedule, GitHub-hosted, one leg per harness and task, each leg's one secret read at job level in the `evals` environment, every upload scanned first); the `no-model-api-in-ci` guard (`scripts/guards/repo.py`) judges every line of it and no other workflow, and its `eval-cli-pin` rule refuses a matrix row without a model and a CLI version, or a Claude Code row off `CLAUDE_CODE_VERSION` (ADR 0217, [[QUALITY]] P-33; [[agent-evals]]).
- A PR into `main` needs the model-free `Eval gate` check of `ci.yml`, listed in `.github/required-checks.json`: it passes only on a green `eval.yml` run of the head's content ([[agent-evals]]); the `release-gate` approval stays a human read.
- Poetry is CI and release tooling, never a dependency: every workflow installs it as one `pipx install poetry==<version>` pin, and the `poetry-below-the-floor` guard refuses a pin below the CVE floor `_POETRY_FLOOR` (`scripts/guards/repo.py`).
- The `guards` job refuses a subprocess call with `text=True` or `universal_newlines=True` and no `encoding` over `dadaia_workspace/` and `scripts/` (`scripts/guards/slop.py`): the locale would decode its output; a `**` spread is not judged. No workflow sets a UTF-8 mode, so the Windows and macOS legs run on each host's own encoding. The lint step selects ruff's `PLW1514`, a text open with no explicit encoding, with preview on for that rule alone; `.gitattributes` keeps `tests/` and `scripts/`, like `dadaia_workspace/public/`, LF on every host.
- Coverage data lands outside the checkout: `-p scripts.covdata` is its one decider, a temp directory removed when pytest exits, and coverage follows subprocesses (`patch = ["subprocess"]`), so the hook entrypoints count.
- `smoke-test` walks the three onboarding levels from the built wheel before anything publishes: `uvx --from <wheel> dadaia-workspace init --repo <file:// bare repo>`, `specs init --context`, then `doctor --context`.

## One version axis, two positions

- The manifest holds the published floor, `pyproject.toml` the label of the build under development and the release PR the number proposed next; nothing else states a version.
- Tests, evals and the release validate only the current build, never a published `dadaia-workspace`: `workflow_never_rules`' `published-dadaia-workspace-install` rule refuses, under `.github`, `tests`, `evals` and `scripts`, a pin, tag, range or bare name of it, spelled in any form PEP 503 normalises to that name, after `install`, `download`, `add`, `--from` or `--with`; `uvx dadaia-workspace init` and `--from <path>` stay legal, and third-party dependencies still resolve from PyPI.
- A `v<version>` tag exists only for numbers release-please released; withholding the `release-gate` approval leaves the tag and CHANGELOG section without an upload, and the number is never reused.
- Consumer-validation candidate wheels are throwaway and never mint a published version.
- `CHANGELOG.md` is written by release-please; a hand-written legacy section is never renamed, renumbered or deleted.

## Wheel content contract

- The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init` needs no asset download; the workspace venv's dependencies still resolve from PyPI ([[public-asset-distribution]]).
- The runtime dependencies are Typer, Rich, jsonschema and packaging; PyYAML, the mutation readout's `pytest-cov` and every test tool sit in the dev group only, so neither the wheel nor `public install` carries them.
- The wheel does not ship the consumer-validation recipe: it lives in `scripts/CONSUMER_VALIDATION_RECIPE.md`, the developer's matrix run against every candidate wheel before deploy ([[consumer-agent-support]]).
- A venv bootstrap installs the running distribution (editable from a checkout, else its re-packed wheel); `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes it install a named candidate wheel instead.

## Discovery surfaces

- `pyproject.toml` `description` is the tagline, byte-equal to `README.md`'s first non-badge paragraph and to `llms.txt`'s `> ` line; `readme = "README.md"` makes the derived README the long description; `[tool.poetry.urls]` carries `Homepage` (`https://marco-menezes.com/projetos/dadaia-workspace`, the author's project page), `Repository`, `Documentation` (`https://github.com/marcoaureliomenezes/dadaia-workspace/tree/main/docs`, the repository's `docs/` folder — no separate site is published), `Changelog` and `Issues`; every README link is absolute, so it resolves on the PyPI page; every keyword names something the README says — pinned by `tests/contract/test_docs_derived_from_memory.py` ([[QUALITY]]).
- Every command's `--help` states behaviour in the reader's words — no requirement, task, audit or ADR id and no code seam name — and every example line spells the absolute venv CLI through the one renderer (`tests/cli/commands/test_help.py`); `docs/cli.md` is derived from it.
- The `Development Status` classifier stays `3 - Alpha` until a released wheel passes the consumer-validation recipe ([[consumer-agent-support]]).
- Channels: PyPI; the GitHub repository description, topics and homepage; `llms.txt` as the agent index, and `llms-full.txt`, which it links: the full text of every repository page `llms.txt` links, in its order, the changelog excepted, written only by `scripts/llms_full.py` and pinned to that output by the same contract test; and the repository's `docs/` folder on the principal branch, with no separate site. Authored documents are reconciled from current product memory; no prose hash marker participates in correctness.

## Dependencies

[[QUALITY]], [[release-lifecycle]], [[public-asset-distribution]], [[cross-platform-portability]], [[consumer-agent-support]].
