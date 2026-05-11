# 02. Operacao CLI, Sessoes e Contexto

Consulta oficial: 2026-05-09.

## Modos de uso

Pi suporta dois modos principais:

- interativo (`pi`): melhor para iteracao no repo;
- one-shot (`pi -p`): melhor para automacao e comandos pontuais.

Exemplos:

```bash
pi "List all .ts files in src/"
pi -p "Summarize this codebase"
cat README.md | pi -p "Summarize this text"
```

## Slash commands essenciais

No dia a dia, foque nestes:

- `/model` troca modelo;
- `/settings` ajusta comportamento;
- `/session` mostra estado e custo;
- `/resume` abre sessao anterior;
- `/new` cria sessao limpa;
- `/compact` compacta contexto;
- `/reload` recarrega contexto, skills e extensoes.

## Filas de mensagem e interrupcao

Pi permite enfileirar mensagens enquanto o agente esta trabalhando.

- Enter: steering apos turno atual;
- Alt+Enter: follow-up apos concluir fluxo;
- Escape: aborta e devolve fila ao editor.

Essa mecanica evita perder linha de raciocinio no meio de tasks longas.

## Gestao de sessoes

Sessoes ficam salvas por diretorio em `~/.pi/agent/sessions/`.

Comandos uteis:

```bash
pi -c
pi -r
pi --session <path-ou-id>
pi --fork <path-ou-id>
pi --no-session
```

## Context files

Pi carrega contexto de:

- `~/.pi/agent/AGENTS.md`;
- parent directories;
- diretorio atual.

Para desativar carregamento automatico:

```bash
pi --no-context-files
```

## Operacao segura

1. Comece read-only para exploracao:

```bash
pi --tools read,grep,find,ls -p "Review the code"
```

2. So depois habilite escrita/edicao.
3. Use checkpoint via git antes de tarefas grandes.
4. Em sessao longa, compacte para reduzir contexto podre.

## Heuristica de produtividade

- tarefa curta: one-shot;
- tarefa ambigua: interativo com checkpoints;
- tarefa longa: interativo + compactacao + sessao nomeada;
- tarefa repetitiva: transformar em template/skill.
