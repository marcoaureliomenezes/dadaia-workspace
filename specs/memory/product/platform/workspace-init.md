---
slug: workspace-init
title: workspace-init
category: product
tldr: entry point; creates .dadaia/, .venv, Python governance hooks and an idempotent structure.
summary: entry point; creates .dadaia/, .venv, Python governance hooks and an idempotent
  structure; PreToolUse registered as ONE Python command (python -m
  dadaia_workspace.hooks.pre_gate), not bash; ctx-inject.sh retained only as a
  non-installed fallback.
tags:
- workspace
- init
- setup
- idempotent
agent_tier: self-pull
token_estimate: 850
last_updated: '2026-07-02'
release_origin: v0.1.48
---

CLI surface: `dadaia init [--workspace PATH] [--skip-assets]` · Closure: sdd-release-lifecycle-v1

## Purpose

The product's entry point. Bootstraps a new workspace by creating the idempotent structure under `.dadaia/` (academy, agentic, reports, scripts, states, src), the Python virtualenv (`.venv`), and the runtime directories **`.claude/`, `.agents/skills/`, `.codex/`** — `.pi/` is NOT created by init: it arrives whole via `dadaia public install --target pi|all` (with `--skip-assets`, `.pi/` stays absent until a manual install). Without `--skip-assets`, init stages+installs the canonical public assets (agents, skills, rules, workflows, scripts, templates, schemas, data, personas, lifecycle_fragments, pi) and configures the governance hooks in `.claude/settings.json` and `.codex/hooks.json`.

The governance hooks are the Python package `dadaia_workspace/hooks/` (8 modules: `__init__`, `_common`, `pre_gate`, `sdd_gate`, `root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`), working on Windows, macOS and Linux without Git Bash or WSL. Per-runtime registration via `infrastructure/runtime_config.py`: on Claude, `python -m dadaia_workspace.hooks.<name>` commands; on Codex, executable wrappers at `.dadaia/hooks/codex-*` referenced in `.codex/hooks.json` — wrapper and matcher registration mechanics are owned by [[public-asset-distribution]]. The PreToolUse is ONE single command (`pre_gate`: root-whitelist → venv-guard → SDD gate, first-block-wins). The git chokepoints (pre-commit lease gate + pre-push CI/security gate) are installed separately by `dadaia ci install-hook`.

`workspace/service.py` recognizes both the old path (`.sh`) and the new Python command to avoid double registration in migrated workspaces. The bash script `ctx-inject.sh` exists in `.dadaia/scripts/` as a legacy artifact, but is no longer the registered hook mechanism.

It is the only feature that can run in a zero workspace — without it, no other feature has anywhere to write state.

## Usage flow

  1. The operator runs `dadaia init` (without `--workspace`: walks up from cwd looking for the sentinel `.dadaia/states/spec_contexts.json` — a bare `.dadaia/` dir without `states/` is skipped as sub-repo/partial init — falling back to cwd when none is found; with `--workspace <dir>`, that dir is authoritative, no ancestor walk — `core/workspace_resolver.py`).
  2. The CLI creates the idempotent tree under `.dadaia/` and the runtime dirs `.claude/`, `.agents/skills/`, `.codex/` (`.pi/` comes from the public install).
  3. `PythonEnvironmentManager` provisions the Python `.venv` using `PLATFORM.venv_scripts_dir` and `PLATFORM.venv_exe_suffix` for cross-platform paths.
  4. Runs automatic `public stage` and `public install` (unless `--skip-assets`).
  5. Installs the `repos.xlsx` catalog into `.dadaia/src/`.
  6. Registers the hook entries: `.claude/settings.json` with the Python command; `.codex/hooks.json` pointing at the `.dadaia/hooks/codex-*` wrappers — single PreToolUse via `pre_gate`.



## Typical trigger

First run in a new workspace, or after cloning a repository that does not yet have a local `.dadaia/`.

## Differentiator

Makes the workspace reproducible from the first command — agents and the operator discover and use distributed assets (skills, workflows, agents) without manual configuration on each new machine. Without init, every workspace would start from scratch or require manual copy-paste of configs.

## Runtime state touched

  * `.dadaia/states/spec_contexts.json` — contexts list (empty until first creation)
  * `.dadaia/academy/academy.json` — courses list (empty)
  * `.dadaia/src/repos.xlsx` — static catalog of known repos
  * `.dadaia/scripts/ctx-inject.sh` — legacy bash script (still present; no longer the registered hook)
  * `.venv/` — Python virtualenv (executor path resolved by `PLATFORM.venv_scripts_dir`/`PLATFORM.venv_exe_suffix`)
  * `.claude/settings.json` — hook entries registered with Python commands (`ctx_inject`, single `pre_gate`, `sdd_post_gate`); per-runtime matchers: [[sdd-gate-v3]] enforcement matrix
  * `.codex/hooks.json` — same entries in Codex format via the `.dadaia/hooks/codex-*` wrappers (wrapper/matcher mechanics: [[public-asset-distribution]])



## Dependencies

  * No feature precedes init — it is the first thing that runs in a zero workspace.
  * Init internally triggers `public-asset-distribution` (stage + install) to populate the tools' runtime dirs.
