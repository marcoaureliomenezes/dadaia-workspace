---
slug: harness-codex
title: Harness — Codex
category: product
tldr: 'Entry harness on the operator''s Codex subscription: TUI with deterministic hooks, Starlark command policy, and a .codex/ projection of agents, skills and rules.'
summary: Capability and scaffold truth for the Codex harness — the interactive TUI
  enforcement posture, the native AGENTS.md read path, the Starlark command policy, the
  Codex-native tier identity of projected agents, and what a Codex-only workspace
  installation contains.
tags:
- harness
- codex
- projection
- enforcement
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

Codex is an entry harness: the operator's `codex` TUI, governed by `AGENTS.md` read
natively up-tree plus the `.codex/` projection. It runs the same nine-role agent roster
against the same SDD documents as every other harness; ordered work is document-governed,
not runtime-driven.

## Usage flow

1. Operator launches `codex` at the workspace root; `AGENTS.md` loads natively;
   `SessionStart` ctx-inject loads the bound context once per session.
2. Interactive sessions get the deterministic gate: PreToolUse `pre_gate` (matcher
   `^(apply_patch|Edit|Write|Bash)$`) + matcher-less PostToolUse heartbeat, registered
   in `.codex/hooks.json` via self-locating wrappers under `.dadaia/hooks/codex-*`.
3. **Headless asymmetry (honesty):** `codex exec` fires NO hooks (upstream codex-cli
   defect, live-verified). Any headless Codex invocation is enforced by the git
   chokepoints alone.
4. Command policy is evaluated natively from `.codex/rules/*.rules` (Starlark prefix
   rules over venv-form paths), not from configuration keys.

## Typical trigger

Operator preference for the Codex TUI, and any session where native `AGENTS.md`
discovery plus Starlark command policy is the desired posture.

## Differentiator

Runs on the operator's Codex subscription with command policy expressed natively in
Starlark. The interactive/headless enforcement split is the key operational fact: never
assume a hook fired in an `exec` run.

## Runtime state touched

Scaffold projected by `dadaia public install --target codex`: `.codex/config.toml`
(header + per-agent config blocks only — no inert keys), `.codex/hooks.json`,
`.codex/agents/` (12 TOML personas — tier identity is Codex-native
`(model id × model_reasoning_effort)`, registry-derived via
`core/model_registry.codex_tier_views()`: deep→high, dispatch→medium reasoning
effort, and rendering fails loudly when two tiers collapse to one `(id, effort)`
pair; doctor lint D-CX-4 blocks Anthropic tier names (Opus/Sonnet/Haiku) and Claude
model/path/tool-name leaks in Codex-projected artifacts), `.codex/rules/`
(Starlark command policy), `.codex/skills/` (context adapters), and the projected
`.codex/DADAIA.md` law file. Wrappers live in `.dadaia/hooks/codex-*`.
A Codex-only workspace = `--target codex` (+ shared `--target agents`). This isolation
is **enforced mechanically at init** — `dadaia init --harness codex` scaffolds
only the `.codex/` surface + the `.dadaia/hooks/codex-*` wrappers and persists the
profile ([[workspace-init]]) — not merely documented.

## Dependencies

- [[tech-stack]] — roster + model catalog single source.
- [[sdd-gate-v3]] — gate + chokepoint mechanism, incl. the headless asymmetry.
- [[public-asset-distribution]] — the `.codex/` projection pipeline.
- [[agent-orchestration]] — the roster that runs inside this harness.
