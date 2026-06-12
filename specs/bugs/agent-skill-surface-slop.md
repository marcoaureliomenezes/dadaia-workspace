---
title: agent-skill-surface-slop
severity: High
opened: 2026-06-05
session_id: null
status: Closed
adopted: 0.1.6
resolved_in: 0.1.7 (rc-4, T-017-32 + T-017-36)
---

**Resolution (0.1.7 rc-4):** projection side fixed in T-017-32 (orphan-prune now applied across ALL copy strategies — `copy_agents_for_opencode` + unconditional codex `.toml` prune). Library side verified CLEAN in T-017-36: `check_agent_skill_refs` reports 0 drift; software-architect.md references only `architect-core-workflow` (exists); devops-engineer.md is a clean plugin stub. Added a `stage`-time ref-integrity gate (`dadaia public stage` now blocks on any `[drift]` agent→skill ref) as defence-in-depth so a broken stage fails fast instead of relying on post-hoc doctor.


# Bug: agent-skill-surface-slop

## Description

The genericization trim (commit `783560c`, 2026-06-03 "sanitize agentic defaults
and repo hygiene") removed a set of domain agents and skills from the library
`public/` surface, but left two residues:

1. **Stale projections in the instance** — the removed agents/skills/rules
   survived in `.claude/`, `.agents/`, `.opencode/` because `dadaia public install`
   overwrites/skips but does not prune (see `install-skips-existing-files`), and
   `dadaia public doctor` only checks manifest-tracked assets so it is blind to
   them (see `doctor-blind-to-projected-drift`). Doctor exited 0 the whole time.
   **This residue has been pruned from the instance** (77 items, operator-directed,
   2026-06-05) — see "Instance prune (done)" below. This bug tracks the
   **library-side** work that makes the trim permanent.

2. **Dangling skill references in surviving generic personas** — two core generic
   agents still reference skills that the library no longer ships. On a fresh
   instantiation these resolve to nothing:
   - `public/agents/software-architect.md:166,167,189,190` →
     `architect-code-audit`, `architect-design-patterns`
   - `public/agents/devops-engineer.md:90,123,124,137,152,221,222,405` →
     `devops-deploy-strategies`, `github-actions-pipelines`,
     `devops-gitflow-governance` (line 405 also points at a non-existent
     `docs/agent-knowledge/devops-engineer/github-actions-pipelines.md`)

## Governing principle (operator, 2026-06-05)

The library skill surface must be reduced to skills that **enforce the native
workspace workflow (SDD lifecycle, memory, tasks, handoff, release, context,
grill, doctor, navigation/review, orchestration, drift-detection)** or are
**tailored for the coordinators** (project-manager, project-auditor,
product-engineer, ai-engineer). Everything else is slop.

Under that principle the following are slop and must leave the library:

- **Eng-domain skills referenced by generic agents** (strip the references too):
  `architect-code-audit`, `architect-design-patterns`, `devops-deploy-strategies`,
  `github-actions-pipelines`, `devops-gitflow-governance`.
- **Frontend/design role skills** (operator: "prune them too") — currently
  manifest-tracked, used by `frontend-engineer` + `design-specialist`:
  `frontend-design`, `frontend-implementation-quality`, `design-reference-research`,
  `design-report-quality-gate`, `ux-ui-review`. Removing these makes those two
  agents lean (base-model knowledge). **Capability reduction — confirm scope in
  grill before executing.**

> Tradeoff note: stripping the eng-domain skills guts `devops-engineer`'s CI/CD
> playbook and `software-architect`'s audit/pattern method. This is the intended
> "lean generic agent" direction, not an oversight — but it is a capability cut,
> not a pure cleanup. `code-reviewer` / `security-reviewer` are unaffected (they
> do not reference their former skills; `architecture-code-review` and
> `security-audit-protocol` were already unreferenced orphans).

## Scope of fix (library-side — ai-engineer / rc-1 R4)

1. Strip the slop-skill references from `software-architect.md` and
   `devops-engineer.md` (and the dead `docs/agent-knowledge` link).
2. Remove the 5 frontend/design skills from `public/skills/` + the manifest +
   strip their references from `frontend-engineer.md` + `design-specialist.md`
   (pending grill confirmation of the capability cut).
3. `dadaia public stage && install --force --target all && doctor` → exit 0,
   no dangling refs, all runtimes (incl. `.codex`) carry the identical reduced
   surface.

This is the natural home for **rc-1 R4 (generic-agent audit)** — fold it in.

## Instance prune (done, reversible)

Removed 77 orphan items on 2026-06-05 (operator-directed):
- 21 orphan skills × 3 runtimes (`.claude/skills`, `.agents/skills`,
  `.opencode/skills`) = 63 dirs
- 6 orphan agents × 2 runtimes (`.claude/agents`, `.opencode/agents`) = 12 files
  (`data-analyst/architect/engineer`, `game-designer/developer/tester`)
- 2 orphan rules (`.claude/rules`): `game-agents-coordination`,
  `game-developer-scope`

Backup: `.dadaia/tmp/claude/20260606/orphan-prune-backup/` (restorable).
Post-prune: all runtimes at 15 agents / 22 skills / 7 rules; `doctor` exit 0.

## Acceptance

- No generic persona references a skill absent from `public/skills/`.
- `public/skills/` contains only native-workflow + coordinator skills (+ whatever
  grill confirms keeping for frontend/design).
- A fresh `dadaia init` + `public install` yields the reduced surface on all
  runtimes; `doctor` exit 0; no orphans.

## Related

- `install-skips-existing-files` (root cause: no prune on install)
- `doctor-blind-to-projected-drift` (root cause: doctor blind to orphans)
- rc-1 R4 (generic-agent over/under-fit audit) — the correct release vehicle
