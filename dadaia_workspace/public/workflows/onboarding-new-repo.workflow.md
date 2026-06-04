---
name: onboarding-new-repo
description: Onboarding a new repo into the workspace. Parallel-capable assessment topology by software-architect (ONBOARD), devops-engineer (SCAN), and qa-engineer (pyramid audit), then project-manager synthesizes findings and product-engineer authors the initial SPEC and road-to-compliance TASKS. Codex runtime receives manual/reference handoffs, not spawned subagents.
version: 0.2.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context — the new repo being onboarded.
  maturity_target:
    type: string
    required: false
    default: "standard"
    description: Desired compliance level — "minimal" (only critical gaps), "standard" (workspace baseline), or "full" (production-grade).
stages:
  - id: arch_assessment
    agent: software-architect
    parallel_group: assessment
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-onboard.handoff.json"
      must_include: ["Architecture maturity", "Gaps"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.maturity_target"
        as: maturity_target

  - id: devops_assessment
    agent: devops-engineer
    parallel_group: assessment
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-onboard.handoff.json"
      must_include: ["CI/CD status", "Compliance gaps"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.maturity_target"
        as: maturity_target

  - id: qa_assessment
    agent: qa-engineer
    parallel_group: assessment
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-onboard.handoff.json"
      must_include: ["Test pyramid", "Coverage gaps"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.maturity_target"
        as: maturity_target

  - id: synthesis
    agent: project-manager
    needs: [arch_assessment, devops_assessment, qa_assessment]
    consumes:
      - ".dadaia/reports/{context}/software-architect/{run_ts}-onboard.handoff.json"
      - ".dadaia/reports/{context}/devops-engineer/{run_ts}-onboard.handoff.json"
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-onboard.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-onboard-synthesis.handoff.json"
      must_include: ["Status", "Road to compliance"]
    inputs:
      - kind: stage_output
        from: stages.arch_assessment.output
        as: arch_report
      - kind: stage_output
        from: stages.devops_assessment.output
        as: devops_report
      - kind: stage_output
        from: stages.qa_assessment.output
        as: qa_report
    gate:
      kind: operator-approval
      prompt: "Approve synthesis report before product-engineer authors the onboarding SPEC?"

  - id: spec_write
    agent: product-engineer
    needs: [synthesis]
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-onboard-synthesis.handoff.json"
    expected_output:
      path: "specs/onboarding/SPEC.md"
      must_include: ["Status", "Road to compliance"]
    inputs:
      - kind: stage_output
        from: stages.synthesis.output
        as: synthesis_report

exit_criteria:
  - all_stages: completed
---

# onboarding-new-repo

Use this workflow the first time a repo enters the dadaia workspace. The three
specialist roles each have a dedicated onboarding/audit mode — this workflow treats them
as a parallel-capable topology and synthesizes a coherent compliance plan.

Runtime note: `parallel_group` records workflow topology. Claude may delegate
parallel-capable stages with native tools. Codex receives manual/reference
handoff files and does not spawn subagents or execute runtime parallelism.

## When to use

- A new repo is added under `repos/`
- An existing repo migrates into the workspace from elsewhere
- Periodic re-audit of a long-running repo to re-baseline compliance

## Stages

Parallel assessment by 3 specialists, each in their canonical audit mode:

- **arch_assessment** — `software-architect` ONBOARD mode: scans the codebase, reads
  any specs that exist, assesses architecture maturity, lists gaps.
- **devops_assessment** — `devops-engineer` SCAN mode: inspects `.github/workflows/`,
  Git flow compliance, branch protection, deploy configuration.
- **qa_assessment** — `qa-engineer` audit mode: measures the unit/integration/E2E
  pyramid, identifies slope tests, mock abuse, volume padding, coverage gaps.

Then a single synthesis:

- **synthesis** — `product-engineer` consumes all three reports and writes an
  onboarding SPEC (`specs/onboarding/SPEC.md`) with a prioritized road-to-compliance
  plan: which gaps must close immediately, which can be deferred, and who owns each.

## Maturity target

The `maturity_target` input shapes how strictly each specialist judges:

- **minimal** — only block on items that pose immediate risk (no security gates, no
  CI at all, no tests at all)
- **standard** (default) — workspace baseline: CI exists, tests pyramid roughly
  balanced, security checks present
- **full** — production-grade: SLOs declared, runbooks present, full pyramid balance,
  observability, security gates

## Output

A single SPEC at `specs/onboarding/SPEC.md`. After approval, the operator runs
`tdd-cycle` (or `bug-fix-fastlane`) per task in the resulting TASKS.md to close the
gaps. Subsequent re-audits can update or replace this SPEC.

## What this workflow does NOT do

- Does not implement any fix — implementation is delegated to `tdd-cycle` per task
- Does not write code in the target repo — all 3 specialists are read-only
- Does not modify CI/CD pipelines — devops-engineer reports, doesn't implement
