---
title: "CHANGELOG version-axis incoherence: dated [0.5.1] atop stacked Unreleased spec-release sections"
status: candidate
opened: 2026-08-14
description: >-
  v0.8.0 CLOSURE backlog return, materialized 2026-08-14 (CLOSURE destined it to
  ideas; promoted to candidate by operator mandate with owners software-engineer +
  product-engineer). CHANGELOG.md at HEAD carries "## [0.5.1] — 2026-08-14" (line 7)
  above three stacked "## [Unreleased] — spec release vX" sections (v0.7.0 line 30,
  v0.6.0 line 107, v0.5.0 line 177) and "## [0.5.0] — Unreleased (spec release
  v0.3.0)" (line 236): the hotfix minted a dated PATCH on top of a package version
  whose own section still reads Unreleased, so the file no longer states truthfully
  what a given package version contains. The two version axes are distinct by design
  (ADR-2: SDD release ids version the SDD process; the 0.x package version versions
  the shipped library) — the ask is a reconciled CHANGELOG convention honoring that
  split, not a renumbering.
intents:
  - subject:
      kind: doc
      ref: memory/product/distribution/pypi-distribution.md#Differentiator
    change: >-
      Define and record the CHANGELOG convention that reconciles the two axes: how
      spec-release sections nest under (or annotate) package-version sections, what
      happens to accumulated "[Unreleased] — spec release vX" sections when a package
      version is finally dated, and how a hotfix PATCH is placed relative to a
      still-Unreleased base version. Restructure CHANGELOG.md once to that
      convention so each package version's section states exactly what it ships.
---

# CHANGELOG version-axis reconciliation

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.8.0/CLOSURE.md`
§"Backlog returns", seventh item, and §"Version bump decision" justification 5
("A CHANGELOG entry would deepen an existing incoherence, not resolve one").

State at HEAD (verified 2026-08-14, section lines from `grep -n "^## \[" CHANGELOG.md`):

```
7:   ## [0.5.1] — 2026-08-14
30:  ## [Unreleased] — spec release v0.7.0
107: ## [Unreleased] — spec release v0.6.0
177: ## [Unreleased] — spec release v0.5.0
236: ## [0.5.0] — Unreleased (spec release v0.3.0)
```

A reader asking "what does package 0.5.1 contain?" finds a dated PATCH whose base
minor is itself undated, with three spec releases' worth of changes floating in
Unreleased sections that belong to that same package version. Pre-existing —
not caused by v0.8.0 (which correctly minted nothing, per its version-bump
decision) and not caused by the hotfix alone; the axes drifted over v0.5.0→v0.7.0.

## Motivation

`CHANGELOG.md` claims Keep a Changelog 1.1.0 + SemVer adherence in its own header;
the current shape honors neither axis. The ADR-2 split (never renumber) is
correct and stays — what is missing is the documented mapping from spec-release
identity to package-version section.

## Acceptance criteria

- A written convention (in `pypi-distribution.md`) states how spec-release deltas
  land in CHANGELOG sections and how a hotfix PATCH relates to an undated base.
- `CHANGELOG.md` is restructured once to that convention: every dated version
  section states exactly what that package version ships; no dated PATCH sits
  above its own undated base without an explanatory rule.
- The never-renumber law is untouched (no SDD release id and no published package
  version changes).

## Ownership

`software-engineer` (file mechanics) + `product-engineer` (convention, memory) —
per operator mandate 2026-08-14.
