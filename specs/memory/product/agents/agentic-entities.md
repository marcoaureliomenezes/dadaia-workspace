---
slug: agentic-entities
title: agentic-entities
category: product
tldr: Abstract-entity registry — Personas, Behaviors, Rules — plus the behavior map binding every skill and scoped rule file to one law section.
summary: The entity registry defines the workspace method abstractly and every scaffolded sub-agent, hook and rule file derives from it; the behavior map binds each skill and scoped rule file to one law section.
tags: [agents, entities, derivation, governance]
---

## The derivation law

- Behaviors, personas, rules and skills are defined harness-agnostically, then implemented per entry harness.
- Constitution §12.5 forbids underived core surface: every `public/agents/*.md` sub-agent derives from a registry Persona and every Persona has its sub-agent, a bijection.
- Every wired `dadaia_workspace.hooks.*` entrypoint is named by a Behavior, derived for every entry harness, and every core rule projection traces to an Abstract Rule.
- Skills under `.agents/skills/` and the `AGENTS.md` guardrail files are the universal surface, read natively by every harness, so they carry no derivation and no registry entry.
- Operator-created sub-agents, skills and rules are exempt; the law governs only what the library scaffolds.
- `public/entities/registry.json` (`agentic-entities-v1`) carries `personas`, `behaviors` and `rules` with their per-harness `implementations`, plus `universal`.

## The behavior map

- `public/entities/behavior-map.json` is the single declaration of which skill and which scoped rule file operate which section of the law.
- A row is `{section, behavior, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`, keyed by the law's section heading.
- Every skill and every scoped `AGENTS.md` source on disk has exactly one row, every law section has at least one owner, and several skills may own one section; today 28 rows over 22 skills and 16 scoped sources.
- The map also carries `declared_overlaps`, the canonical home of an intended skill-activation overlap, and the `SKILL.md` line ceiling; no CLI verb and no hook reads it.
- `tests/contract/test_agentic_entities_derivation.py` pins the bijection, wired-hook coverage, harness coverage and the universal surface at source.
- `public doctor`'s `entities-derivation` check (`ENT-DERIVE-1`, blocking) attests the installed package at behavioral-fidelity depth, a stub body, an identity swap and a broken reference each its own drift class.
- `tests/contract/test_behavior_map.py` is the single map enforcer, red on a member with no row, a section with no owner, a row naming a missing member, a member changed without its hash tuple, or an undeclared overlap.
- It also carries the citation check (every path and `dadaia` verb a public asset cites must resolve) and invocation-model equivalence (a skill no persona grants carries `disable-model-invocation: true`).
- Overlap is checked only where it can mean something: universal skills claiming `**` are out of scope, and stage skills resolve by most-specific glob.

## Always-on budget

- The always-on load — law chain, nine persona bodies, listed skill descriptions — is measured every release against a stated ceiling by a `words × 1.33` estimator with per-section attribution.
- A release measuring above its declared ceiling cuts text; the number is never re-measured, averaged or renegotiated to fit.
- Nine personas, four inside the 120-220 line ceiling and five above it, each overflow carrying the reason its content has no other home ([[architecture]]).

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
