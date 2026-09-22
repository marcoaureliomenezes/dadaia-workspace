# Distribution

Where dadaia-workspace is published, what each channel carries, and who acts. A
channel with no artifact in this repository is an operator step, recorded here rather
than pretended into a task.

## Channels

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->

| channel | artifact | state | who acts |
|---|---|---|---|
| PyPI | the wheel and sdist; `README.md` is the long description and `pyproject.toml` the metadata | live — published from `.github/workflows/release-please.yml` under OIDC trusted publishing, the merge of the release PR firing it | the same workflow, its publish jobs gated on `release_created` and on the `release-gate` environment the operator approves |
| GitHub repository | the repository description, its topics and its homepage — settings, carried by no file in the tree | set — description, homepage and topics from the same tagline and keyword set, each run recorded in `_RELEASE.json`'s `log` | the main thread: `gh repo edit --description … --homepage … --add-topic …`, then `gh repo view --json description,repositoryTopics,homepageUrl` |
| Repository root | `llms.txt` — the llmstxt.org index an agent reads first: what it is, install, the law, the CLI reference, the memory catalog | live — every line links, none restates | `software-engineer`, re-derived at closure like every document under a `derived-from` marker |
| Awesome-lists of agentic tooling | a submitted entry carrying the tagline and the repository link | pending — no submission made | the operator |
| Claude Code skills / plugin registry | a packaged plugin of the skill corpus | blocked — backlog `plugin-packaging-and-skill-evals` owns the packaging and the skill evaluations it requires | the operator picks the backlog entry; nothing ships from this candidate |

## The PyPI metadata contract

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->

Every field PyPI renders has exactly one home, and no number or sentence is restated
in a second file:

- **The number** — `pyproject.toml`'s `version` and `.release-please-manifest.json`,
  which carry the LAST PUBLISHED number: the floor release-please bumps from, restated
  nowhere else. The number proposed next lives only in the open release PR, and a
  `v<version>` tag exists only for a published number, because merging that PR creates
  it.
- **The summary** — `pyproject.toml`'s `description`, the tagline, byte-equal to the
  README's first non-badge paragraph and to `llms.txt`'s `> ` line, pinned by
  `tests/contract/test_docs_derived_from_memory.py`.
- **The long description** — `README.md` itself (`readme = "README.md"`), every
  section of it derived from a named memory atom under that atom's content hash, and
  capped at the 10 KB the same test measures.
- **The links** — `[tool.poetry.urls]`: `Homepage` (the PyPI project page — no
  documentation site exists), `Repository`, `Documentation` (`docs/getting-started.md`
  in the repository), `Changelog` and `Issues`. The same test asserts the five keys.
- **The keywords** — `pyproject.toml`'s `keywords`, which are also the GitHub topic
  set; a keyword naming nothing the README says is deleted rather than kept for
  search.
- **The classifiers** — a claim, not decoration: the development status stays
  `3 - Alpha` until a post-release wheel passes the consumer-validation recipe the
  wheel itself ships.

## What the wheel carries

<!-- derived-from: pypi-distribution sha256:7e18d9868790 -->

The wheel ships `dadaia_workspace/` with the full `public/` tree, so `dadaia init`
works offline from a bare `pip install`, and `CONSUMER_VALIDATION_RECIPE.md`, the
matrix run against every candidate wheel before a deploy. Consumer-validation
candidate wheels are throwaway and never mint a published number —
`DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes a venv bootstrap install one instead of
pinning from PyPI. Withholding release-gate approval is supported: the tag and the
`CHANGELOG.md` section exist, the upload does not, and the number is never reused.
