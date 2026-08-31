# Spec-set review dimension (absorbed from dadaia-workspace-spec-reviewer, T-053-25)

Run when reviewing/refining a spec set before implementation or before declaring a
refinement pass complete. Doctor codes enforce most of this mechanically — this
dimension is the human-shaped pass over what the doctor cannot judge.

## Checks

- Memory atomicity: no changelog/history sections, no narrative of past versions (the
  doctor's forbidden-heading matcher is the mechanical half).
- Product catalog: `memory/product/` folder + `index.md` linking every feature atom;
  `catalog.json` matches frontmatter.
- Each feature atom carries: Purpose, Usage flow, Typical trigger, Differentiator,
  Runtime state touched, Dependencies.
- Diagrams are fenced Mermaid, never external `<img>`; blocks render.
- Status canonicity: `**Status:** Draft|Em revisão|Aprovado` exactly.
- Phase consistency: `_RELEASE.json`'s `phase` matches the artifacts on disk; closure
  `log` classes complete once phase is CLOSURE (`dd-release-implement` RELEASE-EVENTS.md).
- PLAN ≤ 300 lines; no live PLAN/TASKS outside `releases/`; no archived release dir.
- Traceability: every approved requirement maps into PLAN strategy and ≥1 TASKS entry.
- Route unresolved gaps to the PM's operator-gated intake report — never a direct
  backlog append.

## Done when

- Every check above ran; findings ordered by severity, each citing path + trigger.
- No implementation suggestion bypasses an unresolved spec conflict.
