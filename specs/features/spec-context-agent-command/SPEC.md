# Spec: Feature — /spec-context Agent Command

> **Status:** Aprovado
> **Versão:** 4.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/features/spec-context-project/SPEC.md`
> **Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`
> **Substitui:** v2.0 (descartada integralmente)
> **Dependência:** Requer `spec-context-project/SPEC.md` v4.0 aprovado

---

## Contexto

O `/spec-context` é um **agent command** canônico versionado em `dadaia_workspace/public/commands/spec-context.md` e projetado para runtimes que suportam commands. Ele permite ao operador listar, ativar e promover Spec Contexts a partir de sessões de agente sem acessar o terminal diretamente.

A v3.0 alinha-se ao modelo v4.0 do spec-context-project: múltiplos contextos podem estar `ativo` simultaneamente; um é designado `is_primary=True` como o foco principal do workspace. O command expõe `dadaia context list`, `dadaia context activate` e `dadaia context promote` para gerenciar esse estado via agente.

### Topologia de instalação (GAP-003 resolvido)

Cada runtime recebe commands no seu destino nativo quando suportado. Claude Code usa `.claude/commands/`; OpenCode usa `.opencode/commands/`; runtimes sem command support recebem instrução equivalente via `AGENTS.md`/rules. Não há promessa de que Codex execute slash commands Claude Code.

### Isolamento de sessão via `DADAIA_CONTEXT` (GAP-005 resolvido)

Quando o operador quer trabalhar em projetos diferentes em sessões de bot distintas, a solução não é trocar o contexto global via command — é iniciar o bot com `DADAIA_CONTEXT=<name>` na env. O `/spec-context` command opera sobre o estado global (`primary_context.json` / `spec_contexts.json`) e é adequado para fluxos onde o operador gerencia o primário globalmente.

---

## Glossário

| Termo | Definição |
|---|---|
| **Agent command** | Arquivo markdown canônico em `dadaia_workspace/public/commands/` projetado para o destino nativo do runtime quando suportado |
| **Contexto primário** | O Spec Context Project com `is_primary=True`; apontado por `primary_context.json`; foco atual do workspace |
| **Contexto ativo** | Qualquer Spec Context Project em estado `ativo` (repo em disco) — pode haver múltiplos |
| **Operador** | Usuário com ID Telegram autorizado nos bots |

---

## Usuários e Goals

### US-001: Ver contextos e o primário a partir do Telegram

- **Como** operador no Telegram
- **Quero** digitar `/spec-context` sem argumentos
- **Para** ver todos os contextos registrados, seus estados e qual é o primário

**Critérios de Aceite:**
- Dado que o operador envia `/spec-context`, então o agente lista todos os contextos com `nome`, `estado`, `is_primary` e `repo_slug`, e destaca o contexto primário
- Dado que não há contexto primário, então o agente informa claramente e sugere `dadaia context promote <nome>` após ativar um contexto

### US-002: Ativar e promover um contexto a partir do Telegram

- **Como** operador no Telegram
- **Quero** digitar `/spec-context <nome>` para ativar e tornar primário
- **Para** mudar o foco do workspace sem acessar o terminal

**Critérios de Aceite:**
- Dado que o contexto nomeado existe e está `inativo`, quando o operador usa `/spec-context <nome>`, então o agente executa `dadaia context activate <nome>` (que auto-promove se não há primário) e confirma com o novo `specs_dir`
- Dado que o contexto nomeado já está `ativo` mas não é primário, quando o operador usa `/spec-context <nome>`, então o agente executa `dadaia context promote <nome>` e confirma o novo primário
- Dado que o contexto nomeado já é o contexto primário, quando o operador usa `/spec-context <nome>`, então o agente confirma que já é primário sem alterar estado
- Dado que o contexto nomeado não existe, quando o operador usa `/spec-context <nome>`, então o agente reporta erro e lista os contextos disponíveis

---

## Requisitos Funcionais

### Fluxo sem argumento (`/spec-context`)

- FR-001: The command shall run `dadaia context list` and render the result showing `name`, `state`, `is_primary`, and `repo_slug` for each context.
- FR-002: The command shall run `dadaia context show --json` and highlight the current primary context, if any.
- FR-003: If no primary context exists, the command shall state that explicitly and suggest running `dadaia context promote <name>` after activating a context.

