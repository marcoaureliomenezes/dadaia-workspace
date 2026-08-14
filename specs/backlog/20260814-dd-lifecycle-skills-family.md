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
  token economy). Open question reserved for the mandatory grill — NOT decided here:
  does the dadaia- → dd- rename apply only to the cycle family, or to ALL dadaia-*
  skills (dadaia-gitflow, dadaia-grill-me, dadaia-cli, dadaia-test-stewardship, …)?
  It impacts skill names cited textually in the law.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/public/skills/
    change: >-
      Create/rename the 7-skill dd- family at the canonical source:
      dd-backlog-definition (new), dd-release-definition (revisit of
      dadaia-release-definition + rename), dd-release-implement (new),
      dd-release-closure (revisit of dadaia-release-closure + rename),
      dd-audit-project (new; today partial in drift-detection),
      dd-bug-registration (new; today DADAIA.md §6 + fragments),
      dd-bug-fix (new; full Arm B for project bugs). Quality bar dictated by the
      operator: clear, direct, NON-verbose statements; each skill owns its scope with
      zero overlap between skills.
  - subject:
      kind: doc
      ref: dadaia_workspace/public/data/ (DADAIA.md, AGENTS.md — always-on law/rules)
    change: >-
      Dehydrate cycle-specific content out of the always-on rules into the dd- skills:
      rules keep only the always-on law; stage-specific operational protocol moves to
      the on-demand skill for that stage (token economy per session). Every textual
      reference to a renamed skill in the law, in agent frontmatter/bodies
      (e.g. public/agents/product-engineer.md), and in skills that cite skills
      (e.g. project-orchestration) is updated in the same change.
  - subject:
      kind: code
      ref: dadaia public stage/install/doctor + e2e tests asserting projections
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
| `dd-audit-project` | project audit | new; today partial in `drift-detection` |
| `dd-bug-registration` | bug registration in specs | new; today DADAIA.md §6 + fragments |
| `dd-bug-fix` | project bug fix (full Arm B) | new |

Ownership: implementation is `ai-engineer` (AI surface — public skills/rules are its
exclusive domain). A deep `ai-engineer` survey (rules/skills inventory + extraction map
for the dehydration) is being produced in parallel and will be attached as release
evidence at pick time.

## Open question — reserved for the mandatory grill (do not decide in backlog)

Scope of the `dadaia-` → `dd-` rename: cycle family only, or ALL `dadaia-*` skills
(`dadaia-gitflow`, `dadaia-grill-me`, `dadaia-cli`, `dadaia-test-stewardship`, etc.)?
The answer changes which skill names cited textually in DADAIA.md/AGENTS.md and in
agent bodies must be rewritten, and therefore the blast radius of the reference sweep.

## Acceptance criteria

Seven `dd-` skills exist at the canonical source and project cleanly to all harness
trees; no two skills overlap in scope; statements are direct and non-verbose; the
always-on rules no longer carry stage-specific cycle protocol that a dd- skill now
owns; zero dangling references to renamed skills anywhere in law, agents, skills,
manifest, or projection-asserting tests; `dadaia public doctor` green including
`[ok] public-privacy`; suite green.
