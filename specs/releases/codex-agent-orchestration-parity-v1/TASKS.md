# Tasks: Release — codex-agent-orchestration-parity-v1

> **Status:** Aprovado
> **Release ID:** codex-agent-orchestration-parity-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20

---

## Regras de uso

- Flip `[ ]` → `[-]` ao **iniciar** uma task. Flip `[-]` → `[x]` ao **completar**.
- Máximo um `[-]` por agente ao mesmo tempo, exceto tasks com disjoint write sets declarados.
- Tasks de fases posteriores **não podem iniciar** enquanto a task bloqueante da fase anterior não estiver `[x]`.
- Bloqueantes explícitos marcados com ⚠️.

---

## P1 — Cleanup + Baseline

> ⚠️ **P1 deve estar 100% `[x]` antes de qualquer task P2+ começar.**
> O golden snapshot de AC1 é o ponto zero do guard contra regressão Claude.

- [x] **T-01** `software-engineer-python` — Deletar os 4 arquivos de `dadaia_workspace/public/commands/`: `dadaia-academy.md`, `dadaia-workspace-doctor.md`, `dadaia-workspace-refine-specs.md`, `spec-context.md` (FR13)
- [-] **T-02** `software-engineer-python` — Executar `dadaia public install --target claude` e verificar que `.claude/commands/` está vazio; executar `dadaia public install --target opencode` se OpenCode tiver projeção de commands (FR13)
- [ ] **T-03** `software-engineer-python` — Capturar golden snapshot: `find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/pre-codex.txt`; persistir como artefato em `.dadaia/tmp/json/pre-codex-snapshot.txt` (AC1 / ADR-6)

---

## P2 — Runtime Transforms

> Depende de: T-03 `[x]`

- [ ] **T-04** `software-engineer-python` — Criar `dadaia_workspace/infrastructure/runtime_transforms/__init__.py` (módulo vazio)
- [ ] **T-05** `software-engineer-python` — Criar `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py` com `MODEL_MAP` (3 entradas de ADR-5) e `map_model(claude_id: str) -> str` que lança `ValueError` em identifier desconhecido (FR5 / ADR-5)
- [ ] **T-06** `software-engineer-python` — Escrever `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py`: testa `claude-sonnet-4-6→gpt-5.3-codex`, `claude-haiku-4-5-20251001→gpt-5.4-mini`, `claude-opus-4-7→gpt-5.5`, e `ValueError` em identifier inválido
- [ ] **T-07** `software-engineer-python` — Criar `dadaia_workspace/infrastructure/runtime_transforms/codex.py` com `transform_for_codex(canonical_body: str, agent_id: str) -> str` implementando as substituições de ADR-2: `Agent tool` → `subagent`; remoção de hooks Claude-específicos; preservação verbatim do restante (FR2 / ADR-2)
- [ ] **T-08** `software-engineer-python` — Escrever `tests/unit/infrastructure/runtime_transforms/test_codex_transform.py`: golden tests para `project-manager` (substituição Agent tool), `project-auditor` (idem), agente genérico sem Agent tool (output verbatim), e output não-vazio para todos os 20 agentes

---

## P3 — CodexAgentDispatcher

> Depende de: T-03 `[x]`

- [ ] **T-09** `software-engineer-python` — Criar `dadaia_workspace/infrastructure/codex_agent_dispatcher.py` implementando `core/protocols/agent_dispatcher.py`: `capabilities()` → `DispatcherCapabilities(supports_parallel=True, mode=DispatcherMode.CODEX)`; `dispatch()` → sequential; `dispatch_parallel()` → parallel best-effort; capability ausente → `OrchestrationUnsupportedError` com motivo legível (FR8 / ADR-3)
- [ ] **T-10** `software-engineer-python` — Escrever `tests/unit/features/agents/test_codex_dispatcher_sequential.py`: dispatcher resolve um agente e produz invocação Codex correta (AC4)
- [ ] **T-11** `software-engineer-python` — Escrever `tests/unit/features/agents/test_codex_dispatcher_parallel.py`: fan-out múltiplo respeita a capability matrix de ADR-3 (AC5)
- [ ] **T-12** `software-engineer-python` — Escrever `tests/unit/features/agents/test_codex_dispatcher_unsupported.py`: capability ausente devolve `OrchestrationUnsupportedError` com motivo legível; não falha silenciosamente (AC6)

---

## P4 — Agent TOML Generation + config.toml

> Depende de: T-08 `[x]` (transform pronto) + T-06 `[x]` (model mapping pronto)

- [ ] **T-13** `software-engineer-python` — Adicionar `_install_codex_agents()` em `dadaia_workspace/infrastructure/public_assets.py`: lê os 20 `.md` de `public/agents/`, remove frontmatter, passa por `transform_for_codex()`, mapeia `model:` via `map_model()`, serializa TOML com `name`/`model`/`developer_instructions`, escreve `.codex/agents/<agent-id>.toml` (FR1 / FR7)
- [ ] **T-14** `software-engineer-python` — Atualizar `_install_codex()` em `public_assets.py` para chamar `_install_codex_agents()`; atualizar `.codex/config.toml` com 20 blocos `[agents.<name>] config_file = "agents/<name>.toml"` (FR7)
- [ ] **T-15** `software-engineer-python` — Executar `dadaia public install --target codex` e verificar: 20 arquivos em `.codex/agents/`; todos parseáveis por `tomllib`; `developer_instructions` não-vazio; zero strings `claude-*` em `.codex/**` (AC2 + AC3)

