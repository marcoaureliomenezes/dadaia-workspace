---
slug: agentic-entities
title: agentic-entities
category: product
tldr: Abstract-entity registry — Personas, Behaviors, Rules; one behavior map binding every skill and scoped rule to a law section; the always-on budget.
summary: >-
  The workspace method is defined abstractly first: `public/entities/registry.json`
  holds the Personas, Deterministic Behaviors, Abstract Rules, and universal
  skills/AGENTS.md surface. Every scaffolded core sub-agent, hook, and rule file is a
  per-harness derivation of one of these entities (constitution §12.5); the derivation
  contract test and the `public doctor` `entities-derivation` check enforce the
  prohibition, the latter at behavioral-fidelity depth with a mutation fixture per drift
  class. `public/entities/behavior-map.json` is the single map that retired
  `rules-skills-map.json`: 28 rows bind all 22 core skills and all 16 scoped `AGENTS.md`
  sources to exactly one law section each, every section to at least one owner, each with a
  recorded content-hash tuple, and it also holds the declared activation overlaps, the
  citation check and the invocation-model equivalence. Its discovery is structural — the
  enforcer globs the generators rather than reading a hand roster — and it goes RED in five
  directions, each proven by a mutation fixture on the cross-platform matrix. The map is
  test-and-agent surface only, read by no CLI verb and no hook. The always-on load — law
  chain plus nine persona bodies plus the skill descriptions — is measured against a stated
  ceiling every release, and every removal carries a coverage table. The panel
  renders the registry in the Agentic Entities tab and as the Personas section of the
  Agents tab.
tags:
- agents
- entities
- derivation
- governance
last_updated: '2026-08-27'
release_origin: 0.5.0
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
  development cycle's `dd-` skills — one per stage: backlog definition, release
  definition, release implementation (closure included), project audit, bug registration,
  bug fix — are universal in exactly this sense: one canonical `.agents/skills/` home,
  no registry entry, no per-harness copy. A skill is a **folder**: a short `SKILL.md`
  plus the sibling files it discloses its depth to, and every sibling is projected
  wherever the skill is.

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

- **`dd-cli-library` reachability is a reasoned per-agent selection, never a blanket grant.**
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
  for a newly introduced undeclared duplicate. The declaration of an intended overlap lives
  in the map below — `declared_overlaps` is its canonical home — never in a script's own
  table and never in a skill's prose.

### The behavior map

`public/entities/behavior-map.json`, beside the registry and versioned by its own schema, is
the **single** declaration of which skill and which scoped rule file operate which section of
the law. It is a superset of the retired `rules-skills-map.json`, which left with its topic
keying: **one map file exists**, and a grep for the old filename outside history returns zero
hits.

A row is `{section, behavior, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`,
keyed by the law's own section heading. The cardinality is stated exactly: **every skill on
disk and every scoped `AGENTS.md` source on disk has exactly one row; every law section has at
least one owner row.** More than one skill legitimately owning a section is normal — quality
alone owns several — so the RED condition is a section with *no* owner, never two owners
sharing one. The map also carries the fleet's `declared_overlaps` and the `SKILL.md` line
ceiling.

Today that is **28 rows over 22 core skills and 16 scoped `AGENTS.md` sources**. Coverage is
complete in both directions.

**Discovery is structural, never a hand roster.** The enforcer globs the generators — every
`SKILL.md` under `public/skills/`, and every `AGENTS.md`/`*-AGENTS.md` source under
`public/{data,scaffold,templates}/` — so a source added tomorrow goes RED without anyone
editing a list. Every `EXPECTED_SKILLS`-style hand-kept roster the glob made redundant is
deleted rather than kept beside it; a hand list of hand lists is the same defect one level up.

Each row records a **hash tuple** over its section body, its skill body and each scoped file.
Re-recording a tuple is a deliberate act with a named reviewer: the failure message says what
to re-read, not merely that a hash changed. That tuple is the structural answer to the
stale-citation class — a persona or skill citing a section for content that has since moved —
which had fired twice, both times found by a human.

