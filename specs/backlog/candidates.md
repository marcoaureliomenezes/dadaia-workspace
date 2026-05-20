# Backlog — Candidates

Features candidatas a virar release. Cada candidata tem owner sugerido e link para
contexto histórico (archive ou report). Nada aqui autoriza implementação — apenas
sinaliza que vale a pena considerar para a próxima rodada de planning.

## Convenções

- Um bullet por candidata, com formato:
  `- <nome> — <one-liner do problema> (owner: <agent>, contexto: <link>)`
- Manter ordenado por prioridade percebida (mais quente no topo).
- Quando uma candidata virar release ativa, **remover** a entrada daqui e registrar
  no histórico abaixo com data e release-id. O backlog nunca é a fonte autoritativa
  de uma candidata que virou release — a release tem seu próprio SPEC/PLAN/TASKS.
- Sanitizar regularmente: remover itens implementados, obsoletos ou rejeitados.
  Peso morto no backlog contamina o planning.

## Candidatas ativas

- codex-design-frontend-projection-pilot-v1 — Criar skills canônicas faltando (`frontend-design`, `design-report-quality-gate`, `design-reference-research`, `frontend-implementation-quality`) e hardening de boundaries design-specialist/frontend-engineer; o framing "pilot antes de codex-parity" é obsoleto — a paridade Codex foi concluída; esta release é agora standalone focada em skills + agent boundaries. Ver draft em `specs/backlog/codex-design-frontend-projection-pilot-v1.md` (atualizar refs stale: "16 agents" → 20; `panel-r4/r5` → arquivados). (owner: product-engineer, contexto: consultas read-only 2026-05-19 com product-engineer, software-architect, frontend-engineer e design-specialist)
- agents-md-hierarchical-v1 — ⚠️ **Revisão necessária antes de promover:** Codex hierarchical AGENTS.md rendering (múltiplos `AGENTS.md` em sub-dirs com herança), G4 deferido de `multi-platform-parity-v1` (ADR-MP-4 + ADR-ARCH-4). `codex-agent-orchestration-parity-v1` estabeleceu abordagem TOML (`.codex/agents/*.toml`) para personas Codex — avaliar se hierarchical AGENTS.md ainda faz sentido ou é obsoleto dado o TOML approach. (owner: product-engineer, contexto: `_archive/releases/multi-platform-parity-v1/CLOSURE.md § Backlog returns`)
- agent-topology-guard-i6-skill-link-validation-v1 — Estender `scripts/check_agent_topology.py` com invariante I6 validando que cada `skills:` da frontmatter resolve para diretório real em `dadaia_workspace/public/skills/`; confirmado ausente (script tem I1–I5 apenas); `frontend-design` ainda faltando é evidência direta da necessidade. (owner: ai-engineer, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Drifts DRIFT-3`)
- cli-reports-exit-code-alignment-v1 — `tests/integration/test_cli_reports.py::test_10_workspace_not_initialized_exits_3` espera exit 3 mas CLI sai 1 com `WorkspaceNotInitializedError`; teste marcado `xfail` com referência explícita a esta candidata; alinhar implementação OU atualizar teste para refletir comportamento real. (owner: software-engineer-python, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Drifts DRIFT-4`)
- data-pipeline-cycle-workflow-v1 — Novo workflow para fluxo data-engineer: discovery (data-engineer) → review (software-architect + qa-engineer) → implementation (data-engineer) → validation (qa-engineer). Diferido por operator decision Q3 em `agents-r3-v1`. Promover quando primeira demanda de pipeline precisar do framework. (owner: product-engineer, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Backlog returns`)
- dashboard-publication-workflow-v1 — Novo workflow para fluxo data-analyst: build dashboard (data-analyst) → visual review (design-specialist) → publish via DABs (data-analyst). Diferido por operator decision Q3 em `agents-r3-v1`. (owner: product-engineer, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Backlog returns`)
- ai-entity-refinement-workflow-v1 — Novo workflow para fluxo ai-engineer: audit (ai-engineer) → refine personas/skills/rules (ai-engineer) → validate (ai-engineer + product-engineer) → install (devops-engineer). Diferido por operator decision Q3 em `agents-r3-v1`. (owner: product-engineer, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Backlog returns`)
- ai-engineer-recursive-bootstrap-v1 — Primeira dispatch real de `ai-engineer` (Sonnet 4.6 — ADR-X4 moveu de Opus 4.7) na sua própria superfície (audit + autoria/refinamento de skills, rules, workflows, commands, agents, hooks). Diferido por operator decision Q4 em `agents-r3-v1`. Requisito antes de promover: pelo menos uma dispatch real bem-sucedida em escopo restrito. (owner: ai-engineer, contexto: `_archive/releases/agents-r3-v1/CLOSURE.md § Backlog returns`)
- public-assets-coverage-lift-v1 — ⚠️ **Line ranges stale:** lift de cobertura em `dadaia_workspace/infrastructure/public_assets.py` (ranges citados no backlog original — 378–433, 595–650, 675–696 — foram deslocados por `codex-agent-orchestration-parity-v1` que adicionou D-CX-1..5 ao `doctor()`); requer nova medição antes de promover. `tests/unit/infrastructure/test_public_assets.py` não existe — gap confirmado. (owner: software-engineer-python, contexto: `_archive/releases/multi-platform-parity-v1/CLOSURE.md § Drifts §1`)
- cli-asset-granular — Adicionar operações granulares de assets à CLI: `dadaia public list`, `dadaia public install --only rules`, etc.; baixa prioridade. (owner: software-engineer-python, contexto: `z_bug_specs.md` G3 — discovery source `agent-comms-v1`)
- reports-next-cli — `dadaia reports next` (v2): descobre o próximo handoff esperado dado o estado atual do workspace. (owner: software-engineer-python, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-mcp-server — MCP integration (v3): emissão programática de handoff via servidor MCP em vez de skill markdown. (owner: software-architect, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-evaluator — Evaluator semântico (v4): valida qualidade dos findings, não apenas estrutura JSON. (owner: qa-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- agent-comms-wave-2 — Migrar `qa-engineer` para piloto do handoff-emitter (próxima onda). (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- agent-comms-wave-3-7 — Migrar `devops-engineer`, `backend-engineer`, `frontend-engineer` e os 3 `game-*` agents em waves separadas. (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-ci-gate — Adicionar job em `.github/workflows/ci.yml` rodando `dadaia reports validate --all --strict` após 100% adoção dos 10 agentes. (owner: devops-engineer, contexto: SPEC `agent-comms-v1` NFR4)
- reports-hash-mismatch-enforcement — Promover hash-mismatch de warning para erro em strict mode (v2). (owner: software-engineer-python, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- spec-discovery-chain-workflow — Workflow seed para o padrão D4 (PE→architect→SE→PE→SE), se virar recorrente. (owner: product-engineer, contexto: SPEC `agent-comms-v1` Q6)
- reports-handoff-schema-v2 — Evolução do schema para suportar `oneOf` e `$ref` (requer upgrade do validator). (owner: software-architect, contexto: SPEC `agent-comms-v1` AR5)
- agent-monitoring-opencode-v1.1 — Adicionar reader para opencode quando o schema estabilizar (D-AM-14). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-pricing-recompute-v1.1 — Recompute opcional de `cost_micro_usd` quando `pricing.py` muda (drift #4). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Tabela de preços`)
- agent-monitoring-threshold-alerts-v2 — Threshold alerts e cost-per-day notifications. (owner: product-engineer, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-multi-host-v2 — Agregação cross-host quando workspace rodar em mais de uma máquina. (owner: software-architect, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-frontmatter-completo-v2 — Ler frontmatter completo de SKILL.md (autores, tags, parâmetros). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- panel-workspace-resolver-fix — Disambiguate `_resolve_workspace()` entre workspace root e repo root para `dadaia panel` funcionar de qualquer cwd dentro do workspace. (owner: software-engineer-python, contexto: drift em `_archive/releases/dadaia-workspace-panel-v1/CLOSURE.md § Drifts #2`)
- install-scope-flags-r3 — Add `--repos-only` / `--workspace-only` flags to `dadaia public install`. (owner: software-engineer-python, contexto: `_archive/releases/agents-r2-v1/PLAN.md §8.6`; deferred from r2 explicitly)
- panel-csp-script-src-harden — Drop `'unsafe-inline'` from script CSP. (owner: devops-engineer, contexto: `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2` + CLOSURE Drifts §csp-style-src-regression)
- panel-sqlite-workflows-drop — Drop SQLite `workflows` / `workflow_agents` tables via migration 6 (marcadas `# DEAD:` em `schema.py`; zero leitura de produção após R3). (owner: software-engineer-python, contexto: `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2`)
- panel-workflow-run-dispatcher — "Run this workflow" invocation: integração com Claude Code dispatcher via POST endpoint no painel. (owner: software-engineer-python, contexto: `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2`)
- panel-dark-mode — Dark mode permutations para as 3 paletas (Mint/Sage/Warm). (owner: frontend-engineer, contexto: `_archive/releases/dadaia-workspace-panel-r3-v1/SPEC.md §8.2`)
- panel-patch-terminology — Reconciliar uso colloquial de "PATCH" em `dadaia-workspace-panel-v1/PLAN.md` com SemVer PATCH reservado para hotfix. (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` D18)
- hotfix-release-workflow — Iterações futuras sobre `hotfix-release.workflow.md` (dry-run mode, version bump automático, integração com qa-engineer stub). (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` "Delta de workflow")
- vintage-bucket-doc — Documentar Vintage bucket em `docs/sdd-migration-playbook.md` com lista das 10 releases pré-SemVer. (owner: software-engineer-python, contexto: SPEC `sdd-hotfix-track-v1` D14)
- release-pipeline — Pipeline de release semver/build/publicação cross-repo. (owner: devops-engineer, contexto: `_archive/legacy-features/release-pipeline/SPEC.md`)
- multi-bot-context-isolation — Isolamento de contexto entre bots concorrentes. (owner: software-architect, contexto: `_archive/legacy-features/multi-bot-context-isolation/SPEC.md`)
- dadaia-academy — Sistema de cursos in-workspace: migrar para HTML (como reports), revisar conteúdo, servir no painel (nova aba "Academy"). Feature parcialmente implementada; HTML + panel tab pendentes. (owner: software-engineer-python, contexto: `_archive/legacy-features/dadaia-academy/SPEC.md`)
- security — Security spec workspace-level. (owner: software-architect, contexto: `_archive/legacy-features/security/SPEC.md`)

## Histórico (candidatas promovidas a release ou resolvidas)

<!-- Hotfixes migrados em 2026-05-20 — monitorados via specs/z_bug_specs.md -->
<!-- spec-context — sessions share global primary_context.json, no DADAIA_CONTEXT auto-export (2026-05-17T064915Z) -->
<!-- import BUG-003 — paths absolutos não reescritos em import (2026-05-17T000000Z) -->

- infra-install-source-repo-target-v1 → **resolvida** em `codex-agent-orchestration-parity-v1` via R14 self-skip em `public_assets.py` (source repo detectado por `package_version` e ignorado automaticamente; `repos/dadaia-workspace/.claude/` não existe — sem projeções vestigiais) — 2026-05-20
- codex-agent-orchestration-parity-v1 → release `codex-agent-orchestration-parity-v1` (promovido 2026-05-20, encerrado 2026-05-20; SPEC/PLAN/TASKS/CLOSURE em `_archive/releases/codex-agent-orchestration-parity-v1/`; closes 20 TOMLs Codex, CodexAgentDispatcher, runtime_transforms, doctor D-CX-1..5, workflow projection completa, commands cleanup FR13, ADRs 1–6)
- token-cost-bigbang-v1 → release `token-cost-bigbang-v1` (promovido 2026-05-20, encerrado 2026-05-20; SPEC final em `_archive/releases/token-cost-bigbang-v1/`; closes ADR-X1..X7: AGENTS.md canonical, skill Tier-A/B split, agent size budget, Sonnet default, sidecar-first handoff-v1.1, dispatch-to-researcher, plugin-scope)
- agents-r3-v1 → release `agents-r3-v1` (promovido 2026-05-19, encerrado 2026-05-19; SPEC final em `_archive/releases/agents-r3-v1/SPEC.md`; closes 16→20 agent topology: software-engineer-python + software-engineer-node + data-engineer + data-analyst + ai-engineer; 5 drifts documentados)
- dev-server-registry (hotfix) → release `v0.1.1` (promovido 2026-05-17, encerrado 2026-05-17; SPEC final em `_archive/releases/v0.1.1/SPEC.md`)
- dadaia-workspace-brand-identity → release `dadaia-workspace-brand-identity-v1` (promovido 2026-05-17; paleta + tokens CSS consumidos por `agent-monitoring-v1`)
- dadaia-workspace-panel-r2-agents → release `agent-monitoring-v1` (promovido 2026-05-17, encerrado 2026-05-17; SPEC final em `_archive/releases/agent-monitoring-v1/SPEC.md`)
- multi-platform-parity-v1 → release `multi-platform-parity-v1` (promovido 2026-05-17, encerrado 2026-05-17; SPEC final em `_archive/releases/multi-platform-parity-v1/SPEC.md`)
- agent-comms → release `agent-comms-v1` (promovido 2026-05-16, encerrado 2026-05-17; SPEC final em `_archive/releases/agent-comms-v1/SPEC.md`)
- dadaia-workspace-panel → release `dadaia-workspace-panel-v1` (promovido 2026-05-16, encerrado 2026-05-16; SPEC final em `_archive/releases/dadaia-workspace-panel-v1/SPEC.md`)
- sdd-hotfix-track → release `sdd-hotfix-track-v1` (promovido 2026-05-16, encerrado 2026-05-16; SPEC final em `_archive/releases/sdd-hotfix-track-v1/SPEC.md`)
- sdd-release-lifecycle → release `sdd-release-lifecycle-v1` (promovido 2026-05-16; SPEC em `_archive/legacy-features/sdd-release-lifecycle/SPEC.md`)
- agents → releases `agents-r1-v1`, `agents-r2-v1`, `agents-r3-v1` — padrão de agentes canônicos, rules, skills, projeção multi-tool implementados ao longo das 3 releases
- agent-rules-skills → coberto por `agents-r2-v1` — rules e skills em `dadaia_workspace/public/` com projeção multi-runtime
- cross-tool-parity → `multi-platform-parity-v1` — paridade Claude/Codex/OpenCode implementada
- multi-tool-sdd-enforcement → `sdd-enforcement` archive — gate SDD (`sdd-spec-gate.sh`) vigente em todas as tools
- universal-agentic-assets → pipeline `public/ → .dadaia/agentic/ → projeções` implementado via múltiplas releases (`multi-platform-parity-v1`, `codex-agent-orchestration-parity-v1`)
- spec-context-agent-command → `spec-context-project` archive — `dadaia context activate` implementado no CLI
- software-engineer → `agents-r3-v1` — split em `software-engineer-python` + `software-engineer-node`
- qa-engineer, devops-engineer, game-developer, game-agents-split → implementados via `agents-r1-v1` / `agents-r2-v1` / `agents-r3-v1`
- foundation → foundation spec implementada (`specs/foundation/SPEC.md` + architecture memory)
- dev-server-registry (legacy) → `v0.1.1` — registry implementado e corrigido
