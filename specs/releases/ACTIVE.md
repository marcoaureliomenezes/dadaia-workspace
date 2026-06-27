---
release: none
phase: ARCHIVED
---

No active release.

Last shipped: **v0.1.28 — Workflow Model Governance + Panel Control Plane**
(CLOSED + Aprovado; closure at `specs/_archive/releases/v0.1.28/CLOSURE.md`). Delivered the
whole `FEAT-WORKFLOW-MODEL-GOVERNANCE-01` epic A→D: named `WorkflowModelProfile` registry
over `harness_models`, atomic overlay store, single `WorkflowExecutionPolicyResolver`
(CLI > overlay > library default), per-run `workflow_policy` snapshot, Codex/PI per-request
model, Python `dadaia_catalog` as governed source, first-class panel Workflows control
plane (GET/PUT/validate + editor + run evidence + read-only fragment inspector), and the
`WMP-*` governance doctor. Layer-2 = codex|pi only.

Deferred to a future release (see backlog `workflow-model-governance-operator-profiles-and-context-overlays`):
operator-added PI `.local.json` profiles, per-context overlay inheritance, and the
snapshot `runtime_kind`-vs-governed-harness reconciliation under `--harness` override.
