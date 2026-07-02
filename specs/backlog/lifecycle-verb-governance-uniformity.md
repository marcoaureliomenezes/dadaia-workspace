---
name: lifecycle-verb-governance-uniformity
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (B/lifecycle, E.4) + v0.1.47 QA-review blocker
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/pipeline.py#LifecyclePipeline" }
    change: "route release define / backlog define through WorkflowExecutionPolicyResolver (profile-ids-only, snapshot frozen before step 1, apply_resolved_policy the sole author of runtime_kind on EVERY verb, retiring the raw id:effort second path); wire audit/research/bug_report as invocable CLI verbs + container builders OR demote their catalog availability from AVAILABLE; fix run_implement_review_loop: inject the resolved rejection digest into the next implement prompt, run loop steps through the LifecycleAgentRunner gate, and give the loop a CLI caller"
  - subject: { kind: code, ref: "dadaia_workspace/core/models/lifecycle.py#TRANSITIONS" }
    change: "reconcile the review->implementation backtrack transitions with the chosen rework model: with run_implement_review_loop as the canonical rework path, either keep the direct backtrack transitions as its documented mechanism or remove them so the table implies no unused path (absorbs the retired review-rejection-rework-path idea, 2026-06-25)"
---

# BACKLOG — Lifecycle verb governance uniformity

**Priority:** HIGH. The three audit sub-findings beyond persona injection (which
v0.1.47 fixed): model/harness governance covers only the pipeline verb; three
catalog-AVAILABLE workflows are not operator-invocable; the implement/review loop
drops its rejection digest and bypasses the runner gate. Until this ships, the
dadaia-workflows memory atom documents 4 invocable verbs / 7 defined honestly.
