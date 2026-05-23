# ADR-3 — Dispatcher Capability Matrix

> **Status:** Aprovado
> **Release:** codex-agent-orchestration-parity-v1
> **Decided:** 2026-05-20 (grill-me session)
> **Decider:** operador + product-engineer
> **Supersedes:** —

---

## Contexto

A release precisa de uma tabela explícita de capabilities por dispatcher × runtime para
guiar os testes de FR8 (CodexAgentDispatcher hardening) e documentar o que Codex suporta
vs o que é capability gap. Sem essa tabela, testes de dispatcher não têm critério claro
de pass/fail para fan-out e parallel.

---

## Decisão

### Capability Matrix

| Capability | ClaudeAgentDispatcher | CodexAgentDispatcher (new) | CliAgentDispatcher (fallback) |
|---|---|---|---|
| `sequential` | ✅ NATIVE | ✅ NATIVE | ✅ CLI (manual) |
| `parallel` | ✅ NATIVE (`dispatch_parallel`) | ✅ best-effort | ⚠️ CLI (manual, sequencial) |
| `fan-out` | ✅ NATIVE | ✅ best-effort | ⚠️ CLI (manual) |
| `audit-loop` | ✅ NATIVE | ⚠️ best-effort | ❌ unsupported |
| `unsupported-capability` | N/A | ✅ explicit (retorna motivo legível) | ✅ explicit |

**Legenda:**
- `NATIVE` — dispatcher resolve nativamente, sem intervenção manual
- `best-effort` — suportado com limitações; dispatcher tenta e reporta resultado
- `CLI (manual)` — requer intervenção humana; dispatcher emite invocation.md
- `unsupported` — não implementado; dispatcher retorna `OrchestrationUnsupportedError`
- `explicit` — capability ausente é reportada com motivo legível, sem fail silencioso

### UserPromptSubmit — capability gap documentado

`UserPromptSubmit` é um evento de hook Claude-específico. No Codex, não existe equivalente
nativo. O contexto de workspace é provido por:
1. `DADAIA_CONTEXT` env var (quando definida na sessão)
2. `AGENTS.md` no workspace root (carregado uma vez no início da sessão)

**Classificação:** `[not-applicable]` para Codex — gap proposital, não drift.

### Capabilities fora de escopo desta release

As capabilities `escalation` e `delegation-chain` não existem no codebase atual nem nos
workflows canônicos. Deferidas para releases futuras se emergirem como necessidade real.

---

## Consequências

- `CodexAgentDispatcher.capabilities()` retorna um `DispatcherCapabilities` com:
  `supports_parallel=True` (best-effort), `mode=DispatcherMode.CODEX`.
- Testes AC4, AC5, AC6 exercitam `sequential`, `parallel`, e `unsupported-capability`
  respectivamente.
- A capability matrix vive nesta ADR e é referenciada pelos testes; não é duplicada em
  `SKILL.md` (decisão tomada em grill-me: ADR-local é suficiente para esta release).
