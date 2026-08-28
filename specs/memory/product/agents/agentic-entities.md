---
slug: agentic-entities
title: agentic-entities
category: product
tldr: Abstract-entity registry — Personas, Behaviors, Rules — plus the behavior map binding every skill and scoped rule file to one law section.
summary: '`public/entities/registry.json` defines the workspace method abstractly; every scaffolded sub-agent, hook and rule file is a per-harness derivation of it. `public/entities/behavior-map.json` binds every skill and scoped `AGENTS.md` source to exactly one law section.'
tags:
- agents
- entities
- derivation
- governance
---

## The derivation law

Behaviors, personas, rules and skills are defined harness-agnostically, then implemented
per entry harness. Constitution §12.5 forbids underived core surface:

- **Persona → sub-agent.** Every `public/agents/*.md` core sub-agent derives from a
  registry Persona, and every Persona has its sub-agent (bijection).
- **Deterministic Behavior → hook.** Every `dadaia_workspace.hooks.*` entrypoint the
  installer wires is named by a Behavior, derived for every entry harness.
- **Abstract Rule → rule file.** Every core rule projection traces to an Abstract Rule.
- **Universal surface.** Skills under `.agents/skills/` and the `AGENTS.md` guardrail files
  are harness-agnostic: every entry harness reads them natively, so they carry no
  per-harness derivation and no registry entry. A skill is a folder — a short `SKILL.md`
  plus the siblings it discloses its depth to — and every sibling is projected wherever the
  skill is.

Operator-created sub-agents, skills and rules are exempt; the law governs only what the
library scaffolds.

## Registry

`public/entities/registry.json` (`agentic-entities-v1`) carries `personas` (id + mandate),
`behaviors` and `rules` (id + mandate + per-harness `implementations`), and `universal`
(skills root + AGENTS.md locations). Read path: `features/panel/entities.py`.

## The behavior map

`public/entities/behavior-map.json`, versioned by its own schema
(`public/schemas/behavior-map-v1.schema.json`), is the single declaration of which skill
and which scoped rule file operate which section of the law. A row is
`{section, behavior, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`,
keyed by the law's section heading. Cardinality: every skill on disk and every scoped
`AGENTS.md` source on disk has exactly one row; every law section has at least one owner.
Several skills may own one section. Today: 28 rows over 22 core skills and 16 scoped
`AGENTS.md` sources.

The map also carries `declared_overlaps` — the canonical home of an intended
skill-activation overlap — and the `SKILL.md` line ceiling. No CLI verb and no hook reads
it: it is test and agent surface only.

Each row records a hash tuple over its section body, its skill body and each scoped file;
re-recording one is a deliberate act with a named reviewer, and the failure message names
what to re-read.

## Enforcement

- `tests/contract/test_agentic_entities_derivation.py` pins the bijection, wired-hook
  coverage, harness coverage and the universal surface at source.
- `public doctor`'s `entities-derivation` check (`ENT-DERIVE-1`, blocking,
  `infrastructure/codex_doctor.py`) attests the installed package at behavioral-fidelity
  depth: a stub persona body, an identity swap between two personas and a broken behavior
  module reference are each their own blocking drift class with a mutation fixture.
- `tests/contract/test_behavior_map.py` is the single map enforcer. It discovers members
  structurally — globbing every `SKILL.md` under `public/skills/` and every
  `AGENTS.md`/`*-AGENTS.md` under `public/{data,scaffold,templates}/` — and goes red on: a
  skill with no row, a scoped file with no row, a law section with no owner, a row naming a
  member that does not exist, a member changed without its hash tuple re-recorded, a
  `SKILL.md` over the line ceiling, and two non-universal skills overlapping undeclared.
  It also carries the **citation check** (every path and `dadaia` verb a public asset cites
  must resolve, with a projected instance path proven by executing its generating asset)
  and the **invocation-model equivalence** (a skill no persona grants to a model carries
  `disable-model-invocation: true`, checked in both directions).

Skill-activation overlap is checked only where it can mean something: universal skills
claiming `**` are always-on and out of scope; stage skills resolve by most-specific glob.
`dd-cli-library` reachability is a per-agent grant derived from the agent frontmatters —
the two shell-less agents are excluded explicitly, since CLI literacy is inert without a
shell.

## Operating rules

The always-on load — the per-harness law chain, the nine persona bodies and the skill
descriptions the harness must list — is measured against a stated ceiling every release,
by a `words × 1.33` estimator with per-section attribution and comment-form behavior
anchors attributed on their own line. A release measuring above its declared ceiling cuts
text; the number is never re-measured, averaged or renegotiated to fit.

Two mechanisms hold the line: each law topic is stated once and pointed at — a persona
carries a pointer to the law's section, never a restatement — and every removal carries a
coverage table mapping removed block → surviving home, read row by row at review. A fact
with no home stays where it is.

Persona line ceilings follow the same posture: nine personas, four inside the 120–220
ceiling and five above it, each overflow carrying the reason its content has no other home
([[architecture]]). Content relocated out of a persona lands in disclosed skill siblings,
loaded on demand.

## Panel surface

The **Agentic Entities** tab (`features/panel/views/entities.py`) renders Agnostic
(Skills, AGENTS.md), Deterministic Actions and Rules as click-to-expand cards; the
**Agents** tab opens with the Persona definition cards above the derived sub-agent roster.

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
