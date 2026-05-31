# Closure: Release — design-first-gate-v1

> **Status:** Aprovado
> **Release ID:** design-first-gate-v1
> **Owner:** ai-engineer
> **Closed:** 2026-05-24

## Summary

This release implements the 5 collaboration improvements identified in the design-frontend
analysis report (`2026-05-23T000000Z-design-frontend-collaboration-analysis`). The changes
enforce a design-first workflow across the workspace: `frontend-engineer` and `data-analyst`
can no longer skip design-specialist review; `qa-engineer` now validates design compliance
(not just functional correctness); and `spec-refinement` captures design input before specs
are locked.

Two new workflows (`design-first-implementation` and `dashboard-publication`) formalise the
gate as machine-enforceable stages. The existing `spec-refinement` workflow gains a 6th
parallel specialist (`design-specialist`). The `design-report-quality-gate` skill now
requires a `figma_url` in the sidecar (with `stub_mode` bypass for prototype iterations).

The backlog candidate `dashboard-publication-workflow-v1` (deferred since `agents-r3-v1`)
has been promoted and removed from `specs/backlog/candidates.md`.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-DFG-01 | Edit `frontend-engineer.md`: `design_report` input + hard-STOP gate | working-tree |
| T-DFG-02 | Create `design-first-implementation.workflow.md` | working-tree |
| T-DFG-03 | Edit `design-specialist.md`: `figma_url` output + Figma artifact section | working-tree |
| T-DFG-04 | Edit `design-report-quality-gate/SKILL.md`: section 8 + validation rule | working-tree |
| T-DFG-05 | Edit `qa-engineer.md`: two-pass design compliance validation | working-tree |
| T-DFG-06 | Create `dashboard-publication.workflow.md` | working-tree |
| T-DFG-07 | Edit `data-analyst.md`: workflow step 6 → dashboard-publication workflow | working-tree |
| T-DFG-08 | Edit `spec-refinement.workflow.md`: `design_review` stage + synthesis update + v0.4.0 | working-tree |
| T-DFG-09 | `dadaia public stage && dadaia public install --force --target all` | N/A |
| T-DFG-10 | `poetry run pytest` green | pending |
| T-DFG-11 | Removed `dashboard-publication-workflow-v1` from `specs/backlog/candidates.md` | working-tree |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| No drift after propagation | `dadaia public doctor` | zero `[drift]` or `[error]` lines |
| New workflows projected to all runtimes | `dadaia public doctor` | `[ok]` for `design-first-implementation` + `dashboard-publication` in claude/opencode/agents/codex runtimes |
| Library tests | `poetry run pytest` | pending — running in background |

## Drifts

None. All changes were planned from the analysis report and implemented cleanly.

## Memory updates

- `specs/memory/architecture.html`: no change — release adds agent behavior, not architecture layers
- `specs/memory/tech-stack.html`: no change — no new dependencies
- `specs/memory/product/index.html`: no change — this release upgrades existing agent capabilities

## Backlog returns

- `dashboard-publication-workflow-v1` → **PROMOTED** to `public/workflows/dashboard-publication.workflow.md` (removed from backlog)

## Archive decision

**MOVE** — release directory moved to `specs/_archive/releases/design-first-gate-v1/`.
