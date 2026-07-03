---
name: architecture-uml-decomposition
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: operator architectural deep-review 2026-07-02 (lane A — coupling/isolation/UML)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/doctor.py#SpecsDoctor" }
    change: "split the 2,820-line / 54-method god class into focused validator classes (structural tree, lint, orchestration coherence, closure/audit law, bug/backlog governance) behind a thin SpecsDoctor coordinator, each independently testable and class-diagrammable"
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/api.py#render_api_agents_canonical" }
    change: "split the 1,402-line panel views/api.py (24 loose module functions spanning agents/workflows/sessions/reports/academy domains) into per-domain view modules so the panel API surface has one responsibility per module"
  - subject: { kind: catalog, ref: "agent-comms" }
    change: "merge the reports_next / reports_retention / reports_validation feature triplet (three top-level feature packages, ~826 lines total) into one features/reports/ package with next/retention/validation submodules"
  - subject: { kind: doc, ref: "memory/architecture.md#Visual evidence" }
    change: "produce and commit the canonical UML class/package diagrams under specs/assets/architecture/ (the atom's Visual evidence section records zero assets today) and regenerate them at closure of every structural release"
---

# BACKLOG — Architecture UML decomposition

**Priority:** HIGH. The operator requires the implementation to be UML-representable
with clean OOP for human maintenance. The 2026-07-02 review verified the Spec Context
kernel (`features/spec_context`) is well isolated (imports nothing from scaffolding,
projection, or the lifecycle engine); the blockers to a clean class diagram are the two
god modules above plus feature-shape noise. Also owns (prose scope): a one-line scope
docstring decision for `features/workspace_clean` (merge into `workspace` or state why
it stands alone).

Cross-refs: the `lifecycle ↔ workflows` import cycle is owned by
`import-boundary-enforcement`; harness identity/typing by `harness-isolation-profiles`;
legacy package deletions by `legacy-surface-retirement`.
