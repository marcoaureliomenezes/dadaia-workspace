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
  prohibition, the latter at behavioral-fidelity depth with a mutation fixture per drift
  class. Two derivation-surface facts are derived mechanically rather than asserted: the
  reasoned seven-agent `dadaia-cli` reachability (shell-less agents excluded explicitly)
  and the undeclared-overlap check over non-universal skill activation globs. The panel
  renders the registry in the Agentic Entities tab and as the Personas section of the
  Agents tab.
tags:
- agents
- entities
- derivation
- governance
last_updated: '2026-08-18'
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
  natively, so they carry no per-harness derivation and no harness toggle. The
  development cycle's seven `dd-` skills — one per stage: backlog definition, release
  definition, release implementation, release closure, project audit, bug registration,
  bug fix — are universal in exactly this sense: one canonical `.agents/skills/` home,
  no registry entry, no per-harness copy.

Operator-created sub-agents, skills, and rules are exempt: the law governs only what
the library scaffolds.

## Registry

`dadaia_workspace/public/entities/registry.json` (`agentic-entities-v1`): sections
`personas` (id + mandate), `behaviors` and `rules` (id + mandate
+ per-harness `implementations`), `universal` (skills root + AGENTS.md locations).
Read path: `features/panel/entities.py` (`load_registry`, `persona_ids`,
`core_skills`).

## Enforcement

- `tests/contract/test_agentic_entities_derivation.py` — pins the bijection, the
  wired-hook coverage, harness coverage, and the universal surface at source.
- `public doctor` `entities-derivation` check (`ENT-DERIVE-1`, blocking) — independent
  verifier read in `infrastructure/codex_doctor.py`; attests the installed package. It
  proves **behavioral** fidelity, not name bijection alone: a stub persona body, an
  identity swap between two personas, and a broken behavior module reference are each their
  own drift class, each blocking, each pinned by a mutation fixture that proves the check
  fires when that class is introduced.

Two derivation-surface facts are mechanically derived rather than asserted, so a
description can never drift from what the frontmatters actually grant:

- **`dadaia-cli` reachability is a reasoned per-agent selection, never a blanket grant.**
  Seven agents carry it — `ai-engineer`, `code-reviewer`, `project-auditor`,
  `project-manager`, `qa-engineer`, `security-reviewer`, `software-engineer`. The two
  shell-less agents are excluded **explicitly**, because a CLI-literacy grant to an agent
  that cannot run a command is inert. The skill's own description states that actual
  reachability, and a check derives the expectation from the agent frontmatters so a
  grant/description disagreement fails loud.
- **Skill activation overlap is checked where it can mean something.** Universal skills —
  those claiming `**` — are always-on by design, never compete, and are out of scope by
  construction; no check may assert disjointness about them. Stage skills resolve by
  most-specific glob, an intended overlap is **declared**, and the projection-time check
  flags only an *undeclared* overlap between two non-universal skills. It is green on the
  real inventory, and its self-test proves both directions: silent for a `**` skill, firing
  for a newly introduced undeclared duplicate.

## Panel surface

The **Agentic Entities** tab (server-rendered, `views/entities.py`) shows Agnostic
(Skills, AGENTS.md), Deterministic Actions, and Rules as minimal click-to-expand
cards; the **Agents** tab opens with the Persona definition cards above the derived
sub-agent roster.

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
