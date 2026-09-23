# Distribution

Where dadaia-workspace is published and what each channel carries.

## Channels

<!-- derived-from: pypi-distribution sha256:c627d9e5be4d -->

| channel | artifact | how it is published |
|---|---|---|
| PyPI | the wheel; `README.md` is the long description and `pyproject.toml` the metadata | `.github/workflows/release-please.yml`: merging the release PR creates the tag, and the publish jobs, gated on `release_created` and on the operator's `release-gate` approval, upload under OIDC trusted publishing |
| GitHub repository | the repository description, topics and homepage | set from the same tagline and keywords as `pyproject.toml` |
| Repository root | `llms.txt` — an index whose every line links to a derived document, the law, the CLI reference or the memory catalog | committed, derived under its markers |
| Docs site | GitHub Pages serving `docs/` from `main`, with no build toolchain | every page derived under its markers |
| `dadaia-skills` repository | the standalone skills in the Agent Skills layout, installable by `npx skills add` and as a Claude Code marketplace | the `publish-skills-repo` job of the release workflow |

## The PyPI metadata contract

<!-- derived-from: pypi-distribution sha256:c627d9e5be4d -->

Every field PyPI renders has exactly one home:

- **The number** — `pyproject.toml`'s `version` and `.release-please-manifest.json`
  carry the last published number, the floor release-please bumps from; the number
  proposed next lives only in the open release PR, and nothing else states a version.
  A `v<version>` tag exists only for a number release-please released.
- **The summary** — `pyproject.toml`'s `description`, the tagline, byte-equal to the
  README's first non-badge paragraph and to `llms.txt`'s `> ` line, pinned by
  `tests/contract/test_docs_derived_from_memory.py`.
- **The long description** — `README.md` itself (`readme = "README.md"`), derived like
  every other document.
- **The links** — `[tool.poetry.urls]`: `Homepage`, `Repository`, `Documentation` (the
  docs site), `Changelog` and `Issues`.
- **The keywords** — every keyword names something the README says.
- **The classifiers** — the `Development Status` stays `3 - Alpha` until a released
  wheel passes the consumer-validation recipe.

## What the wheel carries

<!-- derived-from: pypi-distribution sha256:c627d9e5be4d -->

The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init`
works offline from a bare install, and
`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md`, the matrix run against
every candidate wheel before a deploy. It installs one CLI under two console-script
names, `dadaia` and `dadaia-workspace`. Consumer-validation candidate wheels are
throwaway and never mint a published version; `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes
a venv bootstrap install one instead of the PyPI release. Withholding the
`release-gate` approval leaves the tag and the `CHANGELOG.md` section without an
upload, and the number is never reused.
