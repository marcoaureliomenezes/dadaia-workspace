# PLAN — opencode-runtime-parity-hardening-v1

**Status:** Aprovado
**Release ID:** opencode-runtime-parity-hardening-v1
**Data:** 2026-05-28
**Aprovado em:** 2026-05-29 (operador; F1 owner-conflict resolvido — Track C → ai-engineer)

---

## Estrutura de Tracks

```
Track A — OpenCode Hardening      Track B — reports next CLI      Track C — agent-comms waves 2-7
(owner: software-engineer-python  (owner: software-engineer-python  (owner: ai-engineer)
 + ai-engineer assets)             + product-engineer spec)
         |                                  |                                  |
   T-OC-01 (investigação)            T-RN-01 (feature layer)           T-AC-01..06 (6 agents)
   T-OC-02 (color strip)             T-RN-02 (CLI command)              T-AC-07 (propagação)
   T-OC-03 (permission verify)       T-RN-03 (testes)                   T-AC-08 (testes)
   T-OC-04 (sdd-gate.ts)
   T-OC-05 (ctx-inject audit)
   T-OC-06 (testes regressão)
         |                                  |                                  |
         └──────────────────────────────────┴──────────────────────────────────┘
                                            |
                                      T-INT-01 (doctor final — todos os 21 agents)
```

**Regra de sequência:** Track C deve estar completo antes de T-OC-06 (testes de regressão Track A).
Tracks A e B são independentes entre si. T-INT-01 é o gate final após os 3 tracks.

---

## Baseline de cobertura (NFR-5)

Medir antes de iniciar Track B:
```bash
cd repos/dadaia-workspace && poetry run pytest --cov=dadaia_workspace --cov-report=term-missing -q
```
Registrar o percentual de `features/` aqui antes de abrir T-RN-01.
Floor constitucional: **80%** na camada `features/`.

**Baseline medido 2026-05-29 (NFR-5):** cobertura TOTAL = **89.57%** (7496 stmts, 782 miss);
camada `features/` bem acima de 80% (módulos em 81–100%). Suíte: 1919 passed, 1 skipped,
1 xpassed, **1 pre-existing failure** (`tests/unit/features/telemetry/test_service.py::test_refresh_runs_all_readers`
— não relacionada a esta release; será resolvida antes do CLOSURE para satisfazer NFR-1).

---

## Track A — OpenCode Runtime Parity Hardening

**Owner:** software-engineer-python (código Python), ai-engineer (assets `.opencode/plugins/`)
**Superfícies de escrita:** `dadaia_workspace/infrastructure/public_assets.py`, `.opencode/plugins/sdd-gate.ts`, `.opencode/plugins/ctx-inject.ts`, `tests/`

### Fase A1 — Investigação bloqueante (owner: software-engineer-python) — ✅ CONCLUÍDA 2026-05-29

Resolvida; resultados completos em SPEC §"Investigação T-OC-01 — Resultados". Resumo:

1. **`permission:` por-agent no OpenCode** — ✅ SUPORTADO em `.opencode/agent/<name>.md`
   como objeto `permission:` (categorias `edit`/`bash`/`webfetch`/`task`/… → `allow`/`deny`/`ask`;
   agent merge sobre global, agent vence). Mapeamento Claude→OpenCode: `Edit`/`Write`→`edit`,
   `Bash`→`bash`, `WebFetch`→`webfetch`, `Agent`→`task`; `WebSearch`→unsupported-comment.
   → T-OC-03 implementa transform.

2. **Evento de hook para tool use** — ✅ `tool.execute.before` CONFIRMADO (type defs
   `@opencode-ai/plugin`), `(input, output)`, `input.tool`, block via `throw`. → T-OC-04.

3. **(bônus) `ctx-inject.ts`** — `chat.message` válido mas assinatura desatualizada → T-OC-05
   corrige para `(input, output)` mutando `output.parts`.

### Fase A2 — Implementação (owner: software-engineer-python)

Sequência após investigação concluída:

