---
slug: context-portability
title: context-portability
tldr: dadaia export writes the workspace's context set to one file; dadaia import registers each unknown context DEAD elsewhere, ready for dadaia context alive.
summary: Moving a workspace's Spec Context Projects to another workspace — export writes .dadaia/dist/spec-contexts.json (spec-contexts-export-v1) after refreshing ALIVE branches; import accepts only that schema, registers unknown names DEAD through the same guarded insert as context create, and names the alive command that restores each.
tags: [context, export, import, portability]
sources:
  - dadaia_workspace/features/export/**
  - dadaia_workspace/features/import_/**
  - dadaia_workspace/cli/commands/export.py
  - dadaia_workspace/cli/commands/import_.py
  - dadaia_workspace/core/models/export.py
---

## Why one atom

- Export and import are the two halves of one user act — carrying a context set from one workspace to another — and share one file schema; neither is useful alone.

## Export

- `dadaia export [--workspace <root>]` re-reads the checked-out branch of every ALIVE context's main repo and writes it back to the registry, then writes one file, `.dadaia/dist/spec-contexts.json`, overwritten each run.
- The file carries `schema_version` `spec-contexts-export-v1`, `exported_at`, `dadaia_version` and per context its main repo slug, name, state, repo URL, branch, associated repos (slug + URL) and `last_sync_at` (the export instant for a refreshed context, else its `dead_since`).
- Any other file in `.dadaia/dist/` is slop for [[workspace-doctor]].

## Import

- `dadaia import <file> [--workspace <root>]` accepts only a file carrying `spec-contexts-export-v1`; a missing file, invalid JSON or another schema exits 1 naming the cause.
- Each record is registered DEAD with its branch and associated repos through the same guarded insert as `dadaia context create`: a known name prints `skipped (exists)`, an invalid name or a slug another context owns prints `skipped (<reason>)`.
- The run lists each `registered (dead)` name and the `dadaia context alive <name>` that clones it ([[context-management]]).
- Import clones nothing and never overwrites a known context.

## Runtime state

`.dadaia/dist/spec-contexts.json` (written by export); `.dadaia/states/spec_contexts.json` (branch refresh on export, new DEAD records on import).

## Dependencies

[[context-management]], [[workspace-doctor]].
