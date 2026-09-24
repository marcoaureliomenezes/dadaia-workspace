---
slug: public-asset-distribution
title: public-asset-distribution
tldr: Public assets staged once, projected into the root map, scoped AGENTS.md, .agents/ and each harness's files, with scaffold and scripts; doctor reports drift.
summary: The stage, install and doctor chain that distributes the agentic surface into a workspace — hash-compared overwrite, rendered personas, whole-folder skills, per-harness hook and agent files derived from one registry, the specs scaffold, and a privacy gate.
tags: [public, assets, distribution, projection, privacy]
sources:
  - dadaia_workspace/features/public/**
  - dadaia_workspace/infrastructure/projection.py
  - dadaia_workspace/infrastructure/projection_rules.py
  - dadaia_workspace/infrastructure/public_assets.py
  - dadaia_workspace/infrastructure/public_assets_common.py
  - dadaia_workspace/infrastructure/install_plan.py
  - dadaia_workspace/infrastructure/install_helpers.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/**
  - dadaia_workspace/infrastructure/privacy_check.py
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/public/scaffold/**
  - dadaia_workspace/public/templates/**
  - dadaia_workspace/public/scripts/**
  - dadaia_workspace/cli/commands/public.py
---

## The chain

- `dadaia public stage` copies `dadaia_workspace/public/` into `.dadaia/agentic/<type>/` with a SHA256 manifest that carries no timestamp, so an unchanged stage writes identical bytes, rendering the registry tables (zones, root canon, repo exclusions, specs canon) into the law fragments so every canon table in the projected law is the registry itself.
- `dadaia public install` projects the staged assets into the authored set — the root `AGENTS.md` map, the scoped `AGENTS.md` family, `.agents/skills/`, `.agents/agents/` — plus, per registered harness, its own agent and hook files: `.claude/settings.json` and per-entry symlinks under `.claude/`, `.codex/{config.toml,hooks.json,rules,agents/*.toml}`, `.cursor/{hooks.json,agents/*.md}`, `.devin/hooks.v1.json`, `.github/{hooks/*.json,agents/*.agent.md}` and the hook wrappers under `.dadaia/hooks/`; Kimi Code reads the shared tree and gets no files of its own ([[harness-kimi-code]]).
- One harness registry drives every per-harness file: each harness is one record naming its directory, its persona transcode and its hook format, so adding a harness is one data row ([[agentic-entities]]).
- Hooks are the Python package `dadaia_workspace/hooks/`, rendered into each harness's own hook format; a harness action with no pre-event is declared ungated (Cursor file writes, one `public doctor` WARN).
- Install compares content, not existence: a differing staged hash overwrites without `--force`, which is reserved for a hand-edited projection; an operator's own keys in a shared settings file are left alone.
- A skill is a folder projected whole to `.agents/skills/<name>/`; `.claude/skills/<name>` is a relative symlink to it, or a hash-verified copy where links are unavailable, and the install ledger records which.
- The three `agents/dd-*.md` personas stage generic and render into `.agents/agents/` with the resolved model and effort from `.dadaia/states/agent_model_policy.json`; the Codex transcode fails closed without a model.
- `public install` refuses the dadaia-workspace source repository root unless `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1`.

## Doctor

- `dadaia public doctor` compares source against staging, then staging against each projection, printing `[ok]`, `[missing]`, `[drift]` or `[foreign]` per file and exiting non-zero on any mismatch; a persona compares against its rendered form, so an applied policy reads `[ok]` and a hand-edit `[drift]`.
- `SYMLINK-TARGET-1` attests every ledgered link: a symlink resolving to its `.agents/` path or a hash-equal copy, anything else one finding with `fix: .dadaia/.venv/bin/dadaia public install --force`.
- The privacy gate runs over source and staged assets and reports `[ok] public-privacy` only on a clean surface; CI treats it as a release gate.
- `install` and `doctor` cover the harnesses in `.dadaia/states/harness_profile.json` plus the shared authored set; `dadaia harness add <name>` is the one way a harness joins ([[workspace-init]]); an unledgered entry inside a harness directory is `dadaia doctor`'s `WS-<harness>-slop` ([[workspace-doctor]]).

## Scaffold and consumer fan-out

- The scaffolded `specs/` tree is the canon — `AGENTS.md`, an English `constitution.md`, `memory/` (`ARCHITECTURE.md` with `## Principles`, `## Tech Stack`, `## Structure`; `QUALITY.md` with `## Principles`, `## Test architecture`, `## Gates`; `product/`), `releases/`, `backlog/`, `bugs/`, `audits/`, `ADRs/` — stamped `specs_pattern_version: 7`; `dadaia specs init` writes it ([[specs-migration]]).
- The scaffold writes only absent files, each through one `O_CREAT|O_NOFOLLOW` open: an existing file or a symlinked destination is skipped, and a path escaping the tree through a symlinked parent is never written.
- Every scoped scaffold `AGENTS.md` is the system of record of its area, at most 4096 bytes (the root map 8192, a `SKILL.md` 6144 — `tests/contract/test_context_map.py`); `TREE-5` heals each by shipped hash, and operator-owned files are never overwritten ([[workspace-doctor]]).
- Repo templates land with `dadaia specs init`: `repo-AGENTS.md` as the main repo's `AGENTS.md`, `tests-AGENTS.md` only into an existing `tests/` directory holding none; once written they are the operator's and never overwritten.
- An installed file still carrying `<ANGLE-BRACKET>` placeholders is `AGENTS-PLACEHOLDER-1` or `MEM-PLACEHOLDER-1` in `dadaia doctor`'s `specs` section.
- Consumer-repo `AGENTS.md` fan-out is gated by the canonical banner: absent creates, a stale banner is restored as `[updated]`, a bannerless file is `[foreign]` and never overwritten; a symlinked destination file is `[foreign]`.

## Shipped scripts

- `dadaia_workspace/public/scripts/` stages into `.dadaia/agentic/scripts/`: `pre-push-ci-gate.sh`, the source the hook installer copies into each repo's `.git/hooks/pre-push` ([[context-management]], [[sdd-gate-v3]]); `certify-dadaia-workspace.sh`, a one-command entry to `dadaia certify` through the workspace venv ([[consumer-agent-support]]); `lint-memory-atoms.py`, a standalone entry to the package's memory-atom lint; `lint-dadaia-cli-reachability.py`, which fails when a persona's `dd-cli-library` grant disagrees with its `Bash` tool or a public skill-script citation names a missing script or verb.

## Dependencies

[[agentic-entities]], [[pypi-distribution]], [[workspace-init]], [[workspace-doctor]], [[context-management]], [[specs-migration]], [[sdd-gate-v3]], [[consumer-agent-support]], [[harness-kimi-code]].
