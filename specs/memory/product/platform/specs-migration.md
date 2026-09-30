---
slug: specs-migration
title: specs-migration
tldr: specs init brings specs/ to the canon and writes the gitflow, never committing; specs upgrade re-stamps 6-8 as 9, folding flat trios; migrate lifts registry v1.
summary: The verbs that bring persisted state up to what this installation reads — dadaia specs init (onboarding level 3a; absent scaffolds, dadaia upgrades, foreign moves to specs-bkp/, the constitution's gitflow block written or kept), dadaia specs upgrade (a tree stamped 6 or above folds TECHSTACK.md and a flat release trio, runs the doctor's repair set and is re-stamped 9; below 6 it refuses without writing) and dadaia migrate (spec_contexts.json v1 to v2, planned, confirmed, atomic).
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

- `dadaia specs init [--context <ctx>] [--specs-dir <path>] [--name <project>] [--replace-foreign] [--principal <b>] [--integration <b>] [--work-prefix <p>]` is onboarding level 3a: it targets the context's main repo `specs/` (the bound context when `--context` is omitted); with no context resolvable it exits 1 with `fix: <cli> specs init --context <name>`.
- An absent `specs/` gets the canon scaffold ([[public-asset-distribution]]); a dadaia tree (stamped 6 or above) runs `specs upgrade`, then gains only its missing canon files; a constitution whose frontmatter does not parse, or whose `gitflow:` block does not validate, is malformed and refused, exit 1, nothing written (fix: repair its YAML); anything else is foreign.
- The project gitflow is the `gitflow: {principal: <name>, integration: <name>, work: <prefix>}` block of `specs/constitution.md` frontmatter ([[sdd-gate-v3]]); each flag wins over the tree's own valid block, which wins over detection — principal from the local `origin/HEAD` unless it is unset or the integration branch, else `master` when origin has it, else `main`; integration `develop`; work prefix `feature/`, a work branch cut from the integration branch. The names must be valid branch names, principal and integration must differ, and the work prefix may not nest under a role name; an invalid result exits 1 before any write. The same flags twice is a no-op, an operator's custom names are never reset, and stdout names the gitflow written (`[gitflow] …`).
- One frontmatter merge-writer serves both `specs_pattern_version` and `gitflow`: a written key's line is replaced in place, a new one appended, every other key and the body kept byte for byte.
- A foreign tree is replaced only with consent, `--replace-foreign`; without it the run exits 1, writes nothing and prints `fix: <cli> specs init --context <ctx> --replace-foreign`.
- With consent, `specs/` is renamed to `specs-bkp/` in the same repo — tracked files through `git mv`, staged and uncommitted, every byte kept — then scaffolded; when `specs-bkp/` already exists the second backup lands in `specs-bkp/<UTC timestamp>/`, the one backup location the publish commits.
- It also installs the main repo's scoped law where absent, its `<repo-name>` rendered as the project (`--name`, else the main repo's directory name): `AGENTS.md` at the repo root, and `tests/AGENTS.md` only when `tests/` exists; an existing or symlinked target is never overwritten or written through.
- Every written path is printed (`[created]`, `[moved]`, the upgrade's own lines); `specs init` never commits — the project publication, `context baseline`, commits and pushes the onboarding paths ([[context-management]]).
- [[workspace-doctor]]'s `GITFLOW-1` warns on an absent or malformed block (the gate then reads the default) with `fix: <cli> specs init --specs-dir <specs>` (no flags); on an absent block, executing it writes the detected gitflow and clears the finding.

## `dadaia specs upgrade`

- `dadaia specs upgrade [--specs-dir <path>] [--dry-run]` reads the tree's `specs_pattern_version` and stamps only the canonical version (9); `--specs-dir` defaults to the bound context.
- A tree below 6 is refused with no filesystem write, naming the prerequisite: upgrade with an earlier dadaia-workspace line first.
- A tree still holding `memory/TECHSTACK.md` has its body appended under `## Tech Stack` at the end of `memory/ARCHITECTURE.md` and the file deleted; a candidate document still flat at a release root moves verbatim into that release's next `rc-<N>/`, judged by shape, a closed `rc-<N>/` never touched; an upgradable tree (stamped 6, 7 or 8) is then re-stamped 9. An `ARCHITECTURE.md` still carrying the two-part Principles layout is refused whole, exit 1, nothing written, naming the rewrite it needs.
- On every run, whatever the version: a `releases/_ideas/` holding nothing but its `AGENTS.md` is removed, Portuguese `**Status:**` tokens in each release's live candidate (never a closed `rc-<N>/` or `_archive/`) are rewritten to `Approved`, `In review` or `Draft`, the doctor's own `specs` repair set runs (fixed law sections, placeholder atoms, scaffolded law files, [[workspace-doctor]]) and every ledger whose `check` fails is re-derived by its own script; an error the repair cannot clear prints `[refused]` with its `fix:` line and exits 1.
- Each change prints one line — `[ideas-repair]`, `[status-vocabulary]`, `[tech-stack]`, `[candidate]`, `[repair]`, `[stamp] <constitution> -> 9`; `--dry-run` plans the same set prefixed `would` and writes nothing; a canonical tree with nothing to repair prints `[ok] … no-op`.
- `dadaia_workspace/core/specs_version.py`'s `state` is the one reader of a tree's state — `absent`, `malformed`, `foreign`, `upgradable` or `canonical`, with its one fix; onboarding's `specs` step reports it ([[workspace-init]]).

## `dadaia migrate`

- Bare `dadaia migrate [--dry-run] [--yes]` migrates `.dadaia/states/spec_contexts.json` from schema 1 to 2: states `ativo`/`inativo` become `alive`/`dead`, `activated_at` becomes `alive_since`, `is_primary` is dropped, `dead_since` added, `states/primary_context.json` deleted and `.dadaia/sessions/` created.
- It prints the plan and asks for confirmation unless `--yes`. `dadaia reconcile` runs the same migration as one of its steps.
- A registry at schema 2 or above, the context store's own schema 3 included, is nothing to do for both `dadaia migrate` and reconcile; a non-numeric schema version is refused with manual intervention required.
- The context store refuses a schema 1 registry with `dadaia migrate` as the fix and reads schema 2 and 3 alike ([[context-management]]).

## Dependencies

[[context-management]], [[workspace-doctor]], [[spec-context-project]].