1. **T-OC-02 (color strip)** — independente da investigação, pode iniciar imediatamente.
2. **T-OC-03 (permission)** — depende do resultado da investigação A1-item1.
3. **T-OC-04 (sdd-gate.ts)** — depende do resultado da investigação A1-item2.
4. **T-OC-05 (ctx-inject audit)** — independente, pode correr em paralelo com T-OC-03/04.

### Fase A3 — Testes de regressão (owner: software-engineer-python)

**T-OC-06 — executar somente após Track C concluído** (T-AC-07 completo).

---

## Track B — `dadaia reports next` CLI

**Owner:** software-engineer-python (implementação), product-engineer (review do contrato)
**Superfícies de escrita:** `dadaia_workspace/features/reports_validation/` (novo módulo ou extensão), `dadaia_workspace/cli/commands/reports.py`, `tests/`

**Independente de Track A e Track C** — pode iniciar e fechar em qualquer ordem.

### Fase B1 — Feature layer (owner: software-engineer-python)

Implementar lógica de negócio em `dadaia_workspace/features/reports_validation/` (ou novo
módulo `dadaia_workspace/features/reports_next/`). Contrato: ver FR-RN-1 no SPEC.

### Fase B2 — CLI command (owner: software-engineer-python)

Adicionar subcomando `next` em `dadaia_workspace/cli/commands/reports.py`, delegando para o
serviço da Fase B1.

### Fase B3 — Testes (owner: software-engineer-python)

Casos mínimos definidos em FR-RN-2. Cobertura da camada features ≥ 80%.

---

## Track C — agent-comms waves 2-7

**Owner:** ai-engineer (edição de agentes + propagação); software-engineer-python (testes em `tests/`)
**Superfícies de escrita:** `dadaia_workspace/public/agents/` (6 arquivos), propagação

> **Nota de autoridade:** `public/agents/**` é write-surface exclusiva de `ai-engineer`
> (write_allowlist). `product-engineer` (`specs/**` only) seria bloqueado pelo path-scope gate.
> `product-engineer` permanece owner da spec, não da edição de agentes.

**Deve ser concluído antes de T-OC-06 do Track A.**

### Fase C1 — Edição dos 6 agents (owner: ai-engineer)

Ordem sugerida (piloto primeiro, game agents por último):

| Ordem | Agent | Observação |
|---|---|---|
| 1 | `qa-engineer` | Piloto — validar padrão antes dos demais |
| 2 | `devops-engineer` | — |
| 3 | `backend-engineer` | — |
| 4 | `game-designer` | Game agents — revisar write_allowlist após `<ctx>` |
| 5 | `game-developer` | — |
| 6 | `game-tester` | Body já tem sidecar-first section — apenas frontmatter + invocação |

Referência para o padrão: `dadaia_workspace/public/agents/data-analyst.md`.

### Fase C2 — Propagação e validação (owner: ai-engineer)

```bash
dadaia public stage && dadaia public install --target all
dadaia public doctor
```

### Fase C3 — Testes (owner: software-engineer-python)

Verificar/adicionar testes para os 6 agents em `tests/`.

---

## Gate de integração final

### T-INT-01 — doctor completo (owner: software-engineer-python)

Após Track A (A3) e Track C (C2) concluídos:

```bash
dadaia public doctor  # todos os 21 agents [ok] em todos os runtimes suportados
```

Satisfaz AC-AC-2. Libera CLOSURE.

---

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| `tool.execute.before` não existe no OpenCode 1.14.x | Média | Investigação A1 é bloqueante; implementação de sdd-gate.ts só inicia após confirmação |
| `permission:` por-agent não suportado | Média | Investigação A1 define o caminho; AC-OC-2 tem dois caminhos válidos no SPEC |
| PLAN.md extraction instável (FR-RN-1) | Baixa | Contrato de parsing explícito definido no SPEC; fallback para exit 3 com mensagem orientadora |
| game-tester body duplicação | Baixa | Nota explícita na tabela da Fase C1 |
