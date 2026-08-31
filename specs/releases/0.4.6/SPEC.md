# SPEC — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer
**Opened:** 2026-08-31
**Consumes:** skills-quality-consolidation

---

## 1. Problem and context

The operator ordered a heavy audit of the library's 22 skills against a
reference corpus of skills by a recognised AI engineer
(`.dadaia/references/skills-examples`), with three verbatim reference copies
(`codebase-design`, `domain-modeling`, `improve-codebase-architecture`) living
as unmanaged local instance skills. The audit (session 2026-08-31, ratified
verbatim) extracted a 15-rule authoring standard and found: dead frontmatter
fields (`tldr`/`applyTo`) consumed by nothing, descriptions violating
context-pointer discipline, a `When/Steps/Done when/References` monoculture
turning flat reference into pseudo-steps, governance sediment (FR/T-xxx ids,
"absorbed/renamed from" notes) in ~10 skills, broken internal anchors
(`dd-gitflow-default §3a` cited by two skills but not existing as a section),
duplicate headings/step numbers, negations of retired shapes, five
skill-pairs whose split carries no load, and no which-skill-when router.

## 2. Objective

Minimise and harden the skill surface: 25 instance skill directories become 20
library skills, every one conformant to the 15-rule authoring standard, the
standard itself codified where `ai-engineer` authors (AUTHORING.md), the whole
ecosystem (behavior-map, personas, law, scoped AGENTS.md, tests, projections)
equalized, and every library skill named `dd-*`.

## 3. Scope (candidate 2)

- FR1 — Authoring standard codified: the 15 rules land in
  `dd-ai-eng-knowhow`'s `AUTHORING.md` sibling as the binding skill-authoring
  contract (merged with, not appended beside, its existing content).
- FR2 — Merge A: `dadaia-glossary` + local `domain-modeling` →
  `dd-domain-modeling` (passive sharpen-inline + active challenge/scenario
  discipline; `CONTEXT-FORMAT.md` sibling; ADR-offering criteria — hard to
  reverse / surprising / real trade-off — adapted to the
  `specs/ADRs/decisions.jsonl` canon). Local copy deleted.
- FR3 — Merge B: local `improve-codebase-architecture` folded into
  `dd-architecture-survey` (exploration friction prompts, YAGNI scoping,
  `HTML-REPORT.md` as report-mode sibling). Local `codebase-design` copy
  diff-folded into `dadaia-codebase-design` then deleted.
- FR4 — Merge C: `dd-diagnose` folded into `dd-bug-resolution` (lifecycle +
  7-phase method, `LINEAGE.md` kept as sibling); `dd-diagnose` deleted;
  `dd-bug-registration` stays separate.
- FR5 — Merge D: `dadaia-step0-memory-bootstrap` folded into
  `dadaia-workspace-spec-navigator` as its first phase; step0 deleted.
- FR6 — Systemic conformance pass on every kept skill: `tldr`/`applyTo`
  frontmatter removed; descriptions rewritten as trigger pointers (identity,
  history and grant lists stripped); sediment purged; dead negations removed;
  form follows content (reference stays sections/tables, steps stay steps) —
  including `dadaia-test-stewardship` restructured by branch,
  `dd-backlog-definition` co-located into sections,
  `dd-manager-orchestration` fake steps retired in favour of its tables,
  `dd-cli-library` trimmed to cache-of-expensive-lookups.
- FR7 — Structural fixes: `dd-gitflow-default` commit shapes promoted to a
  real `§3a`-addressable section; `dd-release-definition` duplicate `## 3`
  fixed and the `**Consumes:**` protocol given its own section;
  `dd-manager-orchestration` duplicate step number fixed; `dd-grill-me` round
  format moved into the body.
- FR8 — Router: a which-skill-when map section in `dd-manager-orchestration`
  (no new skill), covering the Arm A/Arm B arcs and the underneath-vocabulary
  skills.
- FR9 — Core design-skill wiring: `dd-release-definition`,
  `dd-backlog-definition`, `dd-bug-resolution` and `dd-release-implement`
  reference `dadaia-codebase-design` / `dd-domain-modeling` /
  `dd-architecture-survey` at the exact steps where design, vocabulary or
  survey judgement is exercised; `product-engineer` and `project-manager`
  gain the `dadaia-codebase-design` and `dd-domain-modeling` grants.
- FR10 — Rename sweep (last): `dadaia-*` → `dd-*` for the seven remaining
  library skills, `dd-release-implement` → `dd-release-implementation`; every
  citation updated (skills, personas, `DADAIA.md`, scoped `AGENTS.md`
  sources, hooks/scripts, tests, memory atoms where they cite skill names).
- FR11 — Ecosystem equalization + reprojection: `behavior-map.json` rows,
  `declared_overlaps` and hash tuples re-recorded; scaffold
  `backlog/AGENTS.md` §5 aligned to the purge-on-pick law (`DADAIA.md` §6.6);
  `dadaia public stage` → `install --target all` → `public doctor` `[ok]`;
  local CI preflight green.

## 4. Out of scope

- New skills beyond the merged `dd-domain-modeling` (net count goes down).
- Persona body/mandate changes beyond `skills:` grant lists.
- Hook, gate or CLI behaviour changes.
- The reference corpus under `.dadaia/references/` (read-only input).
- Godot-* and other operator-private instance skills.

## 5. Acceptance

- A2.1 — `dadaia_workspace/public/skills/` holds exactly 20 directories, all
  `dd-*`-prefixed; the five audit merge/delete decisions are observable
  (no `dadaia-glossary`, `dd-diagnose`, `dadaia-step0-memory-bootstrap`
  directories; no local `codebase-design`, `domain-modeling`,
  `improve-codebase-architecture` instance dirs).
- A2.2 — Zero skills carry `tldr:` or `applyTo:` frontmatter; every
  description is a trigger pointer (no grant lists, no rename/absorb
  history).
- A2.3 — `pytest` (behavior-map enforcer, orphan checker, FR27 citations,
  FR28 grants, public pipeline) green; `dadaia public doctor` `[ok]`;
  `dadaia specs doctor` 0 errors.
- A2.4 — `AUTHORING.md` carries the 15-rule standard; a grep for the five
  structural bugs named in FR7 comes back clean.
