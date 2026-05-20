---
name: game-dev-cycle
description: >
  Ciclo de implementação exclusivo para games: game-tester define acceptance criteria →
  game-designer implementa assets estáticos → game-developer implementa lógica →
  game-tester valida com UE5 Automation + PIE screenshots.
version: 0.1.0
schema_version: "1"
when_to_use: "SPEC.md com Status: Aprovado + task OPEN em TASKS.md de projeto tauan-games."
inputs:
  context:
    type: string
    required: true
    description: Active spec context (tauan-games project).
  task_id:
    type: string
    required: true
    description: Approved task identifier from TASKS.md (e.g. T001).
  game:
    type: string
    required: true
    description: Game directory name (e.g. aero-fighters-v2).
stages:
  - id: acceptance_criteria
    agent: game-tester
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-criteria.handoff.json"
      must_include: ["Test Scenarios", "Expected Behaviors", "Acceptance Criteria"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve acceptance criteria and test scenarios before implementation starts?"

  - id: design_impl
    agent: game-designer
    needs: [acceptance_criteria]
    consumes:
      - ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-criteria.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-{task_id}-design.handoff.json"
      must_include: ["Assets Implemented", "Design Decisions"]
    inputs:
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve static assets before logic implementation starts?"

  - id: logic_impl
    agent: game-developer
    needs: [design_impl]
    consumes:
      - ".dadaia/reports/{context}/game-designer/{run_ts}-{task_id}-design.handoff.json"
      - ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-criteria.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-{task_id}-impl.handoff.json"
      must_include: ["Implementation Complete", "Tests Pass"]
    inputs:
      - kind: stage_output
        from: stages.design_impl.output
        as: design_report
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve logic implementation before validation?"

  - id: validation
    agent: game-tester
    needs: [logic_impl]
    consumes:
      - ".dadaia/reports/{context}/game-developer/{run_ts}-{task_id}-impl.handoff.json"
      - ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-criteria.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-quality.handoff.json"
      must_include: ["Quality Report", "Severity", "PIE Screenshots"]
    inputs:
      - kind: stage_output
        from: stages.logic_impl.output
        as: impl_report
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
    gate:
      kind: operator-approval
      prompt: "Approve quality report? (No Critical/High bugs = PASS)"

exit_criteria:
  - all_stages: completed
---

# game-dev-cycle

Ciclo de implementação exclusivo para games com 3 agentes especializados.

O `game-tester` abre e fecha o ciclo: define critérios antes da implementação
e valida com UE5 Automation + PIE screenshots depois.

**Em caso de falha na validação:**
- Bugs de design → game-designer corrige → re-validation
- Bugs de lógica → game-developer corrige → re-validation
- O game-tester classifica e direciona cada bug para o agente correto.

**Coordenação:** seguir o Decision Authority Matrix de `game-agents-coordination.md`.
