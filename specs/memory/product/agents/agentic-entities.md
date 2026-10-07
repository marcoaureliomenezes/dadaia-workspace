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
| `root-whitelist` | blocks a file-tool write that would mint an entry the layout law judges slop — at the root, `.dadaia/`, a closed-canon zone, or the first level of `repos/` and `worktrees/` | pre-tool gate |
| `venv-guard` | blocks the dadaia CLI (`dadaia`, `python -m dadaia_workspace`) run outside the workspace venv, judging every command of a Bash line (after `&&`, `;`, `|`, an env assignment or a shell keyword), naming the corrected command | pre-tool gate |
| `sdd-gate` | classifies each write ADDITIVE / PROTECTED / MUTATING (PROTECTED holding a code floor with or without the install ledger), scope-judges MUTATING writes into a repo against the session's bind and sends every other write under `repos/<slug>/`, audits aside, to a worktree | pre-tool gate (+ post-tool session heartbeat where the harness has one) |
| `context-memory-injection` | runs the session-start reaper (`dadaia doctor --fix --expired-only --quiet`) and injects the bound context's bootstrap through whichever session-start and prompt hooks the harness has | session start (+ prompt) |
| `git-chokepoints` | pre-push allows only a work branch of the project gitflow, a job branch `wt/<M.m.p>-rc<N>/<job>`, a backlog branch `wt/backlog/<slug>`, or the bootstrap birth of its principal and integration branches, and refuses a non-canon `specs/` path or a denylisted secret in the pushed range | git hooks, identical for every harness |

- The first three ride ONE merged entrypoint, `dadaia_workspace.hooks.pre_gate`; with the session-start reaper they are the four hook behaviours every harness receives, and every BLOCK carries one fix line, a command or `Operator action: <one act>`.
- A harness differs only in serialization — the event names, the hook file and the answer shape its wrapper translates to; no harness adds a behaviour ([[sdd-gate-v3]]).
- Every projected hook entry carries a `timeout`: 10 s for the tool lanes (pre-gate, post-gate), 30 s for the session lanes (ctx-inject, reaper); every harness lets the action through when it fires, so a pre-gate slower than 10 s is a declared fail-open window and itself a Stall-class bug.
- With no workspace venv every hook wrapper — the Kimi Code shims included — warns on stderr and exits 0, letting the action through; each ctx-inject lane also prints, in its harness's context envelope ([[context-management]]), `dadaia: no workspace venv at <ws>/.dadaia/.venv — the gate is off.` and, on its own line, `fix: uvx dadaia-workspace init <ws>`, on every firing until the venv exists, with no marker file and no per-session state ([[sdd-gate-v3]]).

## The universal surface

- The root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills/dd-*` and `.agents/agents/dd-*.md` are authored once and read natively or through per-entry symlinks and transcodes, so they carry no per-harness derivation.
- Every `dd-` skill touching a governed area opens that area's scoped `AGENTS.md` as step 1 — how scoped law reaches a harness that loads only the root->cwd chain.
- `dadaia_workspace/public/data/CONTEXT-MAP.md` records every surface's purpose, what belongs in it and its per-harness load trigger; a surface's size is a soft review signal, never a build failure (ADR 0143), and a `SKILL.md`'s line limits are the behavior map's.

## The behavior map

- `dadaia_workspace/public/entities/behavior-map.json` declares which skill and which scoped rule file operate which section of the root map: `rows` of `{section, anchor, skill, scoped_agents_md[], hash_tuple, recorded_by, recorded_at}`, plus `skill_md_line_soft`, `skill_md_line_ceiling`, `declared_overlaps` and `standalone_skills` (the skills that stand without a workspace, pinned by `tests/infrastructure/test_entity_doctor__standalone_skills.py`).
- Every skill and scoped `AGENTS.md` source has exactly one row, every law section at least one owner; several skills may own one section.
- The corpus is 17 `dd-*` skill directories; a projected `SKILL.md` longer than `skill_md_line_soft` is a doctor `SKILL-MD-LENGTH` warning ([[workspace-doctor]]), and one longer than `skill_md_line_ceiling` turns `tests/infrastructure/test_entity_doctor.py` red ([[QUALITY]]).

## Enforcement

- `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py` pins the bijection, wired-hook coverage, harness coverage and the universal surface.
- `tests/infrastructure/test_entity_doctor.py` is the map enforcer: red on a member without a row, a section without an owner, a row naming a missing member, a changed member without its new hash tuple, or an undeclared overlap; it also resolves every path and `dadaia` verb a public asset cites (`dadaia_workspace/features/specs/citations.py`), every `dd-*` body pointer, and requires `disable-model-invocation: true` on a skill no persona grants.
- `tests/core/test_cli_line__every_block_carries_a_fix.py` is the one fix-line harness: every BLOCK site, driven through its public seam, prints exactly one fix line — `Operator action: <one act>` or a command whose first word exists — with no `<…>` placeholder and no `&&`, which the pre-gate allows fed back as Bash and every host shell runs verbatim; one argv rendered by `core/cli_line` and by the scripts' `_specs.py` is one line; one walk over the package, the skill scripts and the tracked law and docs refuses a fix position spelling the CLI outside the renderer, and in `public/**/*.md` a command line with a bare `dadaia <verb>`, `$DADAIA_BIN`, or a verb or flag the live command tree lacks.
- `tests/features/workspace/test_onboarding__onboarding_steps.py` pins the onboarding step list (ids, kinds, order).
- `dadaia public doctor`'s attesting `entities-derivation` check (`ENT-DERIVE-1`) inspects the installed package: a stub persona, an identity swap between filename and `name:`, or a behaviour naming a missing hook module each report drift.

## Dependencies

[[agent-orchestration]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-doctor]], [[ARCHITECTURE]], [[QUALITY]].
