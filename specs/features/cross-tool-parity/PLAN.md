# Implementation Plan: Cross-Tool Parity

**Feature:** cross-tool-parity
**Status:** Aprovado
**SPEC:** `specs/features/cross-tool-parity/SPEC.md`
**Data:** 2026-05-09

---

## Decisões de Arquitetura

**ADR-CTP-001: AGENTS.md é o documento universal cross-tool.**
Contém as mesmas regras de `.claude/rules/`, escritas para leitura direta por AI sem
acesso ao sistema de rules do Claude Code. Não é mais conteúdo de bot Telegram.

**ADR-CTP-002: Agentes OpenCode/Codex vivem como seções em AGENTS.md.**
OpenCode e Codex não têm mecanismo de arquivos separados. Agentes são personas ativadas
via instrução natural. Claude Code continua com `.claude/agents/*.md`.

**ADR-CTP-003: Spec Context via instrução explícita, não hook.**
Claude Code usa ctx-inject.sh (UserPromptSubmit). Para OpenCode/Codex: AGENTS.md instrui
a AI a rodar `dadaia context list` na abertura de sessão. Sem hook técnico equivalente.

**ADR-CTP-004: AGENTS.md template vive em `public/data/`.**
`dadaia_workspace/public/data/AGENTS.md` é a fonte canônica.
`dadaia public install` o copia para `<workspace-root>/AGENTS.md` (workspace root level,
não dentro de `.claude/`).

**ADR-CTP-005: `dadaia init` adiciona AGENTS.md ao scaffold.**
`WorkspaceService.init()` já cria `.claude/`, `CLAUDE.md`, etc. Adicionar `AGENTS.md`
segue o mesmo padrão: cria se não existir.

---

## Arquitetura das Mudanças

### 1. Novo arquivo: `dadaia_workspace/public/data/AGENTS.md`
Template canônico. Conteúdo idêntico ao `AGENTS.md` que o operador deve ter no workspace.
Não usa placeholders — é instalado literalmente.

### 2. Atualizar: `dadaia_workspace/public/agents/*.md` (4 arquivos)
Adicionar seções padronizadas em cada agente:
- `## dadaia CLI` — referência ao `dadaia context list`, `dadaia academy run`, etc.
- `## Python / venv policy` — `.dadaia/.venv/bin/python`
- `## Spec Context` — como descobrir o contexto ativo

### 3. Atualizar: `dadaia_workspace/features/workspace/service.py`
`WorkspaceService.init()` → adicionar AGENTS.md ao scaffold via `public/data/AGENTS.md`.

### 4. Atualizar: `dadaia_workspace/features/public/service.py`
`PublicAssetService.install()` → incluir `public/data/AGENTS.md` como target no workspace root
(não em `.claude/` — AGENTS.md vive um nível acima).

---

## Arquivos Afetados

| Arquivo | Ação | Camada |
|---|---|---|
| `dadaia_workspace/public/data/AGENTS.md` | Criar | Public assets |
| `dadaia_workspace/public/agents/architect-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/product-auditor-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/product-engineer-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/public/agents/soft-engineer-agent.md` | Atualizar | Public assets |
| `dadaia_workspace/features/workspace/service.py` | Atualizar | Feature |
| `dadaia_workspace/features/public/service.py` | Verificar/Atualizar | Feature |

---

## Dependências

- Nenhuma dependência de outras features
- `dadaia export` (já implementado) inclui `AGENTS.md` via `resolve_includes()` — já funciona
  pois busca qualquer arquivo `AGENTS.md` no workspace root

---

## Riscos

| Risco | Mitigação |
|---|---|
| AGENTS.md ficar fora de sync com `.claude/rules/` | Manutenção manual documentada; `dadaia doctor` pode verificar |
| `dadaia init` sobreescrever AGENTS.md customizado | Usar "create if absent" — não sobreescrever |
| public/data/ não existe como diretório | Verificar e criar se necessário |
