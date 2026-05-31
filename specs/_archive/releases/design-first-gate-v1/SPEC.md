# SPEC: design-first-gate-v1

**Status:** Aprovado
**Release ID:** design-first-gate-v1
**Owner:** ai-engineer
**Phase:** IMPLEMENTATION

## Objective

Implement the 5 collaboration improvements identified in the design-frontend collaboration
analysis report (`2026-05-23T000000Z-design-frontend-collaboration-analysis`). The changes
enforce a design-first workflow where `design-specialist` always produces a report before
`frontend-engineer` implements, `qa-engineer` validates design compliance (not just
functional correctness), and `data-analyst` goes through a formal publication workflow.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | `frontend-engineer` must declare `design_report` as an input contract field and include a hard-STOP gate in prose: no new visual surface without a design-specialist handoff JSON |
| FR-02 | A new `design-first-implementation` workflow encodes the design gate as 4 formal stages: design_production → design_quality_gate → implementation → qa_validation |
| FR-03 | `design-specialist` declares a `figma_url` as a produced output; a new "Figma artifact requirement" section documents what the artifact must contain and the `stub_mode` bypass |
| FR-04 | `design-report-quality-gate` skill adds section 8 (figma_url) to the checklist and a corresponding validation rule |
| FR-05 | `qa-engineer` expands the frontend-engineer pair notes to require two passes: functional E2E + design compliance (token audit, spacing, contrast, visual regression) |
| FR-06 | A new `dashboard-publication` workflow formalises the dashboard design gate (promotes `dashboard-publication-workflow-v1` from backlog) |
| FR-07 | `data-analyst` references the formal `dashboard-publication` workflow in its workflow protocol, replacing the prose-only invoke |
| FR-08 | `spec-refinement` workflow gains a 6th parallel specialist: `design-specialist` in `design_review` stage; synthesis consumes its output; version bumps to 0.4.0 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | `dadaia public doctor` exits 0 after propagation |
| NFR-02 | `poetry run pytest` green after changes |
| NFR-03 | `stub_mode: true` bypass preserved — prototype iterations must not be blocked |
| NFR-04 | `design_report` input in `frontend-engineer` uses `stop_if_missing: false` — bug-fix tasks must not be blocked by schema enforcement |

## Acceptance Criteria

- [ ] All 8 source files edited or created in `dadaia_workspace/public/`
- [ ] `dadaia public stage && dadaia public install --target all` succeeds
- [ ] `dadaia public doctor` exits 0 (all assets `[ok]`)
- [ ] `cd repos/dadaia-workspace && poetry run pytest` exits 0
- [ ] `dashboard-publication-workflow-v1` removed from `specs/backlog/candidates.md`

## Out of scope

- Actually enforcing the Figma requirement on existing reports (only new reports going forward)
- Implementing Playwright visual regression tooling (qa-engineer adds the protocol; tooling is a separate concern)
- Migrating `qa-engineer` or `data-analyst` to handoff-emitter (tracked separately in `agent-comms-wave-2/3`)
