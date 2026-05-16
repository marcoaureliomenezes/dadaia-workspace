---
name: game-bugfix
description: >
  Fast-track para bugs reportados por usuário não capturados pelo game-tester.
  game-tester reproduz e classifica → game-developer ou game-designer corrige →
  game-tester valida regressão.
version: 0.1.0
schema_version: "1"
when_to_use: "Bug reportado por usuário em produção não identificado pelo game-tester."
inputs:
  context:
    type: string
    required: true
    description: Active spec context (redacted-slug project).
  bug_description:
    type: string
    required: true
    description: Description of the reported bug with reproduction steps if available.
  game:
    type: string
    required: true
    description: Game directory name (e.g. redacted-slug-v2).
stages:
  - id: reproduce
    agent: game-tester
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-bug-reproduce.html"
      must_include: ["Bug Classification", "Evidence", "Reproduction Steps"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.bug_description"
        as: bug_description
    gate:
      kind: operator-approval
      prompt: "Confirm reproduction and bug classification before fix?"

  - id: fix_logic
    agent: game-developer
    needs: [reproduce]
    on_failure: skip
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-bug-fix.html"
      must_include: ["Fix Applied", "Tests Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: bug_report
    gate:
      kind: operator-approval
      prompt: "Approve logic fix before regression testing?"

  - id: fix_design
    agent: game-designer
    needs: [reproduce]
    on_failure: skip
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-bug-fix.html"
      must_include: ["Fix Applied", "Asset Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: bug_report
    gate:
      kind: operator-approval
      prompt: "Approve design fix before regression testing?"

  - id: regression
    agent: game-tester
    needs: [fix_logic, fix_design]
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-bug-regression.html"
      must_include: ["Regression Result", "Test Suite Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: original_bug
    gate:
      kind: operator-approval
      prompt: "Approve regression report and close bug?"

exit_criteria:
  - all_stages: completed
---

# game-bugfix

Fast-track para bugs reportados por usuários não identificados pelo game-tester.

O game-tester classifica o bug (lógica vs design) no estágio `reproduce`.
Os estágios `fix_logic` e `fix_design` são mutuamente exclusivos — apenas o relevante
é executado (via `on_failure: skip` no outro).

O `regression` stage final garante que o fix não introduziu regressão e que o
test suite foi atualizado para prevenir recorrência.
