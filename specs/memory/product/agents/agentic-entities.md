---
slug: agentic-entities
title: agentic-entities
category: product
tldr: Abstract-entity registry — Personas, Deterministic Behaviors, Abstract Rules, universal surface — that every scaffolded core implementation derives from.
summary: >-
  The workspace method is defined abstractly first: `public/entities/registry.json`
  holds the Personas, Deterministic Behaviors, Abstract Rules, and universal
  skills/AGENTS.md surface. Every scaffolded core sub-agent, hook, and rule file is a
  per-harness derivation of one of these entities (constitution §12.5); the derivation
  contract test and the `public doctor` `entities-derivation` check enforce the
  prohibition. The panel renders the registry in the Agentic Entities tab and as the
  Personas section of the Agents tab.
tags:
- agents
- entities
- derivation
- governance
token_estimate: 420
last_updated: '2026-08-10'
release_origin: v0.3.0
---

## The derivation law

dadaia-workspace is a method, not a harness add-on: behaviors, personas, rules, and
skills are defined agnostically, then implemented per entry harness. Constitution
§12.5 makes underived core surface forbidden:

- **Persona → sub-agent.** Every `public/agents/*.md` core sub-agent derives from a
  Persona in the registry, and every Persona has its derived sub-agent (bijection).
- **Deterministic Behavior → hook.** Every `dadaia_workspace.hooks.*` entrypoint the
  installer wires is named by a Behavior, and every Behavior is derived for every
  entry harness.
- **Abstract Rule → rule file.** Every core rule projection (the `DADAIA.md` law per
  harness, the Codex command policy) traces to an Abstract Rule.
- **Universal surface.** Skills under `.agents/skills/` and the `AGENTS.md` guardrail
  files are harness-agnostic by construction — every entry harness reads them
  natively, so they carry no per-harness derivation and no harness toggle.

Operator-created sub-agents, skills, and rules are exempt: the law governs only what
the library scaffolds.

## Registry

`dadaia_workspace/public/entities/registry.json` (`agentic-entities-v1`): sections
`personas` (id + mandate; plugin stubs flagged), `behaviors` and `rules` (id + mandate
+ per-harness `implementations`), `universal` (skills root + AGENTS.md locations).
Read path: `features/agents/entities.py` (`load_registry`, `persona_ids`,
`core_skills`).

## Enforcement

- `tests/contract/test_agentic_entities_derivation.py` — pins the bijection, the
  wired-hook coverage, harness coverage, and the universal surface at source.
- `public doctor` `entities-derivation` check (`ENT-DERIVE-1`, blocking) — independent
  verifier read in `infrastructure/codex_doctor.py`; attests the installed package.

## Panel surface

The **Agentic Entities** tab (server-rendered, `views/entities.py`) shows Agnostic
(Skills, AGENTS.md), Deterministic Actions, and Rules as minimal click-to-expand
cards; the **Agents** tab opens with the Persona definition cards above the derived
sub-agent roster.

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
