---
name: dadaia-workspace-spec-reviewer
description: >
  Use when: reviewing or refining dadaia-workspace specs before implementation or
  before declaring a refinement pass complete. Audits memory Markdown atomicity,
  RELEASE.json's phase field, status canonicity, RELEASE.json's closure-log entries,
  external image references, and the 300-line PLAN policy. Loads canonical owner
  docs first, detects duplicated ownership, and routes unresolved gaps to the PM's
  operator-gated intake report.
tldr: "Audit spec set (memory atomicity, phase, status tokens, closure log, PLAN length) before implementation; route gaps to PM intake."
---

# dadaia-workspace-spec-reviewer

## 1. When

- Reviewing or refining dadaia-workspace specs before implementation.
- Before declaring a refinement pass complete.

## 2. Steps

1. Load `<specs-dir>/constitution.md`.
2. Load atomic memory: `memory/ARCHITECTURE.md`, `memory/product/catalog.json`, `memory/product/index.md`, `memory/TECHSTACK.md`.
3. Load feature atoms under `memory/product/` on demand.
4. Read `<specs-dir>/releases/<release-id>/RELEASE.json`'s `phase` field directly (no fold, no `ACTIVE.md`).
5. Load active release artifacts: `SPEC.md`, `PLAN.md`, `TASKS.md`.
6. Load `RELEASE.json`'s closure `log` entries when phase is CLOSURE or ARCHIVED — `CLOSURE.md` retired, never expect one.
7. Load `specs/backlog/BACKLOG.json`'s `active` array if present.
8. Check memory atomicity: no `Changelog|History|Histórico|Versions?` sections, no narrative of past versions.
9. Check the product memory catalog: `memory/product/` is a folder, `index.md` links every feature atom.
10. Check `catalog.json` matches the Markdown frontmatter when present.
11. Check each feature atom has: Purpose, Usage flow, Typical trigger, Differentiator, Runtime state touched, Dependencies.
12. Check no external image references — a diagram is a fenced Mermaid block, never an `<img>` to an external file.
13. Check Mermaid blocks are syntactically readable by the target renderer.
14. Check status canonicity: `**Status:** Draft|Em revisão|Aprovado` exactly — no `[x] Approved`, `Accepted`, `Completed`.
15. Check phase consistency: `RELEASE.json`'s `phase` matches the artifacts that exist.
16. Check PLAN is <= 300 lines — warning before 2026-05-17, error after.
17. Check closure narrative completeness: every `RELEASE-EVENTS.md`-named class present once phase is CLOSURE.
18. Check no archived release directory exists — a shipped release is deleted outright, only its histo record survives.
19. Check no live PLAN/TASKS outside `releases/` (except legacy `features/*/` during migration).
20. Check `_archive/` is never cited as a gate of authority.
21. Check traceability: every approved requirement maps into PLAN strategy and at least one TASKS entry.
22. Report findings ordered by severity.
23. Route unresolved issues to the PM's operator-facing intake report — never append to the backlog directly.

## 3. Done when

- Every dimension in §2 steps 8-21 has been checked and findings are ordered by severity.
- No implementation suggestion bypasses an unresolved spec conflict.
- Every finding cites the path plus the marker/attribute that triggered it.
- If no blocking issues remain, the report says so explicitly.

## 4. References

- `dd-backlog-definition` §5 — intake routing, never a direct backlog append.
- `dd-release-implement` (`RELEASE-EVENTS.md`) — closure `log` conversion table.
- `specs/memory/AGENTS.md` — feature-atom heading rule.
- Segmented releases (ADR-1/ADR-5): audit the segment named by `RELEASE.json`'s `segment` field, under `releases/<release-id>/<segment>/`.
