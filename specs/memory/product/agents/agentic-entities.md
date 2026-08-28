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

Behaviors, personas, rules and skills are defined harness-agnostically, then implemented per entry
harness. Constitution §12.5 forbids underived core surface: every `public/agents/*.md` core
sub-agent derives from a registry Persona and every Persona has its sub-agent (bijection); every
wired `dadaia_workspace.hooks.*` entrypoint is named by a Behavior, derived for every entry harness;
every core rule projection traces to an Abstract Rule. Skills under `.agents/skills/` and the
`AGENTS.md` guardrail files are the **universal surface** — read natively by every entry harness, so
they carry no per-harness derivation and no registry entry, a skill being a folder (a short
`SKILL.md` plus the siblings it discloses its depth to) projected whole. Operator-created
sub-agents, skills and rules are exempt; the law governs only what the library scaffolds.
`public/entities/registry.json` (`agentic-entities-v1`) carries `personas` (id + mandate),
`behaviors` and `rules` (id + mandate + per-harness `implementations`), and `universal`.

## The behavior map

`public/entities/behavior-map.json` is the single declaration of which skill and which scoped rule
file operate which section of the law. A row is
`{section, behavior, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`, keyed by the
law's section heading. Every skill on disk and every scoped `AGENTS.md` source on disk has exactly
one row; every law section has at least one owner; several skills may own one section. Today: 28
rows over 22 core skills and 16 scoped `AGENTS.md` sources. The map also carries
`declared_overlaps` — the canonical home of an intended skill-activation overlap — and the
`SKILL.md` line ceiling. No CLI verb and no hook reads it: it is test and agent surface only, and
re-recording a row's hash tuple is a deliberate act with a named reviewer.

Enforcement runs at three points. `tests/contract/test_agentic_entities_derivation.py` pins the
bijection, wired-hook coverage, harness coverage and the universal surface at source. `public
doctor`'s `entities-derivation` check (`ENT-DERIVE-1`, blocking) attests the installed package at
behavioral-fidelity depth, a stub persona body, an identity swap between two personas and a broken
behavior module reference each being its own blocking drift class.
`tests/contract/test_behavior_map.py` is the single map enforcer: it discovers members structurally
and goes red on a skill or scoped file with no row, a law section with no owner, a row naming a
member that does not exist, a member changed without its hash tuple re-recorded, a `SKILL.md` over
the line ceiling, and two non-universal skills overlapping undeclared. It also carries the
**citation check** (every path and `dadaia` verb a public asset cites must resolve) and the
**invocation-model equivalence** (a skill no persona grants to a model carries
`disable-model-invocation: true`, checked both ways). Overlap is checked only where it can mean
something: universal skills claiming `**` are out of scope, and stage skills resolve by
most-specific glob.

## Always-on budget

The always-on load — the per-harness law chain, the nine persona bodies and the skill descriptions
the harness must list — is measured against a stated ceiling every release by a `words × 1.33`
estimator with per-section attribution. A release measuring above its declared ceiling cuts text;
the number is never re-measured, averaged or renegotiated to fit. Each law topic is stated once and
pointed at, and every removal carries a coverage table mapping removed block → surviving home, read
row by row at review — a fact with no home stays where it is. Nine personas, four inside the 120-220
line ceiling and five above it, each overflow carrying the reason its content has no other home
([[architecture]]).

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
