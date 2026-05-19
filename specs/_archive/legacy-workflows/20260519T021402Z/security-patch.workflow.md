---
name: security-patch
description: Coordinated response to a CVE or security alert. devops-engineer assesses impact, an implementer applies the patch, qa-engineer + software-architect validate in parallel, then qa validates the deploy.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context (target project).
  cve_id:
    type: string
    required: true
    description: CVE identifier or alert reference (e.g. CVE-2026-12345 or Dependabot-PR-99).
  implementer_agent:
    type: string
    required: false
    default: software-engineer
    description: Which engineer applies the patch. One of frontend-engineer, backend-engineer, software-engineer, game-developer.
stages:
  - id: cve_review
    agent: devops-engineer
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-{cve_id}-impact.html"
      must_include: ["Impact assessment", "Affected packages"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.cve_id"
        as: cve_id
    gate:
      kind: operator-approval
      prompt: "Approve patch plan and proceed with implementation?"

  - id: patch_impl
    agent: "{{implementer_agent}}"
    needs: [cve_review]
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-{cve_id}-patch.html"
      must_include: ["Patch applied", "All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.cve_review.output
        as: cve_review_report

  - id: regression_test
    agent: qa-engineer
    needs: [patch_impl]
    parallel_group: post_patch
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{cve_id}-regression.html"
      must_include: ["Regression suite"]
    inputs:
      - kind: stage_output
        from: stages.patch_impl.output
        as: patch_report

  - id: security_audit
    agent: software-architect
    needs: [patch_impl]
    parallel_group: post_patch
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-{cve_id}-security.html"
      must_include: ["Security audit"]
    inputs:
      - kind: stage_output
        from: stages.patch_impl.output
        as: patch_report

  - id: deploy_validation
    agent: qa-engineer
    needs: [regression_test, security_audit]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{cve_id}-deploy.html"
      must_include: ["Deploy validated"]
    inputs:
      - kind: stage_output
        from: stages.regression_test.output
        as: regression_report
      - kind: stage_output
        from: stages.security_audit.output
        as: security_report
    gate:
      kind: operator-approval
      prompt: "Approve deploy of security patch?"

exit_criteria:
  - all_stages: completed
---

# security-patch

Coordinated multi-agent response to a security advisory (CVE, Dependabot, internal
incident finding).

## When to use

- A CVE is reported on a dependency the workspace uses
- Dependabot opens a security PR
- An internal audit (`architect-code-audit`) flags a security issue that requires patching
- A penetration test report calls out a vulnerability

## Pipeline

1. **cve_review** — `devops-engineer` assesses the alert: which services/packages are
   affected, severity, exploit availability, recommended remediation. Includes a patch
   plan (upgrade vs workaround vs config change). Operator gate before proceeding.
2. **patch_impl** — the chosen implementer applies the patch. The implementer is chosen
   by the stack of the affected code (`backend-engineer` for Go, `software-engineer` for
   Python/Node, etc.). Tests must pass before this stage closes.
3. **Parallel post-patch validation:**
   - **regression_test** — `qa-engineer` runs the regression E2E suite to ensure the
     patch did not break existing behavior.
   - **security_audit** — `software-architect` verifies the patch actually addresses the
     vulnerability and didn't introduce new attack surface.
4. **deploy_validation** — `qa-engineer` validates the patched deploy in the live
   environment. Operator-approval gate before closure.

## Why this is a separate workflow

The patch flow has unique constraints not present in `tdd-cycle`:
- The fix is dictated by the CVE, not by SPEC evolution
- Security review by `software-architect` is mandatory (not optional)
- Time pressure differs — severity drives urgency
- Operator gates are placed for risk management, not feature approval
