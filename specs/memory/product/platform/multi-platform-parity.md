---
slug: multi-platform-parity
title: multi-platform-parity
category: product
tldr: Claude Code, Codex, and PI receive truthful runtime-specific projections from one canonical public source.
summary: >-
  Defines Layer-1 projection parity without pretending the harnesses have identical
  primitives. Each harness derives its own entities from the core definitions; Claude remains
  Layer-1-only. Git chokepoints protect commit/push independently of harness hooks.
tags:
- codex
- claude-code
- pi
- parity
- multi-platform
token_estimate: 271
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

Canonical assets originate under `dadaia_workspace/public/` and project to each
runtime's native surface. Shared intent stays consistent; runtime capabilities remain
honest.

## Layer 1

- Claude Code receives agents, skills, rules, workflows, and Python hook registration.
- Codex receives `AGENTS.md`, native custom-agent TOML, skills, Starlark command rules,
  and interactive hook registration. `codex exec` does not rely on interactive hooks.
- PI receives `SYSTEM.md`, prompts, skills, and a post-trust TypeScript extension that
  delegates write decisions to the Python gate.

`.pi/**` is executable after trust and therefore contains no secrets or operator-local
paths. Generated projection files are never edited in place.

## Harness derivation

Every entry harness derives its own entities from the same core definitions; `fake` is
the deterministic test adapter. Personas are shared,
while model/profile selection remains harness-specific.

## Independent Boundaries

The Git hooks `pre-commit-presence-gate.sh` and `pre-push-ci-gate.sh` run regardless of
harness hook support. The first is advisory for concurrency; the second enforces CI and
the exact-commit security verdict.

## Projection Validation

`dadaia public doctor` checks manifest hashes, runtime-specific rendering, skill/agent
references, policy resolution, plugin precedence, and public privacy. Unknown install
targets fail; profile-aware install/doctor operate only on configured harnesses.

## Dependencies

[[public-asset-distribution]], [[harness-claude-code]], [[harness-codex]],
[[harness-pi]], [[sdd-gate-v3]].
