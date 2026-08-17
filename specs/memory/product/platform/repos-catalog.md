---
slug: repos-catalog
title: repos-catalog
category: product
tldr: repos.xlsx lookup for fast discovery of known repos with slug + URL.
summary: repos.xlsx lookup for fast discovery of known repos with slug +
  URL.
tags:
- repos
- catalog
- discovery
last_updated: '2026-07-16'
release_origin: v0.1.48
---

CLI surface: `dadaia repos list` · Closure: sdd-release-lifecycle-v1

## Purpose

Queries the static catalog of known repos at `.dadaia/agentic/data/repos.xlsx` (canonical source `dadaia_workspace/public/data/repos.xlsx`) and displays slug, URL, description. Serves as fast discovery for the operator to create new contexts without memorizing URLs.

## Usage flow

  1. `dadaia repos list` — shows a table with all catalog repos.
  2. The operator identifies the desired slug and uses it in `dadaia context create <name> --repo <slug>`.
  3. **Programmatic consumer:** `dadaia context create` without `--url` queries the catalog via `ReposService.list_known()` (`cli/commands/context.py` → `container.build_repos_service()`) to back-fill `repo_url`, failing gracefully when the catalog is absent; an explicit `--url` wins over the lookup.
  4. To update the catalog: edit the XLSX manually (or regenerate it via a dedicated release).



## Typical trigger

When the operator is about to create a context for a repo whose exact URL they do not remember.

## Differentiator

Without the catalog, creating a context required pasting the full URL every time. The short slug shortens the path and centralizes discovery.

## Runtime state touched

  * Read-only: `.dadaia/agentic/data/repos.xlsx`



## Dependencies

  * Depends on [[public-asset-distribution]] (projects the XLSX into `.dadaia/agentic/data/`); `.dadaia/src/` is a retired legacy dir, quarantined by reconcile.
  * Consumed by [[context-management]] (the operator checks repos list before creating a context).
