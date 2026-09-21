---
slug: agentic-entities
title: agentic-entities
tldr: Abstract-entity registry — Personas, Behaviors, Rules — plus the behavior map binding every skill and scoped rule file to one law section.
summary: The entity registry defines the workspace method abstractly and every scaffolded sub-agent, hook and rule file derives from it; the behavior map binds each skill and scoped rule file to one law section.
tags: [agents, entities, derivation, governance]
---

## The derivation law

- Behaviors, personas, rules and skills are defined harness-agnostically, then implemented per entry harness.
- The derivation law forbids underived core surface (`specs/constitution.md` §3 Dispatcher Purity names the registry as the one source of a persona; the constitution is at 6.0.0, four articles plus the fixed slop block): every `public/agents/*.md` sub-agent derives from a registry Persona and every Persona has its sub-agent, a bijection.
- Every wired `dadaia_workspace.hooks.*` entrypoint is named by a Behavior, derived for every entry harness whose record carries a hook derivation (Claude, Codex, Cursor, Devin, Copilot; Kimi's shims are user-level), and every core rule projection traces to an Abstract Rule; a hook exists only as the per-harness implementation of a behaviour the workspace defines, so no harness invents a fifth behaviour.
- The universal surface — the root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills/dd-*` and `.agents/agents/dd-*.md` — is authored once and read natively (Codex, Kimi, Cursor, Devin, Copilot — Devin reads `.agents/agents` too) or through per-entry symlinks and transcodes (Claude, Cursor agents, Copilot `.agent.md`), so it carries no derivation and no registry entry; every dd- skill opens its area's scoped law as step 1, which is how a scoped file reaches a harness that loads only the root->cwd chain.
- Operator-created sub-agents, skills and rules are exempt; the law governs only what the library scaffolds.
- `public/entities/registry.json` (`agentic-entities-v1`) carries `personas`, `behaviors` and `rules` with their per-harness `implementations`, plus `universal`; a persona's `mandate` is one sentence and the registry's only restatement of a role (the reviewers' say "validates at candidate close" and "three-axis review", nothing more).

## The behavior map

- `public/entities/behavior-map.json` is the single declaration of which skill and which scoped rule file operate which section of the law.
- A row is `{section, anchor, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`, keyed by a section heading of the root map.
- Every skill and every scoped `AGENTS.md` source on disk has exactly one row, every law section has at least one owner, and several skills may own one section.
- The map also carries `declared_overlaps`, the canonical home of an intended skill-activation overlap, the `SKILL.md` line ceiling, and `standalone_skills` — the one list of skills that stand without a workspace, read by the skills-repository build and its contract test; no CLI verb and no hook reads it ([[public-asset-distribution]]).
- The corpus is 18 `dd-*` skill directories; `tests/contract/test_slop_ratchets.py` V35 pins the directory count and the total `public/skills/**/*.md` line count at their measured post-closure values, down only, re-pinned at every corpus-touching closure ([[QUALITY]]).
- `tests/contract/test_agentic_entities_derivation.py` pins the bijection, wired-hook coverage, harness coverage and the universal surface at source.
- `public doctor`'s `entities-derivation` check (`ENT-DERIVE-1`, blocking) attests the installed package at behavioral-fidelity depth, a stub body, an identity swap and a broken reference each its own drift class.
- `tests/contract/test_behavior_map.py` is the single map enforcer, red on a member with no row, a section with no owner, a row naming a missing member, a member changed without its hash tuple, or an undeclared overlap.
- It also runs the citation check through `features/specs/citations.py::dead_citations` (every path and `dadaia` verb a public asset cites must resolve — the one finder `MEM-DRIFT-2` and the derived-docs test share), the body-pointer finder (every backticked `dd-*` token and every `` `dd-x` §N `` pair in `public/agents/*.md` and `public/skills/**/*.md` resolves to a skill directory and a `## N.` heading) and invocation-model equivalence (a skill no persona grants carries `disable-model-invocation: true`).
- Overlap is checked only where it can mean something: universal skills claiming `**` are out of scope, and stage skills resolve by most-specific glob.

## Always-on budget

- The always-on load is the root map alone (<= 8192 B); scoped law (<= 4096 B each) and skills (<= 6144 B each) load on demand; `public/data/CONTEXT-MAP.md` records every surface's ceiling, measured bytes and per-harness load trigger, and `tests/contract/test_context_map.py` is the ratchet (ADR 0017).
- Three personas (ADR 0016) — `dd-project-manager`, `dd-software-engineer`, `dd-code-reviewer`, rendered once into `.agents/agents/`; least privilege derives from each persona's `activity_class` at install (Claude `permissionMode`/`disallowedTools`, Codex `sandbox_mode`); a persona states a rule once and points at the skill that operates it — no playbook table, no restated handoff-schema bullet ([[ARCHITECTURE]]).

## Dependencies

[[agent-orchestration]], [[public-asset-distribution]], [[TECHSTACK]], [[QUALITY]].
