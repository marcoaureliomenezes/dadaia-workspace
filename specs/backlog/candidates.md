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

- agent-comms-v1 — handoff-v1.schema.json + `dadaia reports validate` CLI + `dadaia-handoff-emitter` skill; bridges the declared-but-empty `schema_ref: handoff-schema-v1` across 10 agents (82 references); includes z_bug_specs.md migration to backlog (owner: product-engineer, contexto: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T220000Z-agent-comms-research.html`)
- dadaia-workspace-panel-r2-agents — Surface installed agents and multi-agent workflows in the panel; replaces the Release-1 placeholder card (owner: product-engineer, contexto: `_archive/releases/dadaia-workspace-panel-v1/SPEC.md` § Future)
- panel-workspace-resolver-fix — Disambiguate `_resolve_workspace()` between workspace root and repo root so `dadaia panel` works from any cwd inside the workspace, not only from the workspace root (owner: software-engineer, contexto: drift documented em `_archive/releases/dadaia-workspace-panel-v1/CLOSURE.md § Drifts #2`)
- panel-patch-terminology — Reconciliar uso colloquial de "PATCH" em `dadaia-workspace-panel-v1/PLAN.md` L76-78 com SemVer PATCH agora reservado para hotfix release (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` D18)
- hotfix-release-workflow — Iterações futuras sobre `dadaia_workspace/public/workflows/hotfix-release.workflow.md` (dry-run mode, automatic version bump, integração com qa-engineer stub) (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` "Delta de workflow")
- vintage-bucket-doc — Documentar Vintage bucket em `docs/sdd-migration-playbook.md` com lista das 10 releases pré-SemVer (owner: software-engineer, contexto: SPEC `sdd-hotfix-track-v1` D14)
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

## Hotfixes pendentes

(vazio — bullets neste formato: `- <YYYY-MM-DDTHHMMSSZ> <LOW|MEDIUM|HIGH|CRITICAL> <component> — <one-liner> (post-mortem: <link>)`)

## Histórico (candidatas promovidas a release)

- sdd-release-lifecycle → release `sdd-release-lifecycle-v1` (promovido em 2026-05-16; source SPEC em `_archive/legacy-features/sdd-release-lifecycle/SPEC.md`)
- sdd-hotfix-track → release `sdd-hotfix-track-v1` (promovido em 2026-05-16, encerrado em 2026-05-16; contexto: `.claude/plans/devemos-melhorar-o-streamed-snail.md`; SPEC final em `_archive/releases/sdd-hotfix-track-v1/SPEC.md`)
- dadaia-workspace-panel → release `dadaia-workspace-panel-v1` (promovido em 2026-05-16, encerrado em 2026-05-16; SPEC final em `_archive/releases/dadaia-workspace-panel-v1/SPEC.md`)
