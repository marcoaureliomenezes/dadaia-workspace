# Implementation Plan: Cross-Tool Parity

**Feature:** cross-tool-parity
**Status:** Aprovado
**SPEC:** `specs/features/cross-tool-parity/SPEC.md`
**Data:** 2026-05-09
**Consolidado por:** `specs/features/universal-agentic-assets/PLAN.md`

---

## Decisões de Arquitetura

**ADR-CTP-001: AGENTS.md é o documento universal cross-tool.**
Contém as regras SDD universais, escritas para leitura direta por AI sem depender de um runtime específico.

**ADR-CTP-002: Personas são canônicas em `public/agents/`.**
Claude Code recebe `.claude/agents/`; OpenCode recebe projeção nativa quando suportada; Codex recebe personas via `AGENTS.md`/rules quando não houver sub-agentes nativos.

**ADR-CTP-003: Spec Context via CLI universal, hook quando suportado.**
Todos os runtimes usam `dadaia context list` e `dadaia context show --json`; runtimes com hook suportado podem injetar contexto automaticamente.

**ADR-CTP-004: Assets vivem em `public/`, staging em `.dadaia/agentic/`.**
`dadaia_workspace/public/` é fonte canônica; `dadaia public stage` gera `.dadaia/agentic/`; `dadaia public install` projeta para runtimes.

**ADR-CTP-005: `dadaia init` chama o fluxo universal.**
`WorkspaceService.init()` deve criar staging e projeções multi-runtime sem sobrescrever customizações locais.

---

## Arquitetura das Mudanças

### 1. Template universal em `dadaia_workspace/public/`
Template canônico de `AGENTS.md`, staged em `.dadaia/agentic/` e projetado para o workspace root.

### 2. Atualizar: `dadaia_workspace/public/agents/*.md` (4 arquivos)
Adicionar seções padronizadas em cada agente:
- `## dadaia CLI` — referência ao `dadaia context list`, `dadaia academy run`, etc.
- `## Python / venv policy` — `.dadaia/.venv/bin/python`
- `## Spec Context` — como descobrir o contexto ativo

### 3. Atualizar: `dadaia_workspace/features/workspace/service.py`
`WorkspaceService.init()` → chamar staging e `public install --target all`.

### 4. Atualizar: `dadaia_workspace/features/public/service.py`
`PublicAssetService` → implementar stage, projections e doctor conforme `universal-agentic-assets`.

---

## Arquivos Afetados

| Arquivo | Ação | Camada |
|---|---|---|
| `dadaia_workspace/public/**` | Criar/Atualizar templates e assets | Public assets |
| `dadaia_workspace/public/agents/architect-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/product-auditor-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/product-engineer-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/soft-engineer-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/features/workspace/service.py` | Atualizar | Feature |
| `dadaia_workspace/features/public/service.py` | Atualizar stage/install/doctor | Feature |

---

## Dependências

- Depende de `specs/features/universal-agentic-assets/`
- `dadaia export` (já implementado) inclui `AGENTS.md` via `resolve_includes()` — já funciona
  pois busca qualquer arquivo `AGENTS.md` no workspace root

---

## Riscos

| Risco | Mitigação |
|---|---|
| AGENTS.md ficar fora de sync com regras runtime | `dadaia public doctor` compara package, staging e projeções |
| `dadaia init` sobreescrever AGENTS.md customizado | Usar "create if absent" — não sobreescrever |
| runtime sem capability equivalente | Reportar `unsupported`, não criar falsa paridade |
