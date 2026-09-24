---
slug: workspace-init
title: workspace-init
tldr: Idempotent bootstrap — dadaia init <dir> --harness <name> [--repo <url>] — venv, zones, law, one harness; with --repo the first context ALIVE and bound.
summary: dadaia init takes a required directory and one registered harness, provisions the venv, the registry's init/install zones, the shared skills root and that harness's projection, seeds the states and the harness profile, stages and installs public assets; with --repo it clones the first repo, makes it ALIVE, binds it and installs the pre-push hook. dadaia harness add extends the roster later.
tags: [workspace, init, setup, idempotent]
sources:
  - dadaia_workspace/cli/commands/init.py
  - dadaia_workspace/cli/commands/harness.py
  - dadaia_workspace/features/workspace/**
  - dadaia_workspace/infrastructure/python_env.py
  - dadaia_workspace/infrastructure/json_harness_profile_store.py
  - dadaia_workspace/core/workspace_resolver.py
---

## Bootstrap

- `dadaia init <dir> --harness <name> [--repo <url>] [--skip-assets]` is the only verb that works on an empty directory: `<dir>` is required (created if absent, refused with one `fix:` if it holds a foreign tree, never resolved from the cwd), `--harness` names one registered harness (`claude`, `codex`, `kimi-code`, `cursor`, `devin`, `copilot`), and a re-run is idempotent.
- It provisions `.dadaia/.venv`, every `.dadaia/` zone whose creator is init or install, and `.agents/skills`; the harness's own directory comes from its projection. An absent zone is [[workspace-doctor]]'s `WS-<zone>-missing`.
- The tree it lays down is a view of `dadaia_workspace/core/workspace_layout.py` — the root law, `DADAIA_ZONES`, `STATES_CANON` — the same rows `dadaia public stage` renders into the law files ([[public-asset-distribution]]).
- It seeds `states/spec_contexts.json` and `states/server_registry.json` as empty documents without overwriting existing data ([[server-registry]]).
- `states/harness_profile.json` is the roster, written through the profile store's one writer (shared with `dadaia doctor --fix`); a re-init with another harness merges into the persisted roster, never narrowing it.
- Unless `--skip-assets`, init runs public stage and install, the one writer of every hook wiring; with `--skip-assets` the output warns the workspace is ungated until `dadaia public install` runs.
- `dadaia harness add <name>` stages if needed, installs that harness's set and appends it to the roster; `dadaia harness list` reads it.

## First project

- With `--repo <url>`, init clones into `repos/<slug>/` and composes the context verbs — `create --main-repo <slug>`, `alive`, the session bind (printing the `--print-env` line) — then installs the pre-push hook; a re-run with the same URL reuses the context, and a failed clone prints the same command as its `fix:` ([[context-management]]).
- Without `--repo`, init closes with three lines: sessions launch at the root, the harness's law-loading note, and the `dadaia context create <name> --main-repo <slug> --url <url>` that makes the first project; a single-repo workspace is the degenerate multi-repo case.
- `install_git_hooks` in `dadaia_workspace/features/workspace/bootstrap.py` is the one installer of the git hook (`pre-push`, from `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`), called by `init --repo` and by `dadaia ci install-hook`; a drifted installed copy is [[workspace-doctor]]'s `HOOKS-DRIFT-1`.
- Init deletes no projection.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]], [[context-management]].
