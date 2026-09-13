---
slug: workspace-init
title: workspace-init
tldr: Idempotent bootstrap of workspace state, the Python venv, the selected harness projections and the governance hooks.
summary: dadaia init provisions the venv, creates the registry's init zones and the selected harness roots, seeds the state files and the harness profile, then stages and installs public assets.
tags: [workspace, init, setup, idempotent]
---

## Bootstrap

- `dadaia init [--workspace PATH] [--skip-assets] [--harness <set>]` is the only verb that operates on a zero workspace, and re-running it is idempotent.
- It provisions `.dadaia/.venv`, creates every zone whose registry creator is `init`, the shared `.agents/skills` root and the chosen harness dirs; the `install` zones (`agentic`, `hooks`) are `public install`'s, and an absent zone of either creator is [[workspace-doctor]]'s `WS-<zone>-missing`.
- What it creates is a view of the one registry, `core/workspace_layout.py` — the root law, `DADAIA_ZONES`, `STATES_CANON` — the same rows `public stage` renders into `DADAIA.md` and `.dadaia/AGENTS.md`, so the tree init lays down and the law's tables cannot disagree ([[public-asset-distribution]]).
- It seeds `states/spec_contexts.json` and `states/server_registry.json` as empty documents without overwriting existing data, and writes `states/harness_profile.json` through the profile store's one writer, shared with `dadaia doctor --fix`.
- Unless `--skip-assets` it runs public stage/install, the one writer of every hook wiring; skipping assets leaves the workspace ungated and the output says so.
- The persisted harness profile accepts `claude`, `codex`, `kimi-code` or `all`; omitted means all, and public install and doctor honor it.
- A harness projection is created only when that harness is selected, and a re-init with a subset merges into the persisted profile in canonical Layer-1 order.
- Init deletes no projection; the git chokepoints (`core/workspace_layout.INSTALLED_GIT_HOOKS`: `pre-commit`, `pre-push`) install separately per repo via `dadaia ci install-hook`, and an installed copy drifting from the shipped script is [[workspace-doctor]]'s `HOOKS-DRIFT-1`.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]].
