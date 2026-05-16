---
name: game-spec-definition
description: >
  Discovery → 5-way parallel specialist analysis (arch + devops + game-developer +
  game-designer + game-tester) → synthesis. Replaces spec-refinement for game contexts.
  Optional web specialists (backend-engineer + frontend-engineer) via include_web_specialists=true.
version: 0.1.0
schema_version: "1"
when_to_use: "Active context is a game project (redacted-slug). For all other contexts, use spec-refinement."
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (must be a redacted-slug context).
  topic:
    type: string
    required: false
    default: "next-game-feature"
    description: Free-form topic label (e.g. redacted-slug-v2).
  include_web_specialists:
    type: boolean
    required: false
    default: false
    description: When true, adds backend-engineer and frontend-engineer to the parallel analysis group.
stages:
  - id: discovery
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-game-discovery.html"
      must_include: ["Findings", "Decisões necessárias", "Acceptance Criteria Draft"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.topic"
        as: topic
    gate:
      kind: operator-approval
      prompt: "Approve game discovery report before triggering parallel analysis?"

  - id: arch_review
    agent: software-architect
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-game-arch.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: devops_review
    agent: devops-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-game-devops.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: gameplay_analysis
    agent: game-developer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-gameplay-analysis.html"
      must_include: ["Mechanic Viability", "JSBSim Feasibility"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: design_analysis
    agent: game-designer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-design-analysis.html"
      must_include: ["Map Feasibility", "Asset Pipeline", "Research Findings"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: qa_criteria
    agent: game-tester
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-acceptance-criteria.html"
      must_include: ["Acceptance Criteria", "Known UE5 Risks"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: synthesis
    agent: product-engineer
    needs: [arch_review, devops_review, gameplay_analysis, design_analysis, qa_criteria]
    expected_output:
      path: "specs/releases/{release_id}/SPEC.md"
      must_include: ["Status", "Critérios de Aceite"]
    inputs:
      - kind: stage_output
        from: stages.arch_review.output
        as: arch_report
      - kind: stage_output
        from: stages.devops_review.output
        as: devops_report
      - kind: stage_output
        from: stages.gameplay_analysis.output
        as: gameplay_report
      - kind: stage_output
        from: stages.design_analysis.output
        as: design_report
      - kind: stage_output
        from: stages.qa_criteria.output
        as: qa_report
    gate:
      kind: operator-approval
      prompt: "Approve the synthesized GAME SPEC before promoting it to 'Em revisão'?"

exit_criteria:
  - all_stages: completed
---

# game-spec-definition

Workflow de definição de spec exclusivo para projetos de jogo. Substitui `spec-refinement`
quando o contexto ativo é `redacted-slug` ou outro projeto de jogo.

Os 5 especialistas paralelos substituem os especialistas genéricos do spec-refinement:
`game-developer` (viabilidade de mecânicas), `game-designer` (pipeline de assets e mapas),
e `game-tester` (acceptance criteria e riscos UE5 conhecidos) substituem `qa-engineer`,
`frontend-engineer` e `backend-engineer`.

Para jogos com componentes de backend (leaderboard, matchmaking, EOS), use
`include_web_specialists=true` para adicionar `backend-engineer` e `frontend-engineer`
ao grupo paralelo de especialistas.

**Coordenação:** todos os agentes seguem o Decision Authority Matrix definido em
`game-agents-coordination.md`. Divergências são resolvidas via `product-engineer`;
conflitos não resolvidos disparam `dadaia-grill-me` com o operador.