---

## P5 — Workflow Projection

> Depende de: T-03 `[x]`

- [ ] **T-16** `software-engineer-python` — Atualizar `_install_codex_workflows()` em `public_assets.py` para projetar todos os 7 workflows canônicos; hoje faltam `audit-cycle.workflow.md` e `code-review-fan-out.workflow.md` (FR9 / ADR-4)
- [ ] **T-17** `software-engineer-python` — Executar `dadaia public install --target codex` e verificar que `.codex/workflows/` tem exatamente os 7 arquivos canônicos (FR9)

---

## P6 — Rules + Skills

> Depende de: T-03 `[x]`

- [ ] **T-18** `software-engineer-python` — Auditar `.codex/rules/`: os 2 arquivos existentes (`game-agents-coordination.md`, `game-developer-scope.md`) são comportamentais (ADR-1/D2) — remover de `.codex/rules/`; verificar que `.codex/rules/` fica vazio ou contém apenas arquivos executáveis (FR11)
- [ ] **T-19** `software-engineer-python` — Verificar se `public/skills/**` já é projetado para `.agents/skills/` via `_install_agents_skills()` ou equivalente; se não, implementar projeção Tier-A; executar install e verificar hash-equivalência canônico ↔ projeção (FR12)

---

## P7 — Doctor Hardening

> Depende de: T-15 `[x]` (TOMLs gerados) + T-17 `[x]` (workflows completos)

- [ ] **T-20** `software-engineer-python` — Adicionar checks D-CX-1..5 em `doctor()` de `public_assets.py`: (D-CX-1) agente canônico sem TOML; (D-CX-2) TOML sem registro em `config.toml`; (D-CX-3) `.codex/workflows/` drift vs canônico; (D-CX-4) string `claude-*` em `.codex/**`; (D-CX-5) `developer_instructions` vazio; retorna não-zero com mensagem nomeando o agente/workflow (FR10)

---

## P8 — Test Suite (qa-engineer)

> Depende de: T-20 `[x]` (doctor com novos checks)

- [ ] **T-21** `qa-engineer` — Escrever `tests/integration/features/public/test_doctor_codex_checks.py`: AC7 (remoção artificial de workflow → doctor não-zero); AC8 (corrupção de TOML → doctor não-zero nomeando agente); AC9 (TOML ausente → doctor não reporta `[ok]`)
- [ ] **T-22** `qa-engineer` — Verificar cobertura ≥ 80% para `runtime_transforms/` e `codex_agent_dispatcher.py`; ajustar testes se necessário

---

## P9 — Validação Final

> Depende de: T-22 `[x]` (toda suite de testes pronta)

- [ ] **T-23** `software-engineer-python` — Executar AC1: `find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/post-codex.txt && diff /tmp/pre-codex.txt /tmp/post-codex.txt` → diff vazio
- [ ] **T-24** `software-engineer-python` — Executar AC2: todos os 20 TOMLs parseáveis por `tomllib` sem exceção
- [ ] **T-25** `software-engineer-python` — Executar AC3: `grep -rE '(^|[^a-zA-Z0-9_-])claude-' .codex/` → zero linhas
- [ ] **T-26** `qa-engineer` — Executar AC4–AC6: `pytest -q tests/unit/features/agents/test_codex_dispatcher_*.py` → exit 0
- [ ] **T-27** `qa-engineer` — Executar AC7–AC9: `pytest -q tests/integration/features/public/test_doctor_codex_checks.py` → exit 0
- [ ] **T-28** `software-engineer-python` — Executar AC10: `dadaia specs doctor` → 0 errors / 0 warnings

---

## P10 — CLOSURE Prep

> Depende de: T-28 `[x]` (todos os ACs verdes)
> Owner exclusivo: `product-engineer` (memory atomicity — workspace-protocol §5)

- [ ] **T-29** `product-engineer` — Redigir `CLOSURE.md` com evidências de AC1–AC10 (diff output, pytest output, grep output, doctor output)
- [ ] **T-30** `product-engineer` — Atualizar `specs/memory/architecture.html`: bloco no agent-topology layer descrevendo renderer split (canonical → Claude/Codex adapters) (AC11)
- [ ] **T-31** `product-engineer` — Atualizar `specs/memory/product/agent-orchestration.html`: capability matrix de ADR-3 (AC11)
- [ ] **T-32** `product-engineer` — Atualizar `specs/memory/tech-stack.html`: parity guard para Codex registrado (AC11)
- [ ] **T-33** `product-engineer` — Registrar OK do operador nas 6 ADRs lidas end-to-end em `CLOSURE.md` (AC12)
- [ ] **T-34** `product-engineer` — Flip `ACTIVE.md` → `phase: CLOSURE`; arquivar release em `specs/_archive/releases/codex-agent-orchestration-parity-v1/` após CLOSURE completa

---

**Status:** Aprovado
