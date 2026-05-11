# 02. Commands, Skills e Memoria

## Slash commands existem para controlar a sessao

A documentacao oficial descreve `commands` como a forma rapida de controlar Claude Code de dentro da propria sessao.

Eles servem para:

- limpar ou compactar contexto;
- trocar modelo ou effort;
- ajustar permissoes;
- inspecionar memoria;
- abrir diffs;
- gerenciar plugins, hooks, tasks e MCP.

## Exemplos de commands que voce realmente vai usar

### `/help`

Mostra os comandos disponiveis.

### `/memory`

Abre a superficie de memoria: arquivos `CLAUDE.md`, `CLAUDE.local.md`, rules carregadas e auto memory.

### `/permissions`

Permite ajustar `allow`, `ask` e `deny` para tools e padroes de execucao.

### `/plan`

Entra em plan mode. E uma das melhores defesas contra implementacao impulsiva.

### `/diff`

Ajuda a revisar o que mudou sem depender apenas da narrativa do agente.

### `/tasks`

Ajuda a acompanhar trabalho em background.

## Built-in commands versus skills

A documentacao faz uma distincao importante:

- built-in commands sao comportamento implementado no proprio CLI;
- skills usam o mesmo mecanismo de skills customizadas: prompts reutilizaveis que Claude pode executar sob demanda.

Isso importa porque nem todo comando e uma "feature hardcoded". Parte deles e, na verdade, uma embalagem operacional de workflow.

## MCP prompts como commands

Outro detalhe importante: MCP servers podem expor prompts que aparecem como commands usando o formato `/mcp__<server>__<prompt>`.

Na pratica, isso transforma o conjunto de commands visiveis em algo parcialmente dinamico.

## Como pensar memoria do jeito certo

Use `CLAUDE.md` para o que precisa orientar todas as sessoes.

Use rules para organizar ou escopar instrucoes.

Use auto memory para learnings recorrentes que surgem no trabalho real.

Se tudo vai para `CLAUDE.md`, o arquivo vira ruido.

Se tudo vai para auto memory, o projeto perde governanca.

Se nada e persistido, voce reexplica as mesmas coisas em toda sessao.

## Boa pratica operacional

Quando Claude nao estiver seguindo o esperado:

1. abra `/memory`;
2. verifique quais instrucoes realmente carregaram;
3. cheque se ha conflito entre regras;
4. confirme se a orientacao deveria estar em `CLAUDE.md`, rule path-scoped ou skill.

Essa rotina costuma resolver o problema mais rapido do que reescrever o prompt cinco vezes.