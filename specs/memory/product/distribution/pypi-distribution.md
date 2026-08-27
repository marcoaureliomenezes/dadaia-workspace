---
slug: pypi-distribution
title: pypi-distribution
category: product
tldr: The published PyPI package on one version axis, the OIDC publish pipeline, the minted-unpublished shape, and the wheel content contract.
summary: >-
  Owns PyPI distribution as product behavior — the live `dadaia-workspace` package, the
  `.github/workflows/release.yml` pipeline (version-vs-tag check → five test legs → build →
  release-gate approval → OIDC trusted publishing + tag → post-publish smoke), the wheel
  content contract (public assets ship in-package), and the single version axis: one number
  carries the release id, the `pyproject.toml` version and, once published, the PyPI
  lineage. Minting and publishing are separate acts — `HEAD` carries the newest minted
  number while the published lineage carries only the numbers the withheld release-gate
  approval let through, and a minted-unpublished number is retired rather than reused. The
  CHANGELOG records that lineage completely — a git-derived, range-cited section for every
  published version, and an unpublished-internal annotation for every heading matching
  none; nothing is deleted or renamed.
tags:
- distribution
- pypi
- release
- packaging
last_updated: '2026-08-27'
release_origin: v0.4.5
---

## Purpose

`dadaia-workspace` is a published PyPI package: `pip install dadaia-workspace`
installs the library and its `dadaia` CLI. `pyproject.toml` `version` is the single source
of the number, and no other file restates it. Minting a number and publishing it are two
acts: the number is minted at a release's final candidate and reaches PyPI only when the
operator approves the release gate.
Consumer-validation candidates are throwaway wheels — they NEVER mint intermediate
published versions; version numbers advance only at deploy time, on the operator's order.
PyPI descriptions are immutable per release: a documentation-only fix to the project page
requires a version bump, never an in-place edit.

Publication is fully automated by `.github/workflows/release.yml` with **OIDC
trusted publishing** — no long-lived PyPI token exists in the repository or its
secrets; the `pypi` GitHub environment carries the trust binding.

## Usage flow

1. A version bump lands on `main` (`pyproject.toml` `version = "<major.minor.patch>"` — an
   operational-change-lane commit or a release merge).
2. `release.yml` fires on the `main` push. The `check` job compares the pyproject
   version against existing `v*` tags: tag exists ⇒ every downstream job skips
   (idempotent); new version ⇒ the pipeline proceeds.
3. Five test legs re-run on the release commit: `unit-fast`, `contract-coverage`
   (80% gate), `integration`, `e2e-python`, `e2e-panel` (Playwright against a
   bootstrapped panel workspace).
4. `build` produces sdist + wheel (`poetry build`) and uploads them as a
   versioned artifact.
5. `approve` blocks on the **`release-gate` GitHub environment** — a human
   approval step before anything reaches PyPI. Withholding it is a supported outcome, not
   a stall: `publish` never runs, no `v<version>` tag is created, and the merge to `main`
   still shipped the code. That is exactly how a number becomes minted-unpublished.
6. `publish` downloads the built artifact, publishes via
   `pypa/gh-action-pypi-publish` under the `pypi` environment (OIDC
   `id-token: write`), then creates and pushes the `v<version>` git tag.
7. `smoke-test` (ubuntu/py3.12) waits for PyPI propagation, `pip install
   dadaia-workspace==<version>` from the live index, runs `dadaia --help` and a
   real `dadaia init` in a tmpdir, asserting the state file exists. (The PyPI
   JSON index can lag the CDN right after publish — the smoke waits, then
   installs by exact version.)

## Typical trigger

The operator orders a package release (version bump on `main`), or an agent needs
to know how the shipped library reaches consumers and what a version number refers
to.

## Differentiator

