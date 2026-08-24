---
slug: harness-codex
title: Harness — Codex
category: product
tldr: 'Entry harness on the operator''s Codex subscription: TUI and headless exec, version-qualified live-certified hook fire, Starlark policy, .codex/ projection.'
summary: Capability and scaffold truth for the Codex harness — the version-qualified
  enforcement posture (hooks live-certified at codex-cli 0.144.4 for both TUI and headless
  exec, every other version probe-driven through dadaia certify's codex-live-probe against
  the installed binary), the native AGENTS.md read path that carries the law once to parent
  and delegated agents alike, the compacted role-only persona TOMLs, the behavioral-fidelity
  derivation check, the Starlark command policy, the Codex-native tier identity of projected
  agents, and what a Codex-only workspace installation contains.
tags:
- harness
- codex
- projection
- enforcement
last_updated: '2026-08-24'
release_origin: v0.3.0
---

## Purpose

Codex is an entry harness: the operator's `codex` TUI and its headless `codex exec`,
governed by `AGENTS.md` read natively up-tree plus the `.codex/` projection. It runs the
same nine-role agent roster against the same SDD documents as every other harness; ordered
work is document-governed, not runtime-driven.

## Usage flow

1. Operator launches `codex` at the workspace root; `AGENTS.md` loads natively —
   verified to deliver the law exactly **once** per session, since this harness resolves
   no import chain that would deliver a second copy — and `SessionStart` ctx-inject loads
   the bound context once per session.
2. Sessions get the deterministic gate: PreToolUse `pre_gate` (matcher
   `^(apply_patch|Edit|Write|Bash)$`) + matcher-less PostToolUse heartbeat, registered
   in `.codex/hooks.json` via self-locating wrappers under `.dadaia/hooks/codex-*`.
3. **Hook fire is version-qualified, never assumed.** At **codex-cli 0.144.4** hooks are
   live-certified to fire in **both** the TUI and headless `codex exec` — the earlier
   blanket "`exec` fires no hooks" claim described one older CLI and is not a standing
   property of the harness. Trust for any other installed version is probe-driven, not
   inferred: `dadaia certify`'s `codex-live-probe` invokes the **installed** binary
   (`codex --version`, then a real read-only `codex exec`) and reports what it observed.
   The trust-boundary reporter degrades honestly — no installed binary, or a version other
   than the certified one, yields **UNVERIFIED** plus the instruction to re-certify, never
   a silent assumption in either direction. Whatever the verdict, the git chokepoints
   enforce the commit/push boundary independently of any hook firing.
4. Command policy is evaluated natively from `.codex/rules/*.rules` (Starlark prefix
   rules over venv-form paths), not from configuration keys.

## Typical trigger

Operator preference for the Codex TUI or headless `codex exec`, and any session where
native `AGENTS.md` discovery plus Starlark command policy is the desired posture.

## Differentiator

Runs on the operator's Codex subscription with command policy expressed natively in
Starlark, and certifies its runtime behavior by **exercising the installed binary** rather
than inferring it from projected files — static projection tests validate shape and never
attest runtime behavior. The operational fact to carry: hook fire is a property of the
installed CLI version, so read the certification verdict rather than assuming either way.

## Post-compaction

The law reaches every Codex context through **native per-directory `AGENTS.md`
discovery**, independent of hook wiring — proven on the executed path for the parent
session *and* for a delegated custom agent, each of which independently surfaced the
projected law and its own persona identity. The nine persona TOMLs therefore carry role
identity and role-specific decisions only, with the inline law restatement removed: they
shrank **8.3%** against a re-measured byte baseline, every one of the nine smaller and none
larger. That compaction is what makes the load-once property true — the law now arrives
exactly once in the effective context, where the restatement had it arriving twice.

## Runtime state touched

Scaffold projected by `dadaia public install --target codex`: `.codex/config.toml`
(header + per-agent config blocks only — no inert keys), `.codex/hooks.json`,
`.codex/agents/` (**9** TOML personas, one per registry Persona — tier identity is Codex-native
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
- [[sdd-gate-v3]] — gate + chokepoint mechanism; the chokepoints are what hold when a
  version's hook fire is UNVERIFIED.
- [[agentic-entities]] — the behavioral-fidelity derivation check over the nine personas.
- [[public-asset-distribution]] — the `.codex/` projection pipeline.
- [[agent-orchestration]] — the roster that runs inside this harness.
