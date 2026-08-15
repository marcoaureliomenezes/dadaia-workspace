---
title: "dadaia-gitflow: record the reconciliation-merge mechanic"
status: candidate
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "One line stating that
  every squash-merge to main requires a subsequent reconciliation merge of main into
  develop, and that such a merge resolves resurrected loose copies in favour of
  develop's archives. public/** is ai-engineer's surface." Verified at HEAD
  2026-08-14: dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md carries no
  "reconciliation" mention — the mechanic is still undocumented.
intents:
  - subject:
      kind: catalog
      ref: sdd-bug-backlog-governance
    change: >-
      The dadaia-gitflow skill (canonical source under dadaia_workspace/public/skills/,
      ai-engineer surface) gains the reconciliation-merge line: every squash-merge to
      main is followed by a reconciliation merge of main into develop, resolving
      resurrected loose copies in favour of develop's archives. Note: if the dd-skills
      release renames/absorbs dadaia-gitflow content, the line lands wherever the
      branch contract lives then.
---

# dadaia-gitflow: record the reconciliation-merge mechanic

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", fourth item (destination `backlog/candidates.md`). Implementer:
`ai-engineer` (public skill surface).

## Acceptance criteria

The branch-contract skill states the mechanic in one direct line; projections updated
via the §7 chain; `dadaia public doctor` green.
