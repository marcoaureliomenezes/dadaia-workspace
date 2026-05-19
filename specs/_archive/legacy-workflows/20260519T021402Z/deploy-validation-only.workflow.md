---
name: deploy-validation-only
description: Standalone deploy validation by qa-engineer against a live environment. Useful for post-release smoke, validating deploys triggered outside the normal cycle, or auditing existing production state.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context (target project).
  deploy_url:
    type: string
    required: true
    description: URL or environment identifier to validate (e.g. https://app.example.com or staging).
  scope:
    type: string
    required: false
    default: "smoke"
    description: Validation depth — "smoke" (critical paths), "full" (entire E2E suite), or "feature" (one feature only).
stages:
  - id: run_validation
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-deploy-validation.html"
      must_include: ["Deploy URL", "Scenario Results"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.deploy_url"
        as: deploy_url
      - kind: workflow_input
        from: "$.inputs.scope"
        as: scope

exit_criteria:
  - all_stages: completed
---

# deploy-validation-only

A single-stage workflow for validating an existing deploy without going through an
implementation cycle.

## When to use

- After a release: smoke-test the new prod build
- After a deploy triggered manually outside the `tdd-cycle`
- Auditing a long-running environment for regressions
- Re-validating an environment after an infra change (no code change involved)

## Stage

The single stage runs `qa-engineer` against the supplied `deploy_url`. The agent:

1. Reads `SPEC.md` of the context to know what features should exist
2. Picks the toolchain matching the target (Playwright + MCP for browser; httpx for APIs;
   CLI black-box for scripts)
3. Runs validation at the `scope` requested (`smoke` / `full` / `feature`)
4. Captures evidence via the `playwright` MCP plugin for browser targets (screenshots,
   console messages, network failures)
5. Writes a deploy validation report

## Output shape

The report includes deploy metadata (URL, commit if discoverable, environment),
a scenario-by-scenario results table, and a clear PASS/FAIL verdict per scenario.
