---
slug: workspace-init
title: workspace-init
category: product
tldr: Idempotent bootstrap of workspace state, the Python venv, the selected harness projections and the governance hooks.
summary: dadaia init creates the canonical runtime tree, provisions the venv, records the harness profile, stages and installs public assets, and configures runtime hooks.
tags: [workspace, init, setup, idempotent]
---

## Bootstrap

- `dadaia init [--workspace PATH] [--skip-assets] [--harness <set>]` is the only verb that operates on a zero workspace, and re-running it is idempotent.
- It creates the canonical `.dadaia/` subdirectories, the virtual environment at `.dadaia/.venv`, an empty context registry and the selected harness roots.
- Unless `--skip-assets` it runs public stage/install and registers the gate, injection and post-gate hooks for the supported runtimes.
- The persisted harness profile accepts `claude`, `codex`, `kimi-code` or `all`; omitted means all, and public install and doctor honor it.
- A harness projection is created only when that harness is selected, and a re-init with a subset merges into the persisted profile in canonical Layer-1 order.
- Init deletes no projection, and git chokepoints install separately via `dadaia ci install-hook`.
- Runtime state is `.dadaia/.venv/`, `.dadaia/states/spec_contexts.json`, `.dadaia/states/harness_profile.json`, `.dadaia/agentic/`, and the harness roots the profile selects.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]].
