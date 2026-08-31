# TASKS — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 2 — skills quality consolidation

- [x] T-046-08 — FR1: codify the 15-rule authoring standard into
  `dd-ai-eng-knowhow`'s `AUTHORING.md` (merged with its existing content, one
  standard, no duplication); re-record that row's behavior-map hash.
  Write set: dadaia_workspace/public/skills/dd-ai-eng-knowhow/**,
  dadaia_workspace/public/entities/behavior-map.json.
  Blocked by: none. Delivers: every later task applies a written, binding
  standard the operator ratified.
- [x] T-046-09 — FR2 Merge A: `dd-domain-modeling` born from `dadaia-glossary`
  + local `domain-modeling` (CONTEXT-FORMAT.md sibling; ADR criteria adapted
  to `specs/ADRs/decisions.jsonl`); `dadaia-glossary` dir deleted; local
  `domain-modeling` instance dirs deleted; grants swapped
  (software-architect, product-engineer); behavior-map row + overlaps +
  hashes; cross-citations updated.
  Write set: dadaia_workspace/public/skills/**,
  dadaia_workspace/public/agents/*.md,
  dadaia_workspace/public/entities/behavior-map.json,
  .agents/skills/domain-modeling/ (delete), .claude/skills/** (delete),
  CONTEXT.md.
  Blocked by: T-046-08. Delivers: one skill owns the domain language, active
  and passive, reachable by every prose-writing agent.
- [-] T-046-10 — FR3 Merge B: `dd-architecture-survey` absorbs
  `improve-codebase-architecture` (friction prompts, YAGNI scoping,
  HTML-REPORT.md report-mode sibling); `dadaia-codebase-design` diff-folded
  against the reference `codebase-design`; both local instance copies
  deleted; behavior-map hashes.
  Write set: dadaia_workspace/public/skills/dd-architecture-survey/**,
  dadaia_workspace/public/skills/dadaia-codebase-design/**,
  dadaia_workspace/public/entities/behavior-map.json,
  .agents/skills/improve-codebase-architecture/ (delete),
  .agents/skills/codebase-design/ (delete), .claude/skills/** (delete).
  Blocked by: T-046-08. Delivers: the survey carries the full reference
  method dadaia-ized; zero unmanaged reference copies remain.
- [ ] T-046-11 — FR4 Merge C: `dd-bug-resolution` absorbs `dd-diagnose`
  (7-phase method inline, LINEAGE.md kept as sibling); `dd-diagnose` deleted;
  `DADAIA.md` §7.3 law source updated; behavior-map row removed, overlap
  triple updated, hashes.
  Write set: dadaia_workspace/public/skills/dd-bug-resolution/**,
  dadaia_workspace/public/skills/dd-diagnose/ (delete),
  dadaia_workspace/public/data/DADAIA.md,
  dadaia_workspace/public/entities/behavior-map.json, cross-citations in
  public/skills/**.
  Blocked by: T-046-08. Delivers: Arm B post-registration is one skill —
  lifecycle and method, no forced hop.
- [ ] T-046-12 — FR5 Merge D: `dadaia-workspace-spec-navigator` absorbs
  `dadaia-step0-memory-bootstrap` as its first phase; step0 deleted; persona
  grants deduped; behavior-map row folded, hashes.
  Write set: dadaia_workspace/public/skills/dadaia-workspace-spec-navigator/**,
  dadaia_workspace/public/skills/dadaia-step0-memory-bootstrap/ (delete),
  dadaia_workspace/public/agents/*.md,
  dadaia_workspace/public/entities/behavior-map.json, cross-citations.
  Blocked by: T-046-08. Delivers: one session-grounding protocol (context →
  memory → release trio), no duplicated catalog/atom steps.
- [ ] T-046-13 — FR6 systemic conformance pass over the 16 kept skills:
  `tldr`/`applyTo` removed, descriptions rewritten as trigger pointers,
  sediment and dead negations purged, form-follows-content restructures
  (test-stewardship by branch, backlog-definition sections,
  manager-orchestration tables, cli-library trim, handoff-emitter and
  task-manager branch separation, audit-project id purge + spec-review
  integration); behavior-map hashes re-recorded.
  Write set: dadaia_workspace/public/skills/**,
  dadaia_workspace/public/entities/behavior-map.json.
  Blocked by: T-046-09, T-046-10, T-046-11, T-046-12. Delivers: every kept
  skill audits clean against the 15 rules.
- [ ] T-046-14 — FR7+FR8+FR9: gitflow commit-shapes promoted to a citable
  `§3a` section; release-definition duplicate `## 3` fixed and `**Consumes:**`
  sectioned; manager-orchestration duplicate step fixed + which-skill-when
  router section; grill round format into the body; core design-skill wiring
  into the four lifecycle skills; PE/PM gain design/domain grants;
  behavior-map hashes.
  Write set: dadaia_workspace/public/skills/**,
  dadaia_workspace/public/agents/*.md,
  dadaia_workspace/public/entities/behavior-map.json.
  Blocked by: T-046-13. Delivers: broken anchors gone; a dispatcher can route
  any demand to the right skill from one map.
- [ ] T-046-15 — FR10 rename sweep (last content act): seven `dadaia-*` dirs
  → `dd-*`, `dd-release-implement` → `dd-release-implementation`; whole-tree
  citation sweep (public/**, tests, memory atoms, CONTEXT.md, scoped
  AGENTS.md sources); behavior-map rows renamed.
  Write set: dadaia_workspace/public/**, tests/**, specs/memory/**,
  CONTEXT.md.
  Blocked by: T-046-14. Delivers: one uniform `dd-*` namespace, zero stale
  citations (FR27 green).
- [ ] T-046-16 — FR11 equalization + reprojection: scaffold backlog AGENTS.md
  §5 aligned to purge-on-pick; behavior-map final verification; `dadaia
  public stage` → `install --target all` → `public doctor` `[ok]`; stale
  projected skill dirs removed from every harness target; full local CI
  preflight green.
  Write set: dadaia_workspace/public/scaffold/backlog/AGENTS.md,
  dadaia_workspace/public/entities/behavior-map.json, .claude/**, .agents/**,
  .codex/**, .kimi-code/**, specs/backlog/AGENTS.md.
  Blocked by: T-046-15. Delivers: instance mirrors the library; doctor and
  preflight prove it.
