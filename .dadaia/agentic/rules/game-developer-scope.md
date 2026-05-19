# game-developer-scope

Esta rule é sempre ativa neste workspace.

## Domínio Exclusivo de Jogos

Três agentes especializados têm autoridade exclusiva sobre todo o código de jogo.
Código de jogo inclui qualquer arquivo dentro de `repos/redacted-slug/`.

| Agente | Sub-domínio | O que escreve |
|---|---|---|
| `game-developer` | Lógica | C++, Blueprints (gameplay), IA, física, balística, mecânicas |
| `game-designer` | Design | Assets estáticos, materiais, mapas, áudio, scripts de pipeline |
| `game-tester` | Testes | Scripts de automação UE5, reports HTML com evidências |

## Proibido para Outros Agentes

Nenhum dos agentes abaixo deve modificar arquivos em `repos/redacted-slug/`:
`product-engineer`, `software-architect`, `software-engineer`, `frontend-engineer`,
`backend-engineer`, `qa-engineer`, `devops-engineer`.

Estes agentes podem **LER** arquivos de jogo para contexto, mas nunca escrever.

Se receber uma tarefa que envolva código de jogo, responda:

```
[SCOPE ERROR] Código de jogo é domínio exclusivo dos agentes game-developer,
game-designer e game-tester. Use o agente correto para esta tarefa.
```

## Fronteira de Escopo

O critério é simples: se o arquivo vive em `repos/redacted-slug/`, é domínio dos
agentes de jogo. Se vive fora, não é.

## Jogos Ativos no Workspace

| Jogo | Engine | Agentes responsáveis |
|---|---|---|
| `redacted-slug-trex` | Phaser.js 3.60 | game-developer, game-designer, game-tester |
| `redacted-slug` | Three.js r165 | game-developer, game-designer, game-tester |
| `redacted-slug-v2` | Unreal Engine 5 | game-developer, game-designer, game-tester |

## O Que Cada Agente NÃO Toca

**game-developer:** assets visuais, áudio, terreno, materiais, mapas, testes

**game-designer:** lógica de jogo, IA de inimigos, física de voo, balística, testes

**game-tester:** código de produção e assets — apenas scripts de teste e reports
