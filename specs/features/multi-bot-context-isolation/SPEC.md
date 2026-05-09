# Spec: Feature — Multi-Bot Spec Context Isolation

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/features/spec-context-project/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Contexto

O operador usa 3 bots do Telegram em paralelo (Claude Code, Codex, OpenCode), cada um podendo
trabalhar em um Spec Context Project diferente. Esta spec define como cada bot obtém isolamento
de contexto e como o operador troca de contexto dentro de cada chat do Telegram.

O mecanismo base (DADAIA_CONTEXT env var, primary_context.json, ctx-inject.sh) já está
implementado no dadaia-workspace. Esta spec define a integração com os bots.

---

## Glossário

| Termo | Definição |
|---|---|
| **Contexto de sessão** | O Spec Context Project ativo para um bot específico, armazenado em memória no processo do bot |
| **Contexto global** | O contexto primário registrado em `primary_context.json`; compartilhado entre todos |
| **Isolamento por-bot** | Capacidade de cada bot manter contexto próprio independente do global |
| **DADAIA_CONTEXT** | Env var que sobrepõe primary_context.json para o subprocess do AI |

---

## Decisão de Arquitetura (ADR-002)

| Bot | Mecanismo de isolamento |
|---|---|
| Claude Code | `DADAIA_CONTEXT` env var passado ao subprocess `claude`; `ctx-inject.sh` injeta no sistema |
| Codex | `_current_context` no processo Python; injetado no TELEGRAM_BRIEF de cada invocação |
| OpenCode | `primary_context.json` global; sem isolamento por-bot (limitação do binary `opencode-telegram`) |

---

## Requisitos Funcionais

### Claude Code bot (`claude-telegram-bot.py`)

- FR-CC-001: O bot deve expor o comando Telegram `/context <nome>` que ativa o contexto nomeado e armazena-o no estado do processo Python.
- FR-CC-002: Todo subprocess `claude` invocado após `/context <nome>` deve receber `DADAIA_CONTEXT=<nome>` como variável de ambiente, dando prioridade sobre `primary_context.json`.
- FR-CC-003: Trocar contexto via `/context` NÃO deve alterar `primary_context.json` diretamente — o `dadaia context activate` é chamado apenas para garantir que o repo está em disco.
- FR-CC-004: O bot deve confirmar o contexto ativo mostrando `nome` e `specs_dir`.
- FR-CC-005: `/context` sem argumento deve mostrar o contexto atual da sessão.

### Codex bot (`codex-telegram-bot.py`)

- FR-CX-001: O bot deve expor o comando Telegram `/context <nome>` que ativa o contexto nomeado.
- FR-CX-002: O `WORKSPACE` do bot deve ser `/home/workspace` (não `/home/workspace/repos/dadaia-agents`).
- FR-CX-003: O TELEGRAM_BRIEF de cada invocação deve incluir dinamicamente o contexto ativo (nome do projeto, `specs_dir`, instrução para ler specs antes de qualquer implementação).
- FR-CX-004: Trocar contexto via `/context` NÃO deve alterar `primary_context.json`.
- FR-CX-005: O TELEGRAM_BRIEF deve remover referências hardcoded a `specs/features/` e `specs/security/` — essas paths são relativas ao projeto ativo, resolvidas dinamicamente.

### OpenCode bot (`opencode-serve` + `opencode-telegram`)

- FR-OC-001: O servidor `opencode-serve` deve ler SDD rules via `opencode.json` em `/home/workspace`.
- FR-OC-002: O `opencode.json` deve incluir `CLAUDE.md` e o SDD enforcer rule como instruções.
- FR-OC-003: Troca de contexto no OpenCode é feita via linguagem natural; o AI executa `dadaia context activate <nome>` e `dadaia context promote <nome>` conforme `spec-context-project/SPEC.md`.

### SDD rules availability

- FR-SDD-001: Claude Code bot já lê `.claude/rules/` de `/home/workspace/.claude/` — manter.
- FR-SDD-002: Após fix de WORKSPACE do Codex, as regras SDD chegam via TELEGRAM_BRIEF dinâmico.
- FR-SDD-003: OpenCode lê `opencode.json` de `/home/workspace`; instruções devem incluir referência ao `dadaia-workspace-sdd-enforcer.md`.

---

## Requisitos Não-Funcionais

- NFR-001: Isolamento por-bot é em memória — não persiste entre restarts do serviço.
- NFR-002: O `/context <nome>` chama `dadaia context activate <nome>` para garantir que o repo está em disco; o efeito colateral de auto-promote é aceitável.
- NFR-003: O OpenCode não tem isolamento por-bot — trocar contexto nele altera o estado global; documentado como limitação.

---

## Critérios de Aceite

1. `/context redacted-slug` no chat do Codex → próximas respostas usam specs de `repos/redacted-slug/specs/`
2. `/context dadaia-workspace` no chat do Claude Code → `DADAIA_CONTEXT=dadaia-workspace` passado ao subprocess; `ctx-inject.sh` confirma `session=dadaia-workspace`
3. Trocar contexto no bot A não altera o que o bot B reporta como contexto
4. OpenCode responde sobre SDD rules quando perguntado
5. `dadaia context show --json` reflete apenas mudanças globais (promote), não trocas por-bot

---

## Fora de Escopo

- Persistência do contexto por-bot entre restarts do serviço (em memória apenas)
- Isolamento por-bot para OpenCode (limitação do binary `opencode-telegram`)
- Suporte a múltiplos usuários por bot
- Criação/deleção de contextos via comando Telegram (use terminal ou `dadaia` CLI)