**One version axis, two positions on it.** There is a single number: a release id **is**
the version that release mints, `v`-prefixed (`v0.4.2` ⇔ package `0.4.2`), so
`pyproject.toml`, the release directory and the CHANGELOG section for a release all carry
the same digits. No number is minted on an internal axis, and a release never renumbers
itself to reconcile with the package.

What the one axis carries at two different positions is **`HEAD`** and the **published
lineage**. `pyproject.toml` on `main` is the newest **minted** number; PyPI shows the
newest **published** one; a git tag `v<version>` exists only for the published ones,
because the publish job is what creates it. The two positions coincide whenever the
operator approves the release gate, and diverge whenever the approval is deliberately
withheld.

Today `main` reads `0.4.5` and the published lineage runs `0.4.2 → 0.4.4`. **`0.4.3` and
`0.4.5` were minted locally and never published** — the shape is now repeated rather than
accidental, so it is product truth and not a footnote. A minted-unpublished number keeps
its CHANGELOG section, annotated as a local-only mint, and its archived release directory;
the number is **retired rather than reused**, because reusing it would collide with both.
Each such gap in the lineage is the honest record of a withheld approval, never a missing
entry. Publication of an already-minted number remains available on a later operator order,
and a higher number may supersede it instead; nothing in the shape forecloses either.

`CHANGELOG.md` carries the reconciling preamble this implies: it states which of its
historical headings were minted internally and never reached PyPI, maps them to the
internal ids they documented, and declares the forward rule — one `## [x.y.z]` section
corresponds to exactly one published package version. Existing sections are never renamed
or renumbered; the preamble carries the meaning instead.

**The lineage's record is complete and derived, never invented.** Every published version
carries a section, including the ten that previously had none: each is a compact
retroactive section **derived from git history**, stating inline the exact `git log` range
and commit count it was built from, so any reviewer can re-run the identical command and
check it line by line. Nothing is embellished — a version whose history yields little gets
a short factual entry rather than a manufactured feature list. In the other direction, the
three headings matching no published version are **annotated** as unpublished-internal
rather than deleted: nothing in the file is ever removed or renamed, because a changelog
that rewrites itself is no longer evidence.

**Wheel content contract:** the wheel ships the complete runtime product —
`dadaia_workspace/` with the full `public/` asset tree (agents, skills, rules,
workflows, scripts, schemas, templates, data, scaffold, runtime, personas,
lifecycle_fragments) so
`dadaia init` works offline from a bare pip install
with no network fetch of assets. The wheel also ships
`public/data/CONSUMER_VALIDATION_RECIPE.md` — the canonical consumer-side
validation matrix (statements F-01..F-23, verdict APROVADA / BLOQUEADA /
APROVADA COM EXCEÇÃO EXPLÍCITA) that a consumer-side validator runs against
EVERY candidate wheel before deploy; internal gates (`certify` included) never
approve a deploy by themselves. `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` makes
workspace-venv bootstraps install the candidate itself instead of pinning the
(possibly unpublished) version from PyPI.

## Runtime state touched

- `pyproject.toml` — `version` (single source of the package version) and the
  PyPI classifiers (`POSIX :: Linux + MacOS + Microsoft :: Windows`).
- `CHANGELOG.md` — one section per published version, each traceable to a commit range,
  plus the preamble that reconciles the headings predating that rule and the
  unpublished-internal annotations on the headings matching no published version.
- `.github/workflows/release.yml` — the release pipeline (inventoried in
  [[quality-assurance]]).
- GitHub environments `release-gate` (human approval) and `pypi` (OIDC trusted
  publishing binding).
- Git tags `v<package-version>` — created by the publish job after a successful
  upload, so a tag exists for exactly the published numbers and for no minted-unpublished
  one.

## Dependencies

- [[quality-assurance]] — the five test legs the pipeline re-runs, and the CI
  workflow inventory row for `release.yml`.
- [[public-asset-distribution]] — the `public/` asset tree the wheel carries.
- [[cross-platform-portability]] — the PyPI OS classifiers the 3-OS CI matrix backs.
