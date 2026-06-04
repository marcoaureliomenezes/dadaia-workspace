---
name: code-review-fan-out
description: Per-PR parallel-capable review topology by code-reviewer + security-reviewer + design-specialist -> project-manager consolidates verdict. Codex runtime receives manual/reference handoffs, not spawned subagents. design-specialist decides internally whether to skip if design is not applicable to the PR.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name.
  pr_ref:
    type: string
    required: true
    description: Pull-request reference (e.g. PR number, branch name, or commit SHA) to review.
  include_design:
    type: boolean
    required: false
    default: false
    description: Hint to design-specialist that this PR has visual/UX changes. Agent still decides whether to produce a substantive review or a skip-not-applicable stub.
stages:
  - id: research_evidence
    name: research-evidence
    agent: researcher
    description: "Evidence harvest — dispatch researcher to gather facts before main analysis."
    consumes: []
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-researcher-evidence.handoff.json"
    inputs:
      - kind: workflow_input
        from: "$.inputs.pr_ref"
        as: pr_ref
      - kind: workflow_input
        from: "$.inputs.context"
        as: context

  - id: code_review
    agent: code-reviewer
    needs: [research_evidence]
    parallel_group: review
    consumes:
      - ".dadaia/handoff/{context}/{run_ts}-researcher-evidence.handoff.json"
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-code-reviewer-{pr_ref}-review.handoff.json"
      must_include: ["Findings", "Verdict"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.pr_ref"
        as: pr_ref
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: security_review
    agent: security-reviewer
    needs: [research_evidence]
    parallel_group: review
    consumes:
      - ".dadaia/handoff/{context}/{run_ts}-researcher-evidence.handoff.json"
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-security-reviewer-{pr_ref}-review.handoff.json"
      must_include: ["Security findings", "Verdict"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.pr_ref"
        as: pr_ref
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: design_review
    agent: design-specialist
    needs: [research_evidence]
    parallel_group: review
    consumes:
      - ".dadaia/handoff/{context}/{run_ts}-researcher-evidence.handoff.json"
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-design-specialist-{pr_ref}-review.handoff.json"
      must_include: ["Verdict"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.pr_ref"
        as: pr_ref
      - kind: workflow_input
        from: "$.inputs.include_design"
        as: include_design
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: consolidation
    agent: project-manager
    needs: [code_review, security_review, design_review]
    consumes:
      - ".dadaia/handoff/{context}/{run_ts}-code-reviewer-{pr_ref}-review.handoff.json"
      - ".dadaia/handoff/{context}/{run_ts}-security-reviewer-{pr_ref}-review.handoff.json"
      - ".dadaia/handoff/{context}/{run_ts}-design-specialist-{pr_ref}-review.handoff.json"
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-{pr_ref}-verdict.handoff.json"
      must_include: ["Consolidated verdict", "Action items"]
    inputs:
      - kind: stage_output
        from: stages.code_review.output
        as: code_report
      - kind: stage_output
        from: stages.security_review.output
        as: security_report
      - kind: stage_output
        from: stages.design_review.output
        as: design_report

exit_criteria:
  - all_stages: completed
---

# code-review-fan-out

Per-PR multi-dimensional code review.

Runtime note: `parallel_group` records workflow topology. Claude may delegate
parallel-capable stages with native tools. Codex receives manual/reference
handoff files and does not spawn subagents or execute runtime parallelism.

Three reviewers form a parallel-capable group and
`project-manager` consolidates their findings into a single actionable verdict.

## When to use

- Any PR that warrants more than a lightweight diff review
- PRs touching security-sensitive paths (auth, secrets handling, input validation)
- PRs with visible UI or UX changes (set `include_design=true`)
- Sprint review gates before merge to main

## Stages

1. **3-way parallel-capable review** — all three may run concurrently only on runtimes with real delegation:
   - **code_review** — `code-reviewer` applies the `architecture-code-review`
     skill: readability, SOLID principles, design-pattern misuse, complexity,
     test coverage adequacy.
   - **security_review** — `security-reviewer` applies `security-audit-protocol`
     in PR-diff mode: checks for new secrets, injection vectors, broken access
     control, dependency additions with known CVEs.
   - **design_review** — `design-specialist` evaluates visual/UX changes using
     the `ux-ui-review` skill. When the PR has no UI changes the agent produces
     a short "not applicable" stub — no workflow schema change is needed because
     the skip decision is internal to the agent.

2. **consolidation** — `project-manager` reads all three reports and emits a
   unified verdict: Approve / Request Changes / Needs Discussion. Lists
   prioritized action items with owner assignments.

## Design-specialist skip behaviour

The `include_design` input is a hint, not a gate. `design-specialist` always runs
and always produces a report. When `include_design=false` and the diff contains no
UI-relevant files the agent writes a one-paragraph "not applicable" stub, fulfilling
the stage output contract without blocking consolidation.

## Output

The consolidation report is the PR verdict. The operator or the author acts on
the listed action items before merging. No code is written — all stages are
read-only except for report files under `.dadaia/reports/`.
