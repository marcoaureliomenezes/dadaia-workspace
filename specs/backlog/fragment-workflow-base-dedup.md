---
name: fragment-workflow-base-dedup
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: v0.1.47 grill D-6 + audit lifecycle lane
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/workflows/release_definition.py#ReleaseDefinitionWorkflow" }
    change: "extract a shared FragmentGateWorkflow base from the 5 near-verbatim workflow bodies (~1,500 duplicated lines across _run_model_step/_resolve_upstream/_produce_payload/_scope); persona/fragment/dynamic-context assembly then lives at ONE seam (v0.1.47 threaded a shared persona helper through each body as the minimal fix; this entry removes the duplication itself so one-seam-only fixes cannot recur)"
---

# BACKLOG — Fragment workflow base dedup

**Priority:** MEDIUM. Structural prevention for the persona-injection class of defect.
