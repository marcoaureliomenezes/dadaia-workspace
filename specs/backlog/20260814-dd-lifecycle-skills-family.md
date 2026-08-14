---
title: "dd- lifecycle skills family — the skill surface mirrors the development cycle 1:1"
status: candidate
opened: 2026-08-14
description: >-
  Operator thesis: the development-cycle skills are not loose standalone skills — they
  are the operational interface of the capabilities dadaia-workspace offers developers
  during the development cycle. The skill surface must mirror the cycle 1:1: one
  dd-prefixed skill per lifecycle stage, seven in total. Two exist today under other
  names (dadaia-release-definition, dadaia-release-closure) and are revisited + renamed;
  one exists partially (drift-detection covers part of project audit); four are new
  (backlog definition, release implementation, bug registration in specs, full Arm B
  bug fix). Cycle-specific content that today lives in always-on rules is DEHYDRATED
  out of the rules into these on-demand skills (rules = always-on, skills = on-demand;
  token economy). The grill of 2026-08-14 settled the open questions — see the ADR
  notes section below.
intents:
  - subject:
      kind: catalog
      ref: agentic-entities
    change: >-
      Create/rename the 7-skill dd- family at the canonical source
      (dadaia_workspace/public/skills/): dd-backlog-definition (new),
      dd-release-definition (revisit of dadaia-release-definition + rename),
      dd-release-implement (new), dd-release-closure (revisit of
      dadaia-release-closure + rename), dd-audit-project (full merge+rename of
      drift-detection per grill ADR #8/E-2), dd-bug-registration (new; today
      DADAIA.md §6 + fragments), dd-bug-fix (new; full Arm B for project bugs).
      Quality bar dictated by the operator: clear, direct, NON-verbose statements;
      each skill owns its scope with zero overlap between skills.
  - subject:
      kind: catalog
      ref: public-asset-distribution
    change: >-
      Dehydrate cycle-specific content out of the always-on rules
      (dadaia_workspace/public/data/ — DADAIA.md, AGENTS.md) into the dd- skills:
      rules keep only the always-on law; stage-specific operational protocol moves to
      the on-demand skill for that stage (token economy per session). Every textual
      reference to a renamed skill in the law, in agent frontmatter/bodies
      (e.g. public/agents/product-engineer.md), and in skills that cite skills
      (e.g. project-orchestration) is updated in the same change. Per grill ADR #7
      (E-1), ai-engineer authors the public/data/DADAIA.md source under the three
      guardrails (approved task write-set, F-0 persona fix, law-diff eyeballed
      pre-merge); the 9 dehydration cuts ride the SPEC as verbatim FRs (ADR #11/E-5).
  - subject:
      kind: cli
      ref: public install
    change: >-
      The family lands via the §7 projection chain (source change + stage + install +
      doctor green, [ok] public-privacy). The rename must update every reference:
      staging manifest entries, projected trees (.claude/, .agents/, .codex/,
      .kimi-code/), and the e2e/contract tests that assert projected skill paths and
      names.
---

# dd- lifecycle skills family

## Description

See frontmatter. The target family, prefix `dd-`, one skill per cycle stage:

| Skill | Stage | Origin |
|---|---|---|
| `dd-backlog-definition` | backlog definition | new |
| `dd-release-definition` | release definition | revisit of `dadaia-release-definition` + rename |
| `dd-release-implement` | release implementation | new |
| `dd-release-closure` | release closure | revisit of `dadaia-release-closure` + rename |
| `dd-audit-project` | project audit | full merge+rename of `drift-detection` (grill ADR #8) |
| `dd-bug-registration` | bug registration in specs | new; today DADAIA.md §6 + fragments |
| `dd-bug-fix` | project bug fix (full Arm B) | new |

Ownership: implementation is `ai-engineer` (AI surface — public skills/rules are its
exclusive domain). The `ai-engineer` survey (rules/skills inventory + extraction map for
the dehydration) is release evidence (report 2026-08-14T122310Z).

## Grill decisions (2026-08-14 refinement report — settled, do not re-litigate)

- **Rename scope (ADR #12/E-6):** Scenario 1 — cycle family only (2 renames + the E-2
  merge), ~9 files. Fleet-wide `dadaia-*`→`dd-*` deferred as a future mechanical
  candidate.
- **drift-detection (ADR #8/E-2):** ceases to exist; `dd-audit-project` = inherited
  technical content + lifecycle wrapper (1 audit → 1 remediation release → full
  disposition → archive).
- **Gate-cadence table (ADR #9/E-3):** moves from `project-orchestration` into
  `dd-release-implement`; referenced by name from the dispatcher skill.
- **Bug reservation (ADR #10/E-4):** `dd-bug-fix` documents today's advisory-presence
  signal only; the reservation primitive is the separate backlog entry
  `bug-picked-ledger-event`.
- **Disposition vocabulary (ADR #13/E-7):** canonical in `dd-backlog-definition`;
  closure/audit/bug-registration skills reference by name.
- **Backlog single source (ADR #14):** `specs/backlog/BACKLOG.md` (ACTIVE + LEDGER),
  purge-on-pick mandatory, JSONL rejected for backlog; consolidation lands inside this
  release; §5 amended at source via the E-1 path.

## Acceptance criteria

Seven `dd-` skills exist at the canonical source and project cleanly to all harness
trees; no two skills overlap in scope; statements are direct and non-verbose; the
always-on rules no longer carry stage-specific cycle protocol that a dd- skill now
owns; zero dangling references to renamed skills anywhere in law, agents, skills,
manifest, or projection-asserting tests; `dadaia public doctor` green including
`[ok] public-privacy`; suite green.
