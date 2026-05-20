# Plan: Release — codex-agent-orchestration-parity-v1

> **Status:** Aprovado
> **Release ID:** codex-agent-orchestration-parity-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20

---

## Estratégia

Dez fases sequenciais. A ordem é rígida: FR13 (cleanup de commands) vem primeiro porque
define o baseline do guard AC1, e o baseline deve ser capturado antes de qualquer mudança
Codex. As fases de infraestrutura (transform + model mapping + dispatcher) precedem a
geração de artefatos (TOMLs + workflows) para garantir que os helpers existam quando o
installer os chama. Doctor hardening e validação fecham o ciclo.

**Agentes responsáveis por fase:**

| Phase | Agente | Domínio |
|---|---|---|
| P1 — Cleanup + Baseline | `software-engineer-python` | FR13, AC1 snapshot |
| P2 — Runtime transforms | `software-engineer-python` | ADR-2, ADR-5 |
| P3 — CodexAgentDispatcher | `software-engineer-python` | FR8, ADR-3 |
| P4 — Agent TOML + config | `software-engineer-python` | FR1, FR7 |
| P5 — Workflow projection | `software-engineer-python` | FR9, ADR-4 |
| P6 — Rules + Skills | `software-engineer-python` | FR11, FR12 |
| P7 — Doctor hardening | `software-engineer-python` | FR10 |
| P8 — Test suite | `qa-engineer` | AC1–AC10 |
| P9 — Validação final | `software-engineer-python` + `qa-engineer` | AC1–AC12 |
| P10 — CLOSURE prep | `product-engineer` | AC11, AC12 |

---

## Camadas afetadas

| Camada | Ação |
|---|---|
| `dadaia_workspace/public/commands/` | DELETE (4 arquivos — FR13) |
| `dadaia_workspace/infrastructure/runtime_transforms/` | NEW directory + `codex.py` + `model_mapping.py` |
| `dadaia_workspace/infrastructure/codex_agent_dispatcher.py` | NEW |
| `dadaia_workspace/infrastructure/public_assets.py` | EDIT (`_install_codex_agents`, `_install_codex_workflows`, `doctor()`) |
| `.codex/agents/` | NEW directory + 20 TOML files |
| `.codex/config.toml` | EDIT (20 `[agents.<name>]` registrations) |
| `.codex/workflows/` | EDIT (adicionar `audit-cycle`, `code-review-fan-out`) |
| `.codex/rules/` | READ-ONLY (todas as rules são comportamentais — ADR-1/D2) |
| `.claude/**` | READ-ONLY (NG1 + AC1; mudança intencional apenas em P1) |
| `tests/unit/infrastructure/runtime_transforms/` | NEW |
| `tests/unit/features/agents/` | NEW (`test_codex_dispatcher_*.py`) |
| `tests/integration/features/public/` | EDIT (doctor Codex checks) |

---

## Ordem de execução

### P1 — Cleanup + Baseline (FR13 + AC6 setup)

**Obrigatório primeiro.** Qualquer mudança fora deste escopo antes de P1 completar
contamina o baseline de AC1.

1. Deletar `dadaia_workspace/public/commands/dadaia-academy.md`
2. Deletar `dadaia_workspace/public/commands/dadaia-workspace-doctor.md`
3. Deletar `dadaia_workspace/public/commands/dadaia-workspace-refine-specs.md`
4. Deletar `dadaia_workspace/public/commands/spec-context.md`
5. Executar `dadaia public install --target claude` → verifica `.claude/commands/` limpo
6. Executar `dadaia public install --target opencode` → idem para OpenCode se aplicável
7. **Capturar golden snapshot:** `find .claude -type f -print0 | xargs -0 sha256sum | sort > /tmp/pre-codex.txt`
8. Commitar snapshot como artefato da release em `.dadaia/tmp/json/pre-codex-snapshot.json`

### P2 — Runtime transforms (ADR-2 + ADR-5)

Criar o módulo de transforms antes do installer precisar deles.

1. Criar `dadaia_workspace/infrastructure/runtime_transforms/__init__.py`
2. Criar `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py`
   - `MODEL_MAP` com os 3 mappings de ADR-5
   - `map_model(claude_id: str) -> str` — `ValueError` em identifier desconhecido
3. Criar `dadaia_workspace/infrastructure/runtime_transforms/codex.py`
   - `transform_for_codex(canonical_body: str, agent_id: str) -> str`
   - Substituições obrigatórias de ADR-2: `Agent tool` → `subagent`, remover
     referências a hooks Claude-específicos, preservar resto verbatim
