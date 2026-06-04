---
name: audit-cycle
description: project-auditor orchestrates a 4-way parallel-capable audit topology (code-reviewer + security-reviewer + researcher + qa-engineer), then synthesizes a compliance score. Codex runtime receives manual/reference handoffs, not spawned subagents. Triggered manually per project.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (project to audit).
  scope:
    type: string
    required: false
    default: "full"
    description: Audit scope — "full" (entire project) or "partial" (a specific module or feature area).
stages:
  - id: audit_intake
    agent: project-auditor
    expected_output:
      path: ".dadaia/reports/{context}/project-auditor/{run_ts}-intake.handoff.json"
      must_include: ["Audit scope", "Known risks"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.scope"
        as: scope
    gate:
      kind: operator-approval
      prompt: "Approve audit scope?"

  - id: research_evidence
    name: research-evidence
    agent: researcher
    needs: [audit_intake]
    description: "Evidence harvest — dispatch researcher to gather facts before main analysis."
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.audit_intake.output
        as: intake_report

  - id: code_review
    agent: code-reviewer
    needs: [audit_intake, research_evidence]
    parallel_group: audit
    consumes:
      - ".dadaia/reports/{context}/project-auditor/{run_ts}-intake.handoff.json"
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/code-reviewer/{run_ts}-audit.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.audit_intake.output
        as: intake_report
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: security_review
    agent: security-reviewer
    needs: [audit_intake, research_evidence]
    parallel_group: audit
    consumes:
      - ".dadaia/reports/{context}/project-auditor/{run_ts}-intake.handoff.json"
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/security-reviewer/{run_ts}-audit.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.audit_intake.output
        as: intake_report
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: research_review
    agent: researcher
    needs: [audit_intake, research_evidence]
    parallel_group: audit
    consumes:
      - ".dadaia/reports/{context}/project-auditor/{run_ts}-intake.handoff.json"
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/researcher/{run_ts}-audit.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.audit_intake.output
        as: intake_report
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: qa_review
    agent: qa-engineer
    needs: [audit_intake, research_evidence]
    parallel_group: audit
    consumes:
      - ".dadaia/reports/{context}/project-auditor/{run_ts}-intake.handoff.json"
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-audit.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.audit_intake.output
        as: intake_report
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: synthesis
    agent: project-auditor
    needs: [code_review, security_review, research_review, qa_review]
    consumes:
      - ".dadaia/reports/{context}/code-reviewer/{run_ts}-audit.handoff.json"
      - ".dadaia/reports/{context}/security-reviewer/{run_ts}-audit.handoff.json"
      - ".dadaia/reports/{context}/researcher/{run_ts}-audit.handoff.json"
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-audit.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-auditor/{run_ts}-synthesis.handoff.json"
      must_include: ["Compliance score", "Drift items", "Recommended actions"]
    inputs:
      - kind: stage_output
        from: stages.code_review.output
        as: code_report
      - kind: stage_output
        from: stages.security_review.output
        as: security_report
      - kind: stage_output
        from: stages.research_review.output
        as: research_report
      - kind: stage_output
        from: stages.qa_review.output
        as: qa_report

exit_criteria:
  - all_stages: completed
---

# audit-cycle

Comprehensive compliance audit workflow triggered manually per project.

Runtime note: `parallel_group` records workflow topology. Claude may delegate
parallel-capable stages with native tools. Codex receives manual/reference
handoff files and does not spawn subagents or execute runtime parallelism.

`project-auditor` owns the full lifecycle: scopes the audit (intake), dispatches
four specialist reviewers as a parallel-capable review group, and synthesizes a compliance score with
prioritized action items.

## When to use

- Periodic compliance check for a long-running project
- Pre-release audit before a major version ships
- Post-incident deep-dive to identify systemic weaknesses
- Operator-requested snapshot of overall project health

## Stages

1. **audit_intake** — `project-auditor` defines the audit scope, lists known
   risks from memory and recent CLOSURE reports, and proposes which areas each
   specialist should focus on. Operator-approval gate ensures scope is agreed
   before specialist work begins.

2. **4-way parallel-capable audit** — all four may run concurrently after intake only on runtimes with real delegation:
   - **code_review** — `code-reviewer` applies the `architecture-code-review`
     skill: 6-axis checklist, OOP/SOLID, design-pattern misuse, complexity
     heuristics.
   - **security_review** — `security-reviewer` applies `security-audit-protocol`:
     OWASP 2025, dep-scan, secrets scan, IaC review, STRIDE analysis.
   - **research_review** — `researcher` benchmarks the project against industry
     practices: dependency currency, OSS alternatives, known CVEs, relevant
     RFCs.
   - **qa_review** — `qa-engineer` evaluates the test pyramid: unit/integration/
     E2E balance, mock abuse, coverage gaps, slope tests.

3. **synthesis** — `project-auditor` aggregates all four reports into a single
   compliance score (1–10) per the `drift-detection` skill rubric, lists drift
   items with severity tags, and proposes a prioritized set of recommended
   actions for the operator to approve.

## Output

The synthesis report is the primary deliverable. The operator uses it to decide
which recommended actions become backlog tasks (routed via `project-manager`) and
which are deferred. No code is written by this workflow — it is read-only except
for report files under `.dadaia/reports/`.
