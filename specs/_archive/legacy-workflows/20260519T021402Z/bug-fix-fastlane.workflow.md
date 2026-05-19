---
name: bug-fix-fastlane
description: "Fast-lane hotfix loop. qa-engineer reproduces the bug as a failing test, the implementer applies the minimum fix, qa-engineer validates the deploy. No refactor stage, no product consult — for urgent fixes only. Fixes that require updates to `specs/memory/product/*.html` must migrate to a hotfix release (file under `specs/backlog/candidates.md` section `## Hotfixes pendentes`)."
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context.
  task_id:
    type: string
    required: true
    description: Bug ticket or TASKS.md reference (e.g. BUG-042 or T-FIX-12).
  implementer_agent:
    type: string
    required: false
    default: software-engineer
    description: Which engineer applies the fix. One of frontend-engineer, backend-engineer, software-engineer, game-developer.
stages:
  - id: reproduce_test
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-reproduce.html"
      must_include: ["Failing tests"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id

  - id: hotfix
    agent: "{{implementer_agent}}"
    needs: [reproduce_test]
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-{task_id}-hotfix.html"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.reproduce_test.output
        as: failing_tests_report

  - id: deploy_validation
    agent: qa-engineer
    needs: [hotfix]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-deploy.html"
      must_include: ["Deploy validated"]
    inputs:
      - kind: stage_output
        from: stages.hotfix.output
        as: hotfix_report
    gate:
      kind: operator-approval
      prompt: "Approve hotfix deploy validation and close the ticket?"

exit_criteria:
  - all_stages: completed
---

# bug-fix-fastlane

Use this workflow when you need to fix a production bug **fast** and the regular
`tdd-cycle` overhead (refactor stage, product consult, deeper review) is not warranted.

The 3 stages map directly to the classic hotfix protocol:

1. **reproduce_test** — `qa-engineer` writes a failing test that captures the bug.
   This is the contract for "fixed" — when the test goes green, the bug is gone.
2. **hotfix** — the chosen implementer (`frontend-engineer`, `backend-engineer`,
   `software-engineer`, or `game-developer`) applies the minimum change to make the
   test pass. **No refactoring** — that is a separate concern handled in `tdd-cycle`.
3. **deploy_validation** — `qa-engineer` validates the deploy against the real
   environment (Playwright MCP for browser surfaces; httpx/curl for APIs; CLI for
   scripts). Gated by operator-approval so the fix isn't closed silently.

When to use `tdd-cycle` instead:
- Non-urgent feature work
- Bug requires architectural changes
- Operator wants a refactor stage to clean up the code path
