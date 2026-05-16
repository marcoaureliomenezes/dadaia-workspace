# Backlog — Candidates

Features candidatas a virar release. Cada candidata tem owner sugerido e link para
contexto histórico (archive ou report). Nada aqui autoriza implementação — apenas
sinaliza que vale a pena considerar para a próxima rodada de planning.

## Convenções

- Um bullet por candidata, com formato:
  `- <nome> — <one-liner do problema> (owner: <agent>, contexto: <link>)`
- Manter ordenado por prioridade percebida (mais quente no topo).
- Quando uma candidata virar release ativa, mover linha para o histórico abaixo com
  data e release-id correspondente.

## Candidatas ativas

Originadas da triagem de Phase 6 da meta-release `sdd-release-lifecycle-v1`. Cada uma
era uma feature SPEC.md em Draft sob o modelo antigo `specs/features/<name>/`, agora
arquivada em `specs/_archive/legacy-features/<name>/SPEC.md`. Promover para release exige
nova passagem de discovery + grill-me + SPEC Aprovado pelo product-engineer.

- dev-server-registry — Registry para resolver conflito de portas entre agentes em dev. PLAN antigo de 2287 linhas precisava ser compactado (owner: software-engineer, contexto: `_archive/legacy-features/dev-server-registry/SPEC.md`)
- release-pipeline — Pipeline de release semver/build/publicação cross-repo (owner: devops-engineer, contexto: `_archive/legacy-features/release-pipeline/SPEC.md`)
- agents — Padrão de agentes canonical em `dadaia_workspace/public/agents/` + projeção multi-tool (owner: product-engineer, contexto: `_archive/legacy-features/agents/SPEC.md`)
- agent-rules-skills — Rules e skills compartilhadas entre agentes (owner: product-engineer, contexto: `_archive/legacy-features/agent-rules-skills/SPEC.md`)
- cross-tool-parity — Paridade de features entre Claude Code, Codex e OpenCode (owner: devops-engineer, contexto: `_archive/legacy-features/cross-tool-parity/SPEC.md`)
- multi-tool-sdd-enforcement — Gate SDD funcionando em todas as tools (owner: devops-engineer, contexto: `_archive/legacy-features/multi-tool-sdd-enforcement/SPEC.md`)
- universal-agentic-assets — Asset chain `public/ → .dadaia/agentic/ → projeções` (owner: software-engineer, contexto: `_archive/legacy-features/universal-agentic-assets/SPEC.md`)
- spec-context-agent-command — Comando `dadaia context activate` integrado ao agent dispatcher (owner: software-engineer, contexto: `_archive/legacy-features/spec-context-agent-command/SPEC.md`)
- multi-bot-context-isolation — Isolamento de contexto entre bots concorrentes (owner: software-architect, contexto: `_archive/legacy-features/multi-bot-context-isolation/SPEC.md`)
- dadaia-academy — Sistema de cursos in-workspace (owner: software-engineer, contexto: `_archive/legacy-features/dadaia-academy/SPEC.md`)
- software-engineer — Especificação do agente software-engineer (owner: product-engineer, contexto: `_archive/legacy-features/software-engineer/SPEC.md`)
- qa-engineer — Especificação do agente qa-engineer (owner: product-engineer, contexto: `_archive/legacy-features/qa-engineer/SPEC.md`)
- devops-engineer — Especificação do agente devops-engineer (owner: product-engineer, contexto: `_archive/legacy-features/devops-engineer/SPEC.md`)
- game-developer — Especificação do agente game-developer (owner: product-engineer, contexto: `_archive/legacy-features/game-developer/SPEC.md`)
- game-agents-split — Divisão do game-developer em 3 sub-agentes (developer/designer/tester) (owner: product-engineer, contexto: `_archive/legacy-features/game-agents-split/SPEC.md`)
- foundation — Foundation spec workspace-level (owner: software-architect, contexto: `_archive/legacy-features/foundation/SPEC.md`)
- security — Security spec workspace-level (owner: software-architect, contexto: `_archive/legacy-features/security/SPEC.md`)

## Histórico (candidatas promovidas a release)

- sdd-release-lifecycle → release `sdd-release-lifecycle-v1` (promovido em 2026-05-16; source SPEC em `_archive/legacy-features/sdd-release-lifecycle/SPEC.md`)
