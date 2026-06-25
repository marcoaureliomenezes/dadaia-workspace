# PLAN: v0.1.19 — Drift Elimination, Memory Diagrams, PI E2E Parity, User README

**Status:** Aprovado
**Release ID:** v0.1.19

## Approach

Single feature branch (`feature/pi-operational-v1`, continuing the unmerged
stack). Three phases:

1. **DEFINITION** — author SPEC/PLAN/TASKS; eliminate memory drift (MD-1..9); add
   mermaid diagrams (DG-1..6); regenerate the memory catalog. Memory writes are
   permitted only in DEFINITION/CLOSURE (gate MEMORY class).
2. **IMPLEMENTATION** — code (PKG-1, ARCH-NIT-1), PI E2E tests (QA-1..4),
   constitution tense fix (CONST-1), full README rewrite (F). Each task reserves
   `[-]` before writing and `[x]` after; preflight kept green throughout.
3. **CLOSURE** — CLOSURE.md, archive, auto-memory update; full review ladder (QA +
   code-review + security) on the closing tip; gated push; PR update; CI watched
   to green.

## Sequencing & rationale

- Memory first (DEFINITION) because the drift fixes are the highest-value change
  (a false fact is injected into every session via `tech-stack.md`) and they do
  not depend on the code/test work.
- Diagrams co-located with their atoms; designed for GitHub mermaid rendering
  (flowchart/graph), kept small and legible (the operator wants human-readable).
- Catalog regenerated AFTER frontmatter edits (MD-6) so the injected index
  reflects PI.
- Code + tests next; preflight after each to keep the tree green.
- README last in IMPLEMENTATION so it can reference the final, verified surface.
- Reviews on the closing tip (per release-governance: reviews mature the release;
  the push boundary is gated by the per-push-cycle security verdict).

## Risk & mitigation

- **Subagent repo-`.dadaia/` pollution / truncation** (recurring gotcha): the
  coordinator performs file writes at top level; subagents are used only for the
  ADDITIVE review gates and the final drift re-audit, and are told to write
  handoffs to the workspace-root `.dadaia/` and create no caches in the repo.
- **SPEC-DOC-027 release-dir naming:** the dir is SemVer `v0.1.19` from creation
  (avoids the known `release new` slug-vs-doctor bug).
- **Cross-platform tests:** new PI tests use only portable `os`/`pathlib` APIs
  (no POSIX-only `utime(follow_symlinks=)`); injected fake runners, no live `pi`.

## Verification

`dadaia specs doctor` (0 err) · `dadaia public doctor` (`[ok] public-privacy`) ·
`dadaia ci preflight` (green) · `poetry build` (wheel) · mermaid renders ·
fresh drift re-audit reports zero unresolved drift.