4. Escrever `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py`
   - Testa os 3 mappings + `ValueError` em identifier desconhecido
5. Escrever `tests/unit/infrastructure/runtime_transforms/test_codex_transform.py`
   - Golden tests: `project-manager`, `project-auditor`, agente genérico sem Agent tool,
     output não-vazio para todos os 20 agentes

### P3 — CodexAgentDispatcher (FR8 + ADR-3)

1. Criar `dadaia_workspace/infrastructure/codex_agent_dispatcher.py`
   - Implementa `core/protocols/agent_dispatcher.py`
   - `capabilities()` → `DispatcherCapabilities(supports_parallel=True, mode=DispatcherMode.CODEX)`
   - `dispatch(invocation)` → sequential, produz invocação Codex
   - `dispatch_parallel(invocations)` → parallel best-effort (ADR-3)
   - Capability ausente → `OrchestrationUnsupportedError` com motivo legível, nunca falha silenciosa
2. Escrever `tests/unit/features/agents/test_codex_dispatcher_sequential.py` (AC4)
3. Escrever `tests/unit/features/agents/test_codex_dispatcher_parallel.py` (AC5)
4. Escrever `tests/unit/features/agents/test_codex_dispatcher_unsupported.py` (AC6)

### P4 — Agent TOML generation + config.toml (FR1 + FR7)

1. Adicionar `_install_codex_agents()` em `public_assets.py`:
   - Lê os 20 `.md` de `public/agents/`
   - Remove frontmatter, passa body por `transform_for_codex()` (ADR-2)
   - Mapeia `model:` via `map_model()` (ADR-5)
   - Serializa TOML com `name`, `model`, `developer_instructions`
   - Escreve `.codex/agents/<agent-id>.toml`
2. Atualizar `_install_codex()` para chamar `_install_codex_agents()`
3. Atualizar `.codex/config.toml` com 20 blocos `[agents.<name>]`:
   ```toml
   [agents.<name>]
   config_file = "agents/<name>.toml"
   ```
4. Executar `dadaia public install --target codex` e verificar:
   - 20 arquivos em `.codex/agents/`
   - Cada arquivo parseável por `tomllib`
   - `developer_instructions` não-vazio em todos
   - Zero strings `claude-*` em `.codex/**`

### P5 — Workflow projection (FR9 + ADR-4)

1. Atualizar `_install_codex_workflows()` em `public_assets.py` para projetar todos os 7
   workflows canônicos (hoje projeta 5 — faltam `audit-cycle` e `code-review-fan-out`)
2. Executar `dadaia public install --target codex`
3. Verificar `.codex/workflows/` com 7 arquivos (lista exata da canônica)

### P6 — Rules + Skills (FR11 + FR12)

**FR11 (Rules):** Todas as 4 rules canônicas são comportamentais (ADR-1/D2) — `.codex/rules/`
não recebe novos arquivos. Verificar que os 2 arquivos existentes (`game-agents-coordination.md`,
`game-developer-scope.md`) são comportamentais e se devem permanecer ou ser removidos.
Se comportamentais, remover de `.codex/rules/` (estavam lá por erro).

**FR12 (Skills):** Verificar se `_install_codex()` ou `_install_agents_skills()` já
projeta `public/skills/**` para `.agents/skills/`. Se não:
1. Adicionar lógica em `public_assets.py` para projetar Tier-A skills
2. Executar `dadaia public install --target agents`
3. Verificar hash-equivalência entre canônico e projeção

### P7 — Doctor hardening (FR10)

Adicionar em `dadaia_workspace/infrastructure/public_assets.py` → `doctor()`:

1. **Check D-CX-1:** agente canônico sem `.codex/agents/<name>.toml` → drift
2. **Check D-CX-2:** `.codex/agents/<name>.toml` sem `[agents.<name>]` em `config.toml` → drift
3. **Check D-CX-3:** `.codex/workflows/` com lista diferente de `public/workflows/` → drift
4. **Check D-CX-4:** qualquer string `claude-*` em `.codex/**` → erro
5. **Check D-CX-5:** `developer_instructions` vazio em qualquer `.codex/agents/*.toml` → erro

Doctor retorna não-zero em qualquer check com mensagem nomeando o agente ou workflow.

### P8 — Test suite (qa-engineer)

`qa-engineer` define e escreve:

