---
slug: plugin-packs
title: plugin-packs
category: product
tldr: in-package plugin packs enabled per workspace via `dadaia plugin install`; the 3 stub agents carry real behavior on the plugin/sonnet tier once installed.
summary: The plugin-distribution capability — in-package packs under public/plugins/ (frontend-design + devops), the `dadaia plugin install/list/doctor` CLI on a ports-and-adapters seam (PluginPack/InstalledPlugins core model + PluginStore port + JsonPluginStore adapter), a per-workspace installed_plugins.json ledger, profile-scoped projection that overwrites the projected core stub with the pack's real agent body, core-install precedence so a later public install never reverts an installed pack, plugin doctor per-file status, and the three plugin agents (frontend-engineer, design-specialist, devops-engineer) carrying real behavior on the registry plugin/sonnet tier once their pack is installed. Additive-only (no uninstall this release).
tags:
- plugins
- distribution
- install
- agents
token_estimate: 700
last_updated: '2026-07-04'
release_origin: v0.1.60
---

## Purpose

Three agents ship as behavior-less stubs in the core install — `frontend-engineer` and
`design-specialist` (browser HTML/CSS/JS/TS/React + UX/UI) and `devops-engineer` (CI/CD,
GitHub Actions, gitflow, deploy). They are **not** part of the 9-core roster (constitution
§14). Plugin packs are how an operator **enables** them for a specific workspace, turning
the `[PLUGIN REQUIRED]` stub into a real, dispatchable agent with a genuine SDD-role body.

Packs are distributed **in-package** (no network, offline-safe, privacy-clean): the source
lives under `dadaia_workspace/public/plugins/<pack>/` and is staged like every other public
asset type. Two packs ship: `frontend-design` (agents `frontend-engineer` +
`design-specialist`, skill `browser-frontend-implementation`) and `devops` (agent
`devops-engineer`, skill `github-actions-cicd`). Each pack carries a `pack.json` descriptor.

## Usage flow

1. The operator runs `dadaia plugin install <pack>` (`frontend-design` or `devops`) for a
   workspace. A bogus pack name is a clear usage error (exit 2).
2. Install projects the pack's agents/skills/rules from `.dadaia/agentic/plugins/<pack>/`
   into the runtime roots — **profile-scoped exactly like core `public install --target all`**
   (a claude-only workspace projects only the `.claude/` agent, never a `.codex/` orphan;
   absent profile ⇒ all targets). The pack's real agent body **overwrites the projected core
   stub**; the Codex agent TOML renders the pack model (`gpt-5.3-codex`, the sonnet/plugin
   tier).
3. Install records the pack in the per-workspace ledger `.dadaia/states/installed_plugins.json`
   (`{"schema_version":"1","plugins":[...]}`); re-installing the same pack is a no-op.
4. `dadaia plugin list` shows available vs installed packs; `dadaia plugin doctor` reports
   `[ok]`/`[drift]`/`[missing]` per installed-pack file.
5. **Precedence:** a later core `dadaia public install` reads the ledger and re-projects the
   pack body (not the stub) for any installed plugin — an installed pack agent is never
   silently reverted.

```mermaid
flowchart LR
  SRC["public/plugins/&lt;pack&gt;/"] --> STAGE[".dadaia/agentic/plugins/&lt;pack&gt;/"]
  STAGE -->|dadaia plugin install| PROJ[".claude/.codex/.agents (profile-scoped)"]
  PROJ --> LEDGER[".dadaia/states/installed_plugins.json"]
  LEDGER -->|core public install precedence| PROJ
```

## Typical trigger

The operator wants browser-frontend / design-review / CI-CD agents active in a workspace
(e.g. building a web UI or a deploy pipeline) instead of routing that work to the operator.

## Differentiator

Before v0.1.60 the plugin agents were permanent stubs and the `plugin-scope` rule said "no
install command exists", so plugin-domain work always routed to the operator (and releases
like v0.1.59 needed a recorded `plugin-scope` deviation to let core agents do browser/UX
work). The install command **retires that deviation class**: plugin capability is now a real,
per-workspace opt-in. The design maximizes reuse of proven machinery — it rides the v0.1.58
`_COPY_DIRS` "plugins" staging and mirrors the `harness_profile` ports-and-adapters seam — and
stays shippable by scoping to machinery + minimal-viable content (full skill corpora are the
`plugin-pack-content-libraries` backlog return; uninstall is `plugin-uninstall`).

## Estado runtime tocado

- `dadaia_workspace/public/plugins/<pack>/` — canonical in-package pack source (agents,
  skills, `pack.json`).
- `.dadaia/agentic/plugins/<pack>/` — staged pack assets.
- `.dadaia/states/installed_plugins.json` — the per-workspace installed-plugins ledger.
- `.claude/agents/<name>.md`, `.codex/agents/<name>.toml`, `.agents/skills/` — the projected
  pack agent bodies (overwriting the core stub; profile-scoped).

## Dependencies

- [[public-asset-distribution]] — the plugin projection is an extension of the public
  stage/install/doctor chain (hash-compare, profile-scoping, manifest, `public doctor`).
- [[agent-orchestration]] — the 3 plugin agents and their off-opus (`plugin`/sonnet, `tier:
  3`) model assignment.
- [[tech-stack]] — the registry `plugin` tier and the two "tier" axes.
- [[workspace-init]] — the harness profile that scopes pack projection.
