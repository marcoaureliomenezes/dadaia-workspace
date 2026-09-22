---
slug: agentic-entities
title: agentic-entities
tldr: The entity registry — three personas, the deterministic behaviours every harness implements, the rules — and the behavior map binding each skill to law.
summary: The registry defines the workspace method harness-agnostically and every scaffolded persona, hook and rule derives from it; this atom holds the one enumeration of the hook behaviours the harness atoms link to; the behavior map binds each skill and scoped rule file to one law section.
tags: [agents, entities, derivation, governance]
sources:
  - dadaia_workspace/public/entities/**
  - dadaia_workspace/public/data/CONTEXT-MAP.md
  - dadaia_workspace/public/skills/**
  - dadaia_workspace/infrastructure/entity_doctor.py
---

## The registry

- `dadaia_workspace/public/entities/registry.json` (`agentic-entities-v1`) carries `personas`, `behaviors` and `rules`, each behaviour and rule with its per-harness `implementations`, plus `universal`.
- Personas: `dd-product-engineer`, `dd-software-engineer`, `dd-code-reviewer`; a `mandate` is one sentence and the registry's only restatement of a role ([[agent-orchestration]]).
- Every `dadaia_workspace/public/agents/*.md` persona derives from a registry persona and every registry persona has its file — a bijection; every wired `dadaia_workspace.hooks.*` entrypoint is named by a behaviour; every core rule projection traces to a registry rule.
- Operator-created sub-agents, skills and rules are out of scope; the derivation governs only what the library scaffolds.

## The deterministic behaviours

The one enumeration; every harness atom links here.

| Behaviour | What it does | Lane |
|---|---|---|
| `root-whitelist` | blocks a file-tool write that would mint a new workspace-root entry | pre-tool gate |
| `venv-guard` | blocks `dadaia`/`pip`/`python -m dadaia_workspace` run outside the workspace venv, naming the corrected command | pre-tool gate |
| `sdd-gate` | classifies each write ADDITIVE / PROTECTED / MUTATING and scope-judges MUTATING writes under `repos/<slug>/` for a bound session | pre-tool gate (+ post-tool reaper where the harness has one) |
| `context-memory-injection` | runs the session-start reaper (`dadaia doctor --fix --expired-only --quiet`) and, where the harness has a prompt hook, injects the bound context's bootstrap | session start (+ prompt) |
| `git-chokepoints` | pre-push allows only `feature/{M.m.p}` with a green preflight | git hooks, identical for every harness |

- The first three ride ONE merged entrypoint, `dadaia_workspace.hooks.pre_gate`; with the session-start reaper they are the four hook behaviours every harness receives, and every BLOCK carries one `fix:` line.
- A harness differs only in serialization — the event names, the hook file and the answer shape its wrapper translates to; no harness adds a behaviour ([[sdd-gate-v3]]).

## The universal surface

- The root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills/dd-*` and `.agents/agents/dd-*.md` are authored once and read natively or through per-entry symlinks and transcodes, so they carry no per-harness derivation.
- Every `dd-` skill touching a governed area opens that area's scoped `AGENTS.md` as step 1 — how scoped law reaches a harness that loads only the root->cwd chain.
- `dadaia_workspace/public/data/CONTEXT-MAP.md` records every surface's byte ceiling, measured installed size and per-harness load trigger: the always-on load is the root map (<= 8192 B), each scoped file <= 4096 B, each `SKILL.md` <= 6144 B; `tests/contract/test_context_map.py` is the ratchet.

## The behavior map

- `dadaia_workspace/public/entities/behavior-map.json` declares which skill and which scoped rule file operate which section of the root map: `rows` of `{section, anchor, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`, plus `skill_md_line_ceiling`, `declared_overlaps` and `standalone_skills` (the skills that stand without a workspace, read by the skills-repository build — [[public-asset-distribution]]).
- Every skill and scoped `AGENTS.md` source has exactly one row, every law section at least one owner; several skills may own one section.
- The corpus is 18 `dd-*` skill directories, pinned with the total skill Markdown line count by the down-only ratchet in `tests/contract/test_slop_ratchets.py` ([[QUALITY]]).

## Enforcement

- `tests/contract/test_agentic_entities_derivation.py` pins the bijection, wired-hook coverage, harness coverage and the universal surface.
- `tests/contract/test_behavior_map.py` is the map enforcer: red on a member without a row, a section without an owner, a row naming a missing member, a changed member without its new hash tuple, or an undeclared overlap; it also resolves every path and `dadaia` verb a public asset cites (`dadaia_workspace/features/specs/citations.py`), every `dd-*` body pointer, and requires `disable-model-invocation: true` on a skill no persona grants.
- `dadaia public doctor`'s attesting `entities-derivation` check (`ENT-DERIVE-1`) inspects the installed package: a stub persona, an identity swap between filename and `name:`, or a behaviour naming a missing hook module each report drift.

## Dependencies

[[agent-orchestration]], [[public-asset-distribution]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[QUALITY]].