### Fluxo com argumento (`/spec-context <nome>`)

- FR-004: If the target context is `inativo`, the command shall run `dadaia context activate <nome>` (which auto-promotes if no primary exists) and report the new state with its `specs_dir`.
- FR-005: If the target context is `ativo` but not primary, the command shall run `dadaia context promote <nome>` and confirm the new primary with its `specs_dir`.
- FR-006: If the target context is already the primary context, the command shall confirm it is already primary without changing state.
- FR-007: If the target context name does not exist, the command shall report a `Context not found` error and list available contexts.
- FR-008: After any successful state change, the command shall output the updated `specs_dir` so the agent and operator know where specs will be loaded from.

### Integridade do contrato com dadaia CLI

- FR-009: The command shall use only the official `dadaia` CLI surface for all state changes. It shall not read `primary_context.json` or `spec_contexts.json` directly.
- FR-010: The command shall use `dadaia context show --json` as the source of truth for the current primary context.

### Distribuição

- FR-011: The command source shall live at `dadaia_workspace/public/commands/spec-context.md`.
- FR-012: The command shall be deployed to runtime-native command directories via `dadaia public install`: `.claude/commands/spec-context.md` for Claude Code, `.opencode/commands/spec-context.md` for OpenCode when supported, and `unsupported` for runtimes without command support.

---

## Requisitos Não-Funcionais

- NFR-001: [Segurança] O acesso ao `/spec-context` command é controlado pelo gateway do bot (redacted-infra `allowFrom`, redacted-infra `dmPolicy`), não pelo command em si.
- NFR-002: [Transparência] Toda operação state-changing executada pelo command deve ser mostrada ao operador antes ou durante a execução, incluindo o comando `dadaia` exato.
- NFR-003: [Falha segura] Se `dadaia context activate` falhar, o command deve reportar o erro exato sem deixar o workspace em estado inconsistente.
- NFR-004: [Idempotência] Executar `/spec-context <nome>` quando aquele contexto já está ativo deve confirmar o estado sem alterar nada.

---

## Fluxo Detalhado

```
/spec-context [<nome>]
       │
       ▼
┌─────────────────────┐    ┌────────────────────────────────────────────────────┐
│ sem argumento       │    │ com <nome>                                         │
│                     │    │                                                    │
│ dadaia context list │    │ Resolve estado via dadaia context list             │
│ dadaia context show │    │                                                    │
│   --json            │    │ inativo?  → dadaia context activate <nome>        │
│                     │    │             (auto-promove se não há primário)      │
│ Exibir lista +      │    │ ativo, não primário? → dadaia context promote <nome>│
│ contexto primário   │    │ já primário? → confirmar, sem mudança             │
└─────────────────────┘    │ não existe? → erro + listar contextos             │
                           │                                                    │
                           │ Se sucesso: exibir specs_dir novo                 │
                           └────────────────────────────────────────────────────┘
```

---

## Padrão de Isolamento via `DADAIA_CONTEXT`

Para operadores que precisam de sessões de bot isoladas em projetos diferentes, o mecanismo correto é iniciar o agente com a env var:

```bash
# Bot 1: sessão isolada no projeto dadaia-agents
DADAIA_CONTEXT=dadaia-agents claude --dangerously-skip-permissions

# Bot 2: sessão isolada no projeto redacted-slug
DADAIA_CONTEXT=redacted-slug opencode
```

Nesse caso, o hook `ctx-inject.sh` usa o contexto da env var, ignorando `primary_context.json`. O `/spec-context` command opera sobre o estado global (`spec_contexts.json` + `primary_context.json`) e NÃO sobrescreve a env var `DADAIA_CONTEXT`.

---

## Artefato de Saída

Um único arquivo markdown em:
```
dadaia_workspace/public/commands/spec-context.md
```

Instalado em runtime em:
```
<workspace-root>/.claude/commands/spec-context.md
<workspace-root>/.opencode/commands/spec-context.md
```

---

## Fora de Escopo

- Criação de novos contextos via `/spec-context` (use `dadaia context create`)
- Deleção de contextos via `/spec-context`
- Configuração de `DADAIA_CONTEXT` env var via command (deve ser feito na camada de infraestrutura do bot)
- Suporte a alias `/ctx` (pode ser adicionado como arquivo separado em versão futura)