1. `tests/integration/features/public/test_doctor_codex_checks.py`:
   - AC7: remover workflow de `.codex/workflows/` → doctor retorna não-zero
   - AC8: corromper `.codex/agents/<name>.toml` → doctor retorna não-zero nomeando o agente
   - AC9: remover `.codex/agents/<name>.toml` → doctor não reporta `[ok]` (reporta drift)
2. Verificar cobertura ≥ 80% para `runtime_transforms/` e `codex_agent_dispatcher.py`

### P9 — Validação final

Executar todos os ACs em sequência:

| AC | Comando | Critério |
|---|---|---|
| AC1 | `find .claude -type f -print0 \| xargs -0 sha256sum \| sort > /tmp/post.txt && diff /tmp/pre-codex.txt /tmp/post.txt` | diff vazio |
| AC2 | `python3 -c "import tomllib; [tomllib.load(open(f,'rb')) for f in glob('.codex/agents/*.toml')]"` | sem exceção |
| AC3 | `grep -rE '(^|[^a-zA-Z0-9_-])claude-' .codex/` | zero linhas (exit 1) |
| AC4 | `pytest -q tests/unit/features/agents/test_codex_dispatcher_sequential.py` | exit 0 |
| AC5 | `pytest -q tests/unit/features/agents/test_codex_dispatcher_parallel.py` | exit 0 |
| AC6 | `pytest -q tests/unit/features/agents/test_codex_dispatcher_unsupported.py` | exit 0 |
| AC7 | (integration test — remoção artificial de workflow) | doctor não-zero |
| AC8 | (integration test — corrupção de TOML) | doctor não-zero com nome |
| AC9 | (integration test — TOML ausente) | doctor não reporta `[ok]` |
| AC10 | `dadaia specs doctor` | 0 errors / 0 warnings |

### P10 — CLOSURE prep (product-engineer)

1. Redigir `CLOSURE.md` com evidências dos ACs (snapshots, diff output, pytest output)
2. Atualizar memory atoms (AC11):
   - `specs/memory/architecture.html` — bloco no agent-topology layer: renderer split canonical → Claude/Codex adapters
   - `specs/memory/product/agent-orchestration.html` — capability matrix de ADR-3
   - `specs/memory/tech-stack.html` — parity guard para Codex registrado
3. Operador lê as 6 ADRs end-to-end (AC12) e registra OK em CLOSURE
4. Flip `ACTIVE.md` → `phase: CLOSURE`
5. Arquivar em `specs/_archive/releases/codex-agent-orchestration-parity-v1/`

---

## Riscos técnicos

| Risco | Mitigação |
|---|---|
| P1 não executado antes de qualquer mudança Codex | TASKS.md bloqueia: task P1 deve estar `[x]` antes de qualquer task P2+ começar |
| `transform_for_codex()` trunca ou corrompe persona body | Golden tests por agente (20 fixtures em P2) |
| `map_model()` recebe identifier novo sem mapping | `ValueError` explícito → install falha antes de gerar TOML inválido |
| `.codex/rules/` com files comportamentais (2 arquivos existentes) | P6 verifica e remove se comportamentais |
| Doctor check D-CX-4 dá falso positivo em comentários ou docs | Regex em AC3 usa `(^|[^a-zA-Z0-9_-])claude-` — não pega substrings como `not-claude-related` |
| AC1 falha por mudança não-intencional em `.claude/**` durante P2–P7 | Rodar AC1 após cada phase; não só no P9 |

---

## Plano de validação por phase

- **Pós-P1:** `.claude/commands/` vazio; snapshot capturado em `/tmp/pre-codex.txt`
- **Pós-P2:** `pytest tests/unit/infrastructure/runtime_transforms/` → exit 0
- **Pós-P3:** `pytest tests/unit/features/agents/test_codex_dispatcher_*.py` → exit 0
- **Pós-P4:** `dadaia public install --target codex` → 20 TOMLs; AC2 + AC3 verdes
- **Pós-P5:** `.codex/workflows/` com exatamente 7 arquivos
- **Pós-P6:** `.codex/rules/` apenas com executáveis (ou vazio); `.agents/skills/` populado
- **Pós-P7:** `dadaia public doctor` detecta drift artificial nos testes D-CX-1..5
- **Pós-P8:** `pytest tests/integration/features/public/test_doctor_codex_checks.py` → exit 0
- **Pós-P9:** todos os ACs verdes; AC1 diff vazio
- **Pós-P10:** `dadaia specs doctor` → 0 errors / 0 warnings; memory atoms atualizados

**Status:** Aprovado
