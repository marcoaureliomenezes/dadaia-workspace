---
slug: workspace-init
title: workspace-init
category: product
tldr: Idempotent bootstrap of workspace state, Python venv, selected harness projections, and governance hooks.
summary: >-
  `dadaia init` creates the canonical `.dadaia/` runtime, provisions
  `.dadaia/.venv`, records the harness profile, stages/installs public assets, and
  configures runtime hooks without creating repository-local state.
tags:
- workspace
- init
- setup
- idempotent
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

`dadaia init [--workspace PATH] [--skip-assets] [--harness <set>]` is the only
feature that operates on a zero workspace. Re-running it is idempotent.

## Bootstrap

Init creates the canonical workspace `.dadaia/` subdirectories, the Python virtual
environment at `.dadaia/.venv`, an empty context registry, and the selected harness
roots. Unless `--skip-assets` is used, it runs public stage/install and registers the
merged Python gate, context injection, and post-gate hooks for supported runtimes.

The persisted harness profile accepts `claude`, `codex`, `kimi-code`, or `all`; omitted means
all. Public install and doctor honor that profile. A harness projection is created only
when that harness is selected or assets are installed for all targets. A re-init with a harness subset
**merges** into the persisted profile (canonical L1 order) — init deletes no projection,
so it never un-manages one; narrowing the managed set is a deliberate operator state
edit, never an init side effect (bug init-harness-profile-silent-narrowing).

Git chokepoints are installed separately through `dadaia ci install-hook` from
`pre-commit-presence-gate.sh` and `pre-push-ci-gate.sh`.

## Runtime State

- `.dadaia/.venv/`
- `.dadaia/states/spec_contexts.json`
- `.dadaia/states/harness_profile.json`
- `.dadaia/agentic/`
- `.claude/`, `.codex/`, `.kimi-code/`, `.agents/` according to the profile

No `src/` cache or repo-local `.dadaia/` is part of workspace initialization.

## Dependencies

[[public-asset-distribution]], [[multi-platform-parity]], [[workspace-doctor]].
