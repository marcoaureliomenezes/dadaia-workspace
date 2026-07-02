---
name: import-boundary-enforcement
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (A-5)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/policy_resolver.py#WorkflowExecutionPolicyResolver" }
    change: "fix the 5 red import-linter chains: put json_workflow_model_policy_store behind a core protocol port for its 3 feature consumers (policy_resolver, policy_doctor, panel.views.workflow_policy); break the subject_registry -> cli.main -> infrastructure.bug_reporter chain (inject the Typer app-tree/anchor provider from the composition root); then wire lint-imports into the CI lint job AND dadaia ci preflight; add a features-no-cross-feature contract with today's 8 edges as documented ignores; break the workflows<->lifecycle import cycle; finalize the setup.cfg comment; core-purity follow-up: move core/specs_backup + core/specs_version write-I/O out of core/ or name them authorized exceptions with a grep guard"
---

# BACKLOG — Import-boundary enforcement

**Priority:** HIGH. Contracts are red (2/6 broken) and CI-unenforced while four sources
claimed otherwise (doc side fixed in v0.1.47); violations grew 3 -> 5 between the bug
filing and the audit — the silent-erosion thesis is proven. Bug deferred here:
`import-linter-contracts-red-but-not-ci-enforced`.

**Cycle-break shape (2026-07-02 review, lane A):** the `workflows ↔ lifecycle` cycle is
bidirectional (`workflows/dadaia_catalog.py` imports 8 lifecycle symbols while
`lifecycle/policy_doctor.py` lazily imports the governed catalog back). Break it by
extracting the governed workflow catalog + step-sequence declarations into a shared
seam neither feature imports from the other, then add the features-no-cross-feature
contract on top.
