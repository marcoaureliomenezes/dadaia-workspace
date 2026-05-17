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

- multi-platform-parity-v1 — Close G1/G2/G3/G5 from the platform-boundaries analysis: render Codex agents as `[agents.<name>]` blocks in `.codex/config.toml`, stop copying inert workflows to `.codex/workflows/`, add `[not-applicable]` doctor status, install short-circuits on it. Confines new code to `infrastructure/public_assets.py`; preserves the `.dadaia/agentic/` SHA256 manifest and the `dadaia-workspace-dev-guardrail` rule. Promote to release only after `agent-comms-v1` reaches CLOSURE. (owner: product-engineer, contexto: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T233537Z-platform-boundaries-analysis.html` + `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T011435Z-multi-platform-grill-me.html` + `.dadaia/reports/dadaia-workspace/software-architect/2026-05-17T012117Z-multi-platform-pillar-position.html` + `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T012220Z-multi-platform-pillar-impact.html`)
- cli-asset-granular — Adicionar operações granulares de assets à CLI: `dadaia public list`, `dadaia public install --only rules`, etc.; mantido como baixa prioridade após encerramento do Spec Context v3.0. (owner: software-engineer, contexto: `z_bug_specs.md` G3 — discovery source `agent-comms-v1`)
- reports-next-cli — `dadaia reports next` (v2): descobre o próximo handoff esperado dado o estado atual do workspace (owner: software-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-mcp-server — MCP integration (v3): emissão programática de handoff via servidor MCP em vez de skill markdown (owner: software-architect, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-evaluator — Evaluator semântico (v4): valida qualidade dos findings, não apenas estrutura JSON (owner: qa-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- agent-comms-wave-2 — Migrar `qa-engineer` para piloto do handoff-emitter (próxima onda) (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- agent-comms-wave-3-7 — Migrar `devops-engineer`, `backend-engineer`, `frontend-engineer` e os 3 `game-*` agents em waves separadas (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-ci-gate — Adicionar job em `.github/workflows/ci.yml` rodando `dadaia reports validate --all --strict` após 100% adoção dos 10 agentes (owner: devops-engineer, contexto: SPEC `agent-comms-v1` NFR4)
- reports-hash-mismatch-enforcement — Promover hash-mismatch de warning para erro em strict mode (v2) (owner: software-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- spec-discovery-chain-workflow — Workflow seed para o padrão D4 (PE→architect→SE→PE→SE), se virar recorrente (owner: product-engineer, contexto: SPEC `agent-comms-v1` Q6)
- reports-handoff-schema-v2 — Evolução do schema para suportar `oneOf` e `$ref` (requer upgrade do validator) (owner: software-architect, contexto: SPEC `agent-comms-v1` AR5)
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

- 2026-05-17T000000Z MEDIUM import — BUG-003: `dadaia import` não detecta nem reescreve paths absolutos em arquivos não-lib-originated (ex.: hooks em `.claude/settings.json`) apontando para fora do novo `workspace_root`; próximo import em outra máquina pode reintroduzir hooks VPS. (post-mortem: `specs/z_bug_specs.md` — discovery source `agent-comms-v1`)

## Histórico (candidatas promovidas a release)

- sdd-release-lifecycle → release `sdd-release-lifecycle-v1` (promovido em 2026-05-16; source SPEC em `_archive/legacy-features/sdd-release-lifecycle/SPEC.md`)
- sdd-hotfix-track → release `sdd-hotfix-track-v1` (promovido em 2026-05-16, encerrado em 2026-05-16; contexto: `.claude/plans/devemos-melhorar-o-streamed-snail.md`; SPEC final em `_archive/releases/sdd-hotfix-track-v1/SPEC.md`)
- dadaia-workspace-panel → release `dadaia-workspace-panel-v1` (promovido em 2026-05-16, encerrado em 2026-05-16; SPEC final em `_archive/releases/dadaia-workspace-panel-v1/SPEC.md`)
- agent-comms → release `agent-comms-v1` (promovido em 2026-05-16, encerrado em 2026-05-17; SPEC final em `_archive/releases/agent-comms-v1/SPEC.md`; release-id: `agent-comms-v1`, closed: 2026-05-17)
