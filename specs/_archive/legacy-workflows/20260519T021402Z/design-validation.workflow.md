---
name: design-validation
description: Sequential design validation. qa-engineer captures screenshots via Playwright, then design-specialist performs UX review against design system and WCAG 2.2 AA criteria.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name.
  deploy_url:
    type: string
    required: true
    description: Base URL of the deployed environment to validate (e.g. staging URL).
  scope:
    type: string
    required: false
    default: "full"
    description: Validation scope — "full" (all pages/flows) or a specific page slug or feature area.
stages:
  - id: capture_screens
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-design-screens.html"
      must_include: ["Screenshots", "Pages covered"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.deploy_url"
        as: deploy_url
      - kind: workflow_input
        from: "$.inputs.scope"
        as: scope
      - kind: workflow_input
        from: "$.inputs.context"
        as: context

  - id: ux_review
    agent: design-specialist
    needs: [capture_screens]
    expected_output:
      path: ".dadaia/reports/{context}/design-specialist/{run_ts}-ux-review.html"
      must_include: ["WCAG findings", "Design system conformance", "Verdict"]
    inputs:
      - kind: stage_output
        from: stages.capture_screens.output
        as: screens_report

exit_criteria:
  - all_stages: completed
---

# design-validation

Sequential workflow for validating visual design and UX quality against design
system standards and WCAG 2.2 AA accessibility criteria.

## When to use

- After a frontend deploy to staging, before operator sign-off
- After any significant UI change (new component, layout refactor, theme update)
- As the design gate in a `tdd-cycle` or `cross-cutting-feature` workflow when
  the operator requests an explicit design review
- Periodic spot-check of existing pages for accessibility regressions

## Stages

1. **capture_screens** — `qa-engineer` uses Playwright to navigate the deployed
   environment and capture full-page screenshots plus interaction-state captures
   (hover states, focus rings, modal open, error states). The report includes all
   pages/flows covered and any Playwright errors encountered. Scope is controlled
   by the `scope` input: "full" captures all known routes; a slug restricts to
   that feature area.

2. **ux_review** — `design-specialist` receives the screen captures and applies
   the `ux-ui-review` skill:
   - WCAG 2.2 AA checklist (colour contrast, focus management, ARIA roles,
     keyboard navigability, text alternatives)
   - Design system conformance (spacing tokens, typography scale, component
     variants, colour palette)
   - Visual hierarchy and layout consistency
   - Mobile/responsive breakpoint review (if captures include mobile viewport)

   The verdict is one of: **Pass** / **Pass with notes** / **Fail** (blocking
   issues found). Blocking issues must be resolved before the operator approves
   the deploy.

## Output

The UX review report is the primary deliverable. `design-specialist` does not
edit any code — it only produces the report. Remediation tasks, if any, are
routed back to `frontend-engineer` via `project-manager`.
