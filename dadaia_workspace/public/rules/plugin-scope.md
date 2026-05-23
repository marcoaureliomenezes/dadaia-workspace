---
name: plugin-scope
description: Enforces that the frontend-design plugin is restricted to frontend-engineer and design-specialist only.
always_on: true
---

# plugin-scope

Esta rule é sempre ativa neste workspace.

## Restrição do Plugin frontend-design

O plugin `frontend-design` é restrito aos agentes `frontend-engineer` e `design-specialist`.
**Nenhum outro agente pode invocar skills ou tools deste plugin.**

### Agentes autorizados

| Agente | Plugins autorizados |
|---|---|
| `frontend-engineer` | `frontend-design`, `playwright` |
| `design-specialist` | `frontend-design`, `playwright` |

### Proibido para todos os outros agentes

Se você não é `frontend-engineer` ou `design-specialist` e recebeu uma tarefa que envolve o plugin `frontend-design`, responda:

```
[PLUGIN SCOPE ERROR] frontend-design plugin is restricted to frontend-engineer + design-specialist. Dispatch the correct agent.
```

### Rationale

O plugin `frontend-design` polui o contexto de agentes não-UI e cria risco de
leakage de padrões de design fora da superfície UI/UX. Ver ADR-X7 em `specs/constitution.md`.
