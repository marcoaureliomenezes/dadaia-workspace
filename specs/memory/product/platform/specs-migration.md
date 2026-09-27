---
slug: specs-migration
title: specs-migration
tldr: specs init brings specs/ to the canon and writes the project gitflow, never committing; specs upgrade walks 6 to 7; migrate lifts registry v1.
summary: The verbs that bring persisted state up to what this installation reads — dadaia specs init (onboarding level 3a; absent scaffolds, dadaia upgrades, foreign moves to specs-bkp/, the constitution's gitflow block written or kept), dadaia specs upgrade (one live hop, 6 to 7, plus fixed law sections and lossless template repairs; below 6 it refuses without writing) and dadaia migrate (spec_contexts.json v1 to v2, planned, confirmed, atomic).
tags: [migration, upgrade, specs, registry, onboarding]
sources:
  - dadaia_workspace/features/migrate/**
  - dadaia_workspace/cli/commands/migrate.py
  - dadaia_workspace/cli/commands/specs.py
  - dadaia_workspace/core/specs_version.py
---

## Why one atom

- Every verb here brings an older or foreign persisted state up to what this installation reads; the version logic lives in `dadaia_workspace/features/migrate/` and `dadaia_workspace/core/specs_version.py` (pure: the pattern-version canon and the tree classifier), and every constitution read and frontmatter write in `dadaia_workspace/core/gitflow.py`.

## `dadaia specs init`

- `dadaia specs init [--context <ctx>] [--specs-dir <path>] [--name <project>] [--replace-foreign] [--principal <b>] [--integration <b>] [--work-prefix <p>]` is onboarding level 3a: it targets the context's main repo `specs/` (the bound context when `--context` is omitted); with no context resolvable it exits 2 with `fix: <cli> specs init --context <name>`.
- An absent `specs/` gets the canon scaffold ([[public-asset-distribution]]); a dadaia tree (stamped 6 or above) runs `specs upgrade`, then gains only its missing canon files; a constitution whose frontmatter does not parse, or whose `gitflow:` block does not validate, is malformed and refused, exit 2, nothing written (fix: repair its YAML); anything else is foreign.
- The project gitflow is the `gitflow: {principal: <name>, integration: <name>, work: <prefix>}` block of `specs/constitution.md` frontmatter ([[sdd-gate-v3]]); each flag wins over the tree's own valid block, which wins over detection — principal from the local `origin/HEAD`, else `main`; integration `develop`; work prefix `feature/`. The names must be valid branch names, principal and integration must differ, and the work prefix may not nest under a role name; an invalid result exits 2 before any write. The same flags twice is a no-op, an operator's custom names are never reset, and stdout names the gitflow written (`[gitflow] …`).
- One frontmatter merge-writer serves both `specs_pattern_version` and `gitflow`: a written key's line is replaced in place, a new one appended, every other key and the body kept byte for byte.
- A foreign tree is replaced only with consent, `--replace-foreign`; without it the run exits 2, writes nothing and prints `fix: <cli> specs init --context <ctx> --replace-foreign`.
- With consent, `specs/` is renamed to `specs-bkp/` in the same repo — tracked files through `git mv`, staged and uncommitted, every byte kept — then scaffolded; when `specs-bkp/` already exists the second backup lands in `specs-bkp/<UTC timestamp>/`, the one backup location the publish commits.
- It also installs the main repo's scoped law where absent, its `<repo-name>` rendered as the project (`--name`, else the main repo's directory name): `AGENTS.md` at the repo root, and `tests/AGENTS.md` only when `tests/` exists; an existing or symlinked target is never overwritten or written through.
- Every written path is printed (`[created]`, `[moved]`, the upgrade's own lines); `specs init` never commits — the project publication, `context baseline`, commits and pushes the onboarding paths ([[context-management]]).
- [[workspace-doctor]]'s `GITFLOW-1` warns on an absent or malformed block (the gate then reads the default) with `fix: <cli> specs init --specs-dir <specs>` (no flags); on an absent block, executing it writes the detected gitflow and clears the finding.

## `dadaia specs upgrade`

- `dadaia specs upgrade [--specs-dir <path>] [--target <int>] [--dry-run]` reads the tree's `specs_pattern_version` and aims at the canonical version (7) by default; `--specs-dir` defaults to the bound context.
- A tree below 6 is refused with no filesystem write, naming the prerequisite: upgrade with an earlier dadaia-workspace line first.
- A tree at 6 walks the one hop: `memory/TECHSTACK.md`'s body is appended under `## Tech Stack` at the end of `memory/ARCHITECTURE.md` and the file deleted, then the tree is re-stamped. A canonical memory still carrying the two-part Principles layout is left byte-identical for the doctor to name.
- On every run, whatever the version: every fixed law section (`<!-- dadaia:fixed <id> -->` blocks) missing or stale in a present file is inserted or refreshed from the library fragment, unfilled placeholder atoms are removed, a `releases/_ideas/` holding nothing but its `AGENTS.md` is removed, and Portuguese `**Status:**` tokens in live trio documents (never `_archive/`) are rewritten to `Approved`, `In review` or `Draft` — so a v6 tree ends doctor-clean.
- Each change prints one line — `[tech-stack]`, `[fixed-section]`, `[placeholder-repair]`, `[status-vocabulary]`, `[stamp] <from> -> <to>`; `--dry-run` plans the same set prefixed `would` and writes nothing; a tree at the target with nothing to repair is a no-op.
- [[workspace-doctor]]'s `SPECS-VERSION` warns on a tree below the canonical version.

## `dadaia migrate`

- Bare `dadaia migrate [--dry-run] [--yes]` migrates `.dadaia/states/spec_contexts.json` from schema 1 to 2: states `ativo`/`inativo` become `alive`/`dead`, `activated_at` becomes `alive_since`, `is_primary` is dropped, `dead_since` added, `states/primary_context.json` deleted and `.dadaia/sessions/` created.
- It prints the plan and asks for confirmation unless `--yes`. `dadaia reconcile` runs the same migration as one of its steps.
- A registry at schema 2 or above, the context store's own schema 3 included, is nothing to do for both `dadaia migrate` and reconcile; a non-numeric schema version is refused with manual intervention required.
- The context store refuses a schema 1 registry with `dadaia migrate` as the fix and reads schema 2 and 3 alike ([[context-management]]).

## Dependencies

[[context-management]], [[workspace-doctor]], [[spec-context-project]].