**One enforcer, not two.** A single contract test in the gating tier reads the map, the law and
the on-disk inventory, and goes **RED in five directions**: a skill on disk with no row, a
scoped `AGENTS.md` on disk with no row, a law section with no owner row, a row naming a member
that does not exist, and a member changed without its hash tuple re-recorded. Each direction
carries its own mutation fixture, and each fixture is observed RED before its correction and
green after **on the cross-platform CI matrix** — because the file this enforcer replaced was
itself the home of a registered bug in which a mutation fixture never turned red on Windows.
It also fails when a `SKILL.md` exceeds the declared line ceiling or two non-universal skills
overlap undeclared. Two further checks ride the same test rather than earning a second script:

- **The citation check.** Every path a public asset cites must exist and every `dadaia`
  verb it cites must resolve, and the test names the first that does not. A projected
  instance path is proven by executing the asset that generates it, so the check is honest
  on a fresh checkout and platform-agnostic in how it compares paths.
- **The invocation-model equivalence.** A skill no persona grants to a model carries
  `disable-model-invocation: true`, and the equivalence is checked in **both** directions,
  so neither a human-entry skill costing always-on description tokens nor a granted skill
  hidden from the model can survive. An operative dependency between skills is written as
  the imperative "Call the Skill tool with `<name>`", never as prose.

The predecessor collision lint is **retired**, with its hard-coded overlap table; its
self-test fixtures were ported onto the new test, so coverage moved rather than dropped.
The same discipline governed the map's own retirement: before the old enforcer file was
deleted, every test function it carried had a **named counterpart** in the new one, proven by
a name-diff with a zero-hit residue plus a one-line note per check recording the behavior it
still asserts. Byte equality is not the criterion and would be unachievable in an extended
enforcer; *no behavior dropped* is.

**The map adds no runtime dependency.** No CLI verb reads it and no hook loads it — it is
consumed by the test suite and by agents. That is the general posture: skills instruct
procedure, audits measure conformance, and hooks and the CLI validate only at the publication
boundary.

## Operating Rules

**The always-on budget is measured against a stated ceiling, every release.** What every
session pays before it does anything is the per-harness law chain, the nine persona bodies and
the skill descriptions the harness must list. The measurement recipe is fixed — a word-count
estimator of `words × 1.33` over the same three sets, with **per-section attribution and
comment-form behavior anchors attributed on their own line**, so an anchor can never hide
inside a section's number.

A **ceiling is not a target, and an overshoot is not renegotiated**: a release that measures
above its declared ceiling cuts text until it does not. Re-measuring, averaging across the
persona set, and moving a section into a skill the law then has to cite are all refused. The
number is recorded as it is measured and the ambition is never redefined to fit it. The
persona bodies remain roughly three quarters of the mass and the law file alone exceeds the
long-run ≤3.5k ambition on its own, so the remaining gap is structural: closing it takes
relocation into on-demand surfaces, not another rewording round.

Two mechanisms hold the line the diet already won. Each law topic is **stated once and
pointed at** — a persona carries a pointer to the law's own section rather than a
restatement, and a restatement is never accepted in place of a pointer. And every removal
carries a **coverage table**: removed block → the surviving home that now carries it, read
row by row at review, because the risk of a diet is deleting a law with no other home. A
fact with no home stays where it is, with its justification.

Line ceilings follow the same posture: nine personas, four inside the 120–220 ceiling and
five above it, each overflow named with the reason its content has no other home
([[architecture]]). Content relocated out of a persona lands in the disclosed skill siblings
that already exist, which are loaded on demand — so a skill sibling growing while the fleet
shrinks is the mechanism working, not fleet growth.

## Panel surface

The **Agentic Entities** tab (server-rendered, `views/entities.py`) shows Agnostic
(Skills, AGENTS.md), Deterministic Actions, and Rules as minimal click-to-expand
cards; the **Agents** tab opens with the Persona definition cards above the derived
sub-agent roster.

## Dependencies

[[agent-orchestration]], [[panel]], [[public-asset-distribution]], [[tech-stack]].
