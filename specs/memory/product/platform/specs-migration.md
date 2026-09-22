---
slug: specs-migration
title: specs-migration
tldr: dadaia specs upgrade walks a specs/ tree from pattern 6 to the canonical 7 and repairs template leftovers; dadaia migrate lifts a v1 context registry to v2.
summary: The two upgrade verbs for existing state — dadaia specs upgrade (one live hop, 6 to 7, folding memory/TECHSTACK.md into ARCHITECTURE.md, plus lossless template repairs; below 6 it refuses without writing) and dadaia migrate (spec_contexts.json v1 to v2, planned, confirmed, atomic).
tags: [migration, upgrade, specs, registry]
sources:
  - dadaia_workspace/features/migrate/**
  - dadaia_workspace/cli/commands/migrate.py
  - dadaia_workspace/cli/commands/specs.py
  - dadaia_workspace/core/specs_version.py
---

## Why one atom

- Both verbs bring an older workspace's persisted state up to what this installation reads, and both live in `dadaia_workspace/features/migrate/`.

## `dadaia specs upgrade`

- `dadaia specs upgrade [--specs-dir <path>] [--target <int>] [--dry-run]` reads the tree's `specs_pattern_version` and aims at the canonical version (7) by default; `--specs-dir` defaults to the bound context.
- A tree below 6 is refused with no filesystem write, naming the prerequisite: upgrade with an earlier dadaia-workspace line first.
- A tree at 6 walks the one hop: `memory/TECHSTACK.md`'s body is appended under `## Tech Stack` at the end of `memory/ARCHITECTURE.md` and the file deleted, then the tree is re-stamped. A canonical memory still carrying the two-part Principles layout is left byte-identical for the doctor to name.
- On every run, whatever the version: unfilled placeholder atoms are removed, a `releases/_ideas/` holding nothing but its `AGENTS.md` is removed, and Portuguese `**Status:**` tokens in live trio documents (never `_archive/`) are rewritten to `Approved`, `In review` or `Draft`.
- `--dry-run` plans the same set and writes nothing; a run with nothing to do is a no-op.
- [[workspace-doctor]]'s `SPECS-VERSION` warns on a tree below the canonical version.

## `dadaia migrate`

- Bare `dadaia migrate [--dry-run] [--yes]` migrates `.dadaia/states/spec_contexts.json` from schema 1 to 2: states `ativo`/`inativo` become `alive`/`dead`, `activated_at` becomes `alive_since`, `is_primary` is dropped, `dead_since` added, `states/primary_context.json` deleted and `.dadaia/sessions/` created.
- It prints the plan and asks for confirmation unless `--yes`. `dadaia reconcile` runs the same migration as one of its steps.
- A registry at schema 2 or above, the context store's own schema 3 included, is nothing to do for both `dadaia migrate` and reconcile; a non-numeric schema version is refused with manual intervention required.
- The context store refuses a schema 1 registry with `dadaia migrate` as the fix and reads schema 2 and 3 alike ([[context-management]]).

## Dependencies

[[context-management]], [[workspace-doctor]], [[spec-context-project]].
