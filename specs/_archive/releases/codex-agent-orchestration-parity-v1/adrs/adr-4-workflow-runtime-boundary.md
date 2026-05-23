# ADR-4 — Workflow Runtime Boundary

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** operador
> **Supersedes:** —

---

## Contexto

A release precisa que `.codex/workflows/` reflita exatamente os 7 workflows canônicos
(hoje tem 5 — faltam `audit-cycle` e `code-review-fan-out`). Antes de implementar,
era necessário decidir a arquitetura de renderização: estática no install time vs
dinâmica no dispatch time.

---

## Decisão

**Opção A — Render-at-install (estático).** O `_install_codex` em `public_assets.py`
gera os arquivos `.codex/workflows/` no momento do `dadaia public install`. Os workflows
são arquivos estáticos em disco após o install.

---

## Rationale

| Critério | Opção A (escolhida) | Opção B (descartada) |
|---|---|---|
| Consistência com padrão atual | ✅ Os 5 workflows existentes já são gerados assim | ❌ Requer nova infraestrutura |
| Complexidade de implementação | ✅ Mínima — apenas adicionar 2 workflows ao install path | ❌ Alta — adapter runtime, WorkflowDefinition neutro modificado |
| Risco de escopo creep | ✅ Baixo | ❌ Alto (NG5 proíbe campos Codex-only no WorkflowDefinition) |
| Compatibilidade com NG5 | ✅ WorkflowDefinition neutro inalterado | ⚠️ Tentador adicionar campos Codex-only |
| Doctor check | ✅ Simples: comparar lista de arquivos vs canônico | ✅ Possível, mas mais complexo |

Os 5 workflows já existentes em `.codex/workflows/` são estáticos gerados pelo install —
Opção A é o padrão em produção. Opção B não tem justificativa de produto nesta release.

---

## Consequências

- `_install_codex` em `public_assets.py` ganha lógica para projetar todos os 7 workflows
  canônicos de `dadaia_workspace/public/workflows/` para `.codex/workflows/`.
- `audit-cycle.workflow.md` e `code-review-fan-out.workflow.md` passam a ser projetados.
- `dadaia public doctor` detecta drift em ambos os sentidos: workflow canônico sem
  projeção Codex, e projeção Codex sem correspondente canônico (AC7).
- `WorkflowDefinition` permanece neutro — zero campos Codex-only (NG5 respeitado).
