---
slug: context-portability
title: context-portability
tldr: dadaia export writes one export-v1 artifact, soft JSON or a hard tar.gz adding the unpushed lane and wt-rc work; init DIR --from <artifact> replicates it.
summary: Moving a workspace — export only reads the registry and writes .dadaia/dist/spec-contexts.json, or with --hard .dadaia/dist/workspace-export.tar.gz holding that JSON plus a secret-scanned bundle of each open lane and wt-rc tree and each pause bundle; init --from validates the artifact against the one export-v1 schema before any write, installs every harness it names, registers its contexts DEAD through the guarded insert, lists what it cannot replicate or reach, places the bundles where worktree resume finds them and prints the context alive line of each context ALIVE in the artifact.
tags: [context, export, init, portability, worktrees]
sources:
  - dadaia_workspace/features/export/**
  - dadaia_workspace/cli/commands/export.py
  - dadaia_workspace/cli/commands/init.py
  - dadaia_workspace/public/schemas/export-v1.schema.json
---

## Why one atom

- Export and `init --from` are the two halves of one user act — carrying a workspace to another directory or machine — and share one artifact format; `ExportService` alone writes and reads it.

## The artifact

- `export-v1` is one schema for both artifacts' JSON (`dadaia_workspace/public/schemas/export-v1.schema.json`): `schema_version` `export-v1`, `dadaia_version` (the installed version, else `editable`), `harnesses` (the workspace roster from `harness_profile.json`) and per context its main repo `slug`, `name`, `state` (the registry's lowercase `alive`/`dead`), `repo_url` and `associated_repos` (`slug` + `url`).
- A main or associated repo with no remote is recorded with url `null`.
- The artifact carries no branch and no timestamp; the format version is the only version pinned, `dadaia_version` is read for display only.

## Export

- `dadaia export [--workspace <root>]` reads the registry and changes nothing in it; it writes `.dadaia/dist/spec-contexts.json`, overwritten each run, and prints the path and the context count.
- `dadaia export --hard` writes `.dadaia/dist/workspace-export.tar.gz` instead, built in a scratch directory under `.dadaia/tmp/` and moved into place atomically: the JSON as member `spec-contexts.json`, then one `<repo>/<name>.bundle` member per bundle, every member name POSIX-spelled.
- The bundles come from the worktree owner's rows alone ([[worktrees]]): each pause bundle as it sits in `.dadaia/dist/<repo>/`, and for each open lane or `wt-rc` tree a bundle of the commits no `origin` ref holds, written by pause's one bundle writer; a tree origin already holds whole carries nothing, and a job or task tree is never carried. A dirty open tree refuses the export with pause's commit-first fix line and the tree stays as it is.
- Every bundle is scanned before the archive is written by the export feature's own scan, the pre-push denylist and baseline matcher ([[sdd-gate-v3]]) handed to it by the composition root, the terms the repo's own name carries dropped, over the objects it adds to its repo, unbundled into a scratch bare repo that borrows the repo's objects and `origin` refs, so nothing is written into the repo; any hit refuses with the masked findings and writes no archive.
- Every scan git call runs through one runner with a timeout; git missing or past its timeout is one refusal. A scan refusal relays git's own reason and names the act that clears its cause: git that cannot start, an unreadable bundle or scratch directory (an `Agent action:` naming that path), a full or unwritable disk in git's own words (the `Agent action:` to free space and write permission under `.dadaia/tmp`, then rerun the export), a missing prerequisite (`git -C <repo> fetch origin`), an object read failure (`git -C <repo> fsck`), and a damaged pause bundle (an `Operator action:` to rule whether it is restored from a copy or discarded; paused work is never deleted by an agent).
- A symlinked bundle refuses, and a pause bundle whose repo is not checked out refuses with `context alive <ctx>`: it cannot be scanned against its repo. Export runs no visibility probe and calls no host CLI.
- `.dadaia/dist/` admits only `spec-contexts.json`, `workspace-export.tar.gz` and a folder per registered repo slug, so [[workspace-doctor]]'s `--fix` never moves an artifact or a pause bundle.

## `init DIR --from <artifact>`

- `init DIR --from <artifact>` ([[workspace-init]]) reads the artifact, soft or hard, before writing anything: a missing or unreadable file, invalid JSON, anything the `export-v1` schema refuses (an old `spec-contexts-export-v1` file included) or a harness name the registry does not know refuses with one fix line, re-exporting with the current dadaia-workspace.
- A hard artifact's members are checked before any extraction, by one member check serving read and restore: the JSON once and within its size cap, every other a regular file named `<repo>/<name>.bundle` once, with no `.`/`..` step, link or absolute path, its repo one of the artifact's contexts; a bundle whose path in `.dadaia/dist/` is already taken, by a file or a link, dangling or not, refuses with nothing written, since that file may be the only copy.
- `--from` with `--repo` refuses with one fix line; every `init` fix line carries `--from` when it was given; with no terminal only DIR is required, and that fix line adds no `--harness`; an artifact naming no harness refuses with the init line carrying the first entry harness.
- It installs every harness the artifact names, then registers each context DEAD through the same guarded insert as `dadaia context create` ([[context-management]]): a context holding a url-less repo with no `repos/<slug>` checkout to adopt prints `not replicated: no remote`, and the run ends that list with one fix line, adding a remote to each url-less repo and exporting again; a known name, an invalid name or a slug another context owns prints `skipped` with the reason; each registered one prints `registered (dead)`.
- Each url of a registered context is probed with `git ls-remote` through the git client's url guard, with a timeout, no terminal prompt and ssh in batch mode, `-o BatchMode=yes` appended to the user's own ssh command (`GIT_SSH_COMMAND`, else `core.sshCommand`, else `GIT_SSH`, else `ssh`); an unreachable url is listed, never fatal.
- A hard artifact's bundles are extracted with the stdlib `tarfile` `data` filter to `.dadaia/dist/<repo>/<name>.bundle`, never overwriting, where `worktree resume` finds them; a soft artifact has none. The run ends with the venv CLI's `context alive <name>` line for each context ALIVE in the artifact.
- `init --from` serves a fresh and an existing workspace alike, and clones nothing: `context alive` clones, then `worktree resume` brings each bundled tree back.

## Runtime state

`.dadaia/dist/spec-contexts.json` and `.dadaia/dist/workspace-export.tar.gz` (written by export); `.dadaia/dist/<repo>/<name>.bundle` (pause bundles, and those a hard artifact restores); `.dadaia/states/spec_contexts.json` (read by export, new DEAD records by `init --from`).

## Dependencies

[[context-management]], [[workspace-init]], [[worktrees]], [[sdd-gate-v3]], [[workspace-doctor]].
