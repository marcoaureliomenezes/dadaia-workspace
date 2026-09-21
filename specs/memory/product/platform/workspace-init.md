---
slug: workspace-init
title: workspace-init
tldr: One-line idempotent bootstrap — init <dir> --harness <name> [--repo <url>] — venv, zones, law, one harness; with --repo the first context ALIVE and bound.
summary: dadaia init takes a required directory and exactly one registered harness, provisions the venv, the registry's init zones, the authored set and that harness's directory, seeds the states and the harness profile, stages and installs public assets; with --repo it clones the first repo and composes create/alive/bind plus the pre-push hook. `harness add` is the only later extension.
tags: [workspace, init, setup, idempotent]
---

## Bootstrap

- `dadaia init <dir> --harness <name> [--repo <url>] [--skip-assets]` is the only verb that operates on a zero workspace: `<dir>` is a required positional (created if absent, refused with one `fix:` if it holds a foreign tree — the directory is an argument, never resolved from the cwd or an ancestor walk), `--harness` names exactly one `HARNESS_RECORDS` entry (`all` and comma sets died at 0.4.7 c8), and re-running it is idempotent.
- It provisions `.dadaia/.venv`, creates every zone whose registry creator is `init`, the shared `.agents/{skills,agents}` roots and the one chosen harness's directory; the `agentic` and `hooks` zones are created by init from the same registry table the doctor reads, and an absent zone of either creator is [[workspace-doctor]]'s `WS-<zone>-missing`.
- What it creates is a view of the one registry, `core/workspace_layout.py` — the root law, `DADAIA_ZONES`, `STATES_CANON` — the same rows `public stage` renders into `DADAIA.md` and `.dadaia/AGENTS.md`, so the tree init lays down and the law's tables cannot disagree ([[public-asset-distribution]]).
- It seeds `states/spec_contexts.json` and `states/server_registry.json` as empty documents without overwriting existing data, and writes `states/harness_profile.json` through the profile store's one writer, shared with `dadaia doctor --fix`.
- Unless `--skip-assets` it runs public stage/install, the one writer of every hook wiring; skipping assets leaves the workspace ungated and the output says so.
- `.dadaia/states/harness_profile.json` is the roster: init writes the one chosen harness, `dadaia harness add <name>` stages if needed, installs that harness's set and appends it, `harness list` reads it; `public install` and `public doctor` cover the roster plus the shared authored set, and a missing profile is read once as the harness directories present at the root, never as "all" ([[public-asset-distribution]]).
- With `--repo <url>`, init clones into `repos/<slug>/` through the context lifecycle's own clone, then composes the existing `create --main-repo <slug>`, `alive` and the session binding (the `--print-env` line is printed) and installs the pre-push chokepoint — one caller of the lifecycle, never a second implementation; a re-run with the same URL reuses the existing context, and a failed clone leaves a truthful `fix:` (the same command, once the URL is reachable) ([[context-management]]).
- Without `--repo`, init closes with three lines: sessions launch at the root, the harness's law-loading note, and where projects live plus the single `dadaia context create --main-repo <slug>` that makes the first one; no other context verb is named — a single-repo workspace is the degenerate multi-repo case.
- Init deletes no projection; the git chokepoints (`core/workspace_layout.INSTALLED_GIT_HOOKS`) have one installer, `features/workspace/bootstrap.install_git_hooks`, called by `init --repo` and by `dadaia ci install-hook` alike, and an installed copy drifting from the shipped script is [[workspace-doctor]]'s `HOOKS-DRIFT-1`.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]].
