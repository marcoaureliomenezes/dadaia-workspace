---
name: dashboard-publication
description: Design-gated dashboard publication. data-analyst builds → design-specialist reviews viz grammar + palette → qa-engineer validates data correctness + a11y → operator approves → data-analyst publishes via DABs.
version: 1.0.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name.
  dashboard_name:
    type: string
    required: true
    description: Dashboard name/slug being published.
  task_id:
    type: string
    required: true
    description: Approved task identifier from TASKS.md.
stages:
  - id: build_dashboard
    name: build-dashboard
    agent: data-analyst
    description: "Build dashboard SQL queries, widget layout, Genie config, and Playwright evaluation. Deploy to dev workspace."
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/data-analyst/{run_ts}-{task_id}-dashboard.handoff.json"
      must_include: ["Dashboard layout", "SQL queries", "Playwright evaluation"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id

  - id: design_review
    name: design-review
    agent: design-specialist
    needs: [build_dashboard]
    description: "Review dashboard viz grammar, palette, hierarchy, and accessibility. Consume Playwright screenshots from data-analyst report."
    consumes:
      - ".dadaia/reports/{context}/data-analyst/{run_ts}-{task_id}-dashboard.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/design-specialist/{run_ts}-{dashboard_name}-review.handoff.json"
      must_include: ["palette", "hierarchy", "Approved"]
    inputs:
      - kind: stage_output
        from: stages.build_dashboard.output
        as: dashboard_report
    gate:
      kind: operator-approval
      prompt: "Design review complete. Approve before qa-engineer validation and production publish?"

  - id: qa_validation
    name: qa-validation
    agent: qa-engineer
    needs: [design_review]
    description: "Validate dashboard: data correctness (query results match expected), refresh cadence, widget accessibility (axe-core), and KPI-tile screenshot comparison."
    consumes:
      - ".dadaia/reports/{context}/design-specialist/{run_ts}-{dashboard_name}-review.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-dashboard-validation.handoff.json"
      must_include: ["Data correctness pass", "A11y pass", "Refresh cadence pass"]
    inputs:
      - kind: stage_output
        from: stages.design_review.output
        as: design_review_report

  - id: publish
    name: publish
    agent: data-analyst
    needs: [qa_validation]
    description: "Publish the dashboard to production via DABs bundle deploy. Record deploy URL, audit trail, and sharing settings."
    consumes:
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-dashboard-validation.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/data-analyst/{run_ts}-{task_id}-published.handoff.json"
      must_include: ["Deployed", "Production URL", "Sharing settings"]
    inputs:
      - kind: stage_output
        from: stages.qa_validation.output
        as: validation_report
    gate:
      kind: operator-approval
      prompt: "QA validation passed. Confirm production deploy of dashboard?"

exit_criteria:
  - all_stages: completed
---

# dashboard-publication

Formal workflow for publishing Databricks dashboards with a mandatory design gate before
any production publication. Promotes `dashboard-publication-workflow-v1` from the backlog
(deferred from `agents-r3-v1`, Q3 operator decision).

## When to use

Use this workflow for every new dashboard publication and every significant dashboard
redesign. Minor data updates to existing published dashboards (new partition, updated
filter) may skip the `design_review` stage if the visual layout is unchanged — document
the skip reason in the task report.

## Stages

1. **build_dashboard** — `data-analyst` builds the full dashboard: SQL queries, widget
   layout, Genie space config (if applicable), Playwright evaluation screenshots.
   The dashboard is deployed to the dev workspace. The report includes embedded
   screenshots as evidence for the design review.

2. **design_review** — `design-specialist` reviews the dashboard's visual quality:
   viz grammar (chart type appropriateness), palette (colour-blind-safe, contrast),
   information hierarchy (KPI → decomposition → detail), annotation clarity, and
   accessibility. An operator-approval gate here allows the operator to review the
   design assessment before the QA stage begins.

3. **qa_validation** — `qa-engineer` validates:
   - *Data correctness:* query results match expected values for known test partitions
   - *Refresh cadence:* timestamp widget shows data within the declared SLA window
   - *Accessibility:* axe-core audit on the deployed dashboard URL
   - *KPI regression:* screenshot diff against baseline for each KPI tile

4. **publish** — `data-analyst` executes the production DABs bundle deploy. The
   publish report records the production URL, sharing configuration (default: specific
   users/groups, never public), and audit trail. An operator-approval gate at the end
   confirms intent before production traffic reaches the dashboard.

## Relationship to data-analyst workflow protocol

This workflow replaces the inline prose "invoke design-specialist" step in the
`data-analyst` workflow protocol (step 6). The protocol's step 6 now instructs
data-analyst to run this workflow rather than invoking design-specialist directly,
ensuring the design gate and QA validation are both formally enforced.
