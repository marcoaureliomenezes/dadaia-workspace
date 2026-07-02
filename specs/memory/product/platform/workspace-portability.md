---
slug: workspace-portability
title: workspace-portability
category: product
tldr: export/import of the whole workspace as a tar.gz for backup or migration between
  machines.
summary: export/import of the whole workspace as a tar.gz for backup or migration between
  machines.
tags:
- portability
- export
- import
- backup
agent_tier: self-pull
token_estimate: 400
last_updated: '2026-07-02'
release_origin: v0.1.48
---

CLI surface: `dadaia export [--output DIR] [--include-reports] [--exclude-mnt]` and `dadaia import <archive> [--workspace DEST] [--skip-activate]` · Closure: sdd-release-lifecycle-v1

## Purpose

Packages and restores the workspace's durable state (state files, academy, rules, skills) as a portable `.tar.gz`. Secrets (`.env`), caches and cloned `repos/` are excluded by default; HTML reports opt-in via flag.

Restore patches absolute paths for the new machine, reactivates contexts as they were, and (unless `--skip-activate`) re-runs `workspace-init` to reconfigure hooks.

## Usage flow

  1. `dadaia export` — generates `.dadaia/dist/workspace-<timestamp>.tar.gz` with state + academy + rules + skills.
  2. The operator transports the archive (scp, upload, etc.) to the new machine.
  3. On the new machine, in a clean directory: `dadaia import /path/to/archive.tar.gz`.
  4. Import extracts, patches absolute paths, restores contexts and (by default) runs init.
  5. The operator validates with `dadaia context list` and `dadaia doctor`.



## Typical trigger

Migration between machines, periodic backup, or sharing a workspace template with a colleague/team.

## Differentiator

A reproducible workspace in a few seconds without a manual rebuild — all context configurations, rules, skills and academy materials preserved. Without this feature, migrating a workspace would require manually reproducing dozens of files across several runtime dirs.

## Runtime state touched

  * Export: creates `.dadaia/dist/<archive>.tar.gz`
  * Import: extracts over the destination workspace, overwrites `.dadaia/states/*`, `.dadaia/academy/`, `.claude/rules/`, `.agents/skills/`
  * Cloned repos do NOT travel — re-clone via `dadaia context alive` after import



## Dependencies

  * Export depends on [[context-management]] (reads `spec_contexts.json`).
  * Import triggers [[workspace-init]] internally to reconfigure hooks.
