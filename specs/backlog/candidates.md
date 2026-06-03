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

- ctx-inject-path-aware-message-v1 — PATH-aware `[context: none]` message in `ctx-inject.sh`: detect at runtime whether `dadaia` is on PATH (`command -v dadaia`) before emitting the full `.dadaia/.venv/bin/dadaia` path hint; emit short form when binary is on PATH, full-path form otherwise. QA flagged in ctx-inject-v2-drift-fix-v1 closure; AC-3 satisfied with hardcoded path (not a defect). (owner: ai-engineer, contexto: `specs/_archive/releases/ctx-inject-v2-drift-fix-v1/CLOSURE.md § Backlog returns`)
- r2-lock-toctou-hardening-v1 — três defects pré-existentes na camada de locking de `spec-context-session-locks-v1` (R2) surfaçados por K-QA-RACE: (a) STALE impl lock não bloqueia review bind, (b) `check_impl_xor_review` TOCTOU race window, (c) `create_impl_lock` shared `.tmp` name levanta `FileNotFoundError` em vez de `LockHeldError` em race same-release; proposta: workspace-flock wrapping do XOR check-then-act + per-thread `.tmp` names em `dadaia_workspace/features/spec_context/locking.py`. (owner: software-engineer-python, contexto: `specs/backlog/r2-lock-toctou-hardening-v1.md`)
- memory-structured-source-migration-v2 — enriquece os schemas v1 para representação lossless dos atoms ricos (diagram arrays, extensible sections, raw-HTML escape hatch), upgrade do renderer/extractor e gate de fidelidade FIDELITY-1 (owner: software-engineer-python, contexto: specs/_archive/releases/memory-structured-source-v1/CLOSURE.md)
- agents-md-hierarchical-v1 — ⚠️ **Revisão necessária antes de promover:** Codex hierarchical AGENTS.md rendering (múltiplos `AGENTS.md` em sub-dirs com herança), G4 deferido de `multi-platform-parity-v1` (ADR-MP-4 + ADR-ARCH-4). `codex-agent-orchestration-parity-v1` estabeleceu abordagem TOML (`.codex/agents/*.toml`) para personas Codex — avaliar se hierarchical AGENTS.md ainda faz sentido ou é obsoleto dado o TOML approach. (owner: product-engineer, contexto: `_archive/releases/multi-platform-parity-v1/CLOSURE.md § Backlog returns`)
- reports-mcp-server — MCP integration (v3): emissão programática de handoff via servidor MCP em vez de skill markdown. (owner: software-architect, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-evaluator — Evaluator semântico (v4): valida qualidade dos findings, não apenas estrutura JSON. (owner: qa-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- reports-ci-gate — Adicionar job em `.github/workflows/ci.yml` rodando `dadaia reports validate --all --strict` após 100% adoção dos 10 agentes. (owner: devops-engineer, contexto: SPEC `agent-comms-v1` NFR4)
- reports-hash-mismatch-enforcement — Promover hash-mismatch de warning para erro em strict mode (v2). (owner: software-engineer-python, contexto: SPEC `agent-comms-v1` § Out-of-scope)
- spec-discovery-chain-workflow — Workflow seed para o padrão D4 (PE→architect→SE→PE→SE), se virar recorrente. (owner: product-engineer, contexto: SPEC `agent-comms-v1` Q6)
- reports-handoff-schema-v2 — Evolução do schema para suportar `oneOf` e `$ref` (requer upgrade do validator). (owner: software-architect, contexto: SPEC `agent-comms-v1` AR5)
- agent-monitoring-opencode-v1.1 — Adicionar reader para opencode quando o schema estabilizar (D-AM-14). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-pricing-recompute-v1.1 — Recompute opcional de `cost_micro_usd` quando `pricing.py` muda (drift #4). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Tabela de preços`)
- agent-monitoring-threshold-alerts-v2 — Threshold alerts e cost-per-day notifications. (owner: product-engineer, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-multi-host-v2 — Agregação cross-host quando workspace rodar em mais de uma máquina. (owner: software-architect, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- agent-monitoring-frontmatter-completo-v2 — Ler frontmatter completo de SKILL.md (autores, tags, parâmetros). (owner: software-engineer-python, contexto: `_archive/releases/agent-monitoring-v1/SPEC.md § Out of scope`)
- hotfix-release-workflow — Iterações futuras sobre `hotfix-release.workflow.md` (dry-run mode, version bump automático, integração com qa-engineer stub). (owner: product-engineer, contexto: SPEC `sdd-hotfix-track-v1` "Delta de workflow")
- vintage-bucket-doc — Documentar Vintage bucket em `docs/sdd-migration-playbook.md` com lista das 10 releases pré-SemVer. (owner: software-engineer-python, contexto: SPEC `sdd-hotfix-track-v1` D14)
- release-pipeline — Pipeline de release semver/build/publicação cross-repo. (owner: devops-engineer, contexto: `_archive/legacy-features/release-pipeline/SPEC.md`)
- multi-bot-context-isolation — Isolamento de contexto entre bots concorrentes. (owner: software-architect, contexto: `_archive/legacy-features/multi-bot-context-isolation/SPEC.md`)
- security — Security spec workspace-level. (owner: software-architect, contexto: `_archive/legacy-features/security/SPEC.md`)

## Histórico (candidatas promovidas a release ou resolvidas)

- panel-kanban-v1 → release `panel-kanban-v1` (promovido 2026-05-30; Kanban tab read-only sobre session files R2 + handoff-v1.1 verdict field + CI dual-approval gate; CLOSED 2026-05-31)
- memory-context-enforcement-v1 → release `memory-context-enforcement-v1` (promovido 2026-05-30; Phase 1 da initiative de memória; CLOSED 2026-05-31; lean 5K-token injection + catalog.json + Step-0 em 21 personas)
- memory-structured-source-v1 → release `memory-structured-source-v1` (promovido 2026-05-30; Phase 2 da initiative de memória; CLOSED 2026-05-31; 4 schemas + renderer + doctor STRUCT/SYNC + gate RULE A + scaffold YAML; C-6 deferred → memory-structured-source-migration-v2)
- data-pipeline-cycle-workflow-v1 → **RESOLVIDA** como PM Playbook em orchestration-consolidation-v1 (2026-05-29)
- ai-entity-refinement-workflow-v1 → **RESOLVIDA** como PM Playbook em orchestration-consolidation-v1 (2026-05-29)
- ai-engineer-recursive-bootstrap-v1 → **RESOLVIDA** como PM Playbook em orchestration-consolidation-v1 (2026-05-29)
- opencode-runtime-parity-hardening-v1 → release `opencode-runtime-parity-hardening-v1` (promovido 2026-05-28; 3 tracks: T-OC-* OpenCode hardening, T-RN-* reports-next CLI, T-AC-* agent-comms waves 2-7; SPEC em `specs/releases/opencode-runtime-parity-hardening-v1/SPEC.md`)
- context-gate-cross-repo-fix-v1 → **RESOLVIDA** pela v3.2 do `sdd-spec-gate.sh` (2026-05-28): linha 99 já deriva `FILE_SPECS_DIR` do FPATH em vez do primary_context para Rule A (memory atomicity). Confirmado via inspeção; não requer release dedicada.
- reports-next-cli → **ABSORVIDO** em `opencode-runtime-parity-hardening-v1` como Track B (T-RN-*): `dadaia reports next` workflow-aware.
- agent-comms-wave-2 → **ABSORVIDO** em `opencode-runtime-parity-hardening-v1` como Track C (T-AC-*): waves 2-7 unificadas.
- agent-comms-wave-3-7 → **ABSORVIDO** em `opencode-runtime-parity-hardening-v1` como Track C (T-AC-*): waves 2-7 unificadas.
- cli-asset-granular → **RESOLVIDA** em `workspace-hardening-v1` (2026-05-28): `dadaia public list` + `dadaia public install --only <type>` entregues em T-WH-11+12.
- panel-workflow-run-dispatcher → **RESOLVIDA** em `workspace-hardening-v1` (2026-05-28): POST `/api/workflows/<name>/run` + Run button no card grid entregues em T-WH-14..17.

- context-deactivate-hardening-v1 → **RESOLVIDA** em `backlog-consolidation-r1-v1` (2026-05-23): 4 bugs de `dadaia context deactivate` corrigidos em T-BCR-04 (`git_subprocess.py`, `service.py`).
- panel-workspace-resolver-fix → **MERGED** em `dadaia-workspace-panel-r5-v1` (2026-05-21): fix de `_resolve_workspace()` incluído em Phase A, task T-P5-06.
- panel-dark-mode → **MERGED** em `dadaia-workspace-panel-r5-v1` (2026-05-21): token coverage para dark mode das 3 paletas incluída em Phase B (FR-10, task T-P5-10).
- dadaia-academy → **ABSORBED** como aba "Academy" em `dadaia-workspace-panel-r5-v1` (2026-05-21): standalone candidata obsoleta; Academy tab (infrastructure only, sem content modules) entregue via Phase F, tasks T-P5-25 a T-P5-28. Content modules (knowledge basis 01–06) permanecem pendentes para próxima release.
- panel-patch-terminology → **RESOLVIDA** por `sdd-hotfix-track-v1` (2026-05-17): terminologia PATCH/SemVer alinhada; não requer release dedicada.

<!-- Hotfixes migrados em 2026-05-20 — monitorados via specs/z_bug_specs.md -->
<!-- spec-context — sessions share global primary_context.json, no DADAIA_CONTEXT auto-export (2026-05-17T064915Z) -->
<!-- import BUG-003 — paths absolutos não reescritos em import (2026-05-17T000000Z) -->

- codex-design-frontend-projection-pilot-v1 → release `codex-design-frontend-projection-pilot-v1` (promovido 2026-05-20; ADRs CX-001..005 fechados via grill-me; SPEC em `specs/releases/codex-design-frontend-projection-pilot-v1/SPEC.md`; closes: 5 shared skills novas, agent boundary hardening, public/runtime/codex/ infrastructure)
- infra-correctness-v1 → release `infra-correctness-v1` (promovido 2026-05-20; closes: cli-reports-exit-code-alignment-v1, agent-topology-guard-i6-skill-link-validation-v1, public-assets-coverage-lift-v1, panel-csp-script-src-harden, panel-sqlite-workflows-drop, install-scope-flags-r3, init-legacy-resolver-fix [nova descoberta da software-architect])
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
