# game-developer-scope

Esta rule é sempre ativa neste workspace.

## Domínio exclusivo

O agente `game-developer` é o ÚNICO autorizado a escrever, modificar ou evoluir qualquer
código de jogo neste workspace. Código de jogo inclui:
- Qualquer arquivo dentro de `repos/redacted-slug/`
- Game loop, física, colisão, input, rendering, assets procedurais
- Testes de jogabilidade e scripts de build/export de jogos

## Proibido para outros agentes

Os agentes `product-engineer`, `soft-engineer-agent` e `software-architect` NÃO devem
modificar arquivos em `repos/redacted-slug/` ou qualquer outro diretório de jogo.

Se receber uma tarefa que envolva código de jogo, responda:

```
[SCOPE ERROR] Código de jogo é domínio exclusivo do game-developer.
Use o agente game-developer para esta tarefa.
```

## O game-developer NÃO toca em

- Infraestrutura do VPS, Docker, CI/CD
- Pipelines de dados, APIs de negócio
- Dashboards, sistemas de autenticação
- Qualquer arquivo fora do domínio de jogos

## Fronteira de escopo

O critério é simples: se o arquivo vive em `repos/redacted-slug/` ou em um diretório de
projeto de jogo, é domínio do `game-developer`. Se vive fora, não é.
